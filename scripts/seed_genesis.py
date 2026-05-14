#!/usr/bin/env python3
"""Seed a genesis entry into the forensic ledger.

Every ledger chain must begin with an entry whose prev_hash is null and whose
payload self-describes the instance (host, build version, platform, timestamp).
Chain verification uses it as the unambiguous origin anchor (see
`findevil.ledger.verify.verify_chain`).

Idempotent: if the ledger already has at least one row, the script exits 0 without
touching anything. The Writer API is synchronous — we avoid asyncio here for the
same reason `scripts/keygen.py` does.
"""

from __future__ import annotations

import platform
import socket
import sqlite3
import sys

import blake3

from findevil.config.settings import settings
from findevil.ledger.schema import (
    ArtifactRef,
    ArtifactType,
    ReasoningMethod,
    ReasoningStep,
    Severity,
)
from findevil.ledger.writer import LedgerWriter


def _already_seeded(sqlite_path) -> bool:
    if not sqlite_path.exists():
        return False
    try:
        conn = sqlite3.connect(str(sqlite_path))
        try:
            row = conn.execute("SELECT COUNT(*) FROM ledger").fetchone()
            return bool(row and row[0] > 0)
        finally:
            conn.close()
    except sqlite3.DatabaseError:
        return False


def main() -> int:
    if _already_seeded(settings.ledger.sqlite_path):
        print("ledger already has entries; skipping genesis seed")
        return 0

    w = LedgerWriter(
        settings.ledger.sqlite_path,
        settings.ledger.ed25519_sk_path,
        settings.ledger.ed25519_pk_path,
    )
    try:
        host = socket.gethostname()
        # Genesis evidence_ref points at the host itself — the ledger's origin subject.
        # Schema demands min_length=1 on evidence_refs; a user-account ref needs no hash.
        evidence = ArtifactRef(
            type=ArtifactType.USER,
            uri=f"host://{host}",
            extra={"platform": platform.platform()[:256]},
        )
        reasoning = ReasoningStep(
            step_index=0,
            claim=f"genesis anchor for host_id={settings.host_id}",
            method=ReasoningMethod.HUMAN_ASSERTION,
            confidence=1.0,
        )
        # agent_model_hash is a 64-char blake3 hex; seed deterministically from the
        # build identity so verifiers can recover it.
        model_hash = blake3.blake3(
            f"findevil-genesis:{settings.host_id}".encode()
        ).hexdigest()

        entry = w.append(
            agent_id="genesis",
            agent_version="0.1.0",
            agent_model_hash=model_hash,
            host_id=settings.host_id,
            evidence_refs=[evidence],
            primary_artifact_key=f"host:{host}",
            confidence=1.0,
            severity=Severity.INFORMATIONAL,
            reasoning_trace=[reasoning],
        )
        print(f"genesis entry written: finding_id={entry.finding_id}")
        return 0
    finally:
        w.close()


if __name__ == "__main__":
    sys.exit(main())
