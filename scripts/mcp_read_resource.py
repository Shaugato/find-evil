"""Read an MCP resource URI from the live findevil blackboard."""

from __future__ import annotations

import asyncio
import sys

from fastmcp import Client

MCP_URL = "http://127.0.0.1:9310/mcp"


async def main() -> None:
    uri = sys.argv[1] if len(sys.argv) > 1 else "bb://ledger/tip"
    async with Client(MCP_URL) as client:
        payload = await client.read_resource(uri)
        for item in payload:
            print(getattr(item, "text", item))


if __name__ == "__main__":
    asyncio.run(main())
