"""Ledger MCP tool — exposes verify/recent/count via CACAO actuator identifiers."""

from __future__ import annotations

from typing import Any

from findevil.config.settings import settings
from findevil.ledger.reader import LedgerReader
from findevil.ledger.verify import verify_chain
from findevil.tools.registry import register

from ._subprocess import first_target


@register("ledger.verify")
async def verify(commands: list[dict]) -> dict[str, Any]:
    pk = settings.ledger.ed25519_pk_path.read_bytes()
    ok, tainted = verify_chain(settings.ledger.sqlite_path, pk)
    return {"ok": ok, "tainted_seqs": tainted}


@register("ledger.recent")
async def recent(commands: list[dict]) -> dict[str, Any]:
    n = int(first_target(commands).get("n", 50))
    r = LedgerReader()
    try:
        return {"ok": True, "entries": await r.recent(n)}
    finally:
        r.close()


@register("ledger.tip")
async def tip(commands: list[dict]) -> dict[str, Any]:
    r = LedgerReader()
    try:
        return {"ok": True, "tip": await r.tip()}
    finally:
        r.close()


@register("findevil.end")
async def end(commands: list[dict]) -> dict[str, Any]:
    return {"ok": True, "step": "end"}


@register("analyst.review")
async def analyst_review(commands: list[dict]) -> dict[str, Any]:
    # No-op: queued for human review via the dashboard queue key
    from findevil.transport.valkey import get_valkey
    import json, time

    vc = await get_valkey()
    c = await vc._connect()  # noqa: SLF001
    await c.lpush(
        "analyst:review_queue",
        json.dumps({"ts_ns": time.time_ns(), "commands": commands}),
    )
    await c.ltrim("analyst:review_queue", 0, 999)
    return {"ok": True, "queued": True}
