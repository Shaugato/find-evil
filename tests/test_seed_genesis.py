"""Regression: scripts/seed_genesis.py writes a verifiable genesis entry.

This guards against a drift pattern in which the script used obsolete kwargs
(`finding_kind`, `attributes`) that would silently throw at runtime.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_seed_genesis():
    spec = importlib.util.spec_from_file_location(
        "scripts.seed_genesis", str(REPO_ROOT / "scripts" / "seed_genesis.py")
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_seed_genesis_writes_and_verifies(ed25519_keys):
    import findevil.config.settings as s_mod

    from findevil.ledger.verify import verify_chain

    # Rebind settings so the script picks up the tmp paths the conftest env vars
    # pointed at (env vars are applied after the module-level instantiation).
    s_mod.reload()

    sqlite_path = Path(os.environ["FINDEVIL_LEDGER__SQLITE_PATH"])
    if sqlite_path.exists():
        sqlite_path.unlink()

    sg = _load_seed_genesis()
    rc = sg.main()
    assert rc == 0

    _, pk = ed25519_keys
    ok, tainted = verify_chain(sqlite_path, pk)
    assert ok, f"verify_chain after genesis: tainted={tainted}"

    # Second invocation must be idempotent — script exits 0 without touching the row.
    rc2 = sg.main()
    assert rc2 == 0
    ok2, tainted2 = verify_chain(sqlite_path, pk)
    assert ok2 and tainted2 == []
