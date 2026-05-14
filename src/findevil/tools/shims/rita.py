"""RITA beacon-analysis shim — runs `rita show-beacons` and parses output."""

from __future__ import annotations

import json
from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_target, run_cmd


@register("rita.analyze")
async def analyze(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    db = t.get("database") or t.get("value")
    if not db:
        return {"ok": False, "error": "missing target.database"}
    r = await run_cmd(
        ["rita", "show-beacons", db, "--delimiter", ","],
        timeout_s=60.0,
    )
    lines = [ln for ln in r["stdout"].splitlines() if ln.strip()][:200]
    r["parsed"] = lines
    return r
