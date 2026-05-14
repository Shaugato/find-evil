"""EvtxECmd (Eric Zimmerman) shim — parses .evtx files to JSON."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_target, run_cmd


@register("evtxecmd.parse")
async def parse(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    p = t.get("path") or t.get("value")
    if not p or not Path(p).exists():
        return {"ok": False, "error": f"file not found: {p}"}
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "evtx.json"
        r = await run_cmd(
            ["EvtxECmd", "-f", p, "--json", str(out), "--jsonf", "evtx.json"],
            timeout_s=300.0,
        )
        if r["ok"] and out.exists():
            import json as _json

            try:
                r["parsed"] = [
                    _json.loads(ln) for ln in out.read_text(errors="replace").splitlines() if ln
                ]
            except ValueError:
                r["parsed"] = None
        return r
