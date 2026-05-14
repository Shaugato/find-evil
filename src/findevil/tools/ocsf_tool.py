"""Public OCSF export helpers for ledger findings."""

from __future__ import annotations

from typing import Any

from findevil.ledger.interop import to_ocsf_detection_finding
from findevil.ledger.schema import LedgerEntry


def emit_ocsf_finding(entry: LedgerEntry) -> dict[str, Any]:
    """Emit an OCSF Detection Finding (class_uid 2004)."""
    return to_ocsf_detection_finding(entry)
