"""FOR578 CTI plane — STIX→priors parsing and Diamond Model graph (App. D)."""

from __future__ import annotations

from findevil.cti.diamond import build_diamond_graph
from findevil.cti.stix_priors import iocs_from_stix_objects, prior_for_ioc

STIX_OBJECTS = [
    {
        "type": "indicator",
        "id": "indicator--aaaa",
        "name": "C2 ip",
        "confidence": 80,
        "pattern_type": "stix",
        "pattern": "[ipv4-addr:value = '203.0.113.66']",
    },
    {
        "type": "indicator",
        "id": "indicator--bbbb",
        "name": "dropper hash + domain",
        "confidence": 60,
        "pattern_type": "stix",
        "pattern": (
            "[file:hashes.'SHA-256' = "
            "'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'"
            " OR domain-name:value = 'Evil.Example.COM']"
        ),
    },
    # Non-indicator and revoked objects must be ignored.
    {"type": "malware", "id": "malware--cccc"},
    {
        "type": "indicator",
        "id": "indicator--dddd",
        "revoked": True,
        "pattern_type": "stix",
        "pattern": "[ipv4-addr:value = '198.51.100.1']",
    },
]


def test_iocs_parsed_from_stix_patterns():
    iocs = iocs_from_stix_objects(STIX_OBJECTS)
    kinds = sorted((i.kind, i.value) for i in iocs)
    assert kinds == [
        ("domain", "evil.example.com"),
        ("hash", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
        ("ip", "203.0.113.66"),
    ]
    ip = next(i for i in iocs if i.kind == "ip")
    assert ip.confidence == 0.8
    assert ip.source_id == "indicator--aaaa"


def test_priors_are_modest_and_keyed():
    iocs = iocs_from_stix_objects(STIX_OBJECTS)
    for ioc in iocs:
        args = prior_for_ioc(ioc)
        assert args["key"].startswith(("pher:ip:", "pher:domain:", "pher:hash:"))
        assert args["sensor"] == "cti.taxii"
        # A CTI prior alone must never look like consensus-grade evidence.
        assert args["bel"] <= 0.45
        assert args["tau_max"] <= 0.35
        assert args["bel"] <= args["pl"]


def test_diamond_graph_builds_all_four_vertex_kinds():
    rows = [
        {
            "finding_id": "f-1",
            "entry": {
                "host_id": "ws-01",
                "primary_artifact_key": "ip:203.0.113.66",
                "mitre_attack_technique": ["T1071.001"],
            },
        },
        {
            "finding_id": "f-2",
            "entry": {
                "host_id": "ws-01",
                "primary_artifact_key": "proc:ws-01:4242",
                "mitre_attack_technique": ["T1059.001"],
            },
        },
    ]
    g = build_diamond_graph(rows)
    assert g["counts"]["adversary"] == 1
    assert g["counts"]["victim"] == 1
    assert g["counts"]["capability"] == 2
    # Only ip/domain/hash/url artifacts become infrastructure (proc does not).
    assert g["counts"]["infrastructure"] == 1
    kinds = {n["kind"] for n in g["nodes"]}
    assert kinds == {"adversary", "victim", "capability", "infrastructure"}
    # Every edge endpoint must exist as a node.
    node_ids = {n["id"] for n in g["nodes"]}
    assert all(e["src"] in node_ids and e["dst"] in node_ids for e in g["edges"])
