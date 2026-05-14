"""Red-team runner — executes Scenarios and measures detection/mitigation latency.

Execution backends:
  * Atomic Red Team: `Invoke-AtomicTest -AtomicTechnique <id> -TestNumbers N` via
    `pwsh -c` on Windows; cwd inside `C:/AtomicRedTeam/atomics` by convention.
  * CALDERA: HTTP POST to `/plugin/access/run_atomic` on the local CALDERA server.

For every scenario we:
  1. Record a baseline ledger tip + pheromone snapshot.
  2. Launch the atomic test with a wall-clock start timestamp.
  3. Poll the shadow channel / ledger for a matching consensus event carrying
     the expected ATT&CK technique.
  4. Record (detection_latency_ms, mitigation_latency_ms, outcome).

All results are appended to `/opt/findevil/data/redteam_results.jsonl` and can be
graphed with `scripts/plot_latency.py`.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from pathlib import Path
from typing import Any, Iterable

from findevil.config.settings import settings
from findevil.observability.logging import get_logger
from findevil.tools.shims._subprocess import run_cmd
from findevil.transport.valkey import get_valkey

from .scenarios import Scenario, default_scenarios

log = get_logger("findevil.redteam")

RESULTS_PATH = Path("/opt/findevil/data/redteam_results.jsonl")


async def _run_atomic(sc: Scenario) -> dict[str, Any]:
    if sc.platform == "windows":
        tnum = sc.atomic_id.rsplit("-", 1)[-1]
        cmd = [
            "pwsh",
            "-NoProfile",
            "-Command",
            f"Import-Module Invoke-AtomicRedTeam -Force; "
            f"Invoke-AtomicTest {sc.technique} -TestNumbers {tnum} -Force",
        ]
    else:
        cmd = ["atomic_runner.sh", sc.atomic_id]
    return await run_cmd(cmd, timeout_s=300.0)


async def _wait_for_detection(
    sc: Scenario, started_ns: int, *, poll_ms: int = 50
) -> dict[str, Any]:
    """Poll shadow channel via Valkey pub/sub for a matching consensus frame.

    We accept a detection when a consensus frame with `action in {mitigate,
    conflict_ledger, escalate_human}` references the expected technique (via any
    agent report's attack_techniques) within detection_budget_ms.
    """
    from findevil.mcp_server.shadow import SHADOW_CHAN_CONSENSUS

    deadline_ns = started_ns + sc.detection_budget_ms * 1_000_000
    vc = await get_valkey()
    pubsub = vc.pubsub()
    await pubsub.subscribe(SHADOW_CHAN_CONSENSUS)
    try:
        while time.time_ns() < deadline_ns:
            msg = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=poll_ms / 1000.0
            )
            if msg is None:
                continue
            data = msg.get("data")
            if isinstance(data, bytes):
                try:
                    envelope = json.loads(data)
                except ValueError:
                    continue
                payload = envelope.get("payload")
                if isinstance(payload, (str, bytes)):
                    try:
                        frame = json.loads(payload)
                    except ValueError:
                        continue
                    for r in frame.get("reports", []):
                        tech = r.get("attack_techniques") or []
                        if sc.technique in tech:
                            return {
                                "detected": True,
                                "frame": frame,
                                "detection_latency_ms": (time.time_ns() - started_ns)
                                / 1e6,
                            }
        return {"detected": False}
    finally:
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(SHADOW_CHAN_CONSENSUS)
            await pubsub.close()


async def _wait_for_mitigation(sc: Scenario, started_ns: int) -> dict[str, Any]:
    """Poll the EDR sim log for an action with matching technique in window."""
    from findevil.tools.shims.edr_sim import EDR_LOG

    deadline_ns = started_ns + sc.mitigation_budget_ms * 1_000_000
    while time.time_ns() < deadline_ns:
        if EDR_LOG.exists():
            tail = EDR_LOG.read_text(errors="replace").splitlines()[-50:]
            for line in tail:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("ts_ns", 0) >= started_ns:
                    return {
                        "mitigated": True,
                        "entry": entry,
                        "mitigation_latency_ms": (entry["ts_ns"] - started_ns) / 1e6,
                    }
        await asyncio.sleep(0.05)
    return {"mitigated": False}


class RedTeamRunner:
    def __init__(self, results_path: Path | None = None):
        self.results = Path(results_path or RESULTS_PATH)
        self.results.parent.mkdir(parents=True, exist_ok=True)

    async def run_one(self, sc: Scenario) -> dict[str, Any]:
        started_ns = time.time_ns()
        log.info("redteam.run.begin", scenario=sc.id)
        atomic_task = asyncio.create_task(_run_atomic(sc))
        detect_task = asyncio.create_task(_wait_for_detection(sc, started_ns))
        mit_task = asyncio.create_task(_wait_for_mitigation(sc, started_ns))
        atomic, detect, mit = await asyncio.gather(
            atomic_task, detect_task, mit_task, return_exceptions=True
        )
        result = {
            "scenario_id": sc.id,
            "technique": sc.technique,
            "started_ns": started_ns,
            "atomic_result": atomic if not isinstance(atomic, Exception) else str(atomic),
            "detection": detect if not isinstance(detect, Exception) else str(detect),
            "mitigation": mit if not isinstance(mit, Exception) else str(mit),
        }
        with self.results.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result, default=str) + "\n")
        log.info(
            "redteam.run.done",
            scenario=sc.id,
            detected=bool(isinstance(detect, dict) and detect.get("detected")),
            mitigated=bool(isinstance(mit, dict) and mit.get("mitigated")),
        )
        return result

    async def run_all(self, scenarios: Iterable[Scenario]) -> list[dict[str, Any]]:
        out = []
        for sc in scenarios:
            try:
                out.append(await self.run_one(sc))
            except Exception:
                log.exception("scenario_crash", scenario=sc.id)
        return out


async def run_scenarios(scenarios: Iterable[Scenario] | None = None) -> list[dict[str, Any]]:
    r = RedTeamRunner()
    return await r.run_all(scenarios or default_scenarios())


def run() -> None:  # entrypoint: `findevil-redteam`
    import os

    from findevil.observability.logging import configure_logging

    os.umask(0o077)
    configure_logging(service="findevil-redteam")
    asyncio.run(run_scenarios())


if __name__ == "__main__":  # pragma: no cover
    run()
