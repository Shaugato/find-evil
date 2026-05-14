"""Bytewax streaming dataflow (blueprint Part 8.5).

Topology:

   NATS find.raw  ──▶ parse ──▶ key-by pher-key ──▶ tumbling 1s window
                                                          │
                                                          ▼
                                             threshold evaluator → AgentReport
                                                          │
                                                          ▼
                                                D-S fuse + τ deposit
                                                          │
                           ┌──────────────────────────────┼──────────────┐
                           ▼                              ▼              ▼
                  ledger.append() if              ZMQ SUBJ_CONSENSUS   fractal.spawn
                  Bel >= θ_finding or             (dashboard live)     if action=='escalate_human'
                  action is mitigation,                                or bel in pivot band
                  conflict, or escalation

This module defines `build_flow()` returning a `bytewax.dataflow.Dataflow` plus a
`run()` entrypoint used by systemd's `findevil-ingest.service`.

It is not called from the hot sub-ms decision path; that path is pure pheromone
reads on MCP resources. This flow is the *writer* side that keeps pheromones current.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import anyio
import blake3
import msgspec

from findevil.config.settings import settings
from findevil.ledger.events import append_consensus_frame, append_raw_record
from findevil.observability.logging import get_logger
from findevil.observability.metrics import (
    CONSENSUS_ACTIONS,
    CONSENSUS_CONFLICT_K,
    CONSENSUS_DURATION,
    DECISION_LATENCY,
    PHEROMONE_GAUGE,
)
from findevil.swarm.evaluator import evaluate as evaluate_action
from findevil.transport.valkey import (
    get_valkey,
    pher_domain_key,
    pher_hash_key,
    pher_ip_key,
    pher_process_key,
)
from findevil.transport.nats_bus import (
    SUBJ_CONSENSUS_FINDING,
    SUBJ_LEDGER_DUPE,
    SUBJ_LEDGER_LATE,
    SUBJ_RAW_MALFORMED,
)
from findevil.transport.zmq_bus import SUBJ_CONSENSUS, SUBJ_FRACTAL_SPAWN, ZmqBus

from .events import ParsedEvent, RawEvent
from .indicators import indicator_tuple
from .parsers import parse
from .threshold import evaluate as threshold_evaluate

log = get_logger("findevil.ingest")


ALLOWED_LATENESS_NS = {
    "edr": 250_000_000,
    "sysmon": 250_000_000,
    "zeek": 500_000_000,
    "suricata": 500_000_000,
    "yara": 2_000_000_000,
    "syslog": 2_000_000_000,
    "volatility": 180_000_000_000,
}

DEDUPE_TTL_S = int(os.environ.get("FINDEVIL_INGEST_DEDUPE_TTL_S", "300"))


# ---------- pher-key helpers -------------------------------------------------


def _pher_key_for(tup: tuple) -> str | None:
    ip, domain, sha, proc = tup
    if ip:
        return pher_ip_key(ip)
    if domain:
        return pher_domain_key(domain)
    if sha:
        return pher_hash_key(sha)
    if proc:
        if proc.startswith("__raw__:"):
            return f"pher:{proc.removeprefix('__raw__:')}"
        if ":" in proc:
            host, pid = proc.split(":", 1)
            try:
                return pher_process_key(host, int(pid))
            except ValueError:
                pass
        return f"pher:proc:{proc}"
    return None


def _pher_kind(tup: tuple) -> str:
    ip, domain, sha, proc = tup
    if ip:
        return "ip"
    if domain:
        return "domain"
    if sha:
        return "hash"
    if proc:
        if proc.startswith("__raw__:"):
            return proc.removeprefix("__raw__:").split("://", 1)[0]
        return "process"
    return "unknown"


def _raw_event_from_payload(raw_bytes: bytes) -> RawEvent:
    """Decode either the internal RawEvent envelope or flat validation JSON."""
    payload = msgspec.json.decode(raw_bytes)
    if not isinstance(payload, dict):
        raise TypeError("raw payload must be a JSON object")

    # Internal producer envelope: source/sensor/host_id/body.
    if "body" in payload:
        return RawEvent(
            source=str(payload.get("source") or "unknown"),
            sensor=str(payload.get("sensor") or payload.get("source") or "unknown"),
            event_time_ns=payload.get("event_time_ns"),
            ingest_time_ns=payload.get("ingest_time_ns"),
            ts_ns=payload.get("ts_ns"),
            host_id=str(payload.get("host_id") or settings.host_id),
            body=dict(payload.get("body") or {}),
            event_id=payload.get("event_id"),
        )

    # White-hat validation contract: flat source event with indicator_key.
    return RawEvent(
        source=str(payload.get("source") or "synthetic"),
        sensor=str(payload.get("sensor") or payload.get("source") or "synthetic"),
        event_time_ns=payload.get("event_time_ns"),
        ingest_time_ns=payload.get("ingest_time_ns") or time.monotonic_ns(),
        ts_ns=payload.get("ts_ns"),
        host_id=str(payload.get("host_id") or settings.host_id),
        body=payload,
        event_id=payload.get("event_id"),
    )


def consensus_frame_to_pivot_spawn(frame: dict[str, Any]) -> dict[str, Any]:
    """Convert a consensus frame into the Watcher's PivotSpawn envelope."""
    from findevil.fractal.agent import PivotSpawn
    from findevil.fractal.scoped_prompt import build_scoped_prompt, make_exhibits

    reports = list(frame.get("reports") or [])
    seed_technique: str | None = None
    for report in reports:
        for technique in report.get("attack_techniques") or []:
            if isinstance(technique, str) and technique.startswith("T"):
                seed_technique = technique
                break
        if seed_technique:
            break

    exhibits = make_exhibits(
        [
            {
                "exhibit_kind": "consensus_frame",
                "pher_key": frame.get("pher_key"),
                "action": frame.get("action"),
                "belief_evil": frame.get("belief_evil"),
                "plausibility_evil": frame.get("plausibility_evil"),
                "uncertainty": frame.get("uncertainty"),
                "conflict_K": frame.get("conflict_K"),
                "sensor_diversity": frame.get("sensor_diversity"),
            },
            *[
                {
                    "exhibit_kind": "agent_report",
                    "agent_id": report.get("agent_id"),
                    "sensor": report.get("sensor"),
                    "confidence": report.get("confidence"),
                    "attack_techniques": report.get("attack_techniques") or [],
                }
                for report in reports[:8]
            ],
        ]
    )
    spawn = PivotSpawn(
        spawn_id=uuid.uuid4().hex,
        seed_technique=seed_technique,
        scoped_prompt=build_scoped_prompt(frame, exhibits, seed_technique),
        exhibits=exhibits,
        # The implementation guide targets GPU-backed local inference, but the
        # WSL lab often runs llama.cpp on CPU. Keep the configured value as a
        # lower bound while preventing every pivot from expiring before the
        # first local model response.
        ttl_ms=max(settings.fractal.ttl_ms, 45_000),
        depth=0,
    )
    return msgspec.to_builtins(spawn)


