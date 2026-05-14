"""CACAO 2.0 sign/verify round-trip + tamper detection."""

from __future__ import annotations

import nacl.signing

from findevil.cacao.schema import CacaoPlaybook, CacaoStep, sign_playbook, verify_playbook


def _mkpb() -> CacaoPlaybook:
    a = CacaoStep(name="a", actuator="analyst.review")
    b = CacaoStep(name="b", actuator="findevil.end", type="end")
    a.on_success = b.id
    return CacaoPlaybook(
        name="t",
        workflow_start=a.id,
        workflow={a.id: a, b.id: b},
    )


def test_roundtrip_signature_valid():
    sk = nacl.signing.SigningKey.generate()
    pb = sign_playbook(_mkpb(), sk)
    assert verify_playbook(pb, expected_pk=sk.verify_key.encode())


def test_wrong_key_rejected():
    sk = nacl.signing.SigningKey.generate()
    other = nacl.signing.SigningKey.generate()
    pb = sign_playbook(_mkpb(), sk)
    assert not verify_playbook(pb, expected_pk=other.verify_key.encode())


def test_tamper_detected():
    sk = nacl.signing.SigningKey.generate()
    pb = sign_playbook(_mkpb(), sk)
    # mutate name after signing
    tampered = pb.model_copy(update={"name": "tampered"})
    assert not verify_playbook(tampered, expected_pk=sk.verify_key.encode())
