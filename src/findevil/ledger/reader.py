"""Read-only ledger queries for dashboards, narrator, and MCP bb://ledger/tip resource."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from findevil.config.settings import settings


class LedgerReader:
    """Thin wrapper — opens SQLite read-only and answers common queries."""

    def __init__(self, sqlite_path: Optional[Path] = None):
        path = sqlite_path or settings.ledger.sqlite_path
        # URI mode to open as read-only
        self.conn = sqlite3.connect(
            f"file:{path}?mode=ro", uri=True, check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row

    async def tip(self) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT seq, finding_id, entry_hash, prev_hash, ts_ns "
            "FROM ledger ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return {"seq": 0, "entry_hash": None, "prev_hash": None}
        last_anchor = self.conn.execute(
            "SELECT merkle_root, rekor_log_index, ts_ns "
            "FROM anchor ORDER BY batch_seq DESC LIMIT 1"
        ).fetchone()
        return {
            "seq": row["seq"],
            "finding_id": row["finding_id"],
            "entry_hash": row["entry_hash"],
            "prev_hash": row["prev_hash"],
            "ts_ns": row["ts_ns"],
            "last_merkle_root": last_anchor["merkle_root"] if last_anchor else None,
            "last_rekor_log_index": last_anchor["rekor_log_index"] if last_anchor else None,
        }

    async def count_consensus(self) -> int:
        """Number of entries whose payload carries a non-null consensus object."""
        c = 0
        for (payload,) in self.conn.execute("SELECT payload FROM ledger"):
            try:
                if json.loads(payload).get("consensus") is not None:
                    c += 1
            except ValueError:
                continue
        return c

    async def for_artifact(self, artifact_key: str, n: int = 5) -> list[dict[str, Any]]:
        """Latest entries whose payload's primary_artifact_key matches.

        Uses json_extract over the canonical payload — the chain schema keeps
        seq/hash columns lean on purpose, so artifact lookups go through JSON1.
        """
        rows = self.conn.execute(
            "SELECT seq, finding_id, ts_ns, payload FROM ledger "
            "WHERE json_extract(payload, '$.primary_artifact_key') = ? "
            "ORDER BY seq DESC LIMIT ?",
            (artifact_key, n),
        ).fetchall()
        return [
            {
                "seq": r["seq"],
                "finding_id": r["finding_id"],
                "ts_ns": r["ts_ns"],
                "entry": json.loads(r["payload"]),
            }
            for r in rows
        ]

    async def recent(self, n: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT seq, finding_id, entry_hash, ts_ns, payload "
            "FROM ledger ORDER BY seq DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [
            {
                "seq": r["seq"],
                "finding_id": r["finding_id"],
                "entry_hash": r["entry_hash"],
                "ts_ns": r["ts_ns"],
                "entry": json.loads(r["payload"]),
            }
            for r in rows
        ]

    def close(self) -> None:
        self.conn.close()
