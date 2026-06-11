"""Ledger writer — Pydantic validate -> Ed25519 sign -> BLAKE3 chain -> SQLite WAL append.

Per blueprint Part 6.4, p50 ≈ 800 µs target on the P620:
  validate 120 µs + canonicalize 70 µs + Ed25519 40 µs + BLAKE3 5 µs + WAL INSERT 600 µs.
"""

from __future__ import annotations

import base64
import datetime as dt
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Iterable, Optional

import blake3
from nacl.signing import SigningKey

from findevil.observability.metrics import (
    LEDGER_APPEND_SECONDS,
    LEDGER_APPENDS,
    LEDGER_CHAIN_LENGTH,
)

from .schema import (
    ArtifactRef,
    ConsensusInput,
    LedgerEntry,
    ReasoningStep,
    SCHEMA_VERSION,
    Severity,
    new_uuid_v7,
)

DDL = """
CREATE TABLE IF NOT EXISTS ledger (
  seq         INTEGER PRIMARY KEY AUTOINCREMENT,
  finding_id  TEXT    UNIQUE NOT NULL,
  entry_hash  TEXT    NOT NULL,
  prev_hash   TEXT,
  ts_ns       INTEGER NOT NULL,
  payload     BLOB    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ledger_ts ON ledger(ts_ns);

CREATE TABLE IF NOT EXISTS anchor (
  batch_seq       INTEGER PRIMARY KEY,
  merkle_root     TEXT    NOT NULL,
  rekor_log_index INTEGER,
  dsse_bundle     BLOB,
  ts_ns           INTEGER NOT NULL
);
"""


def _as_refs(v: Iterable[Any]) -> list[ArtifactRef]:
    out: list[ArtifactRef] = []
    for r in v:
        out.append(r if isinstance(r, ArtifactRef) else ArtifactRef.model_validate(r))
    return out


def _as_steps(v: Iterable[Any]) -> list[ReasoningStep]:
    out: list[ReasoningStep] = []
    for s in v:
        out.append(s if isinstance(s, ReasoningStep) else ReasoningStep.model_validate(s))
    return out


def _as_consensus(v: Any) -> Optional[ConsensusInput]:
    if v is None or isinstance(v, ConsensusInput):
        return v
    return ConsensusInput.model_validate(v)


class LedgerWriter:
    """Thread-safe single-writer to SQLite WAL.

    One instance per process is the intended pattern. SQLite in WAL mode allows
    concurrent readers while a single writer serializes via a threading lock.
    """

    def __init__(self, sqlite_path: Path, sk_path: Path, pk_path: Path):
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(
            str(sqlite_path), isolation_level=None, check_same_thread=False
        )
        # Blueprint-mandated PRAGMAs
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA busy_timeout=5000;")
        self.conn.execute("PRAGMA temp_store=MEMORY;")
        self.conn.execute("PRAGMA mmap_size=268435456;")
        self.conn.executescript(DDL)
        self.sk = SigningKey(sk_path.read_bytes())
        self.pk_fpr = blake3.blake3(pk_path.read_bytes()).hexdigest()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ read
    def tip(self) -> tuple[Optional[str], int]:
        row = self.conn.execute(
            "SELECT entry_hash, seq FROM ledger ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        return (row[0], row[1]) if row else (None, 0)

    # ----------------------------------------------------------------- write
    def append(
        self,
        *,
        agent_id: str,
        agent_version: str,
        agent_model_hash: str,
        host_id: str,
        evidence_refs: Iterable[Any],
        primary_artifact_key: str,
        confidence: float,
        severity: str | Severity,
        reasoning_trace: Iterable[Any],
        consensus: Any = None,
        chain_of_custody: Optional[list[uuid.UUID]] = None,
        mitre: Optional[list[str]] = None,
        cvss: Optional[float] = None,
    ) -> LedgerEntry:
        t_start = time.perf_counter_ns()
        with self._lock:
            prev_hash, _ = self.tip()
            now = dt.datetime.now(tz=dt.timezone.utc)
            fid = new_uuid_v7()
            sev = severity if isinstance(severity, Severity) else Severity(severity)

            # First pass: assemble with a valid-shape placeholder signature
            # (64 zero-bytes -> 88-char base64 == correct sig length).
            placeholder_sig = base64.b64encode(b"\x00" * 64).decode()
            entry = LedgerEntry(
                finding_id=fid,
                schema_version=SCHEMA_VERSION,
                timestamp=now,
                timestamp_ns=now.microsecond * 1000,
                agent_id=agent_id,
                agent_version=agent_version,
                agent_model_hash=agent_model_hash,
                host_id=host_id,
                evidence_refs=_as_refs(evidence_refs),
                primary_artifact_key=primary_artifact_key,
                confidence=confidence,
                severity=sev,
                cvss_v3_1_base=cvss,
                mitre_attack_technique=mitre or [],
                reasoning_trace=_as_steps(reasoning_trace),
                consensus=_as_consensus(consensus),
                chain_of_custody=chain_of_custody or [],
                prev_hash=prev_hash,
                nonce=base64.b64encode(os.urandom(16)).decode(),
                signing_pubkey_fpr=self.pk_fpr,
                signature=placeholder_sig,
            )

            # Sign canonical bytes without the placeholder signature
            msg = entry.canonical_bytes(include_signature=False)
            sig = self.sk.sign(msg).signature
            entry = entry.model_copy(update={"signature": base64.b64encode(sig).decode()})

            # Finalize chain hash *including* the signature
            entry_hash = blake3.blake3(
                entry.canonical_bytes(include_signature=True)
            ).hexdigest()

            try:
                cur = self.conn.execute(
                    "INSERT INTO ledger(finding_id, entry_hash, prev_hash, ts_ns, payload) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        str(fid),
                        entry_hash,
                        prev_hash,
                        int(now.timestamp() * 1e9),
                        entry.canonical_bytes(include_signature=True),
                    ),
                )
            except Exception:
                LEDGER_APPENDS.labels(outcome="error").inc()
                raise
            LEDGER_APPENDS.labels(outcome="ok").inc()
            if cur.lastrowid is not None:
                LEDGER_CHAIN_LENGTH.set(cur.lastrowid)
            LEDGER_APPEND_SECONDS.observe((time.perf_counter_ns() - t_start) / 1e9)
            return entry

    def close(self) -> None:
        self.conn.close()
