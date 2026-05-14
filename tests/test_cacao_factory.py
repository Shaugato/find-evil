"""CACAO factory — playbook is properly assembled and signed."""

from __future__ import annotations

from pathlib import Path
import uuid

from findevil.cacao.factory import build_playbook
from findevil.cacao.schema import verify_playbook


def test_factory_builds_for_known_technique(cacao_keys):
    sk_bytes, pk_bytes = cacao_keys
    frame = {
        "pher_key": "pher:ip:203.0.113.5",
        "action": "mitigate",
        "belief_evil": 0.9,
        "reports": [{"attack_techniques": ["T1071.001"]}],
    }
    target = {"type": "ipv4-addr", "value": "203.0.113.5"}
    pb = build_playbook(consensus_frame=frame, target=target, technique="T1071.001")
    assert pb.signature is not None
    assert verify_playbook(pb, expected_pk=pk_bytes)
    # Must contain at least one real actuator, plus the end sentinel.
    actuators = {s.actuator for s in pb.workflow.values()}
    assert "findevil.end" in actuators
    assert any(a.startswith("edr.") for a in actuators)
    action_steps = [s for s in pb.workflow.values() if s.actuator.startswith("edr.")]
    assert action_steps[0].commands[0]["type"] == "http-api"
    assert "POST /mcp/tools/call BODY" in action_steps[0].commands[0]["command"]


def test_factory_embeds_parent_finding_reference(cacao_keys):
    parent_id = uuid.uuid4()
    frame = {
        "pher_key": "pher:hash:" + "a" * 64,
        "action": "mitigate",
        "belief_evil": 0.9,
        "reports": [{"attack_techniques": ["T1003.001"]}],
        "parent_finding_id": str(parent_id),
    }
    pb = build_playbook(
        consensus_frame=frame,
        target={"type": "file", "hashes": {"SHA-256": "a" * 64}},
        technique="T1003.001",
    )
    refs = {r["source_name"]: r["external_id"] for r in pb.external_references}
    assert refs["findevil-ledger"] == str(parent_id)
    assert refs["MITRE ATT&CK"] == "T1003.001"


def test_factory_falls_back_to_analyst_review(cacao_keys):
    frame = {
        "pher_key": "pher:unknown:x",
        "action": "escalate_human",
        "belief_evil": 0.5,
        "reports": [],
    }
    pb = build_playbook(consensus_frame=frame, target={"type": "x", "value": "x"})
    actuators = {s.actuator for s in pb.workflow.values()}
    assert "analyst.review" in actuators
