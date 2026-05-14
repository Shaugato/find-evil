"""CACAO executor — verifies signature, dispatches actuators via MCP tools.

Blueprint Part 11.3. The executor:

  * Refuses any playbook that fails `verify_playbook` against the allow-listed
    public key (settings.ledger.cacao_pk_path).
  * Serializes execution per-instance (one instance_id at a time; parallelism is
    across instances, not steps).
  * Writes runtime state to `cacao:instance:{uuid}` in Valkey so the MCP
    `bb://cacao/instance/{uuid}` resource stays live.
  * On terminal state, appends an entry to the forensic ledger tagged
    `action=cacao_executed` with the canonical bytes + signature of the playbook.

Actuators are invoked through fastmcp.Client against the blackboard MCP server.
The server owns shim registration; the executor has no direct local shim path.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import msgspec

from findevil.config.settings import settings
from findevil.observability.logging import get_logger
from findevil.observability.metrics import MITIGATION_LATENCY
from findevil.transport.valkey import get_valkey
from findevil.transport.zmq_bus import SUBJ_MITIGATION, ZmqBus

from .schema import CacaoPlaybook, CacaoStep, verify_playbook

log = get_logger("findevil.cacao.executor")


class ExecutorError(Exception):
    pass


async def _set_state(uuid_: str, **fields) -> None:
    vc = await get_valkey()
    c = await vc._connect()  # noqa: SLF001
    mapping = {k: (json.dumps(v) if not isinstance(v, str) else v) for k, v in fields.items()}
    await c.hset(f"cacao:instance:{uuid_}", mapping=mapping)


async def _append_ledger(
    *,
    playbook: CacaoPlaybook,
    instance_id: str,
    status: str,
    steps_ran: list[str],
    error: Optional[str] = None,
) -> None:
    """Append a `cacao_executed` entry to the forensic ledger.

    The entry is a first-class LedgerEntry (Part 6) whose primary_artifact_key
    points at the CACAO instance, whose evidence_ref wraps the playbook id +
    signature fingerprint, and whose reasoning_trace records the executed step
    chain. Severity is derived from the terminal status so downstream consumers
    can filter on `severity=high` to find failed mitigations.
    """
    try:
        import blake3

        from findevil.ledger.schema import (
            ArtifactRef,
            ArtifactType,
            ReasoningMethod,
            ReasoningStep,
            Severity,
        )
        from findevil.ledger.writer import LedgerWriter
    except Exception:
        log.exception("ledger_writer_import_failed")
        return
    try:
        sig_fpr = (
            blake3.blake3(playbook.signature.encode()).hexdigest()
            if playbook.signature
            else "0" * 64
        )
        evidence = ArtifactRef(
            type=ArtifactType.PROCESS,
            uri=f"cacao://instance/{instance_id}",
            extra={
                "playbook_id": playbook.id,
                "playbook_name": playbook.name[:256],
                "signature_fpr": sig_fpr,
                "steps_ran": ",".join(steps_ran)[:4000],
                "status": status,
            },
        )
        reasoning_steps: list[ReasoningStep] = [
            ReasoningStep(
                step_index=0,
                claim=(
                    f"CACAO playbook {playbook.id} executed for instance "
                    f"{instance_id}: status={status}, steps={len(steps_ran)}"
                ),
                method=ReasoningMethod.HUMAN_ASSERTION,
                confidence=1.0 if status == "succeeded" else 0.5,
                params={"status": status, "error": (error or "")[:512]},
            )
        ]
        model_hash = blake3.blake3(b"findevil-cacao-executor").hexdigest()
        severity = Severity.HIGH if status != "succeeded" else Severity.INFORMATIONAL
        parent_ids: list[uuid.UUID] = []
        mitre: list[str] = []
        for ref in playbook.external_references:
            source = str(ref.get("source_name", ""))
            external_id = str(ref.get("external_id", ""))
            if source == "findevil-ledger":
                try:
                    parent_ids.append(uuid.UUID(external_id))
                except ValueError:
                    pass
            elif source == "MITRE ATT&CK" and external_id.startswith("T"):
                mitre.append(external_id)

        def _do_append() -> None:
            w = LedgerWriter(
                settings.ledger.sqlite_path,
                settings.ledger.ed25519_sk_path,
                settings.ledger.ed25519_pk_path,
            )
            try:
                w.append(
                    agent_id="cacao.executor",
                    agent_version="0.1.0",
                    agent_model_hash=model_hash,
                    host_id=settings.host_id,
                    evidence_refs=[evidence],
                    primary_artifact_key=f"cacao:instance:{instance_id}",
                    confidence=1.0 if status == "succeeded" else 0.5,
                    severity=severity,
                    reasoning_trace=reasoning_steps,
                    mitre=mitre,
                    chain_of_custody=parent_ids,
                )
            finally:
                w.close()

        # Writer is sync + uses a threading.Lock; run off-loop so we don't
        # block other CACAO instances sharing this event loop.
        await asyncio.to_thread(_do_append)
    except Exception:
        log.exception("ledger_append_failed", instance_id=instance_id)


def _mcp_url() -> str:
    return f"http://{settings.mcp.host}:{settings.mcp.port}{settings.mcp.path}"


async def _dispatch_step(step: CacaoStep, *, client) -> dict[str, Any]:
    """Invoke the actuator through MCP."""
    try:
        res = await asyncio.wait_for(
            client.call_tool(step.actuator, {"commands": step.commands}),
            timeout=step.timeout_s,
        )
    except Exception as exc:
        raise ExecutorError(f"MCP actuator failed: {step.actuator}: {exc}") from exc
    return {"actuator": step.actuator, "result": res}


async def execute_playbook(
    pb: CacaoPlaybook,
    *,
    expected_pk_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Verify + run a playbook. Returns {instance_id, status, steps_ran, errors}."""
    t0 = time.perf_counter_ns()
    pk_path = expected_pk_path or settings.ledger.cacao_pk_path
    expected_pk = pk_path.read_bytes() if pk_path.exists() else None

    if not verify_playbook(pb, expected_pk=expected_pk):
        raise ExecutorError("playbook signature verification failed")

    instance_id = uuid.uuid4().hex
    await _set_state(
        instance_id,
        playbook_id=pb.id,
        status="running",
        started_ns=str(time.time_ns()),
        step_cursor="0",
        errors=json.dumps([]),
    )

    try:
        from fastmcp import Client

        steps_ran: list[str] = []
        errors: list[str] = []
        cursor: str | None = pb.workflow_start
        async with Client(_mcp_url()) as client:
            while cursor:
                step = pb.workflow.get(cursor)
                if step is None:
                    errors.append(f"missing step id: {cursor}")
                    break
                if step.type == "end":
                    break
                steps_ran.append(step.id)
                try:
                    await _dispatch_step(step, client=client)
                    cursor = step.on_success or step.on_completion
                except Exception as e:
                    errors.append(f"{step.id}: {type(e).__name__}: {e}")
                    log.exception(
                        "cacao_step_failed",
                        instance_id=instance_id,
                        step=step.id,
                        actuator=step.actuator,
                    )
                    cursor = step.on_failure
                await _set_state(instance_id, step_cursor=str(len(steps_ran)))

        final_status = "succeeded" if not errors else "failed"
        await _set_state(
            instance_id,
            status=final_status,
            finished_ns=str(time.time_ns()),
            errors=json.dumps(errors),
        )
        await _append_ledger(
            playbook=pb,
            instance_id=instance_id,
            status=final_status,
            steps_ran=steps_ran,
            error=errors[0] if errors else None,
        )

        # fire the mitigation broadcast
        try:
            bus = ZmqBus.default()
            sock = bus.pub(SUBJ_MITIGATION)
            sock.send(
                msgspec.json.encode(
                    {
                        "instance_id": instance_id,
                        "playbook_id": pb.id,
                        "status": final_status,
                        "steps_ran": steps_ran,
                        "emitted_ns": time.time_ns(),
                    }
                )
            )
            sock.close(linger=0)
        except Exception:
            log.exception("mitigation_pub_failed", instance_id=instance_id)

        MITIGATION_LATENCY.observe((time.perf_counter_ns() - t0) / 1e9)
        return {
            "instance_id": instance_id,
            "status": final_status,
            "steps_ran": steps_ran,
            "errors": errors,
        }
    except Exception as e:
        log.exception("cacao_executor_fatal", instance_id=instance_id)
        await _set_state(
            instance_id,
            status="failed",
            finished_ns=str(time.time_ns()),
            errors=json.dumps([f"fatal: {type(e).__name__}: {e}"]),
        )
        raise


