"""Volatility 3 shims (MCP tools: volatility.malfind / ldrmodules / hollowfind / handles).

Per blueprint Part 12.1, the primary use is H3 pivots spawned on memory-region
evidence. Each shim takes a `target.image` (path to memory capture) and returns
a JSON-friendly summary of the plugin output.
"""

from __future__ import annotations

import json
import shutil
from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_target, run_cmd


def _vol_bin() -> str:
    return "vol3" if shutil.which("vol3") else "vol"


async def _vol(plugin: str, image: str, extra: list[str] | None = None) -> dict[str, Any]:
    argv = [_vol_bin(), "-f", image, "-r", "json", plugin] + (extra or [])
    r = await run_cmd(argv, timeout_s=180.0)
    if r["ok"]:
        try:
            r["parsed"] = json.loads(r["stdout"] or "[]")
        except ValueError:
            r["parsed"] = None
    return r


@register("volatility.version")
async def version(_commands: list[dict]) -> dict[str, Any]:
    binary = _vol_bin()
    primary = await run_cmd([binary, "--version"], timeout_s=20.0)
    if primary["ok"]:
        return primary
    fallback = await run_cmd([binary, "-h"], timeout_s=20.0)
    fallback["version_probe"] = f"{binary} --version unsupported; fell back to {binary} -h"
    return fallback


@register("volatility.malfind")
async def malfind(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    img = t.get("image") or t.get("value")
    if not img:
        return {"ok": False, "error": "missing target.image"}
    return await _vol("windows.malfind.Malfind", img)


@register("volatility.ldrmodules")
async def ldrmodules(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    img = t.get("image") or t.get("value")
    if not img:
        return {"ok": False, "error": "missing target.image"}
    return await _vol("windows.ldrmodules.LdrModules", img)


@register("volatility.hollowfind")
async def hollowfind(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    img = t.get("image") or t.get("value")
    if not img:
        return {"ok": False, "error": "missing target.image"}
    # hollowfind is in community plugins; fall back to pslist+vadinfo if absent
    primary = await _vol("windows.hollowfind.Hollowfind", img)
    if primary["exit_code"] == 127:
        return await _vol("windows.pslist.PsList", img)
    return primary


@register("volatility.handles")
async def handles(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    img = t.get("image") or t.get("value")
    pid = t.get("pid")
    if not img:
        return {"ok": False, "error": "missing target.image"}
    extra = ["--pid", str(pid)] if pid is not None else []
    return await _vol("windows.handles.Handles", img, extra=extra)
