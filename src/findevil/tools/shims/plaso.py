"""Plaso/log2timeline shim — produces a plaso storage file from an image/directory."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_target, run_cmd

PLASO_SCRIPT_DIR = Path("/opt/findevil/venv/lib/python3.12/site-packages/plaso/scripts")


def _tool_bin(name: str) -> str | None:
    return shutil.which(name) or (
        str(PLASO_SCRIPT_DIR / name) if (PLASO_SCRIPT_DIR / name).exists() else None
    )


def _tool_cmd(name: str) -> list[str]:
    path = _tool_bin(name)
    if path and Path(path).parent == PLASO_SCRIPT_DIR:
        return [sys.executable, path]
    return [path or name]


@register("plaso.version")
async def version(_commands: list[dict]) -> dict[str, Any]:
    if _tool_bin("log2timeline.py"):
        return await run_cmd([*_tool_cmd("log2timeline.py"), "--version"], timeout_s=20.0)
    try:
        import plaso  # type: ignore[import-not-found]
    except ImportError as e:
        return {"ok": False, "error": f"plaso unavailable: {e}"}
    return {
        "ok": True,
        "stdout": f"plaso module {getattr(plaso, '__version__', 'unknown')}\n",
        "stderr": "log2timeline.py not found in PATH",
        "cmd": ["python", "-c", "import plaso"],
    }


@register("plaso.extract")
async def extract(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    src = t.get("source") or t.get("value")
    if not src or not Path(src).exists():
        return {"ok": False, "error": f"source not found: {src}"}
    with tempfile.TemporaryDirectory() as td:
        storage = Path(td) / "plaso.plaso"
        r = await run_cmd(
            [
                *_tool_cmd("log2timeline.py"),
                "--status_view",
                "none",
                str(storage),
                src,
            ],
            timeout_s=1800.0,
        )
        r["storage"] = str(storage) if storage.exists() else None
        return r


@register("plaso.psort")
async def psort(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    storage = t.get("storage") or t.get("value")
    if not storage or not Path(storage).exists():
        return {"ok": False, "error": f"storage not found: {storage}"}
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out.jsonl"
        r = await run_cmd(
            [
                *_tool_cmd("psort.py"),
                "-o",
                "json_line",
                "-w",
                str(out),
                storage,
            ],
            timeout_s=600.0,
        )
        if r["ok"] and out.exists():
            head = out.read_text(errors="replace").splitlines()[:500]
            r["head"] = head
        return r
