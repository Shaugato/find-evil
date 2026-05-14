"""MFTECmd shim — Master File Table parser."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_target, run_cmd


@register("mftecmd.parse")
async def parse(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    mft = t.get("mft") or t.get("value")
    if not mft or not Path(mft).exists():
        return {"ok": False, "error": f"mft not found: {mft}"}
    with tempfile.TemporaryDirectory() as td:
        r = await run_cmd(
            ["MFTECmd", "-f", mft, "--csv", td, "--csvf", "mft.csv"],
            timeout_s=300.0,
        )
        csv = Path(td) / "mft.csv"
        if r["ok"] and csv.exists():
            head = csv.read_text(errors="replace").splitlines()[:500]
            r["csv_head"] = head
        return r
