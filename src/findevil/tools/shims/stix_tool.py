"""STIX 2.1 bundle builder — used by narrator/evaluator for export."""

from __future__ import annotations

from typing import Any

from findevil.ledger.interop import to_stix_bundle
from findevil.ledger.reader import LedgerReader
from findevil.tools.registry import register

from ._subprocess import first_target


@register("stix.bundle")
async def bundle(commands: list[dict]) -> dict[str, Any]:
    seq = int(first_target(commands).get("seq", -1))
    r = LedgerReader()
    try:
        rows = await r.recent(1 if seq < 0 else seq + 1)
        if not rows:
            return {"ok": False, "error": "no ledger entries"}
        entry = rows[0]["entry"] if seq < 0 else next(
            (x["entry"] for x in rows if x["seq"] == seq), None
        )
        if entry is None:
            return {"ok": False, "error": f"seq {seq} not found"}
        return {"ok": True, "bundle": to_stix_bundle(entry)}
    finally:
        r.close()
