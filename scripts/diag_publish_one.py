"""Publish one strong multi-sensor event set for a test IP and watch the tip."""
import asyncio, json, time, urllib.request
import nats

NATS_URL = "nats://127.0.0.1:4222"
SUBJ = "find.raw.rocba.diag"
IP = "203.0.113.207"


def tip():
    with urllib.request.urlopen("http://127.0.0.1:9400/api/ledger/tip", timeout=5) as r:
        return json.loads(r.read()).get("seq")


def ev(source, sensor, body, off, anchor):
    return {"source": source, "sensor": sensor,
            "event_time_ns": anchor + off * 1_000_000,
            "ingest_time_ns": time.monotonic_ns(), "host_id": "diag", "body": body}


async def main():
    anchor = ((time.time_ns() + 2_000_000_000) // 1_000_000_000) * 1_000_000_000
    evs = [
        ev("suricata", "diag-sev1", {"kind": "alert", "dest_ip": IP,
            "alert": {"signature_id": 1, "signature": "diag", "category": "x", "severity": 1}}, 0, anchor),
        ev("edr", "diag-mal", {"kind": "behavior", "verdict": "malicious", "score": 0.92,
            "techniques": ["T1071.001"], "indicators": {"ip": IP}}, 40, anchor),
        ev("zeek", "diag-conn", {"kind": "conn", "id.resp_h": IP, "id.resp_p": 443, "proto": "tcp"}, 80, anchor),
    ]
    before = tip()
    print("tip before:", before)
    nc = await nats.connect(NATS_URL, user="findevil_writer", password="change-me")
    js = nc.jetstream(domain="findevil")
    for e in evs:
        ack = await js.publish(SUBJ, json.dumps(e).encode())
    print("published 3 events, last ack seq:", ack.seq)
    await nc.drain()
    for i in range(20):
        await asyncio.sleep(2)
        t = tip()
        if t and before and t > before:
            print(f"  [{i*2}s] tip MOVED: {before} -> {t}  ✓ bytewax consuming")
            return
    print("  tip did NOT move after 40s — bytewax not producing findings")


asyncio.run(main())
