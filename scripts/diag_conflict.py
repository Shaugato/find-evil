"""Publish conflict events on a test IP, then read back the pheromone state
(bel/pl/conflict_K) via the MCP blackboard to see the ACTUAL fusion numbers."""
import asyncio, json, time
import nats
from fastmcp import Client

NATS_URL = "nats://127.0.0.1:4222"
MCP_URL = "http://127.0.0.1:9310/mcp"
SUBJ = "find.raw.rocba.diag"
IP = "198.51.100.77"


def ev(source, sensor, body, off, anchor):
    return {"source": source, "sensor": sensor,
            "event_time_ns": anchor + off * 1_000_000,
            "ingest_time_ns": time.monotonic_ns(), "host_id": "diag", "body": body}


async def read_pher(client, ip):
    res = await client.read_resource(f"bb://ioc/ip/{ip}")
    for item in res:
        txt = getattr(item, "text", None)
        if txt:
            return json.loads(txt)
    return None


async def trial(js, client, label, suri_sev, edr_score):
    anchor = ((time.time_ns() + 2_000_000_000) // 1_000_000_000) * 1_000_000_000
    evs = [
        ev("suricata", "diag-mal", {"kind": "alert", "dest_ip": IP,
            "alert": {"signature_id": 1, "signature": "diag", "category": "x", "severity": suri_sev}}, 0, anchor),
        ev("edr", "diag-ben", {"kind": "reputation", "verdict": "benign", "score": edr_score,
            "techniques": [], "indicators": {"ip": IP}}, 50, anchor),
    ]
    for e in evs:
        await js.publish(SUBJ, json.dumps(e).encode())
    await asyncio.sleep(7)
    st = await read_pher(client, IP)
    print(f"[{label}] suri_sev={suri_sev} edr_score={edr_score} -> "
          f"bel={st.get('bel_evil') if st else '?'} pl={st.get('pl_evil') if st else '?'} "
          f"K={st.get('conflict_K') if st else '?'} div={st.get('sensor_diversity') if st else '?'}")


async def trial2(js, client, label, suri_sev, edr_score, ip):
    """Two evil-leaning sensors (suricata alert + edr malicious) on one IP."""
    anchor = ((time.time_ns() + 2_000_000_000) // 1_000_000_000) * 1_000_000_000
    evs = [
        ev("suricata", "diag-a", {"kind": "alert", "dest_ip": ip,
            "alert": {"signature_id": 1, "signature": "diag", "category": "x", "severity": suri_sev}}, 0, anchor),
        ev("edr", "diag-b", {"kind": "behavior", "verdict": "malicious", "score": edr_score,
            "techniques": ["T1071.001"], "indicators": {"ip": ip}}, 50, anchor),
    ]
    for e in evs:
        await js.publish(SUBJ, json.dumps(e).encode())
    await asyncio.sleep(7)
    st = await read_pher(client, ip)
    print(f"[{label}] suri_sev={suri_sev} edr_mal={edr_score} -> "
          f"bel={st.get('bel_evil') if st else '?'} K={st.get('conflict_K') if st else '?'} "
          f"(finding if bel>=0.50)")


async def main():
    nc = await nats.connect(NATS_URL, user="findevil_writer", password="change-me")
    js = nc.jetstream(domain="findevil")
    async with Client(MCP_URL) as client:
        await trial(js, client, "sev2-vs-benign", 2, 0.05)
        await trial(js, client, "sev1-vs-benign", 1, 0.05)
        await trial2(js, client, "sev2+edr0.6", 2, 0.6, "198.51.100.78")
        await trial2(js, client, "sev1+edr0.85", 1, 0.85, "198.51.100.79")
    await nc.drain()


asyncio.run(main())
