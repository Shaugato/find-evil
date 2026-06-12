"""Export ledger entries to sanitised JSON for Deliverable 8.

Reads the live ledger read-only and emits a structured, public-safe JSON of
entries (finding_id, timestamps, agent, artifact, reasoning trace, MITRE,
chain-of-custody). Never emits keys or raw evidence bytes.

Usage:
  python scripts/export_ledger.py --since 936 --out docs/hackathon/execution-logs/ledger_export.json
  python scripts/export_ledger.py --last 40 --out ...
"""

from __future__ import annotations

import argparse
import asyncio
import json
import urllib.request
from pathlib import Path

from findevil.ledger.reader import LedgerReader

DASH = "http://127.0.0.1:9400"


def _rows_via_api(last: int) -> list[dict]:
    """Read recent entries through the dashboard API (findevil-owned read path).

    Avoids opening the ledger SQLite directly, which — from a non-findevil
    user — would create foreign-owned WAL sidecars the services can't reopen.
    """
    with urllib.request.urlopen(f"{DASH}/api/ledger/recent?n={min(max(last, 1), 200)}", timeout=10) as r:
        rows = json.loads(r.read())
    return rows if isinstance(rows, list) else []

# Fields that are safe and useful to publish per entry.
_KEEP = (
    "schema_version",
    "agent_id",
    "agent_version",
    "host_id",
    "primary_artifact_key",
    "confidence",
    "severity",
    "mitre_attack_technique",
    "method",
    "reasoning_trace",
    "evidence_refs",
    "chain_of_custody",
    "consensus",
    "emitted_ns",
)


def _sanitise(entry: dict) -> dict:
    out = {k: entry[k] for k in _KEEP if k in entry}
    # Truncate any oversized free-text in reasoning traces.
    for step in out.get("reasoning_trace", []) or []:
        claim = step.get("claim")
        if isinstance(claim, str) and len(claim) > 600:
            step["claim"] = claim[:600] + "…"
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=None, help="export seq > SINCE")
    ap.add_argument("--last", type=int, default=50, help="export last N (if --since unset)")
    ap.add_argument("--via-api", action="store_true",
                    help="read through the dashboard API instead of opening SQLite")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.via_api:
        rows = _rows_via_api(200 if args.since is not None else args.last)
    else:
        async def _load():
            r = LedgerReader()
            try:
                return await r.recent(1000 if args.since is not None else args.last)
            finally:
                r.close()

        rows = asyncio.run(_load())
    if args.since is not None:
        rows = [r for r in rows if int(r.get("seq", 0)) > args.since]
    rows = sorted(rows, key=lambda r: r.get("seq", 0))

    export = {
        "export_kind": "findevil_ledger_sanitised",
        "entry_count": len(rows),
        "entries": [
            {
                "seq": r.get("seq"),
                "finding_id": r.get("finding_id"),
                "entry_hash": r.get("entry_hash"),
                "ts_ns": r.get("ts_ns"),
                "entry": _sanitise(r.get("entry") or {}),
            }
            for r in rows
        ],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(export, indent=2), encoding="utf-8")
    print(f"exported {len(rows)} entries -> {out}")


if __name__ == "__main__":
    main()
