"""Fire a strong multi-sensor malicious scenario to trigger a real CACAO
mitigation, then confirm the executed playbook was signature-verified
(signature_fpr recorded) in the ledger."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import urllib.request

import nats

NATS_URL = "nats://127.0.0.1:4222"
SUBJ = "find.raw.verify.cacao"
DASH = "http://127.0.0.1:9400"


def http_json(path: str):
    with urllib.request.urlopen(f"{DASH}{path}", timeout=10) as r:
        return json.loads(r.read())


def ev(source, sensor, body, off, anchor):
    return {"source": source, "sensor": sensor,
            "event_time_ns": anchor + off * 1_000_000,
            "ingest_time_ns": time.monotonic_ns(), "host_id": "verify-cacao", "body": body}


async def main() -> None:
    sha = hashlib.sha256(f"cacao-probe-{time.time_ns()}".encode()).hexdigest()
    artifact = f"pher:hash:{sha}"
    a = ((time.time_ns() + 2_000_000_000) // 1_000_000_000) * 1_000_000_000
    # Five corroborating malicious sensors on one hash -> belief >> 0.80,
    # sensor_diversity 5 -> action=mitigate -> CACAO playbook fires.
    events = [
        ev("sysmon", "cacao-sysmon", {"EventID": 1, "event_data": {
            "Image": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
            "CommandLine": "powershell -enc <safe>", "ProcessId": "6201",
            "Hashes": f"SHA256={sha}"}}, 0, a),
        ev("yara", "cacao-yara", {"rule": "SAFE_STAGE_LOADER", "sha256": sha,
            "tags": ["apt", "loader"], "namespace": "verify"}, 40, a),
        ev("edr", "cacao-edr", {"kind": "behavior", "verdict": "malicious", "score": 0.97,
            "techniques": ["T1059.001"], "indicators": {"sha256": sha, "pid": 6201}}, 80, a),
        ev("edr", "cacao-amsi", {"kind": "amsi_script_block", "verdict": "malicious",
            "score": 0.93, "techniques": ["T1059.001"], "indicators": {"sha256": sha}}, 120, a),
        ev("suricata", "cacao-suri", {"kind": "alert", "dest_ip": "203.0.113.61",
            "alert": {"signature_id": 910001, "signature": "C2", "category": "trojan",
                      "severity": 1}}, 160, a),
    ]

    before = int(http_json("/api/ledger/tip").get("seq", 0))
    nc = await nats.connect(NATS_URL, user="findevil_writer", password="change-me")
    js = nc.jetstream(domain="findevil")
    for e in events:
        await js.publish(SUBJ, json.dumps(e).encode())
    await nc.drain()
    print(f"published 5-sensor malicious scenario on {artifact[:32]}…; tip before={before}")

    deadline = time.time() + 40
    mitigate_seen = False
    sig_fpr = None
    while time.time() < deadline:
        await asyncio.sleep(3)
        rows = http_json("/api/ledger/recent?n=60")
        for row in rows:
            e = row.get("entry") or {}
            claim = (((e.get("reasoning_trace") or [{}])[0]).get("claim") or "")
            if e.get("primary_artifact_key") == artifact and "action=mitigate" in claim:
                mitigate_seen = True
            params = (((e.get("reasoning_trace") or [{}])[0]).get("params") or {})
            if "signature_fpr" in params:
                sig_fpr = params["signature_fpr"]
        if mitigate_seen and sig_fpr:
            break

    print(f"mitigate consensus fired: {mitigate_seen}")
    print(f"cacao executed entry signature_fpr: {sig_fpr}")
    ok = mitigate_seen and bool(sig_fpr)
    print(f"=== CACAO {'PASS' if ok else 'PARTIAL'} ===")
    raise SystemExit(0 if ok else 1)


asyncio.run(main())
