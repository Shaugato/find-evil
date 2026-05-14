"""SIFT / forensic tool shims (Part 12) exposed as MCP tools & CACAO actuators.

Each shim lives in its own module, registers with `findevil.tools.registry` on
import via `@register("name")`, and presents a uniform async signature:

    async def fn(commands: list[dict]) -> dict: ...

`commands` is the `CacaoStep.commands` list; most tools only read the first
command's `target` field. Each shim returns a structured result dict that CACAO
executor and MCP callers can ingest verbatim.

Import-all-at-once happens in `registry.bootstrap()` so new shims are auto-
registered without touching `__init__.py`.
"""

from .registry import bootstrap, register, registered, resolve

__all__ = ["bootstrap", "register", "registered", "resolve"]
