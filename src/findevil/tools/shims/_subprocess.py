"""Shared subprocess helper for tool shims.

Wraps an async subprocess call with a wall-clock timeout and captures
stdout/stderr + exit code. Never raises; always returns a structured dict.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Any


async def run_cmd(
    argv: list[str],
    *,
    timeout_s: float = 60.0,
    stdin: bytes | None = None,
    cwd: str | None = None,
) -> dict[str, Any]:
    env = os.environ.copy()
    cache_root = Path(env.get("FINDEVIL_TOOL_CACHE_DIR", "/opt/findevil/data/tool-cache"))
    try:
        cache_root.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    env.setdefault("XDG_CACHE_HOME", str(cache_root))
    env.setdefault("HOME", "/opt/findevil/data")
    exe = shutil.which(argv[0])
    if exe is None:
        venv_exe = Path(sys.executable).with_name(argv[0])
        if venv_exe.exists():
            exe = str(venv_exe)
    if exe is None:
        return {
            "ok": False,
            "exit_code": 127,
            "stdout": "",
            "stderr": f"{argv[0]} not found in PATH",
            "cmd": argv,
        }
    try:
        proc = await asyncio.create_subprocess_exec(
            exe,
            *argv[1:],
            stdin=asyncio.subprocess.PIPE if stdin else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )
    except Exception as e:
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"{type(e).__name__}: {e}",
            "cmd": argv,
        }
    try:
        out, err = await asyncio.wait_for(
            proc.communicate(input=stdin), timeout=timeout_s
        )
    except asyncio.TimeoutError:
        proc.kill()
        return {
            "ok": False,
            "exit_code": -9,
            "stdout": "",
            "stderr": f"timeout after {timeout_s}s",
            "cmd": argv,
        }
    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": out.decode(errors="replace"),
        "stderr": err.decode(errors="replace"),
        "cmd": argv,
    }


def first_target(commands: list[dict]) -> dict:
    """Extract the first command's `target` dict, or {} if not present."""
    if not commands:
        return {}
    c0 = commands[0] or {}
    return c0.get("target", {}) or {}


def first_arg(commands: list[dict], key: str, default=None):
    if not commands:
        return default
    return commands[0].get(key, default)
