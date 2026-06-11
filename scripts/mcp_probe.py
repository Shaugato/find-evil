"""Quick MCP probe: call named tools against the live findevil MCP server.

Usage:
    python scripts/mcp_probe.py tool1 tool2 ... [--args '{"tool1": {...}}']

Defaults to probing zeek.version / plaso.version / volatility.version /
tsk.version / tshark.version when no tools are given.
"""

from __future__ import annotations

import asyncio
import json
import sys

from fastmcp import Client

MCP_URL = "http://127.0.0.1:9310/mcp"

DEFAULT_TOOLS = [
    "zeek.version",
    "plaso.version",
    "volatility.version",
    "tsk.version",
    "tshark.version",
]


def _result_payload(result: object) -> object:
    for attr in ("data", "structured_content"):
        value = getattr(result, attr, None)
        if value is not None:
            return value
    content = getattr(result, "content", None)
    if content:
        return [getattr(c, "text", str(c)) for c in content]
    return str(result)


async def main() -> None:
    argv = sys.argv[1:]
    tool_args: dict[str, dict] = {}
    if "--args" in argv:
        idx = argv.index("--args")
        tool_args = json.loads(argv[idx + 1])
        argv = argv[:idx] + argv[idx + 2 :]
    tools = argv or DEFAULT_TOOLS

    async with Client(MCP_URL) as client:
        listed = {t.name for t in await client.list_tools()}
        print(f"server exposes {len(listed)} tools")
        for tool in tools:
            if tool not in listed:
                print(f"{tool}: NOT REGISTERED on server")
                continue
            try:
                result = await client.call_tool(tool, tool_args.get(tool, {}))
                payload = _result_payload(result)
                text = json.dumps(payload, default=str)[:500]
                print(f"{tool}: {text}")
            except Exception as exc:  # noqa: BLE001 - probe reports all failures
                print(f"{tool}: ERROR {exc}")


if __name__ == "__main__":
    asyncio.run(main())
