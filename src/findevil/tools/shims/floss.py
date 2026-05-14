"""flare-floss shim — extract obfuscated strings from PEs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_target, run_cmd


@register("floss.extract")
async def extract(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    path = t.get("path") or t.get("value")
    if not path or not Path(path).exists():
        return {"ok": False, "error": f"file not found: {path}"}
    r = await run_cmd(
        ["floss", "--json", path],
        timeout_s=600.0,
    )
    if r["ok"]:
        import json as _json

        try:
            r["parsed"] = _json.loads(r["stdout"])
        except ValueError:
            r["parsed"] = None
    return r
