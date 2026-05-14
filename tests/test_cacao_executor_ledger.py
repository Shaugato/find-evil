"""Regression: CACAO executor's ledger append uses the real Writer API.

This is the drift that previously blocked end-to-end mitigation runs: the
executor called `LedgerWriter()` with no args and passed obsolete `finding_kind`
/ `attributes` kwargs that don't exist on the schema. This test invokes
`_append_ledger` directly against a temp SQLite and verifies the chain.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import nacl.signing


def test_append_ledger_records_cacao_execution(ed25519_keys, monkeypatch):
    import findevil.config.settings as s_mod

    from findevil.cacao.executor import _append_ledger
    from findevil.cacao.schema import CacaoPlaybook, CacaoStep, sign_playbook
    from findevil.ledger.verify import verify_chain

    # Re-bind the settings singleton to the conftest tmp paths — AppSettings was
    # constructed at import time before the fixture's env overrides took effect.
    s_mod.reload()

    # Build + sign a minimal playbook
    start = CacaoStep(name="start", actuator="analyst.review")
    end = CacaoStep(name="end", actuator="findevil.end", type="end")
    start.on_success = end.id
    pb = CacaoPlaybook(
        name="test-pb",
        workflow_start=start.id,
        workflow={start.id: start, end.id: end},
    )
    pb = sign_playbook(pb, nacl.signing.SigningKey.generate())

    sqlite_path = Path(os.environ["FINDEVIL_LEDGER__SQLITE_PATH"])
    if sqlite_path.exists():
        sqlite_path.unlink()

    asyncio.run(
        _append_ledger(
            playbook=pb,
            instance_id="test-instance-123",
            status="succeeded",
            steps_ran=[start.id],
            error=None,
        )
    )

    _, pk = ed25519_keys
    ok, tainted = verify_chain(sqlite_path, pk)
    assert ok, f"ledger chain tainted after cacao_executed append: {tainted}"
    assert tainted == []

    # Confirm content: agent_id + primary_artifact_key reflect the executor
    from findevil.ledger.reader import LedgerReader

    r = LedgerReader(sqlite_path=sqlite_path)
    try:
        recent = asyncio.run(r.recent(1))
    finally:
        r.close()
    assert len(recent) == 1
    entry = recent[0]["entry"]
    assert entry["agent_id"] == "cacao.executor"
    assert entry["primary_artifact_key"] == "cacao:instance:test-instance-123"
    assert entry["severity"] == "informational"  # succeeded -> informational


def test_append_ledger_failed_status_marks_severity_high(ed25519_keys):
    """A non-succeeded terminal status must raise severity to HIGH."""
    import findevil.config.settings as s_mod

    from findevil.cacao.executor import _append_ledger
    from findevil.cacao.schema import CacaoPlaybook, CacaoStep, sign_playbook
    from findevil.ledger.reader import LedgerReader

    s_mod.reload()

    start = CacaoStep(name="start", actuator="analyst.review")
    end = CacaoStep(name="end", actuator="findevil.end", type="end")
    pb = sign_playbook(
        CacaoPlaybook(
            name="failing-pb",
            workflow_start=start.id,
            workflow={start.id: start, end.id: end},
        ),
        nacl.signing.SigningKey.generate(),
    )

    sqlite_path = Path(os.environ["FINDEVIL_LEDGER__SQLITE_PATH"])
    if sqlite_path.exists():
        sqlite_path.unlink()

    asyncio.run(
        _append_ledger(
            playbook=pb,
            instance_id="fail-1",
            status="failed",
            steps_ran=[start.id],
            error="simulated failure",
        )
    )

    r = LedgerReader(sqlite_path=sqlite_path)
    try:
        recent = asyncio.run(r.recent(1))
    finally:
        r.close()
    entry = recent[0]["entry"]
    assert entry["severity"] == "high"
