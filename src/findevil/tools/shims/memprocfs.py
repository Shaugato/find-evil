"""MemProcFS shim — mount live memory as a filesystem via `memprocfs`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_target, run_cmd


@register("memprocfs.mount")
async def mount(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    image = t.get("image") or t.get("value")
    mnt = t.get("mount_point") or "/mnt/memprocfs"
    if not image or not Path(image).exists():
        return {"ok": False, "error": f"image not found: {image}"}
    Path(mnt).mkdir(parents=True, exist_ok=True)
    return await run_cmd(
        ["memprocfs", "-device", image, "-mount", mnt, "-norefresh"],
        timeout_s=60.0,
    )
