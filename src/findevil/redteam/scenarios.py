"""Atomic Red Team scenarios (blueprint Part 13.1 — Table 6).

Each scenario references a concrete Atomic Test (T####.###) plus the MITRE ATT&CK
technique we expect the swarm to flag within `detection_budget_ms`. Scenarios are
signed with the Ed25519 `redteam_key` to prevent a compromised agent from
fabricating success.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    id: str
    technique: str  # MITRE ATT&CK
    atomic_id: str  # invoke-atomicredteam test id (e.g. "T1059.001-1")
    description: str
    detection_budget_ms: int = 5_000
    mitigation_budget_ms: int = 30_000
    platform: str = "windows"
    requires_elevation: bool = False


def default_scenarios() -> list[Scenario]:
    return [
        Scenario(
            id="atomic-t1059-001-encoded-ps",
            technique="T1059.001",
            atomic_id="T1059.001-1",
            description="PowerShell EncodedCommand payload",
        ),
        Scenario(
            id="atomic-t1003-001-lsass",
            technique="T1003.001",
            atomic_id="T1003.001-1",
            description="LSASS memory dump via comsvcs.dll MiniDump",
            requires_elevation=True,
        ),
        Scenario(
            id="atomic-t1055-remote-thread",
            technique="T1055",
            atomic_id="T1055-1",
            description="CreateRemoteThread process injection",
            requires_elevation=True,
        ),
        Scenario(
            id="atomic-t1071-001-c2-http",
            technique="T1071.001",
            atomic_id="T1071.001-1",
            description="HTTP-beaconing simulation with jitter",
        ),
        Scenario(
            id="atomic-t1105-certutil",
            technique="T1105",
            atomic_id="T1105-4",
            description="certutil download of remote payload",
        ),
        Scenario(
            id="atomic-t1486-ransom-sim",
            technique="T1486",
            atomic_id="T1486-1",
            description="Ransomware-style mass rename (simulation)",
        ),
        Scenario(
            id="atomic-t1547-001-run-key",
            technique="T1547.001",
            atomic_id="T1547.001-1",
            description="Persistence via HKCU Run key",
        ),
        Scenario(
            id="atomic-t1053-005-scheduled-task",
            technique="T1053.005",
            atomic_id="T1053.005-1",
            description="Scheduled task creation",
        ),
        Scenario(
            id="atomic-t1078-type3-logon",
            technique="T1078",
            atomic_id="T1078-1",
            description="Anomalous Type-3/10 logons",
        ),
        Scenario(
            id="atomic-t1566-001-phish-macro",
            technique="T1566.001",
            atomic_id="T1566.001-1",
            description="winword → powershell spawn chain",
        ),
        Scenario(
            id="atomic-t1562-001-defender-off",
            technique="T1562.001",
            atomic_id="T1562.001-1",
            description="Defender AV disabled via PowerShell",
            requires_elevation=True,
        ),
        Scenario(
            id="atomic-t1036-masquerade",
            technique="T1036",
            atomic_id="T1036-1",
            description="Masqueraded PE (svchost.exe in user dir)",
        ),
    ]
