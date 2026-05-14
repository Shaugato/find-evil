"""The Sleuth Kit shims — fls/icat wrappers."""

from __future__ import annotations

from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_target, run_cmd


@register("tsk.fls_version")
async def fls_version(_commands: list[dict]) -> dict[str, Any]:
    return await run_cmd(["fls", "-V"], timeout_s=20.0)


@register("tsk.version")
async def version(commands: list[dict]) -> dict[str, Any]:
    return await fls_version(commands)


@register("tsk.fls")
async def fls(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    image = t.get("image") or t.get("value")
    if not image:
        return {"ok": False, "error": "missing target.image"}
    offset = t.get("offset")
    argv = ["fls", "-r", "-p"]
    if offset is not None:
        argv += ["-o", str(offset)]
    argv.append(image)
    return await run_cmd(argv, timeout_s=120.0)


@register("tsk.icat")
async def icat(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    image = t.get("image")
    inode = t.get("inode")
    if not image or inode is None:
        return {"ok": False, "error": "missing target.image or target.inode"}
    return await run_cmd(["icat", image, str(inode)], timeout_s=60.0)
