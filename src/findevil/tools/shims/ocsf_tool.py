"""OCSF Detection Finding builder — class_uid=2004."""

from __future__ import annotations

from typing import Any

from findevil.ledger.interop import to_ocsf_detection_finding
from findevil.ledger.reader import LedgerReader
from findevil.ledger.schema import LedgerEntry
from findevil.tools.registry import register

from ._subprocess import first_target


@register("ocsf.finding")
async def finding(commands: list[dict]) -> dict[str, Any]:
    seq = int(first_target(commands).get("seq", -1))
    r = LedgerReader()
    try:
        rows = await r.recent(max(1, seq + 1 if seq >= 0 else 1))
        entry = rows[0]["entry"] if seq < 0 else next(
            (x["entry"] for x in rows if x["seq"] == seq), None
        )
        if entry is None:
            return {"ok": False, "error": f"seq {seq} not found"}
        # Reader rows are plain dicts; validate to the schema model so the
        # live emission path matches what the interop layer expects.
        model = LedgerEntry.model_validate(entry)
        return {"ok": True, "ocsf": to_ocsf_detection_finding(model)}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        r.close()
