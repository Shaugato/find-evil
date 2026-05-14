"""Compatibility signing helpers for CACAO validation APIs."""

from __future__ import annotations

import base64
from pathlib import Path

import nacl.signing

from .schema import CacaoPlaybook, CacaoSignature, Playbook
from .schema import sign_playbook as sign_legacy_playbook


def sign_playbook(pb: Playbook | CacaoPlaybook, sk_path: Path) -> Playbook | CacaoPlaybook:
    sk = nacl.signing.SigningKey(Path(sk_path).read_bytes())
    if isinstance(pb, CacaoPlaybook):
        return sign_legacy_playbook(pb, sk)
    sig = sk.sign(pb.canonical_bytes(include_signatures=False)).signature
    return pb.model_copy(
        update={"signatures": [CacaoSignature(value=base64.b64encode(sig).decode())]}
    )
