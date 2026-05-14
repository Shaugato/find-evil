"""TShark shims — packet capture helpers exposed through MCP."""

from __future__ import annotations

from typing import Any

from findevil.tools.registry import register

from ._subprocess import first_target, run_cmd


@register("tshark.version")
async def version(_commands: list[dict]) -> dict[str, Any]:
    return await run_cmd(["tshark", "--version"], timeout_s=20.0)


@register("tshark.summary")
async def summary(commands: list[dict]) -> dict[str, Any]:
    t = first_target(commands)
    pcap = t.get("pcap") or t.get("path") or t.get("value")
    if not pcap:
        return {"ok": False, "error": "missing target.pcap"}
    return await run_cmd(
        ["tshark", "-r", str(pcap), "-T", "fields", "-e", "frame.time_epoch", "-e", "ip.src", "-e", "ip.dst"],
        timeout_s=60.0,
    )
