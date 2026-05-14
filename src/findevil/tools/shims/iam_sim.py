"""IAM simulator — disable_account / force_reset, both recorded locally.

Replace with real AD / Entra ID connector in production."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from findevil.transport.valkey import get_valkey
from findevil.tools.registry import register

from ._subprocess import first_target

IAM_LOG = Path("/opt/findevil/data/iam_sim.log")


async def _record(action: str, target: dict[str, Any]) -> dict[str, Any]:
    IAM_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts_ns": time.time_ns(), "action": action, "target": target}
    with IAM_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    vc = await get_valkey()
    c = await vc._connect()  # noqa: SLF001
    await c.lpush("iam:actions", json.dumps(entry))
    await c.ltrim("iam:actions", 0, 9999)
    return {"ok": True, **entry}


@register("iam.disable_account")
async def disable_account(commands: list[dict]) -> dict[str, Any]:
    return await _record("iam.disable_account", first_target(commands))


@register("iam.force_reset")
async def force_reset(commands: list[dict]) -> dict[str, Any]:
    return await _record("iam.force_reset", first_target(commands))
