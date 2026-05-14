"""RegRipper shim — runs `rip.pl -r hive -p plugin`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_target, run_cmd


@register("regripper.run")
async def run(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    hive = t.get("hive") or t.get("value")
    plugin = t.get("plugin", "soft_run")
    if not hive or not Path(hive).exists():
        return {"ok": False, "error": f"hive not found: {hive}"}
    return await run_cmd(["rip.pl", "-r", hive, "-p", plugin], timeout_s=60.0)
