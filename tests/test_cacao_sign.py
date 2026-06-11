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


def test_jws_roundtrip_eddsa():
    """Doc Part 11.3 — compact JWS via joserfc must round-trip the canonical bytes."""
    from findevil.cacao.sign import sign_playbook_jws, verify_playbook_jws

    sk = nacl.signing.SigningKey.generate()
    pb = _mkpb()
    token = sign_playbook_jws(pb, sk)
    assert token.count(".") == 2  # compact JWS: header.payload.signature

    payload = verify_playbook_jws(token, sk.verify_key.encode())
    assert payload == pb.canonical_bytes(include_signature=False)


def test_jws_wrong_key_and_tamper_rejected():
    from findevil.cacao.sign import sign_playbook_jws, verify_playbook_jws

    sk = nacl.signing.SigningKey.generate()
    other = nacl.signing.SigningKey.generate()
    token = sign_playbook_jws(_mkpb(), sk)
    assert verify_playbook_jws(token, other.verify_key.encode()) is None

    header, payload, sig = token.split(".")
    forged = ".".join([header, payload[:-2] + "AA", sig])
    assert verify_playbook_jws(forged, sk.verify_key.encode()) is None
