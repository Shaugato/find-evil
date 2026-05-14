"""Suricata eve.json query shim."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_target

DEFAULT_EVE = Path("/var/log/suricata/eve.json")


@register("suricata.query")
async def query(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    needle = t.get("value") or t.get("ip") or t.get("domain")
    if not needle:
        return {"ok": False, "error": "missing target.value"}
    eve = Path(t.get("eve_json") or DEFAULT_EVE)
    if not eve.exists():
        return {"ok": False, "error": f"eve.json not found: {eve}"}
    out: list[dict] = []
    with eve.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if needle in line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
                if len(out) >= 200:
                    break
    return {"ok": True, "needle": needle, "matches": out, "n": len(out)}
