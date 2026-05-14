"""Zeek shims — zeek.query, zeek.x509_extract.

`zeek.query` runs a zeek-cut / awk equivalent over the host's live zeek logs
under `/nsm/zeek/current`. For test environments we fall back to the configured
`zeek.logs_dir` setting.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_target, run_cmd

DEFAULT_LOG_DIR = Path("/nsm/zeek/current")
ZEEK_FALLBACK = Path("/opt/zeek/bin/zeek")


def _zeek_bin() -> str:
    return shutil.which("zeek") or (str(ZEEK_FALLBACK) if ZEEK_FALLBACK.exists() else "zeek")


@register("zeek.version")
async def version(_commands: list[dict]) -> dict[str, Any]:
    return await run_cmd([_zeek_bin(), "--version"], timeout_s=20.0)


@register("zeek.query")
async def query(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    ip = t.get("value") or t.get("ip")
    if not ip:
        return {"ok": False, "error": "missing target.value (ip)"}
    log_dir = Path(t.get("logs_dir") or DEFAULT_LOG_DIR)
    if not log_dir.exists():
        return {"ok": False, "error": f"zeek log dir not found: {log_dir}"}
    # zeek-cut is the canonical helper; return up to 100 matches
    r = await run_cmd(
        [
            "bash",
            "-lc",
            f"grep -F '{ip}' {log_dir}/conn.log | head -n 100 || true",
        ],
        timeout_s=20.0,
    )
    lines = [ln for ln in r["stdout"].splitlines() if ln.strip()]
    return {"ok": True, "ip": ip, "lines": lines, "n": len(lines)}


@register("zeek.x509_extract")
async def x509_extract(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    fp = t.get("cert_path") or t.get("value")
    if not fp or not Path(fp).exists():
        return {"ok": False, "error": f"cert not found: {fp}"}
    r = await run_cmd(
        [
            "openssl",
            "x509",
            "-in",
            fp,
            "-noout",
            "-issuer",
            "-subject",
            "-dates",
            "-fingerprint",
            "-sha256",
        ],
        timeout_s=10.0,
    )
    parsed = {}
    for ln in r["stdout"].splitlines():
        if "=" in ln:
            k, _, v = ln.partition("=")
            parsed[k.strip().lower()] = v.strip()
    r["parsed"] = parsed
    return r
