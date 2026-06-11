"""LedgerReader.for_artifact + narrator ledger-exhibit enrichment (Part 10)."""

from __future__ import annotations

import os
from pathlib import Path

import blake3
import pytest

from findevil.ledger.reader import LedgerReader
from findevil.ledger.schema import (
    ArtifactRef,
    ArtifactType,
    ReasoningMethod,
    ReasoningStep,
    Severity,
)
from findevil.ledger.writer import LedgerWriter


def _append(writer: LedgerWriter, artifact_key: str, claim: str) -> None:
    writer.append(
        agent_id="test.reader",
        agent_version="0.1.0",
        agent_model_hash=blake3.blake3(claim.encode()).hexdigest(),
        host_id="test-host",
        evidence_refs=[
            ArtifactRef(
                type=ArtifactType.PROCESS,
                uri=f"proc://test-host/{artifact_key}",
                extra={},
            )
        ],
        primary_artifact_key=artifact_key,
        confidence=0.8,
        severity=Severity.LOW,
        reasoning_trace=[
            ReasoningStep(
                step_index=0,
                claim=claim,
                method=ReasoningMethod.BEHAVIORAL_ML,
                confidence=0.8,
            )
        ],
        mitre=["T1059.001"],
    )


@pytest.fixture()
def populated_ledger(ed25519_keys, tmp_path: Path) -> Path:
    sk_path = Path(os.environ["FINDEVIL_LEDGER__ED25519_SK_PATH"])
    pk_path = Path(os.environ["FINDEVIL_LEDGER__ED25519_PK_PATH"])
    db = tmp_path / "reader-ledger.sqlite"
    w = LedgerWriter(db, sk_path, pk_path)
    try:
        _append(w, "proc:host-a:111", "first finding for 111")
        _append(w, "proc:host-a:222", "finding for other artifact")
        _append(w, "proc:host-a:111", "second finding for 111")
    finally:
        w.close()
    return db


@pytest.mark.asyncio
async def test_for_artifact_filters_and_orders(populated_ledger: Path):
    r = LedgerReader(populated_ledger)
    try:
        rows = await r.for_artifact("proc:host-a:111", n=5)
    finally:
        r.close()
    assert len(rows) == 2
    # Newest first
    assert rows[0]["entry"]["reasoning_trace"][0]["claim"] == "second finding for 111"
    assert all(
        row["entry"]["primary_artifact_key"] == "proc:host-a:111" for row in rows
    )


@pytest.mark.asyncio
async def test_narrator_ledger_exhibits_shape(populated_ledger: Path, monkeypatch):
    from findevil.config.settings import settings
    from findevil.narrator import service as nsvc

    monkeypatch.setattr(settings.ledger, "sqlite_path", populated_ledger)
    exhibits = await nsvc._ledger_exhibits("proc:host-a:111", limit=3)  # noqa: SLF001
    assert len(exhibits) == 2
    ex = exhibits[0]
    assert ex["exhibit_kind"] == "ledger_finding"
    assert ex["claim"] == "second finding for 111"
    assert ex["mitre"] == ["T1059.001"]
    assert ex["agent_id"] == "test.reader"


@pytest.mark.asyncio
async def test_narrator_ledger_exhibits_never_raise(monkeypatch):
    from findevil.config.settings import settings
    from findevil.narrator import service as nsvc

    monkeypatch.setattr(
        settings.ledger, "sqlite_path", Path("/nonexistent/ledger.sqlite")
    )
    exhibits = await nsvc._ledger_exhibits("proc:host-a:111")
    assert exhibits == []
