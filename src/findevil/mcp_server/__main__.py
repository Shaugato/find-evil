"""Module entry point so a standard MCP client can spawn the server with
``python -m findevil.mcp_server`` (stdio transport by default).

    python -m findevil.mcp_server            # stdio (for Claude Desktop / Code)
    python -m findevil.mcp_server --http     # HTTP service (same as `findevil mcp`)

Both reuse the single ``build_server()`` definition — one typed-tool catalog, one
guardrail (no execute_shell).
"""
from __future__ import annotations

import sys

from findevil.mcp_server.server import run, run_stdio

if __name__ == "__main__":
    if "--http" in sys.argv[1:]:
        run()
    else:
        run_stdio()
