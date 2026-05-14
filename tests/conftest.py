"""Pytest fixtures shared by every suite."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="session")
def _temp_findevil_root(tmp_path_factory) -> Path:
    """Point settings paths at a temp dir so tests don't touch /opt/findevil."""
    root = tmp_path_factory.mktemp("findevil")
    (root / "data" / "ledger").mkdir(parents=True, exist_ok=True)
    (root / "data" / "calibrators").mkdir(parents=True, exist_ok=True)
    (root / "etc" / "keys").mkdir(parents=True, exist_ok=True)
    (root / "run" / "zmq").mkdir(parents=True, exist_ok=True)
    os.environ["FINDEVIL_LEDGER__SQLITE_PATH"] = str(root / "data" / "ledger" / "ledger.sqlite")
    os.environ["FINDEVIL_LEDGER__ED25519_SK_PATH"] = str(root / "etc" / "keys" / "ledger.sk")
    os.environ["FINDEVIL_LEDGER__ED25519_PK_PATH"] = str(root / "etc" / "keys" / "ledger.pk")
    os.environ["FINDEVIL_LEDGER__CACAO_SK_PATH"] = str(root / "etc" / "keys" / "cacao.sk")
    os.environ["FINDEVIL_LEDGER__CACAO_PK_PATH"] = str(root / "etc" / "keys" / "cacao.pk")
    os.environ["FINDEVIL_TRANSPORT__ZMQ_IPC_DIR"] = str(root / "run" / "zmq")
    os.environ["FINDEVIL_TRANSPORT__VALKEY_SOCK"] = str(root / "run" / "valkey.sock")
    # Rebuild the settings singleton so it picks up the overrides above — the
    # default module-level instantiation ran BEFORE this fixture executes.
    # Every call site holds a reference to a _SettingsProxy that always forwards
    # to the current instance, so a single reload() is enough.
    import findevil.config.settings as _s

    _s.reload()
    return root


@pytest.fixture()
def ed25519_keys(_temp_findevil_root) -> tuple[bytes, bytes]:
    """Generate Ed25519 keypair and write to the fixture paths."""
    import nacl.signing

    sk = nacl.signing.SigningKey.generate()
    pk = sk.verify_key
    sk_path = Path(os.environ["FINDEVIL_LEDGER__ED25519_SK_PATH"])
    pk_path = Path(os.environ["FINDEVIL_LEDGER__ED25519_PK_PATH"])
    sk_path.write_bytes(sk.encode())
    pk_path.write_bytes(pk.encode())
    return sk.encode(), pk.encode()


@pytest.fixture()
def cacao_keys(_temp_findevil_root) -> tuple[bytes, bytes]:
    import nacl.signing

    sk = nacl.signing.SigningKey.generate()
    sk_path = Path(os.environ["FINDEVIL_LEDGER__CACAO_SK_PATH"])
    pk_path = Path(os.environ["FINDEVIL_LEDGER__CACAO_PK_PATH"])
    sk_path.write_bytes(sk.encode())
    pk_path.write_bytes(sk.verify_key.encode())
    return sk.encode(), sk.verify_key.encode()
