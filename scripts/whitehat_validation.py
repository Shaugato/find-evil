"""Safe end-to-end validation harness for a live FIND EVIL instance.

This script publishes benign synthetic telemetry to the local NATS JetStream
raw-firehose and verifies the expected dashboard API, MCP blackboard, ledger,
and CACAO side effects. It never executes malware or touches external systems.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

import nats
from fastmcp import Client

BASE_URL = "http://127.0.0.1:9400"
MCP_URL = "http://127.0.0.1:9310/mcp"
NATS_URL = "nats://127.0.0.1:4222"
NATS_USER = "findevil_writer"
NATS_PASSWORD = "change-me"
RAW_SUBJECT = "find.raw.whitehat.validation"
HOST_ID = "victim-win11-validation-lab"


@dataclass
class Check:
    name: str
    status: str
    evidence: dict[str, Any] = field(default_factory=dict)
    gap: str | None = None


def safe_sha(seed: str) -> str:
    token = "".join(ch for ch in seed.lower() if ch in "0123456789abcdef")[:8]
    token = (token or "deadbeef").ljust(8, "0")
    return token * 8


def http_json(path: str, timeout: float = 5.0) -> Any:
    with urllib.request.urlopen(BASE_URL + path, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def service_lines() -> list[str]:
    names = [
        "valkey-findevil.service",
        "nats-findevil.service",
        "findevil-dashboard.service",
        "findevil-mcp.service",
        "findevil-ingest.service",
        "findevil-cacao.service",
        "findevil-watcher.service",
        "findevil-narrator.service",
        "findevil-decay.service",
        "findevil-verify.timer",
    ]
    out = subprocess.run(
        ["systemctl", "is-active", *names],
        check=False,
        text=True,
        capture_output=True,
    )
    return out.stdout.splitlines()


def findevil_json(*args: str) -> Any:
    out = subprocess.run(
        ["/opt/findevil/venv/bin/findevil", *args],
        check=False,
        text=True,
        capture_output=True,
    )
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"exit_code": out.returncode, "stdout": out.stdout, "stderr": out.stderr}


def event(
    source: str,
    sensor: str,
    body: dict[str, Any],
    *,
    event_id: str | None = None,
    offset_ms: int = 0,
    base_ns: int | None = None,
) -> dict[str, Any]:
    ts_ns = (base_ns if base_ns is not None else time.time_ns() + 1_000_000_000) + (
        offset_ms * 1_000_000
    )
    return {
        **({"event_id": event_id} if event_id else {}),
        "source": source,
        "sensor": sensor,
        "event_time_ns": ts_ns,
        "ingest_time_ns": time.monotonic_ns(),
        "host_id": HOST_ID,
        "body": body,
    }


def old_event(source: str, sensor: str, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": source,
        "sensor": sensor,
        "event_time_ns": time.time_ns() - 10_000_000_000,
        "ingest_time_ns": time.monotonic_ns(),
        "host_id": HOST_ID,
        "body": body,
    }


async def publish(payloads: list[bytes | dict[str, Any]]) -> None:
    nc = await nats.connect(NATS_URL, user=NATS_USER, password=NATS_PASSWORD)
    js = nc.jetstream(domain="findevil")
    for payload in payloads:
        data = payload if isinstance(payload, bytes) else json.dumps(payload, separators=(",", ":")).encode()
        await js.publish(RAW_SUBJECT, data)
    await nc.drain()


def recent_rows(n: int = 80) -> list[dict[str, Any]]:
    rows = http_json(f"/api/ledger/recent?n={n}")
    return rows if isinstance(rows, list) else []


def rows_for_artifact(artifact_key: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        entry = row.get("entry") or {}
        if entry.get("primary_artifact_key") == artifact_key:
            out.append(row)
    return out


def consensus_rows(artifact_key: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows_for_artifact(artifact_key, rows)
        if (row.get("entry") or {}).get("agent_id") == "swarm.consensus"
    ]


def row_claim(row: dict[str, Any]) -> str:
    trace = (row.get("entry") or {}).get("reasoning_trace") or []
    return str((trace[0] if trace else {}).get("claim", ""))


async def mcp_read_json(uri: str) -> Any:
    async with Client(MCP_URL) as client:
        payload = await client.read_resource(uri)
    if not payload:
        return None
    return json.loads(payload[0].text)


async def mcp_tool_verify() -> dict[str, Any]:
    async with Client(MCP_URL) as client:
        result = await client.call_tool("ledger.verify", {"seq_from": 1})
    return result.data or {}


async def wait_until(predicate, *, timeout_s: float = 20.0, interval_s: float = 1.0):
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        last = predicate()
        if last:
            return last
        await asyncio.sleep(interval_s)
    return last


async def scenario_mitigation(seed: str) -> Check:
    sha = safe_sha(seed)
    artifact = f"pher:hash:{sha}"
    base_ns = ((time.time_ns() + 2_000_000_000) // 1_000_000_000) * 1_000_000_000 + 100_000_000
    before_tip = http_json("/api/ledger/tip")
    before_instances = {
        row.get("instance_id")
        for row in (http_json("/api/cacao/instances").get("instances") or [])
    }
    await publish(
        [
            event(
                "sysmon",
                "sysmon-validation",
                {
                    "EventID": 1,
                    "event_data": {
                        "Image": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                        "ParentImage": "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
                        "CommandLine": "powershell.exe -NoProfile -EncodedCommand <safe-validation-payload>",
                        "ProcessId": "6201",
                        "User": "LAB\\analyst",
                        "Hashes": f"SHA256={sha}",
                    },
                },
                base_ns=base_ns,
            ),
            event(
                "yara",
                "yara-validation",
                {
                    "rule": "FIND_EVIL_SAFE_STAGE_LOADER",
                    "sha256": sha,
                    "tags": ["loader", "apt"],
                    "namespace": "safe_validation",
                },
                offset_ms=50,
                base_ns=base_ns,
            ),
            event(
                "edr",
                "edr-behavior-validation",
                {
                    "kind": "behavior",
                    "verdict": "malicious",
                    "score": 0.97,
                    "techniques": ["T1059.001", "T1566.001"],
                    "indicators": {
                        "sha256": sha,
                        "pid": 6201,
                        "image": "powershell.exe",
                        "ip": "203.0.113.61",
                        "domain": f"stage-{seed}.safe-example.invalid",
                    },
                },
                offset_ms=100,
                base_ns=base_ns,
            ),
            event(
                "edr",
                "edr-amsi-validation",
                {
                    "kind": "amsi_script_block",
                    "verdict": "malicious",
                    "score": 0.93,
                    "techniques": ["T1059.001"],
                    "indicators": {"sha256": sha, "pid": 6201, "image": "powershell.exe"},
                },
                offset_ms=150,
                base_ns=base_ns,
            ),
            event(
                "suricata",
                "suricata-validation",
                {
                    "kind": "alert",
                    "dest_ip": "203.0.113.61",
                    "alert": {
                        "signature_id": 910001,
                        "signature": "FIND EVIL safe C2 validation",
                        "category": "A Network Trojan was detected",
                        "severity": 1,
                    },
                },
                offset_ms=200,
                base_ns=base_ns,
            ),
            event(
                "zeek",
                "zeek-validation",
                {
                    "kind": "conn",
                    "id.orig_h": "10.10.5.61",
                    "id.resp_h": "203.0.113.61",
                    "id.resp_p": 443,
                    "proto": "tcp",
                    "duration": 12.5,
                    "orig_bytes": 8192,
                    "resp_bytes": 2048,
                },
                offset_ms=250,
                base_ns=base_ns,
            ),
        ]
    )

    def _ready():
        rows = recent_rows(100)
        hits = consensus_rows(artifact, rows)
        cacao_instances = http_json("/api/cacao/instances").get("instances") or []
        new_cacao = [row for row in cacao_instances if row.get("instance_id") not in before_instances]
        if hits and new_cacao:
            return rows, hits, new_cacao
        return None

    ready = await wait_until(_ready, timeout_s=25)
    after_tip = http_json("/api/ledger/tip")
    pher = await mcp_read_json(f"bb://ioc/hash/{sha}")
    if not ready:
        return Check(
            "mitigation_path",
            "FAIL",
            {"target_sha": sha, "before_tip": before_tip, "after_tip": after_tip, "mcp_hash": pher},
            "Mitigation scenario did not produce both a consensus ledger row and CACAO instance.",
        )
    _rows, hits, new_cacao = ready
    action_claim = row_claim(hits[0])
    ok = "action=mitigate" in action_claim and after_tip.get("seq", 0) > before_tip.get("seq", 0)
    return Check(
        "mitigation_path",
        "PASS" if ok else "FAIL",
        {
            "target_sha": sha,
            "before_seq": before_tip.get("seq"),
            "after_seq": after_tip.get("seq"),
            "consensus_seq": hits[0].get("seq"),
            "consensus_claim": action_claim,
            "mcp_hash": pher,
            "new_cacao_instances": new_cacao[:3],
        },
        None if ok else "Mitigation evidence exists but action or ledger advance did not match expectations.",
    )


async def scenario_conflict(seed: str) -> Check:
    sha = safe_sha("cf" + seed)
    artifact = f"pher:hash:{sha}"
    base_ns = ((time.time_ns() + 2_000_000_000) // 1_000_000_000) * 1_000_000_000 + 100_000_000
    await publish(
        [
            event(
                "yara",
                "yara-conflict-high",
                {
                    "rule": "FIND_EVIL_SAFE_HIGH_CONFIDENCE",
                    "sha256": sha,
                    "tags": ["apt", "loader"],
                    "namespace": "safe_validation",
                },
                base_ns=base_ns,
            ),
            event(
                "edr",
                "edr-conflict-low",
                {
                    "kind": "baseline_noise",
                    "verdict": "benign",
                    "score": 0.01,
                    "techniques": [],
                    "indicators": {"sha256": sha, "image": "chrome.exe"},
                },
                offset_ms=80,
                base_ns=base_ns,
            ),
        ]
    )

    def _ready():
        hits = consensus_rows(artifact, recent_rows(100))
        return hits if hits else None

    hits = await wait_until(_ready, timeout_s=20)
    if not hits:
        return Check(
            "conflict_ledger_path",
            "FAIL",
            {"sha256": sha},
            "No conflict ledger consensus row was produced.",
        )
    claim = row_claim(hits[0])
    status = "PASS" if "action=conflict_ledger" in claim else "FAIL"
    return Check(
        "conflict_ledger_path",
        status,
        {"sha256": sha, "consensus_seq": hits[0].get("seq"), "claim": claim},
        None if status == "PASS" else "Consensus row did not show action=conflict_ledger.",
    )


async def scenario_escalate(seed: str) -> Check:
    domain = f"escalate-{seed}.validation.invalid"
    artifact = f"pher:domain:{domain}"
    payloads = []
    base_ns = ((time.time_ns() + 2_000_000_000) // 1_000_000_000) * 1_000_000_000 + 100_000_000
    for idx, score in enumerate([0.99, 0.99, 0.01, 0.01]):
        payloads.append(
            event(
                "edr",
                f"edr-escalate-{idx}",
                {
                    "kind": "conflicting_verdict",
                    "verdict": "malicious" if score > 0.5 else "benign",
                    "score": score,
                    "techniques": ["T1059.001"] if score > 0.5 else [],
                    "indicators": {"domain": domain},
                },
                offset_ms=idx * 50,
                base_ns=base_ns,
            )
        )
    await publish(payloads)

    def _ready():
        hits = consensus_rows(artifact, recent_rows(100))
        return hits if hits else None

    hits = await wait_until(_ready, timeout_s=20)
    if not hits:
        return Check("escalate_human_path", "FAIL", {"domain": domain}, "No escalation consensus row was produced.")
    claim = row_claim(hits[0])
    status = "PASS" if "action=escalate_human" in claim else "FAIL"
    return Check(
        "escalate_human_path",
        status,
        {"domain": domain, "consensus_seq": hits[0].get("seq"), "claim": claim},
        None if status == "PASS" else "Consensus row did not show action=escalate_human.",
    )


async def scenario_late_malformed(seed: str) -> Check:
    sha = safe_sha("late" + seed)
    await publish(
        [
            old_event(
                "edr",
                "edr-late-validation",
                {
                    "kind": "late_detection",
                    "verdict": "malicious",
                    "score": 0.95,
                    "techniques": ["T1059.001"],
                    "indicators": {"sha256": sha},
                },
            ),
            b"{this is not valid json",
        ]
    )

    def _ready():
        rows = recent_rows(120)
        late = [row for row in rows if "allowed_lateness_exceeded" in json.dumps(row.get("entry", {}))]
        malformed = [row for row in rows if "decode_failed" in json.dumps(row.get("entry", {}))]
        return (late, malformed) if late and malformed else None

    found = await wait_until(_ready, timeout_s=15)
    if not found:
        return Check(
            "late_and_malformed_routing",
            "FAIL",
            {"late_sha": sha},
            "Late and malformed telemetry were not both recorded in the ledger.",
        )
    late, malformed = found
    return Check(
        "late_and_malformed_routing",
        "PASS",
        {
            "late_sha": sha,
            "late_seq": late[0].get("seq"),
            "malformed_seq": malformed[0].get("seq"),
        },
    )


async def scenario_duplicate(seed: str) -> Check:
    event_id = f"dupe-{seed}"
    base_ns = ((time.time_ns() + 2_000_000_000) // 1_000_000_000) * 1_000_000_000 + 100_000_000
    payload = event(
        "edr",
        "edr-dupe-validation",
        {
            "kind": "behavior",
            "verdict": "malicious",
            "score": 0.91,
            "techniques": ["T1059.001"],
            "indicators": {"domain": f"dupe-{seed}.validation.invalid"},
        },
        event_id=event_id,
        base_ns=base_ns,
    )
    await publish([payload, payload])

    def _ready():
        rows = recent_rows(160)
        dupes = [row for row in rows if "duplicate_event_id" in json.dumps(row.get("entry", {}))]
        return dupes if dupes else None

    dupes = await wait_until(_ready, timeout_s=20)
    if not dupes:
        return Check(
            "duplicate_event_id_routing",
            "FAIL",
            {"event_id": event_id},
            "Duplicate event id was not routed to ledger.dupe.",
        )
    return Check(
        "duplicate_event_id_routing",
        "PASS",
        {"event_id": event_id, "dupe_seq": dupes[0].get("seq")},
    )


async def narrator_check() -> Check:
    def _ready():
        rows = recent_rows(180)
        narrator = [
            row
            for row in rows
            if (row.get("entry") or {}).get("agent_id") == "narrator.judge"
        ]
        return narrator if narrator else None

    narrator = await wait_until(_ready, timeout_s=180, interval_s=5)
    status = findevil_json("status")
    if narrator:
        return Check(
            "narrator_debate_path",
            "PASS",
            {"latest_seq": narrator[0].get("seq"), "claim": row_claim(narrator[0])},
        )
    return Check(
        "narrator_debate_path",
        "FAIL",
        {"findevil_status": status},
        "No narrator.judge ledger entry was produced; local inference endpoint is unavailable or debate failed.",
    )


async def main() -> None:
    seed = f"{time.time_ns() & 0xFFFFFFFF:08x}"
    checks: list[Check] = []

    active = service_lines()
    status = findevil_json("status")
    verify = findevil_json("verify")
    checks.append(
        Check(
            "runtime_readiness",
            "PASS" if all(line == "active" for line in active) and status.get("valkey") and status.get("nats") and status.get("mcp") and status.get("dashboard") else "FAIL",
            {"systemctl": active, "findevil_status": status},
            None if status.get("inference") else "Inference endpoint is down; narrator/fractal live LLM paths cannot be fully validated.",
        )
    )
    checks.append(
        Check(
            "ledger_integrity_baseline",
            "PASS" if verify.get("ok") else "FAIL",
            {"verify": verify, "tip": http_json("/api/ledger/tip")},
        )
    )

    mcp_verify = await mcp_tool_verify()
    checks.append(
        Check(
            "mcp_blackboard_ledger_tool",
            "PASS" if mcp_verify.get("ok") else "FAIL",
            {"ledger.verify": mcp_verify, "ledger_tip_resource": await mcp_read_json("bb://ledger/tip")},
        )
    )

    checks.append(await scenario_mitigation(seed))
    checks.append(await scenario_conflict(seed))
    checks.append(await scenario_escalate(seed))
    checks.append(await scenario_late_malformed(seed))
    checks.append(await scenario_duplicate(seed))
    checks.append(await narrator_check())

    final_verify = findevil_json("verify")
    final_tip = http_json("/api/ledger/tip")
    checks.append(
        Check(
            "ledger_integrity_after_scenarios",
            "PASS" if final_verify.get("ok") else "FAIL",
            {"verify": final_verify, "tip": final_tip},
        )
    )

    report = {
        "seed": seed,
        "generated_ns": time.time_ns(),
        "checks": [check.__dict__ for check in checks],
        "summary": {
            "pass": sum(1 for c in checks if c.status == "PASS"),
            "fail": sum(1 for c in checks if c.status == "FAIL"),
            "gaps": [c.__dict__ for c in checks if c.gap],
        },
    }
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (urllib.error.URLError, ConnectionError) as exc:
        print(json.dumps({"fatal": type(exc).__name__, "error": str(exc)}, indent=2))
        raise
