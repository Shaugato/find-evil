"""Chain verifier — confirms prev_hash linkage, BLAKE3 entry hashes, and Ed25519 signatures.

Run hourly by findevil-verify.timer. Any tainted seq is surfaced via ledger admin alert.
"""

from __future__ import annotations

import base64
import json
import sqlite3
from pathlib import Path
from typing import Optional

import blake3
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from .schema import LedgerEntry


def verify_chain(
    sqlite_path: Path | str,
    pk_bytes: bytes,
    *,
    start_seq: int = 1,
) -> tuple[bool, list[int]]:
    """Verify every ledger row from start_seq onward.

    Returns (ok, tainted_seqs).  ok is True iff tainted_seqs is empty.
    """
    # The hourly systemd verifier runs in a read-only sandbox.  Open SQLite via
    # an immutable read-only URI so verification does not need to create WAL/SHM
    # sidecar files under /opt/findevil/data/ledger.
    db_path = Path(sqlite_path).resolve()
    conn = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
    vk = VerifyKey(pk_bytes)
    prev_hash: Optional[str] = None
    tainted: list[int] = []

    if start_seq > 1:
        prev_row = conn.execute(
            "SELECT entry_hash FROM ledger WHERE seq = ?", (start_seq - 1,)
        ).fetchone()
        if prev_row:
            prev_hash = prev_row[0]

    cursor = conn.execute(
        "SELECT seq, finding_id, entry_hash, prev_hash, ts_ns, payload "
        "FROM ledger WHERE seq >= ? ORDER BY seq",
        (start_seq,),
    )
    for seq, _fid, entry_hash, ph, _ts, payload in cursor:
        try:
            doc = json.loads(payload)
            # content_hash_blake3 is a computed field that round-trips back in;
            # Pydantic won't set it from input but json.loads carries it. Strip.
            doc.pop("content_hash_blake3", None)
            entry = LedgerEntry.model_validate(doc)
        except ValueError:
            tainted.append(seq)
            continue

        # 1) previous-hash linkage
        if entry.prev_hash != prev_hash or ph != prev_hash:
            tainted.append(seq)
            prev_hash = entry_hash
            continue

        # 2) entry hash reproduces
        want = blake3.blake3(entry.canonical_bytes(include_signature=True)).hexdigest()
        if want != entry_hash:
            tainted.append(seq)
            prev_hash = entry_hash
            continue

        # 3) Ed25519 signature verifies
        try:
            sig = base64.b64decode(entry.signature)
            vk.verify(entry.canonical_bytes(include_signature=False), sig)
        except (BadSignatureError, ValueError):
            tainted.append(seq)
            prev_hash = entry_hash
            continue

        prev_hash = entry_hash

    conn.close()
    return (len(tainted) == 0, tainted)
