"""EDR simulator — for lab use, records intent in Valkey so dashboards observe the action.

Real EDR integrations replace this module's registrations with the vendor API
calls. The lab build uses an append-only JSON log to preserve an auditable trail
even without a real EDR connector.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from findevil.transport.valkey import get_valkey
from findevil.tools.registry import register

from ._subprocess import first_target

EDR_LOG = Path("/opt/findevil/data/edr_sim.log")


async def _record(action: str, target: dict[str, Any]) -> dict[str, Any]:
    EDR_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts_ns": time.time_ns(), "action": action, "target": target}
    with EDR_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    vc = await get_valkey()
    c = await vc._connect()  # noqa: SLF001
    await c.lpush("edr:actions", json.dumps(entry))
    await c.ltrim("edr:actions", 0, 9999)
    return {"ok": True, **entry}


@register("edr.kill_process")
async def kill_process(commands: list[dict]) -> dict[str, Any]:
    return await _record("edr.kill_process", first_target(commands))


@register("edr.network_isolate")
async def network_isolate(commands: list[dict]) -> dict[str, Any]:
    return await _record("edr.network_isolate", first_target(commands))


@register("edr.acquire_memory")
async def acquire_memory(commands: list[dict]) -> dict[str, Any]:
    return await _record("edr.acquire_memory", first_target(commands))


@register("edr.block_domain")
async def block_domain(commands: list[dict]) -> dict[str, Any]:
    return await _record("edr.block_domain", first_target(commands))


@register("edr.block_url")
async def block_url(commands: list[dict]) -> dict[str, Any]:
    return await _record("edr.block_url", first_target(commands))


@register("edr.sinkhole")
async def sinkhole(commands: list[dict]) -> dict[str, Any]:
    return await _record("edr.sinkhole", first_target(commands))


@register("edr.snapshot_disk")
async def snapshot_disk(commands: list[dict]) -> dict[str, Any]:
    return await _record("edr.snapshot_disk", first_target(commands))


@register("edr.remove_persistence")
async def remove_persistence(commands: list[dict]) -> dict[str, Any]:
    return await _record("edr.remove_persistence", first_target(commands))


@register("edr.delete_scheduled_task")
async def delete_scheduled_task(commands: list[dict]) -> dict[str, Any]:
    return await _record("edr.delete_scheduled_task", first_target(commands))


@register("edr.reenable_defender")
async def reenable_defender(commands: list[dict]) -> dict[str, Any]:
    return await _record("edr.reenable_defender", first_target(commands))
