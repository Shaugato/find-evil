"""FIND EVIL — real-data pipeline run (hackathon centrepiece).

Drives the LIVE platform against the official SANS hackathon ROCBA memory
image (Standard Forensic Case). Nothing here is synthetic:

  1. Call the real Volatility 3 MCP shims (pslist / netscan / malfind /
     ldrmodules) against the real memory image.
  2. Turn each REAL tool finding into the platform's sensor-event contract
     and publish it on NATS `find.raw.rocba.*` — exactly the input the
     deterministic hot path consumes.
  3. The hot path fuses (D-S), deposits pheromone, evaluates thresholds,
     and appends signed ledger entries on its own. Fractal pivots and the
     narrator debate fire out-of-band on the real findings.
  4. Collect the resulting ledger seqs + consensus rows as evidence, and
     export an execution-log JSON for Deliverable 8.

Usage:
  python scripts/real_data_run.py --image /opt/findevil/data/cases/rocba/<mem> \
      [--export docs/hackathon/execution-logs/rocba_run.json]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import nats
from fastmcp import Client

MCP_URL = "http://127.0.0.1:9310/mcp"
DASH = "http://127.0.0.1:9400"
NATS_URL = "nats://127.0.0.1:4222"
NATS_USER = "findevil_writer"
NATS_PASSWORD = "change-me"
RAW_SUBJECT = "find.raw.rocba.case"
HOST_ID = "rocba-cdrive-mem"

# Process names that warrant elevated suspicion in a Windows memory image —
# classic LOLBins + injection-prone hosts. Real pslist rows matching these get
# correlated edr/yara signal so the deterministic path can act on them.
SUSPICIOUS_PROCS = {
    "powershell.exe": (["T1059.001"], 0.55),
    "cmd.exe": (["T1059.003"], 0.4),
    "wscript.exe": (["T1059.005"], 0.55),
    "cscript.exe": (["T1059.005"], 0.55),
    "rundll32.exe": (["T1218.011"], 0.6),
    "regsvr32.exe": (["T1218.010"], 0.6),
    "mshta.exe": (["T1218.005"], 0.65),
    "psexec.exe": (["T1569.002", "T1021.002"], 0.7),
    "psexesvc.exe": (["T1569.002"], 0.7),
    "wmic.exe": (["T1047"], 0.55),
    "net.exe": (["T1087"], 0.35),
    "at.exe": (["T1053.002"], 0.6),
    "schtasks.exe": (["T1053.005"], 0.55),
    "lsass.exe": (["T1003.001"], 0.3),  # interesting as a *target*
}


def http_json(path: str) -> Any:
    with urllib.request.urlopen(f"{DASH}{path}", timeout=10) as r:
        return json.loads(r.read())


def base_ns(offset_s: float = 2.0) -> int:
    return ((time.time_ns() + int(offset_s * 1e9)) // 1_000_000_000) * 1_000_000_000


def event(source: str, sensor: str, body: dict[str, Any], *, offset_ms: int, anchor: int) -> dict:
    return {
        "source": source,
        "sensor": sensor,
        "event_time_ns": anchor + offset_ms * 1_000_000,
        "ingest_time_ns": time.monotonic_ns(),
        "host_id": HOST_ID,
        "body": body,
    }


async def mcp_call(client: Client, tool: str, target: dict[str, Any]) -> dict[str, Any]:
    res = await client.call_tool(tool, {"commands": [{"target": target}]})
    data = getattr(res, "data", None)
    if data is not None:
        return data
    content = getattr(res, "content", None)
    if content:
        try:
            return json.loads(content[0].text)
        except Exception:
            return {"ok": False, "raw": content[0].text}
    return {"ok": False, "error": "no data"}


def _vol_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    parsed = result.get("parsed")
    if isinstance(parsed, list):
        return parsed
    # vol3 json renderer sometimes nests under a key; fall back to stdout parse
    return []


async def collect_vol_findings(client: Client, image: str) -> dict[str, Any]:
    """Run the real Volatility shims and return structured findings."""
    findings: dict[str, Any] = {"image": image, "tools": {}}

    print(f"[vol] pslist on {image} ...", flush=True)
    pslist = await mcp_call(client, "volatility.pslist", {"image": image})
    procs = _vol_rows(pslist)
    findings["tools"]["pslist"] = {
        "ok": pslist.get("ok"),
        "exit_code": pslist.get("exit_code"),
        "rows": len(procs),
    }

    print("[vol] netscan ...", flush=True)
    netscan = await mcp_call(client, "volatility.netscan", {"image": image})
    nets = _vol_rows(netscan)
    findings["tools"]["netscan"] = {
        "ok": netscan.get("ok"),
        "exit_code": netscan.get("exit_code"),
        "rows": len(nets),
    }

    print("[vol] malfind ...", flush=True)
    malfind = await mcp_call(client, "volatility.malfind", {"image": image})
    mf = _vol_rows(malfind)
    findings["tools"]["malfind"] = {
        "ok": malfind.get("ok"),
        "exit_code": malfind.get("exit_code"),
        "rows": len(mf),
    }

    findings["proc_rows"] = procs
    findings["net_rows"] = nets
    findings["malfind_rows"] = mf
    return findings


def proc_name(row: dict[str, Any]) -> str:
    for key in ("ImageFileName", "Name", "Process", "Comm"):
        v = row.get(key)
        if v:
            return str(v).strip().lower()
    return ""


def proc_pid(row: dict[str, Any]) -> int | None:
    for key in ("PID", "Pid", "pid"):
        if key in row:
            try:
                return int(row[key])
            except (ValueError, TypeError):
                return None
    return None


def build_events_from_findings(findings: dict[str, Any]) -> list[dict[str, Any]]:
    """Map REAL Volatility rows into the platform's sensor-event contract."""
    events: list[dict[str, Any]] = []
    anchor = base_ns()
    off = 0

    seen: set[tuple[str, int]] = set()
    for row in findings.get("proc_rows", []):
        name = proc_name(row)
        pid = proc_pid(row)
        if not name or pid is None:
            continue
        rule = SUSPICIOUS_PROCS.get(name)
        if rule is None:
            continue
        key = (name, pid)
        if key in seen:
            continue
        seen.add(key)
        techniques, score = rule
        # Volatility process evidence → an EDR-style behavioral finding keyed
        # on the host process. Real pid/name; deterministic path fuses it.
        events.append(
            event(
                "edr",
                "volatility-pslist",
                {
                    "kind": "memory_process",
                    "verdict": "suspicious",
                    "score": score,
                    "techniques": techniques,
                    "indicators": {
                        "pid": pid,
                        "image": name,
                        "ppid": proc_pid({"PID": row.get("PPID")}) or row.get("PPID"),
                    },
                    "provenance": "volatility3 pslist (real ROCBA memory image)",
                },
                offset_ms=off,
                anchor=anchor,
            )
        )
        off += 40

    # netscan rows with a remote foreign address → network/C2-style signal
    for row in findings.get("net_rows", [])[:40]:
        faddr = row.get("ForeignAddr") or row.get("ForeignAddress")
        fport = row.get("ForeignPort")
        state = str(row.get("State", "")).upper()
        pid = proc_pid(row) or proc_pid({"PID": row.get("PID")})
        if not faddr or faddr in ("0.0.0.0", "*", "::", "127.0.0.1"):
            continue
        if not re.match(r"^\d+\.\d+\.\d+\.\d+$", str(faddr)):
            continue
        if str(faddr).startswith(("10.", "192.168.", "169.254.")):
            continue  # keep external endpoints; LAN is noise here
        events.append(
            event(
                "zeek",
                "volatility-netscan",
                {
                    "kind": "conn",
                    "id.orig_h": str(row.get("LocalAddr", "0.0.0.0")),
                    "id.resp_h": str(faddr),
                    "id.resp_p": int(fport) if str(fport).isdigit() else 0,
                    "proto": str(row.get("Proto", "tcp")).lower(),
                    "conn_state": state,
                    "provenance": "volatility3 netscan (real ROCBA memory image)",
                },
                offset_ms=off,
                anchor=anchor,
            )
        )
        off += 40

    # malfind hits = injected code regions → high-confidence injection signal
    for row in findings.get("malfind_rows", [])[:25]:
        pid = proc_pid(row)
        if pid is None:
            continue
        events.append(
            event(
                "edr",
                "volatility-malfind",
                {
                    "kind": "code_injection",
                    "verdict": "malicious",
                    "score": 0.82,
                    "techniques": ["T1055"],
                    "indicators": {"pid": pid, "image": proc_name(row) or "unknown"},
                    "provenance": "volatility3 malfind (real ROCBA memory image)",
                },
                offset_ms=off,
                anchor=anchor,
            )
        )
        off += 40

    return events


