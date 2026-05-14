"""Ghidra headless shim — runs an analysis script on an import."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from findevil.config.settings import settings
from findevil.tools.registry import register

from ._subprocess import first_target, run_cmd

GHIDRA_HEADLESS = Path("/opt/ghidra/support/analyzeHeadless")


@register("ghidra.analyze")
async def analyze(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    path = t.get("path") or t.get("value")
    if not path or not Path(path).exists():
        return {"ok": False, "error": f"file not found: {path}"}
    proj_dir = Path(t.get("project_dir", "/opt/findevil/data/ghidra"))
    proj_dir.mkdir(parents=True, exist_ok=True)
    script = t.get("script")  # optional post-script
    if not GHIDRA_HEADLESS.exists():
        return {"ok": False, "error": f"ghidra headless not found: {GHIDRA_HEADLESS}"}
    argv = [
        str(GHIDRA_HEADLESS),
        str(proj_dir),
        "findevil",
        "-import",
        path,
        "-deleteProject",
        "-overwrite",
    ]
    if script:
        argv += ["-postScript", script]
    return await run_cmd(argv, timeout_s=900.0)
