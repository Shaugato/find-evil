"""Pipeline-produced ledger entries."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path


def test_append_consensus_frame_writes_parent_and_consensus_entries(ed25519_keys):
    import findevil.config.settings as s_mod

    from findevil.ledger.events import append_consensus_frame
    from findevil.ledger.reader import LedgerReader
    from findevil.ledger.verify import verify_chain

    s_mod.reload()
    sqlite_path = Path(os.environ["FINDEVIL_LEDGER__SQLITE_PATH"])
    if sqlite_path.exists():
        sqlite_path.unlink()

    sha = "a" * 64
    frame = {
        "pher_key": f"pher:hash:{sha}",
        "kind": "hash",
        "tau": 1.5,
        "sensor_diversity": 2,
        "reports": [
            {
                "agent_id": "edr/sysmon-01",
                "confidence": 0.85,
                "reliability": 0.8,
                "sensor": "sysmon-01",
                "declared_ignorance": 0.05,
            },
            {
                "agent_id": "yara/yara-01",
                "confidence": 0.9,
                "reliability": 0.8,
                "sensor": "yara-01",
                "declared_ignorance": 0.05,
            },
        ],
        "action": "mitigate",
        "belief_evil": 0.84,
        "plausibility_evil": 0.93,
        "uncertainty": 0.09,
        "conflict_K": 0.12,
    }
    written = append_consensus_frame(frame)
    assert len(written) == 3

    _, pk = ed25519_keys
    ok, tainted = verify_chain(sqlite_path, pk)
    assert ok, tainted

    reader = LedgerReader(sqlite_path=sqlite_path)
    try:
        recent = asyncio.run(reader.recent(3))
    finally:
        reader.close()
    consensus = recent[0]["entry"]
    assert consensus["agent_id"] == "swarm.consensus"
    assert consensus["consensus"]["belief_evil"] == 0.84
    assert len(consensus["chain_of_custody"]) == 2


def test_artifact_for_architecture_indicator_schemes():
    from findevil.ledger.events import artifact_for_pher_key

    user = artifact_for_pher_key("pher:user://CORP\\jsmith")
    assert user.type == "user-account"
    assert user.uri == "user-account:CORP\\jsmith"

    reg = artifact_for_pher_key("pher:reg://HKCU\\Software\\Run\\evil")
    assert reg.type == "windows-registry-key"
    assert reg.uri == "windows-registry-key:HKCU\\Software\\Run\\evil"

    task = artifact_for_pher_key("pher:task://\\Microsoft\\Windows\\evil_task")
    assert task.type == "windows-registry-key"
    assert "scheduled-task" in task.uri
