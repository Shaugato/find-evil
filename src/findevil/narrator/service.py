"""Narrator daemon — consumes conflict-ledger/escalate-human events and emits debates.

Subscribes to `consensus.v1` ZMQ PUB. For every frame with action in
{`conflict_ledger`, `escalate_human`} (or an optional `force_debate=True`), we:

  1. Assemble an exhibit list from the frame + recent ledger entries that share
     the same `pher_key`.
  2. Run the LangGraph debate under a wall-clock budget.
  3. Publish the verdict on NATS `ledger.v1.finding.narrator` so the
     ledger-writer service persists it.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Any

import anyio
import blake3
import msgspec

from findevil.config.settings import settings
from findevil.inference.facade import InferenceFacade
from findevil.ledger.events import artifact_for_pher_key
from findevil.ledger.schema import ReasoningMethod, ReasoningStep, Severity
from findevil.ledger.writer import LedgerWriter
from findevil.observability.logging import get_logger
from findevil.transport.nats_bus import SUBJ_LEDGER_FINDING, get_nats
from findevil.transport.zmq_bus import SUBJ_CONSENSUS, ZmqBus

from .graph import NarratorGraph

log = get_logger("findevil.narrator")


class ConsensusFrame(msgspec.Struct, kw_only=True):
    pher_key: str
    kind: str
    tau: float
    sensor_diversity: int
    reports: list[dict]
    action: str
    belief_evil: float
    plausibility_evil: float
    uncertainty: float
    conflict_K: float
    ledger_finding_ids: list[str] = msgspec.field(default_factory=list)
    parent_finding_id: str | None = None


async def _exhibits_for_frame(frame: ConsensusFrame) -> list[dict[str, Any]]:
    """Build the exhibit list from the consensus frame + recent ledger entries.

    Keeps exhibit size bounded (<= 12) so the model's ctx isn't overwhelmed.
    """
    from findevil.fractal.scoped_prompt import make_exhibits

    base = [
        {
            "exhibit_kind": "pheromone_state",
            "pher_key": frame.pher_key,
            "tau": frame.tau,
            "belief_evil": frame.belief_evil,
            "plausibility_evil": frame.plausibility_evil,
            "uncertainty": frame.uncertainty,
            "conflict_K": frame.conflict_K,
            "sensor_diversity": frame.sensor_diversity,
        }
    ]
    for r in frame.reports[:8]:
        base.append({"exhibit_kind": "agent_report", **r})
    # TODO(future): enrich from ledger.recent() when LedgerReader is wired.
    return make_exhibits(base)


async def _handle_frame(
    frame: ConsensusFrame, ng: NarratorGraph, debate_budget_s: float = 300.0
) -> None:
    exhibits = await _exhibits_for_frame(frame)
    try:
        with anyio.move_on_after(debate_budget_s) as scope:
            result = await ng.debate(exhibits=exhibits, swap_judge=False)
        if scope.cancelled_caught:
            log.warning("narrator_budget_exceeded", pher_key=frame.pher_key)
            return
    except Exception:
        log.exception("narrator_debate_failed", pher_key=frame.pher_key)
        return

    payload = {
        "finding_kind": "narrator_verdict",
        "pher_key": frame.pher_key,
        "emitted_ns": time.time_ns(),
        "consensus_frame": msgspec.to_builtins(frame),
        "debate": result,
    }
    try:
        bus = await get_nats()
        await bus.publish(f"{SUBJ_LEDGER_FINDING}.narrator", payload)
    except Exception:
        log.exception("narrator_publish_failed", pher_key=frame.pher_key)

    try:
        await asyncio.to_thread(_append_narrator_ledger, frame, result)
    except Exception:
        log.exception("narrator_ledger_append_failed", pher_key=frame.pher_key)


def _append_narrator_ledger(frame: ConsensusFrame, result: dict[str, Any]) -> None:
    verdict = result.get("verdict") or {}
    if not verdict:
        return
    score = float(verdict.get("score", 0.0))
    guilty = bool(verdict.get("guilty", False))
    parent_ids: list[uuid.UUID] = []
    for candidate in [frame.parent_finding_id, *frame.ledger_finding_ids[-1:]]:
        if not candidate:
            continue
        try:
            parent_ids.append(uuid.UUID(str(candidate)))
            break
        except ValueError:
            continue
    writer = LedgerWriter(
        settings.ledger.sqlite_path,
        settings.ledger.ed25519_sk_path,
        settings.ledger.ed25519_pk_path,
    )
    try:
        writer.append(
            agent_id="narrator.judge",
            agent_version="0.1.0",
            agent_model_hash=blake3.blake3(settings.inference.model_name.encode()).hexdigest(),
            host_id=settings.host_id,
            evidence_refs=[artifact_for_pher_key(frame.pher_key)],
            primary_artifact_key=frame.pher_key,
            confidence=score,
            severity=Severity.MEDIUM if guilty else Severity.INFORMATIONAL,
            reasoning_trace=[
                ReasoningStep(
                    step_index=0,
                    claim=str(verdict.get("rationale", "Narrator verdict")),
                    method=ReasoningMethod.LLM_INFERENCE,
                    confidence=max(0.0, min(1.0, score)),
                    params={
                        "winning_argument": str(verdict.get("winning_argument", "")),
                        "guilty": str(guilty),
                    },
                )
            ],
            chain_of_custody=parent_ids,
        )
    finally:
        writer.close()


async def run_forever(
    *,
    debate_budget_s: float = 300.0,
    max_concurrency: int = 1,
) -> None:
    bus = ZmqBus.default()
    sock = bus.sub(SUBJ_CONSENSUS)
    facade = InferenceFacade()
    ng = NarratorGraph(facade=facade)
    sem = asyncio.Semaphore(max_concurrency)
    log.info("narrator.start")
    tasks: set[asyncio.Task] = set()
    try:
        while True:
            raw = await sock.recv()
            try:
                frame = msgspec.json.decode(raw, type=ConsensusFrame)
            except Exception:
                log.exception("frame_decode_failed")
                continue
            if frame.action not in ("conflict_ledger", "escalate_human"):
                continue

            async def _guarded(f=frame):
                async with sem:
                    await _handle_frame(
                        f, ng, debate_budget_s=debate_budget_s
                    )

            t = asyncio.create_task(_guarded())
            tasks.add(t)
            t.add_done_callback(tasks.discard)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        for t in tasks:
            t.cancel()
        try:
            sock.close(linger=0)
        except Exception:
            pass
        try:
            await facade.close()
        except Exception:
            pass


def run() -> None:  # entrypoint: `findevil-narrator`
    os.umask(0o077)
    from findevil.observability.logging import configure_logging
    from findevil.observability.metrics import start_metrics_server
    from findevil.observability.tracing import init_tracing

    configure_logging(service="findevil-narrator")
    init_tracing(service_name="findevil-narrator")
    start_metrics_server(settings.observability.prometheus_port + 4)
    budget_s = float(os.environ.get("FINDEVIL_NARRATOR_BUDGET_S", "300"))
    max_concurrency = int(os.environ.get("FINDEVIL_NARRATOR_CONC", "1"))
    asyncio.run(
        run_forever(debate_budget_s=budget_s, max_concurrency=max_concurrency)
    )


if __name__ == "__main__":  # pragma: no cover
    run()
