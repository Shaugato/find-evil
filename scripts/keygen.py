#!/usr/bin/env python3
"""Generate Ed25519 keypairs for the ledger and CACAO signer.

Usage:
    python scripts/keygen.py ledger
    python scripts/keygen.py cacao
    python scripts/keygen.py all

Writes the raw 32-byte seed (sk) and 32-byte verify key (pk) to the paths declared
in `findevil.config.settings`. Never overwrites without --force.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nacl.signing

from findevil.config.settings import settings


def _write_kp(sk_path: Path, pk_path: Path, force: bool) -> None:
    if sk_path.exists() and not force:
        print(f"refuse to overwrite {sk_path} (use --force)", file=sys.stderr)
        sys.exit(2)
    sk_path.parent.mkdir(parents=True, exist_ok=True)
    pk_path.parent.mkdir(parents=True, exist_ok=True)
    sk = nacl.signing.SigningKey.generate()
    sk_path.write_bytes(sk.encode())
    pk_path.write_bytes(sk.verify_key.encode())
    try:
        sk_path.chmod(0o600)
        pk_path.chmod(0o644)
    except Exception:
        pass
    print(f"wrote {sk_path}")
    print(f"wrote {pk_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=("ledger", "cacao", "all"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.which in ("ledger", "all"):
        _write_kp(
            settings.ledger.ed25519_sk_path,
            settings.ledger.ed25519_pk_path,
            args.force,
        )
    if args.which in ("cacao", "all"):
        _write_kp(
            settings.ledger.cacao_sk_path,
            settings.ledger.cacao_pk_path,
            args.force,
        )


if __name__ == "__main__":
    main()
