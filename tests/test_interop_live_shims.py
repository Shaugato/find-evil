"""stix.bundle / ocsf.finding MCP shims emit from reader-shaped dict rows.

Regression: the reader returns plain JSON dicts, but to_stix_bundle /
to_ocsf_detection_finding expect LedgerEntry models (entry.timestamp etc.).
The shims must validate dict->model so the live MCP path matches the schema.
"""

from __future__ import annotations

import os
from pathlib import Path

import blake3
import pytest

from findevil.ledger.schema import (
    ArtifactRef,
    ArtifactType,
    ReasoningMethod,
    ReasoningStep,
    Severity,
)
from findevil.ledger.writer import LedgerWriter
from findevil.tools.registry import resolve


@pytest.fixture()
def one_entry_ledger(ed25519_keys, tmp_path, monkeypatch):
    from findevil.config.settings import settings

    sk = Path(os.environ["FINDEVIL_LEDGER__ED25519_SK_PATH"])
    pk = Path(os.environ["FINDEVIL_LEDGER__ED25519_PK_PATH"])
    db = tmp_path / "interop-ledger.sqlite"
    w = LedgerWriter(db, sk, pk)
    try:
        w.append(
            agent_id="test.interop",
            agent_version="0.1.0",
            agent_model_hash=blake3.blake3(b"interop").hexdigest(),
            host_id="test-host",
            evidence_refs=[
                ArtifactRef(type=ArtifactType.IPV4, uri="203.0.113.10", extra={})
            ],
            primary_artifact_key="pher:ip:203.0.113.10",
            confidence=0.8,
            severity=Severity.MEDIUM,
            reasoning_trace=[
                ReasoningStep(step_index=0, claim="interop", method=ReasoningMethod.BEHAVIORAL_ML, confidence=0.8)
            ],
            mitre=["T1071.001"],
        )
    finally:
        w.close()
    monkeypatch.setattr(settings.ledger, "sqlite_path", db)
    return db


@pytest.mark.asyncio
async def test_stix_bundle_live_emission(one_entry_ledger):
    fn = resolve("stix.bundle")
    out = await fn([{"target": {"seq": -1}}])
    assert out["ok"] is True, out
    bundle = out["bundle"]
    assert bundle["type"] == "bundle"
    types = {o["type"] for o in bundle["objects"]}
    assert "indicator" in types


@pytest.mark.asyncio
async def test_ocsf_finding_live_emission(one_entry_ledger):
    fn = resolve("ocsf.finding")
    out = await fn([{"target": {"seq": -1}}])
    assert out["ok"] is True, out
    assert out["ocsf"]["class_uid"] == 2004
    assert out["ocsf"]["category_uid"] == 2
