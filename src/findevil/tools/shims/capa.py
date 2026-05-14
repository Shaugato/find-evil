"""flare-capa shim — in-process extract of ATT&CK + MBC capabilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_target, run_cmd


@register("capa.analyze")
async def analyze(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    path = t.get("path") or t.get("value")
    if not path or not Path(path).exists():
        return {"ok": False, "error": f"file not found: {path}"}
    # capa ships as a CLI; prefer that over the Python API for ABI stability.
    r = await run_cmd(
        ["capa", "--json", path],
        timeout_s=180.0,
    )
    if r["ok"]:
        import json as _json

        try:
            r["parsed"] = _json.loads(r["stdout"])
        except ValueError:
            r["parsed"] = None
    return r
