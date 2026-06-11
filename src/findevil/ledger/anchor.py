"""Merkle anchor job — periodic Sigstore Rekor v2 submission.

Per blueprint Part 6.6 every N (default 256) ledger entries:
  1. Build BLAKE3 Merkle tree (RFC 6962-style domain separation).
  2. Wrap root in an in-toto Statement (predicateType findevil batch-anchor v1).
  3. DSSE-sign via Sigstore and submit to Rekor.
  4. Persist the bundle + log_index in the `anchor` table for later proofs.
"""

from __future__ import annotations

import asyncio
import sqlite3
import time
from pathlib import Path
from typing import Optional

import blake3

from findevil.config.settings import settings
from findevil.observability.metrics import REKOR_ANCHOR_AGE

# RFC-6962-style domain separation: leaf=0x00, node=0x01
LEAF_DOM = b"\x00"
NODE_DOM = b"\x01"


def _blake3(b: bytes) -> bytes:
    return blake3.blake3(b).digest()


def leaf_hash(entry_hash: bytes) -> bytes:
    return _blake3(LEAF_DOM + entry_hash)


def node_hash(a: bytes, b: bytes) -> bytes:
    return _blake3(NODE_DOM + a + b)


def merkle_root(leaves: list[bytes]) -> bytes:
    if not leaves:
        raise ValueError("empty leaf set")
    level = [leaf_hash(b) for b in leaves]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [node_hash(level[i], level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


def merkle_copath(leaves: list[bytes], index: int) -> list[bytes]:
    """Return just the raw sibling-hash co-path proving leaves[index] ∈ root."""
    if not 0 <= index < len(leaves):
        raise IndexError(index)
    level = [leaf_hash(b) for b in leaves]
    copath: list[bytes] = []
    i = index
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        sibling = i ^ 1
        copath.append(level[sibling])
        level = [node_hash(level[j], level[j + 1]) for j in range(0, len(level), 2)]
        i //= 2
    return copath


def merkle_inclusion_proof(leaves: list[bytes], index: int) -> dict:
    """Return a Rekor-v2-aligned inclusion proof envelope.

    Shape:
        {
            "leaf_index": int,
            "tree_size": int,
            "root": bytes,
            "path": list[bytes],  # sibling hashes in leaf->root order
        }

    The raw co-path is also available via `merkle_copath()` for callers that
    don't need the envelope. The `path` is a shallow copy so consumers can
    mutate without affecting the internal computation.
    """
    path = merkle_copath(leaves, index)
    return {
        "leaf_index": index,
        "tree_size": len(leaves),
        "root": merkle_root(leaves),
        "path": list(path),
    }


async def anchor_batch(
    sqlite_path: Path,
    batch_size: Optional[int] = None,
    *,
    rekor_submit: bool = True,
) -> Optional[dict]:
    """Anchor the next complete batch of entries to Rekor.

    Returns a dict describing the anchor or None if no full batch is available.
    The Rekor submission is skipped when rekor_submit=False (offline dev).
    """
    batch_size = batch_size or settings.ledger.anchor_every_n
    conn = sqlite3.connect(str(sqlite_path), isolation_level=None)

    max_batch = conn.execute("SELECT COALESCE(MAX(batch_seq), 0) FROM anchor").fetchone()[0]
    start_seq = max_batch * batch_size + 1
    rows = conn.execute(
        "SELECT seq, entry_hash FROM ledger WHERE seq >= ? ORDER BY seq LIMIT ?",
        (start_seq, batch_size),
    ).fetchall()
    if len(rows) < batch_size:
        conn.close()
        return None

    leaves = [bytes.fromhex(h) for _, h in rows]
    root = merkle_root(leaves)
    batch_seq = max_batch + 1

    rekor_index: Optional[int] = None
    bundle_bytes: Optional[bytes] = None

    if rekor_submit:
        try:
            rekor_index, bundle_bytes = await _submit_to_rekor(root, batch_seq)
        except Exception:  # offline, network down, etc. — record locally anyway
            rekor_index, bundle_bytes = None, None

    conn.execute(
        "INSERT INTO anchor(batch_seq, merkle_root, rekor_log_index, dsse_bundle, ts_ns) "
        "VALUES (?, ?, ?, ?, ?)",
        (batch_seq, root.hex(), rekor_index, bundle_bytes, time.time_ns()),
    )
    conn.close()
    REKOR_ANCHOR_AGE.set(0)
    return {
        "batch_seq": batch_seq,
        "merkle_root": root.hex(),
        "rekor_log_index": rekor_index,
        "leaves": len(leaves),
    }


def update_anchor_age(sqlite_path: Path) -> Optional[float]:
    """Refresh findevil_rekor_anchor_age_seconds from the anchor table.

    Called by the hourly verify job so the gauge keeps growing between
    anchor runs. Returns the age in seconds, or None when nothing anchored.
    """
    conn = sqlite3.connect(str(sqlite_path), isolation_level=None)
    try:
        row = conn.execute("SELECT MAX(ts_ns) FROM anchor").fetchone()
    finally:
        conn.close()
    if not row or row[0] is None:
        return None
    age_s = max(0.0, (time.time_ns() - int(row[0])) / 1e9)
    REKOR_ANCHOR_AGE.set(age_s)
    return age_s


async def _submit_to_rekor(root: bytes, batch_seq: int) -> tuple[int, bytes]:
    """Submit the Merkle root as a DSSE-wrapped in-toto Statement to Rekor."""
    loop = asyncio.get_running_loop()

    def _sign_and_push() -> tuple[int, bytes]:
        # Sigstore Python 4.x removed the older Signer.production convenience
        # API. Use the current trust-config/OIDC flow and keep the BLAKE3 root
        # in the in-toto predicate; the DSSE Subject digest is SHA-256 because
        # Sigstore's typed DSSE model only accepts standard hash algorithm names.
        import hashlib

        from sigstore import dsse
        from sigstore.models import ClientTrustConfig
        from sigstore.oidc import Issuer
        from sigstore.sign import SigningContext

        trust_config = ClientTrustConfig.production()
        issuer = Issuer(trust_config.signing_config.get_oidc_url())
        signing_ctx = SigningContext.from_trust_config(trust_config)
        token = issuer.identity_token(force_oob=True)
        subject = dsse.Subject(
            name=f"findevil-ledger-batch-{batch_seq}",
            digest=dsse.DigestSet({"sha256": hashlib.sha256(root).hexdigest()}),
        )
        stmt = (
            dsse.StatementBuilder()
            .subjects([subject])
            .predicate_type("https://findevil.local/forensic-ledger/batch-anchor/v1")
            .predicate({"batch_seq": batch_seq, "merkle_root_blake3": root.hex()})
            .build()
        )
        with signing_ctx.signer(token, cache=True) as signer:
            bundle = signer.sign_dsse(stmt)
        return int(bundle.log_entry._inner.log_index), bundle.to_json().encode()

    return await loop.run_in_executor(None, _sign_and_push)
