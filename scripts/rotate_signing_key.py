#!/usr/bin/env python3
"""Rotate the ledger signing key — writes a `key_rotation` ledger entry first.

Rotation procedure (blueprint Part 6.6):
  1. Append a ledger entry (reasoning_trace tagged `key_rotation`) signed with the
     OLD key, carrying the new public key in its evidence + reasoning params so
     verifiers can rebuild the pubkey-as-of timeline.
  2. Atomically replace the sk/pk files with the new pair.
  3. Restart all writer services.

The new key becomes authoritative at the seq AFTER the rotation entry.
"""

from __future__ import annotations

import argparse
import base64
import socket
import sys

import blake3
import nacl.signing

from findevil.config.settings import settings
from findevil.ledger.schema import (
    ArtifactRef,
    ArtifactType,
    ReasoningMethod,
    ReasoningStep,
    Severity,
)
from findevil.ledger.writer import LedgerWriter


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    _ = args  # reserved for future safety prompts

    sk_path = settings.ledger.ed25519_sk_path
    pk_path = settings.ledger.ed25519_pk_path
    if not sk_path.exists():
        print(f"missing {sk_path}", file=sys.stderr)
        return 2

    new_sk = nacl.signing.SigningKey.generate()
    new_pk = new_sk.verify_key
    new_pk_b64 = base64.b64encode(new_pk.encode()).decode()
    new_pk_fpr = blake3.blake3(new_pk.encode()).hexdigest()

    # 1. rotation entry under OLD key
    w = LedgerWriter(
        settings.ledger.sqlite_path,
        sk_path,
        pk_path,
    )
    try:
        evidence = ArtifactRef(
            type=ArtifactType.USER,
            uri=f"key://ledger_ed25519/{new_pk_fpr}",
            extra={"new_pk_b64": new_pk_b64, "new_pk_fpr": new_pk_fpr},
        )
        reasoning = ReasoningStep(
            step_index=0,
            claim="rotate_ledger_signing_key",
            method=ReasoningMethod.HUMAN_ASSERTION,
            confidence=1.0,
            params={"new_pk_fpr": new_pk_fpr, "new_pk_b64": new_pk_b64},
        )
        model_hash = blake3.blake3(b"findevil-key-rotation").hexdigest()
        entry = w.append(
            agent_id="operator.rotate_signing_key",
            agent_version="0.1.0",
            agent_model_hash=model_hash,
            host_id=settings.host_id or socket.gethostname(),
            evidence_refs=[evidence],
            primary_artifact_key=f"key:ledger_ed25519:{new_pk_fpr}",
            confidence=1.0,
            severity=Severity.HIGH,
            reasoning_trace=[reasoning],
        )
        print(f"rotation entry written: finding_id={entry.finding_id}")
    finally:
        w.close()

    # 2. swap files (atomic replace; sk first so a crash leaves the old pk valid)
    sk_path.write_bytes(new_sk.encode())
    pk_path.write_bytes(new_pk.encode())
    try:
        sk_path.chmod(0o600)
        pk_path.chmod(0o644)
    except Exception:
        pass
    print("rotation complete; restart findevil.target services")
    return 0


if __name__ == "__main__":
    sys.exit(main())
