"""OCSF + STIX interop smoke tests — minimally ensures top-level fields exist.

Both adapters take a fully-validated `LedgerEntry` Pydantic model; we build one
via the real Writer so the adapters exercise the same shape they see at runtime.
"""

from __future__ import annotations

import os
from pathlib import Path

import blake3

from findevil.ledger.interop import to_ocsf_detection_finding, to_stix_bundle


def _fake_entry(ed25519_keys):
    from findevil.ledger.schema import (
        ArtifactRef,
        ArtifactType,
        ReasoningMethod,
        ReasoningStep,
        Severity,
    )
    from findevil.ledger.writer import LedgerWriter

    sqlite_path = Path(os.environ["FINDEVIL_LEDGER__SQLITE_PATH"])
    sk_path = Path(os.environ["FINDEVIL_LEDGER__ED25519_SK_PATH"])
    pk_path = Path(os.environ["FINDEVIL_LEDGER__ED25519_PK_PATH"])
    if sqlite_path.exists():
        sqlite_path.unlink()

    ref = ArtifactRef(
        type=ArtifactType.IPV4,
        uri="203.0.113.5",
    )
    reasoning = ReasoningStep(
        step_index=0,
        claim="c2_callout",
        method=ReasoningMethod.BEHAVIORAL_ML,
        confidence=0.9,
    )
    w = LedgerWriter(sqlite_path, sk_path, pk_path)
    try:
        entry = w.append(
            agent_id="zeek.dns",
            agent_version="0.1.0",
            agent_model_hash=blake3.blake3(b"unit-test-interop").hexdigest(),
            host_id="test-host",
            evidence_refs=[ref],
            primary_artifact_key="ipv4:203.0.113.5",
            confidence=0.9,
            severity=Severity.HIGH,
            mitre=["T1071.001"],
            reasoning_trace=[reasoning],
        )
    finally:
        w.close()
    return entry


def test_ocsf_class_uid_is_detection_finding(ed25519_keys):
    entry = _fake_entry(ed25519_keys)
    ocsf = to_ocsf_detection_finding(entry)
    assert ocsf["class_uid"] == 2004
    assert ocsf["category_uid"] == 2
    assert ocsf["severity_id"] == 4  # HIGH
    assert ocsf["attacks"] == [{"technique": {"uid": "T1071.001"}}]


def test_stix_bundle_has_indicator_and_observed_data(ed25519_keys):
    entry = _fake_entry(ed25519_keys)
    bundle = to_stix_bundle(entry)
    assert bundle["type"] == "bundle"
    types = {o.get("type") for o in bundle.get("objects", [])}
    assert {"indicator", "observed-data"} <= types or "sighting" in types
    # Every object must carry spec_version 2.1
    for o in bundle["objects"]:
        assert o["spec_version"] == "2.1"
