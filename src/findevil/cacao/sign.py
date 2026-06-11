"""CACAO playbook signing — raw Ed25519 compatibility + JWS (joserfc).

Two signature forms coexist:

- The legacy/compat path signs canonical playbook bytes with a detached
  Ed25519 signature (PyNaCl) stored in ``CacaoSignature.value``.
- The blueprint Part 11.3 path wraps the same canonical bytes in a compact
  JWS using ``EdDSA`` via joserfc, so external CACAO consumers can verify
  with standard JOSE tooling.
"""

from __future__ import annotations

import base64
from pathlib import Path

import nacl.signing
from joserfc import jws
from joserfc.jwk import OKPKey

from .schema import CacaoPlaybook, CacaoSignature, Playbook
from .schema import sign_playbook as sign_legacy_playbook

JWS_ALG = "EdDSA"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _okp_private(sk: nacl.signing.SigningKey) -> OKPKey:
    return OKPKey.import_key(
        {
            "kty": "OKP",
            "crv": "Ed25519",
            "d": _b64url(bytes(sk)),
            "x": _b64url(bytes(sk.verify_key)),
        }
    )


def _okp_public(pk_bytes: bytes) -> OKPKey:
    return OKPKey.import_key(
        {"kty": "OKP", "crv": "Ed25519", "x": _b64url(pk_bytes)}
    )


def sign_playbook(pb: Playbook | CacaoPlaybook, sk_path: Path) -> Playbook | CacaoPlaybook:
    sk = nacl.signing.SigningKey(Path(sk_path).read_bytes())
    if isinstance(pb, CacaoPlaybook):
        return sign_legacy_playbook(pb, sk)
    sig = sk.sign(pb.canonical_bytes(include_signatures=False)).signature
    return pb.model_copy(
        update={"signatures": [CacaoSignature(value=base64.b64encode(sig).decode())]}
    )


def sign_playbook_jws(pb: CacaoPlaybook, sk: nacl.signing.SigningKey) -> str:
    """Compact JWS (EdDSA) over the canonical playbook bytes (doc Part 11.3)."""
    payload = pb.canonical_bytes(include_signature=False)
    return jws.serialize_compact(
        {"alg": JWS_ALG}, payload, _okp_private(sk), algorithms=[JWS_ALG]
    )


def verify_playbook_jws(token: str, pk_bytes: bytes) -> bytes | None:
    """Verify a compact JWS and return the canonical payload, or None."""
    try:
        obj = jws.deserialize_compact(
            token, _okp_public(pk_bytes), algorithms=[JWS_ALG]
        )
    except Exception:
        return None
    payload = obj.payload
    return payload if isinstance(payload, bytes) else str(payload).encode()