def raw_event_id(raw_evt: RawEvent) -> str | None:
    """Return the producer-supplied idempotency key, if one exists.

    Event type fields such as Sysmon EventID are intentionally ignored because
    they are categories, not unique event identities.
    """
    candidates = [
        raw_evt.event_id,
        raw_evt.body.get("event_id"),
        raw_evt.body.get("event_guid"),
        raw_evt.body.get("EventGuid"),
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        value = str(candidate).strip()
        if value:
            return value
    return None


def dedupe_key(raw_evt: RawEvent, event_id: str) -> str:
    digest = blake3.blake3(event_id.encode("utf-8")).hexdigest()
    return f"ingest:seen:{raw_evt.source}:{raw_evt.sensor}:{digest}"


async def is_duplicate_raw_event(raw_evt: RawEvent, *, ttl_s: int = DEDUPE_TTL_S) -> bool:
    event_id = raw_event_id(raw_evt)
    if event_id is None:
        return False
    vc = await get_valkey()
    c = await vc._connect()  # noqa: SLF001 - idempotency sits at the ingest boundary
    inserted = await c.set(dedupe_key(raw_evt, event_id), b"1", ex=ttl_s, nx=True)
    return not bool(inserted)


# ---------- window processor ------------------------------------------------


class _WindowState(msgspec.Struct):
    """Per-pher-key window state: list of ParsedEvents within the 1s window."""

    events: list[ParsedEvent]


async def _process_window(
    tup: tuple, events: list[ParsedEvent], *, bus: ZmqBus
) -> dict[str, Any] | None:
    """Evaluate one window, deposit on pheromone, emit consensus frame."""
    if not events:
        return None

    pher_key = _pher_key_for(tup)
    if pher_key is None:
        return None

    vc = await get_valkey()
    t0 = time.perf_counter_ns()

    # Build agent reports for just this pher-key
    groups = threshold_evaluate(events)
    reports = groups.get(tup, [])
    if not reports:
        return None

    # Read current tau + sensor_diversity BEFORE deposit
    state = await vc.hgetall(pher_key)
    cur_tau = 0.0
    try:
        cur_tau = float(state.get(b"tau", b"0"))
    except ValueError:
        cur_tau = 0.0
    sensor_diversity = len({r.sensor for r in reports})

    # D-S fuse + action selection
    t_fuse_start = time.perf_counter_ns()
    action = evaluate_action(
        reports, pheromone_tau=cur_tau, sensor_diversity=sensor_diversity
    )
    CONSENSUS_DURATION.observe((time.perf_counter_ns() - t_fuse_start) / 1e9)
    CONSENSUS_ACTIONS.labels(action=action["action"]).inc()
    CONSENSUS_CONFLICT_K.observe(action["conflict_K"])

    # Deposit on Valkey — tau delta proportional to (belief - uncertainty)
    tau_delta = max(0.01, action["belief_evil"] - 0.5 * action["uncertainty"])
    report_sensors = sorted({r.sensor for r in reports if r.sensor})
    sensor_tag = reports[0].sensor or "mixed"
    new_tau = await vc.deposit(
        pher_key,
        tau_delta=tau_delta,
        bel=action["belief_evil"],
        pl=action["plausibility_evil"],
        K=action["conflict_K"],
        sensor=sensor_tag,
        tau_max=settings.swarm.tau_max,
        now_ns=time.time_ns(),
    )
    try:
        c = await vc._connect()  # noqa: SLF001 - keep the Lua hot path narrow
        if report_sensors:
            await c.sadd(f"{pher_key}:sensors", *report_sensors)
        await c.hset(
            pher_key,
            mapping={
                "sensor_diversity": str(sensor_diversity),
                "sensor": ",".join(report_sensors),
            },
        )
    except Exception:
        log.exception("pheromone_sensor_metadata_update_failed", pher_key=pher_key)

    kind = _pher_kind(tup)
    PHEROMONE_GAUGE.labels(kind=kind).set(new_tau)

    techniques_by_sensor: dict[str, list[str]] = {}
    for ev in events:
        if ev.attack_techniques:
            cur = techniques_by_sensor.setdefault(ev.sensor, [])
            for t in ev.attack_techniques:
                if t not in cur:
                    cur.append(t)

    # Emit on ZMQ SUBJ_CONSENSUS for dashboard + shadow publisher
    frame = {
        "pher_key": pher_key,
        "kind": kind,
        "tau": new_tau,
        "sensor_diversity": sensor_diversity,
        "reports": [
            {
                "agent_id": r.agent_id,
                "confidence": r.confidence,
                "reliability": r.reliability,
                "sensor": r.sensor,
                "declared_ignorance": r.declared_ignorance,
                "attack_techniques": techniques_by_sensor.get(r.sensor, []),
            }
            for r in reports
        ],
        **action,
    }
    DECISION_LATENCY.observe((time.perf_counter_ns() - t0) / 1e9)

    should_append_ledger = (
        action["action"] in ("mitigate", "conflict_ledger", "escalate_human")
        or action["belief_evil"] >= settings.swarm.theta_finding
    )
    if should_append_ledger:
        try:
            written_ids = await asyncio.to_thread(append_consensus_frame, frame, events=events)
            if written_ids:
                frame["ledger_finding_ids"] = [str(fid) for fid in written_ids]
                frame["parent_finding_id"] = str(written_ids[-1])
        except Exception:
            log.exception("ledger_consensus_append_failed", pher_key=pher_key)

    return frame


# ---------- bytewax dataflow builder ----------------------------------------


def build_flow():
    """Return a Bytewax Dataflow. Lazy import — Bytewax is a heavy dep."""
    from bytewax.dataflow import Dataflow
    from bytewax.operators import windowing as window
    from bytewax import operators as op

    flow = Dataflow("findevil-ingest")

    # Sources: ZMQ hot firehose + NATS durable raw stream.
    from .nats_source import NatsRawSource
    from .zmq_source import ZmqFirehoseSource

    raw_zmq = op.input("zmq-firehose", flow, ZmqFirehoseSource())
    raw_nats = op.input("nats-find-raw", flow, NatsRawSource(subject="find.>"))
    raw = op.merge("merge-raw", raw_zmq, raw_nats)
    process_loop = asyncio.new_event_loop()

    def _decode(raw_bytes: bytes) -> tuple[str, RawEvent | dict[str, Any]]:
        try:
            raw_evt = _raw_event_from_payload(raw_bytes)
        except Exception as exc:
            payload = {
                "subject": SUBJ_RAW_MALFORMED,
                "reason": f"decode_failed:{type(exc).__name__}",
                "raw_blake3": blake3.blake3(raw_bytes).hexdigest(),
                "raw_prefix_hex": raw_bytes[:256].hex(),
                "ingest_time_ns": time.monotonic_ns(),
            }
            try:
                append_raw_record(
                    subject=SUBJ_RAW_MALFORMED,
                    reason=payload["reason"],
                    payload=raw_bytes,
                    source="malformed",
                )
            except Exception:
                log.exception("ledger_malformed_append_failed")
            return ("malformed", payload)

        event_time = raw_evt.timestamp_ns
        if event_time is None:
            payload = {
                "subject": SUBJ_RAW_MALFORMED,
                "reason": "missing_event_time_ns",
                "raw": msgspec.to_builtins(raw_evt),
                "ingest_time_ns": time.monotonic_ns(),
            }
            try:
                append_raw_record(
                    subject=SUBJ_RAW_MALFORMED,
                    reason="missing_event_time_ns",
                    payload=payload,
                    source=raw_evt.source or "unknown",
                )
            except Exception:
                log.exception("ledger_malformed_append_failed")
            return ("malformed", payload)

        ingest_time = raw_evt.ingest_time_ns or time.monotonic_ns()
        raw_evt = RawEvent(
            source=raw_evt.source,
            sensor=raw_evt.sensor,
            event_time_ns=int(event_time),
            ingest_time_ns=int(ingest_time),
            ts_ns=raw_evt.ts_ns,
            host_id=raw_evt.host_id,
            body=raw_evt.body,
            event_id=raw_event_id(raw_evt),
        )
        allowed = ALLOWED_LATENESS_NS.get(raw_evt.source, 2_000_000_000)
        if time.time_ns() - int(event_time) > allowed:
            subject = f"{SUBJ_LEDGER_LATE}.{raw_evt.source or 'unknown'}"
            payload = {
                "subject": subject,
                "reason": "allowed_lateness_exceeded",
                "allowed_lateness_ns": allowed,
                "raw": msgspec.to_builtins(raw_evt),
            }
            try:
                append_raw_record(
                    subject=subject,
                    reason="allowed_lateness_exceeded",
                    payload=payload,
                    source=raw_evt.source or "unknown",
                )
            except Exception:
                log.exception("ledger_late_append_failed")
            return ("late", payload)
        try:
            is_duplicate = process_loop.run_until_complete(is_duplicate_raw_event(raw_evt))
        except Exception:
            log.exception("dedupe_check_failed", source=raw_evt.source, sensor=raw_evt.sensor)
            is_duplicate = False
        if is_duplicate:
            subject = f"{SUBJ_LEDGER_DUPE}.{raw_evt.source or 'unknown'}"
            payload = {
                "subject": subject,
                "reason": "duplicate_event_id",
                "raw": msgspec.to_builtins(raw_evt),
            }
            try:
                append_raw_record(
                    subject=subject,
                    reason="duplicate_event_id",
                    payload=payload,
                    source=raw_evt.source or "unknown",
                )
            except Exception:
                log.exception("ledger_dupe_append_failed")
            return ("dupe", payload)
        return ("ok", raw_evt)

    decoded = op.map("decode", raw, _decode)

    malformed = op.filter_map(
        "malformed-events",
        decoded,
        lambda item: item[1] if item[0] == "malformed" else None,
    )
    late = op.filter_map(
        "late-events",
        decoded,
        lambda item: item[1] if item[0] == "late" else None,
    )
    dupe = op.filter_map(
        "dupe-events",
        decoded,
        lambda item: item[1] if item[0] == "dupe" else None,
    )
    good = op.filter_map(
        "decoded-events",
        decoded,
        lambda item: item[1] if item[0] == "ok" else None,
    )

    def _parse(raw_evt: RawEvent) -> list[ParsedEvent]:
        return parse(raw_evt)

    parsed = op.flat_map("parse", good, _parse)

    def _keyer(ev: ParsedEvent) -> list[tuple[tuple, ParsedEvent]]:
        out: list[tuple[tuple, ParsedEvent]] = []
        direct = indicator_tuple(ev.indicator_key)
        if direct is not None:
            out.append((direct, ev))
            return out
        if ev.ip:
            out.append(((ev.ip, None, None, None), ev))
        if ev.domain:
            out.append(((None, ev.domain, None, None), ev))
        if ev.sha256:
            out.append(((None, None, ev.sha256, None), ev))
        if ev.pid is not None and ev.host_id:
            out.append(((None, None, None, f"{ev.host_id}:{ev.pid}"), ev))
        return out

    keyed = op.flat_map("key-for-pher", parsed, _keyer)

    # 1-second tumbling windows keyed by pher-tuple
    def _string_key(kv: tuple[tuple, ParsedEvent]) -> tuple[str, ParsedEvent]:
        k, v = kv
        return (repr(k), v)

    stringified = op.map("stringify-key", keyed, _string_key)

    windowed = window.collect_window(
        "1s-window",
        stringified,
        clock=window.EventClock(
            ts_getter=lambda ev: datetime.fromtimestamp(ev.ts_ns / 1e9, tz=UTC),
            # Slow evidence is routed by source-specific lateness checks before
            # this point. Keep the hot consensus window responsive.
            wait_for_system_duration=timedelta(seconds=2),
        ),
        windower=window.TumblingWindower(
            length=timedelta(seconds=1),
            align_to=datetime.fromtimestamp(0, tz=UTC),
        ),
    )

    def _evaluate_window(kv):
        key_repr, (_meta, events) = kv
        import ast

        try:
            key_tuple = ast.literal_eval(key_repr)
        except Exception:
            return None
        # Keep async clients bound to a long-lived loop. Creating and closing a
        # loop per window leaves cached Valkey transports attached to dead loops.
        return process_loop.run_until_complete(
            _process_window(key_tuple, list(events), bus=ZmqBus.default())
        )

    evaluated = op.filter_map("evaluate-window", windowed.down, _evaluate_window)

    # Sink: publish consensus and pheromone frames on ZMQ
    from .sinks import NatsJsonSink, ZmqConsensusSink, ZmqPherSink

    op.output("consensus-zmq", evaluated, ZmqConsensusSink())
    op.output("pher-zmq", evaluated, ZmqPherSink())
    op.output(
        "consensus-nats",
        evaluated,
        NatsJsonSink(f"{SUBJ_CONSENSUS_FINDING}.swarm"),
    )
    op.output("malformed-nats", malformed, NatsJsonSink(SUBJ_RAW_MALFORMED))
    op.output("late-nats", late, NatsJsonSink(f"{SUBJ_LEDGER_LATE}.ingest"))
    op.output("dupe-nats", dupe, NatsJsonSink(f"{SUBJ_LEDGER_DUPE}.ingest"))

    # Also fan out to fractal.spawn PUSH socket for escalations + high-bel pivots
    from .sinks import FractalSpawnSink

    def _should_spawn(frame: dict | None) -> bool:
        if frame is None:
            return False
        act = frame.get("action")
        bel = frame.get("belief_evil", 0.0)
        return act in ("escalate_human", "conflict_ledger") or bel >= settings.fractal.pivot_bar

    spawn_candidates = op.filter("needs-fractal", evaluated, _should_spawn)
    spawn = op.map("consensus-to-pivot-spawn", spawn_candidates, consensus_frame_to_pivot_spawn)
    op.output("fractal-spawn", spawn, FractalSpawnSink())

    return flow


def run() -> None:  # entrypoint: `findevil-ingest`
    os.umask(0o077)
    from findevil.observability.logging import configure_logging
    from findevil.observability.metrics import start_metrics_server
    from findevil.observability.tracing import init_tracing

    configure_logging(service="findevil-ingest")
    init_tracing(service_name="findevil-ingest")
    start_metrics_server(settings.observability.prometheus_port + 2)

    from bytewax.testing import run_main

    run_main(build_flow())


if __name__ == "__main__":  # pragma: no cover
    run()
