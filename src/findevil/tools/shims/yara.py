"""YARA shims — scan, quarantine, block_hash.

`yara.scan` uses the `yara-python` library (in-process) so we can return
structured matches with per-rule metadata. `yara.quarantine` is a policy shim
that copies the file to the quarantine directory and records its SHA-256. The
real "block" enforcement happens through the EDR integration; here we only write
to the blackboard so the EDR daemon picks it up.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from findevil.config.settings import settings
from findevil.transport.valkey import get_valkey
from findevil.tools.registry import register

from ._subprocess import first_target, run_cmd

QUARANTINE_DIR = Path("/opt/findevil/data/quarantine")
RULES_DIR = Path("/opt/findevil/data/yara-rules")


@register("yara.version")
async def version(_commands: list[dict]) -> dict[str, Any]:
    return await run_cmd(["yara", "--version"], timeout_s=20.0)


@register("yara.scan")
async def scan(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    path = t.get("path") or t.get("value")
    if not path or not Path(path).exists():
        return {"ok": False, "error": f"file not found: {path}"}
    try:
        import yara  # lazy import; heavy C extension
    except ImportError as e:
        return {"ok": False, "error": f"yara-python unavailable: {e}"}
    try:
        rules_globs = [str(p) for p in RULES_DIR.rglob("*.yar*") if p.is_file()]
        if not rules_globs:
            return {"ok": True, "matches": [], "note": "no rules installed"}
        filepaths = {Path(p).stem: p for p in rules_globs}
        rules = yara.compile(filepaths=filepaths)
        matches = rules.match(path)
        out = [
            {
                "rule": m.rule,
                "namespace": m.namespace,
                "tags": list(m.tags),
                "meta": dict(m.meta),
                "strings": [
                    {
                        "identifier": s.identifier,
                        "offsets": [i.offset for i in s.instances][:8],
                    }
                    for s in m.strings
                ],
            }
            for m in matches
        ]
        return {"ok": True, "matches": out}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


@register("yara.quarantine_file")
async def quarantine_file(commands: list[dict]) -> dict[str, Any]:
    return await _quarantine_common(commands)


@register("yara.quarantine")
async def quarantine(commands: list[dict]) -> dict[str, Any]:
    return await _quarantine_common(commands)


async def _quarantine_common(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    src = t.get("path") or t.get("value")
    if not src or not Path(src).exists():
        return {"ok": False, "error": f"file not found: {src}"}
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(Path(src).read_bytes()).hexdigest()
    dst = QUARANTINE_DIR / f"{h}.bin"
    shutil.copy2(src, dst)
    return {"ok": True, "quarantine_path": str(dst), "sha256": h}


@register("yara.block_hash")
async def block_hash(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    sha = None
    if isinstance(t.get("hashes"), dict):
        sha = t["hashes"].get("SHA-256") or t["hashes"].get("SHA256")
    sha = (sha or t.get("sha256") or "").lower()
    if len(sha) != 64:
        return {"ok": False, "error": "invalid sha256"}
    vc = await get_valkey()
    c = await vc._connect()  # noqa: SLF001
    await c.sadd("blocklist:sha256", sha)
    return {"ok": True, "blocked_sha256": sha}
