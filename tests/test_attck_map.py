"""ATT&CK map completeness: every technique emitted by the blueprint's Appendix C."""

from __future__ import annotations

from findevil.swarm.attck_map import ATTCK_MAP, lookup


def test_every_entry_has_nonempty_actions():
    for tid, entry in ATTCK_MAP.items():
        assert entry.technique == tid
        assert entry.cacao_actions, f"{tid} has no actions"
        assert entry.mcp_tools, f"{tid} has no mcp tools"


def test_lookup_returns_none_for_unknown():
    assert lookup("T9999.999") is None


def test_key_techniques_present():
    for t in [
        "T1059.001",
        "T1003.001",
        "T1055",
        "T1071.001",
        "T1105",
        "T1486",
        "T1547.001",
        "T1053.005",
        "T1078",
        "T1566.001",
        "T1562.001",
        "T1036",
    ]:
        assert lookup(t) is not None, f"missing {t}"
