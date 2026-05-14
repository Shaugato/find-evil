"""Public STIX export helpers for ledger findings."""

from __future__ import annotations

from typing import Any

from findevil.ledger.interop import to_stix_bundle
from findevil.ledger.schema import LedgerEntry


def emit_stix_bundle(entry: LedgerEntry) -> dict[str, Any]:
    """Emit a STIX 2.1 bundle for a validated ledger entry."""
    return to_stix_bundle(entry)
