"""Ledger append + chain verify round-trip.

Part 6.5 invariant: five sequential appends, each independently validated by the
Pydantic LedgerEntry schema, must form a chain whose prev_hash links, BLAKE3
entry hashes, and Ed25519 signatures all round-trip through `verify_chain`.
"""

from __future__ import annotations

import os
from pathlib import Path

import blake3


def _make_entry_kwargs(i: int) -> dict:
    """Build the minimum schema-valid append() kwargs for a synthetic event."""
    from findevil.ledger.schema import (
        ArtifactRef,
        ArtifactType,
        ReasoningMethod,
        ReasoningStep,
        Severity,
    )

    evidence = ArtifactRef(
        type=ArtifactType.PROCESS,
        uri=f"proc://test-host/{1000 + i}",
        extra={"name": "unit-test.exe"},
    )
    reasoning = ReasoningStep(
        step_index=0,
        claim=f"synthetic-finding-{i}",
        method=ReasoningMethod.BEHAVIORAL_ML,
        confidence=0.6 + 0.05 * i,
    )
    return dict(
        agent_id="test.agent",
        agent_version="0.1.0",
        agent_model_hash=blake3.blake3(f"unit-test-model-{i}".encode()).hexdigest(),
        host_id="test-host",
        evidence_refs=[evidence],
        primary_artifact_key=f"proc:test-host:{1000 + i}",
        confidence=0.6 + 0.05 * i,
        severity=Severity.LOW,
        reasoning_trace=[reasoning],
    )


def test_ledger_chain_roundtrip(ed25519_keys):
    """Append N entries through the real Writer and ensure verify_chain() is clean."""
    from findevil.ledger.verify import verify_chain
    from findevil.ledger.writer import LedgerWriter

    _, pk = ed25519_keys
    sqlite_path = Path(os.environ["FINDEVIL_LEDGER__SQLITE_PATH"])
    sk_path = Path(os.environ["FINDEVIL_LEDGER__ED25519_SK_PATH"])
    pk_path = Path(os.environ["FINDEVIL_LEDGER__ED25519_PK_PATH"])
    # Ensure a fresh ledger each run — other tests may share the session path.
    if sqlite_path.exists():
        sqlite_path.unlink()

    w = LedgerWriter(sqlite_path, sk_path, pk_path)
    try:
        entries = [w.append(**_make_entry_kwargs(i)) for i in range(5)]
    finally:
        w.close()

    ok, tainted = verify_chain(sqlite_path, pk)
    assert ok, f"chain invalid; tainted={tainted}"
    assert tainted == []
    assert len({e.finding_id for e in entries}) == 5


def test_ledger_prev_hash_linkage(ed25519_keys):
    """Each entry's prev_hash must equal the previous row's BLAKE3 entry_hash."""
    import sqlite3

    from findevil.ledger.writer import LedgerWriter

    sqlite_path = Path(os.environ["FINDEVIL_LEDGER__SQLITE_PATH"])
    sk_path = Path(os.environ["FINDEVIL_LEDGER__ED25519_SK_PATH"])
    pk_path = Path(os.environ["FINDEVIL_LEDGER__ED25519_PK_PATH"])
    if sqlite_path.exists():
        sqlite_path.unlink()

    w = LedgerWriter(sqlite_path, sk_path, pk_path)
    try:
        for i in range(3):
            w.append(**_make_entry_kwargs(i))
    finally:
        w.close()

    conn = sqlite3.connect(str(sqlite_path))
    try:
        rows = conn.execute(
            "SELECT seq, entry_hash, prev_hash FROM ledger ORDER BY seq"
        ).fetchall()
    finally:
        conn.close()

    assert rows[0][2] is None, "first entry must have null prev_hash"
    for (_, prev_entry_hash, _), (_, _, this_prev) in zip(rows, rows[1:]):
        assert this_prev == prev_entry_hash
