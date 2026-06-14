"""Stigmergy demo — LIVE ingest of the carved ROCBA indicator → self-correction.

Feeds the REAL carved indicator 142.250.64.106 (extracted from the official SANS
ROCBA memory image by demo_rocba_carve.sh) into the live swarm as two CONFLICTING
sensor deposits — a Suricata C2 alert (malicious) vs an EDR triage (benign). The
deterministic consensus computes a Yager conflict (K), and when K crosses the
threshold it raises action=conflict_ledger — the swarm flagging that it cannot
decide and must escalate to the prosecutor/defense/judge debate. That is the
self-correction sequence, born live, on real case data, and signed into the ledger.

Repeatable (appends; the advancing tip IS the proof). No sudo. Defensive only.
Run inside WSL2:  python scripts/demo_rocba_conflict.py
"""
import asyncio, json, time, urllib.request
import nats

NATS_URL = "nats://127.0.0.1:4222"
SUBJ = "find.raw.rocba.diag"
IP = "142.250.64.106"          # REAL indicator carved from the ROCBA image


def tip():
    with urllib.request.urlopen("http://127.0.0.1:9400/api/ledger/tip", timeout=5) as r:
        return json.loads(r.read()).get("seq")


def ev(source, sensor, body, off, anchor):
    return {"source": source, "sensor": sensor,
            "event_time_ns": anchor + off * 1_000_000,
            "ingest_time_ns": time.monotonic_ns(), "host_id": "rocba-live", "body": body}


def conflict_finding(before):
    """Find the consensus finding that just landed on IP and report its conflict."""
    import sqlite3, os
    db = os.environ.get("FINDEVIL_LEDGER", "/opt/findevil/data/ledger/ledger.sqlite")
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    rows = con.execute("SELECT seq, CAST(payload AS TEXT) p FROM ledger WHERE seq>? ORDER BY seq", (before,)).fetchall()
    con.close()
    for r in rows:
        d = json.loads(r["p"])
        if d.get("agent_id") == "swarm.consensus" and d.get("primary_artifact_key", "").endswith(IP):
            c = d.get("consensus") or {}
            tr = (d.get("reasoning_trace") or [{}])[0]
            return r["seq"], c.get("conflict_K"), c.get("belief_evil"), (tr.get("params") or {}).get("action")
    return None


async def main():
    a = ((time.time_ns() + 2_000_000_000) // 1_000_000_000) * 1_000_000_000
    evs = [
        ev("suricata", "rocba-ip-rep",
           {"kind": "alert", "dest_ip": IP,
            "alert": {"signature_id": 2027758, "signature": "ET MALWARE Cobalt Strike C2",
                      "category": "trojan-activity", "severity": 1}}, 0, a),
        ev("edr", "rocba-endpoint-triage",
           {"kind": "behavior", "verdict": "benign", "score": 0.12,
            "techniques": [], "indicators": {"ip": IP}}, 40, a),
        ev("zeek", "rocba-conn",
           {"kind": "conn", "id.resp_h": IP, "id.resp_p": 443, "proto": "tcp"}, 80, a),
    ]
    before = tip()
    print(f"  carved indicator under analysis : {IP}")
    print(f"  ledger tip before               : {before}")
    print(f"  depositing 2 CONFLICTING sensor reports (Suricata=malicious, EDR=benign)…")
    nc = await nats.connect(NATS_URL, user="findevil_writer", password="change-me")
    js = nc.jetstream(domain="findevil")
    for e in evs:
        await js.publish(SUBJ, json.dumps(e).encode())
    await nc.drain()
    for i in range(15):
        await asyncio.sleep(2)
        t = tip()
        if t and before and t > before:
            print(f"  [{i*2 + 2}s] ledger tip MOVED {before} → {t}  ✓ real findings signed live")
            cf = conflict_finding(before)
            if cf:
                seq, K, bel, act = cf
                print(f"  ── SELF-CORRECTION ─────────────────────────────────────────")
                print(f"     consensus finding #{seq} on {IP}")
                print(f"       Yager conflict_K = {K:.3f}   belief_evil = {bel:.3f}")
                print(f"       action           = {act}")
                print(f"     → sensors disagree → escalated to the prosecutor/defense/")
                print(f"       judge debate (narrator), whose verdict is signed back in.")
            return
    print("  tip did not move — is the dashboard/pipeline up?")


asyncio.run(main())
