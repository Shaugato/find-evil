"""MITRE ATT&CK -> owning-agent / MCP-tool / CACAO-action mapping (Appendix C).

Used by the evaluator to populate reasoning_trace and the CACAO factory to pick
response steps. Keep this file hand-maintained; the blueprint Appendix C table is the
authoritative source.
"""

from __future__ import annotations

from typing import NamedTuple


class AttckEntry(NamedTuple):
    technique: str
    signal: str
    agent: str
    mcp_tools: tuple[str, ...]
    cacao_actions: tuple[str, ...]


ATTCK_MAP: dict[str, AttckEntry] = {
    "T1059.001": AttckEntry(
        "T1059.001",
        "Encoded PowerShell / EID 4104",
        "edr-stream",
        ("yara.scan", "regripper.run"),
        ("edr.kill_process", "edr.network_isolate"),
    ),
    "T1003.001": AttckEntry(
        "T1003.001",
        "LSASS 0x1410 + comsvcs .dmp",
        "edr-stream+yara",
        ("volatility.handles", "yara.scan"),
        ("edr.kill_process", "iam.force_reset", "yara.block_hash"),
    ),
    "T1055": AttckEntry(
        "T1055",
        "CreateRemoteThread + RX VAD",
        "volatility-ephemeral",
        ("volatility.malfind", "volatility.ldrmodules", "volatility.hollowfind"),
        ("edr.acquire_memory", "edr.network_isolate"),
    ),
    "T1071.001": AttckEntry(
        "T1071.001",
        "Beacon jitter, young domain",
        "network",
        ("zeek.query", "zeek.x509_extract", "rita.analyze"),
        ("edr.block_domain", "edr.sinkhole"),
    ),
    "T1105": AttckEntry(
        "T1105",
        "certutil/bitsadmin/curl",
        "network+edr",
        ("zeek.query", "yara.scan"),
        ("edr.block_url", "yara.quarantine"),
    ),
    "T1486": AttckEntry(
        "T1486",
        "Mass rename + shadow copy del",
        "edr+yara",
        ("mftecmd.parse", "yara.scan"),
        ("edr.network_isolate", "edr.snapshot_disk"),
    ),
    "T1547.001": AttckEntry(
        "T1547.001",
        "Run key",
        "edr",
        ("regripper.run",),
        ("edr.remove_persistence",),
    ),
    "T1053.005": AttckEntry(
        "T1053.005",
        "Scheduled task",
        "edr",
        ("evtxecmd.parse",),
        ("edr.delete_scheduled_task",),
    ),
    "T1078": AttckEntry(
        "T1078",
        "4624 Type-3/10 anomalies",
        "correlator",
        ("zeek.query", "evtxecmd.parse"),
        ("iam.disable_account",),
    ),
    "T1566.001": AttckEntry(
        "T1566.001",
        "winword->powershell chain",
        "yara+edr",
        ("ole.analyze",),
        ("yara.quarantine_file",),
    ),
    "T1562.001": AttckEntry(
        "T1562.001",
        "Defender disabled",
        "edr",
        ("evtxecmd.parse",),
        ("edr.reenable_defender",),
    ),
    "T1036": AttckEntry(
        "T1036",
        "Masquerading PE",
        "yara+edr",
        ("pescan.static", "capa.analyze"),
        ("yara.quarantine", "yara.block_hash"),
    ),
}


def lookup(technique: str) -> AttckEntry | None:
    return ATTCK_MAP.get(technique)