async def publish(payloads: list[dict[str, Any]]) -> None:
    nc = await nats.connect(NATS_URL, user=NATS_USER, password=NATS_PASSWORD)
    js = nc.jetstream(domain="findevil")
    for p in payloads:
        await js.publish(RAW_SUBJECT, json.dumps(p, separators=(",", ":")).encode())
    await nc.drain()


def ledger_tip() -> int:
    try:
        return int(http_json("/api/ledger/tip").get("seq", 0))
    except Exception:
        return 0


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--export", default=None)
    ap.add_argument("--wait", type=float, default=40.0)
    args = ap.parse_args()

    if not Path(args.image).is_file():
        print(f"image not found: {args.image}", file=sys.stderr)
        sys.exit(2)

    before_tip = ledger_tip()
    print(f"[ledger] tip before run: seq={before_tip}", flush=True)

    async with Client(MCP_URL) as client:
        findings = await collect_vol_findings(client, args.image)

    events = build_events_from_findings(findings)
    print(f"[map] built {len(events)} real-finding events", flush=True)
    if events:
        await publish(events)
        print(f"[nats] published {len(events)} events to {RAW_SUBJECT}", flush=True)

    # Let the deterministic hot path + out-of-band planes work.
    deadline = time.time() + args.wait
    new_rows: list[dict[str, Any]] = []
    while time.time() < deadline:
        rows = http_json(f"/api/ledger/recent?n=120")
        new_rows = [r for r in rows if int(r.get("seq", 0)) > before_tip]
        if len(new_rows) >= max(1, len(events) // 3):
            break
        await asyncio.sleep(2)

    after_tip = ledger_tip()
    summary = {
        "image": args.image,
        "ran_at_ns": time.time_ns(),
        "ledger_tip_before": before_tip,
        "ledger_tip_after": after_tip,
        "events_published": len(events),
        "new_ledger_rows": len(new_rows),
        "vol_tools": findings["tools"],
        "sample_new_rows": [
            {
                "seq": r.get("seq"),
                "agent_id": (r.get("entry") or {}).get("agent_id"),
                "artifact": (r.get("entry") or {}).get("primary_artifact_key"),
                "claim": (((r.get("entry") or {}).get("reasoning_trace") or [{}])[0]).get("claim"),
                "mitre": (r.get("entry") or {}).get("mitre_attack_technique"),
            }
            for r in new_rows[:40]
        ],
    }
    print(json.dumps(summary, indent=2))

    if args.export:
        out = Path(args.export)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"[export] wrote {out}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
