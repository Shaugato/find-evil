"""Live verification battery — runtime evidence for doc-claimed behaviours.

Checks (each prints PASS/FAIL + evidence):
  1. decay        — pheromone tau on a test key actually decreases over time
  2. shapley      — a fresh multi-sensor consensus entry carries non-trivial
                    shapley_attribution naming both agents
  3. stix_live    — stix.bundle MCP tool emits a STIX 2.1 bundle from the
                    latest real finding
  4. ocsf_live    — ocsf.finding MCP tool emits class_uid=2004 from a finding
  5. cacao_signed — most recent CACAO ledger entry records a signature fpr
  6. dedupe       — publishing the same event twice does not double-count
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.request

import nats
from fastmcp import Client

MCP_URL = "http://127.0.0.1:9310/mcp"
DASH = "http://127.0.0.1:9400"
NATS_URL = "nats://127.0.0.1:4222"
SUBJ = "find.raw.verify.battery"

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, evidence: str) -> None:
    RESULTS.append((name, ok, evidence))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {evidence}", flush=True)


def http_json(path: str):
    with urllib.request.urlopen(f"{DASH}{path}", timeout=10) as r:
        return json.loads(r.read())


def ev(source, sensor, body, off, anchor, host="verify-battery"):
    return {"source": source, "sensor": sensor,
            "event_time_ns": anchor + off * 1_000_000,
            "ingest_time_ns": time.monotonic_ns(), "host_id": host, "body": body}


def anchor_ns():
    return ((time.time_ns() + 2_000_000_000) // 1_000_000_000) * 1_000_000_000


async def publish(js, events):
    for e in events:
        await js.publish(SUBJ, json.dumps(e).encode())


async def read_pher(client: Client, ip: str):
    res = await client.read_resource(f"bb://ioc/ip/{ip}")
    for item in res:
        if getattr(item, "text", None):
            return json.loads(item.text)
    return {}


async def main() -> None:
    nc = await nats.connect(NATS_URL, user="findevil_writer", password="change-me")
    js = nc.jetstream(domain="findevil")

    async with Client(MCP_URL) as client:
        # ------------------------------------------------ 1. decay
        # Doc Part 7.1.1: decay applies only when Bel(evil) < 0.15; higher
        # belief reinforces (no decay). Verify BOTH halves of that contract.
        ip_low, ip_high = "198.51.100.140", "198.51.100.144"
        a = anchor_ns()
        await publish(js, [
            # benign-ish event -> low belief -> must decay
            ev("zeek", "decay-low", {"kind": "conn", "id.resp_h": ip_low,
                "id.resp_p": 443, "proto": "tcp"}, 0, a),
            # strong corroborated evil -> bel >= 0.15 -> must reinforce (no decay)
            ev("suricata", "decay-high-a", {"kind": "alert", "dest_ip": ip_high,
                "alert": {"signature_id": 9, "signature": "p", "category": "t", "severity": 2}}, 40, a),
            ev("edr", "decay-high-b", {"kind": "behavior", "verdict": "malicious", "score": 0.7,
                "techniques": [], "indicators": {"ip": ip_high}}, 80, a),
        ])
        await asyncio.sleep(8)
        low0 = float((await read_pher(client, ip_low)).get("tau", 0.0))
        high0 = float((await read_pher(client, ip_high)).get("tau", 0.0))
        await asyncio.sleep(20)
        low1 = float((await read_pher(client, ip_low)).get("tau", 0.0))
        high1 = float((await read_pher(client, ip_high)).get("tau", 0.0))
        decayed = 0 <= low1 < low0
        reinforced = abs(high1 - high0) < 1e-6
        record("decay", decayed and reinforced,
               f"low-bel tau {low0:.4f}->{low1:.4f} (decayed={decayed}); "
               f"high-bel tau {high0:.4f}->{high1:.4f} (held={reinforced})")

        # ------------------------------------------------ 2. shapley (live)
        ip2 = "198.51.100.141"
        a = anchor_ns()
        await publish(js, [
            ev("suricata", "shap-a", {"kind": "alert", "dest_ip": ip2,
                "alert": {"signature_id": 9, "signature": "shap", "category": "t", "severity": 2}}, 0, a),
            ev("edr", "shap-b", {"kind": "behavior", "verdict": "malicious", "score": 0.7,
                "techniques": ["T1071.001"], "indicators": {"ip": ip2}}, 40, a),
        ])
        deadline = time.time() + 30
        shap = None
        while time.time() < deadline and shap is None:
            await asyncio.sleep(3)
            for row in http_json("/api/ledger/recent?n=20"):
                e = row.get("entry") or {}
                if (e.get("primary_artifact_key") == f"pher:ip:{ip2}"
                        and e.get("agent_id") == "swarm.consensus"):
                    shap = (e.get("consensus") or {}).get("shapley_attribution")
                    break
        ok = bool(shap) and len(shap) == 2 and all(v > 0 for v in shap.values())
        record("shapley", ok, f"consensus shapley_attribution={shap}")

        # ------------------------------------------------ 3. STIX live
        res = await client.call_tool("stix.bundle", {"commands": [{"target": {"seq": -1}}]})
        data = res.data or {}
        bundle = data.get("bundle") or {}
        objs = bundle.get("objects", [])
        types = {o.get("type") for o in objs}
        ok = data.get("ok") is True and bundle.get("type") == "bundle" and "indicator" in types
        record("stix_live", ok, f"bundle objects={sorted(types)} count={len(objs)}")

        # ------------------------------------------------ 4. OCSF live
        res = await client.call_tool("ocsf.finding", {"commands": [{"target": {"seq": -1}}]})
        data = res.data or {}
        finding = data.get("finding") or data.get("ocsf") or {}
        ok = data.get("ok") is True and finding.get("class_uid") == 2004
        record("ocsf_live", ok,
               f"class_uid={finding.get('class_uid')} category_uid={finding.get('category_uid')}")

        # ------------------------------------------------ 5. CACAO signed
        rows = http_json("/api/ledger/recent?n=200")
        sig_fpr = None
        for row in rows:
            e = row.get("entry") or {}
            trace = e.get("reasoning_trace") or [{}]
            params = (trace[0] or {}).get("params") or {}
            if "signature_fpr" in params:
                sig_fpr = params["signature_fpr"]
                break
        record("cacao_signed", bool(sig_fpr),
               f"latest cacao entry signature_fpr={str(sig_fpr)[:20]}…" if sig_fpr
               else "no cacao execution entry in recent 200 (run demo to generate)")

        # ------------------------------------------------ 6. dedupe
        # An identical event (same event_id) published twice must be routed to
        # the ledger-dupe stream, not double-counted into consensus.
        async def dupe_msgs() -> int:
            si = await js.stream_info("ledger-dupe")
            return int(si.state.messages)

        before_dupes = await dupe_msgs()
        ip3 = "198.51.100.142"
        a = anchor_ns()
        dup = ev("edr", "dupe-probe", {"kind": "behavior", "verdict": "suspicious", "score": 0.55,
                 "techniques": [], "indicators": {"ip": ip3}}, 0, a)
        dup["event_id"] = f"verify-battery-dup-{a}"
        await publish(js, [dup, dup])  # identical event twice
        await asyncio.sleep(8)
        after_dupes = await dupe_msgs()
        st = await read_pher(client, ip3)
        div = int(st.get("sensor_diversity", 0))
        ok = after_dupes > before_dupes and div <= 1
        record("dedupe",
               ok,
               f"ledger-dupe stream {before_dupes}->{after_dupes}; "
               f"sensor_diversity={div} (replay suppressed)")

    await nc.drain()

    fails = [r for r in RESULTS if not r[1]]
    print(f"\n=== BATTERY: {len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
    raise SystemExit(1 if fails else 0)


asyncio.run(main())