# ---- daemon entrypoint: pull consensus frames + invoke factory+executor -----


async def _daemon_loop() -> None:
    """Consume consensus frames and execute action==mitigate playbooks."""
    from findevil.cacao.factory import build_playbook
    from findevil.transport.zmq_bus import SUBJ_CONSENSUS

    bus = ZmqBus.default()
    sock = bus.sub(SUBJ_CONSENSUS)
    log.info("cacao.executor.start")
    try:
        while True:
            raw = await sock.recv()
            try:
                frame = msgspec.json.decode(raw)
            except Exception:
                log.exception("frame_decode_failed")
                continue
            if frame.get("action") != "mitigate":
                continue
            # derive target from pher_key
            target = _target_from_pher_key(frame.get("pher_key", ""))
            if target is None:
                continue
            pb = build_playbook(consensus_frame=frame, target=target)
            try:
                await execute_playbook(pb)
            except Exception:
                log.exception("execute_playbook_failed", playbook_id=pb.id)
    finally:
        try:
            sock.close(linger=0)
        except Exception:
            pass


def _target_from_pher_key(key: str) -> dict[str, Any] | None:
    if key.startswith("pher:ip:"):
        return {"type": "ipv4-addr", "value": key[len("pher:ip:") :]}
    if key.startswith("pher:hash:"):
        return {"type": "file", "hashes": {"SHA-256": key[len("pher:hash:") :]}}
    if key.startswith("pher:domain:"):
        return {"type": "domain-name", "value": key[len("pher:domain:") :]}
    if key.startswith("pher:proc:"):
        _, host_pid = key.split("pher:proc:", 1)
        host, pid = host_pid.split(":", 1)
        return {"type": "process", "host": host, "pid": int(pid)}
    return None


def run() -> None:  # entrypoint: `findevil-cacao`
    os.umask(0o077)
    from findevil.observability.logging import configure_logging
    from findevil.observability.metrics import start_metrics_server
    from findevil.observability.tracing import init_tracing

    configure_logging(service="findevil-cacao")
    init_tracing(service_name="findevil-cacao")
    start_metrics_server(settings.observability.prometheus_port + 5)
    asyncio.run(_daemon_loop())


if __name__ == "__main__":  # pragma: no cover
    run()
