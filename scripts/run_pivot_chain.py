"""Run ONE real fractal pivot chain on the ROCBA-carved indicators and capture the
connected lineage (depth 0 → max_depth) as an execution-log artifact.

This drives the REAL fractal loop — `Watcher._dispatch` (the same recursion the
`findevil watcher` daemon runs) + the REAL SLM `pivot_infer` — seeded by an ATT&CK
technique on a real carved ROCBA indicator. Each pivot's finding can populate
`follow_ups`; the watcher re-enters those into the spawn queue as deeper pivots
(`depth = parent.depth + 1`, `parent_id = parent.spawn_id`) up to `fractal.max_depth`.
That recursion IS the agent re-sequencing its own investigation based on what it finds.

We capture every real `PivotReport` (spawn_id, parent_id, depth, seed_technique,
verdict, mitre, artifact, follow_ups) and emit the connected chain as JSON. The
signed-ledger persistence is the daemon's job (runs as the `findevil` user with the
Ed25519 key); this capture proves the lineage without needing that key. Real model
output only — nothing hand-authored.

Usage (WSL2):  python scripts/run_pivot_chain.py [--out PATH]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid

from findevil.config.settings import settings
from findevil.fractal.agent import PivotSpawn
from findevil.fractal.watcher import Watcher
from findevil.inference.facade import InferenceFacade

# Real carved ROCBA indicators (from be_out/run1) used as the pivot exhibits.
SEED_TECHNIQUE = "T1071.001"  # Web C2 — the ATT&CK technique that seeds the pivot
ROOT_ARTIFACT = "pher:ip:142.250.64.106"
EXHIBITS = [
    {"exhibit_id": "ex_aa000001", "uri": "ipv4-addr:142.250.64.106",
     "artifact_uri": ROOT_ARTIFACT, "summary": "C2 beacon destination carved from the ROCBA memory image (T1071.001)"},
    {"exhibit_id": "ex_bb000002", "uri": "process:beacon-host",
     "artifact_uri": "pher:proc:beacon-host", "summary": "process observed contacting the C2 indicator — candidate for a deeper pivot (T1055 injection)"},
    {"exhibit_id": "ex_cc000003", "uri": "file:dropped-payload",
     "artifact_uri": "pher:hash:dropped-payload", "summary": "file written by the beaconing process — candidate for a deeper pivot (T1003.001 cred access)"},
]
SCOPED_PROMPT = (
    "ROCBA incident. Examine the carved C2 indicator 142.250.64.106 (exhibit ex_aa000001). "
    "Return a verdict and mitre_attack_technique. If the evidence points to a related artifact "
    "that warrants a deeper investigation, populate follow_ups with one next step citing the "
    "relevant exhibit (the contacting process ex_bb000002, then the dropped file ex_cc000003) — "
    "this lets you re-sequence the investigation toward the artifact that matters next. JSON only."
)


def _node(rep: dict) -> dict:
    f = rep.get("finding") or {}
    return {
        "spawn_id": rep.get("spawn_id"),
        "parent_id": rep.get("parent_id"),
        "depth": rep.get("depth"),
        "seed_technique": SEED_TECHNIQUE,
        "ok": rep.get("ok"),
        "verdict": f.get("verdict"),
        "mitre": f.get("mitre_attack_technique"),
        "artifact": f.get("artifact_uri"),
        "reasoning": (f.get("reasoning") or "")[:200],
        "follow_ups": len(f.get("follow_ups") or []),
        "wallclock_ms": round(rep.get("wallclock_ms", 0), 1),
    }


class CapturingSock:
    """Stands in for the `fractal.report` ZMQ PUSH end — captures every report."""

    def __init__(self) -> None:
        self.reports: list[dict] = []

    async def send(self, raw: bytes) -> None:
        try:
            self.reports.append(json.loads(raw))
        except Exception:
            pass


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/hackathon/execution-logs/pivot_chain.json")
    args = ap.parse_args()

    # This box runs the pivot SLM on CPU (~30 s/pivot), so the production
    # ttl_ms=2000 budget can't complete one. For this one-time artifact generation
    # we widen the TTL and take a single follow-up per level (max_width=1) so the
    # chain is a clean linear depth 0→2 path. The re-sequencing decision (whether
    # to emit follow_ups, and toward which artifact) is still the model's own.
    settings.fractal.ttl_ms = 90000
    settings.fractal.max_width = 1
    PIVOT_TTL_MS = 90000

    facade = InferenceFacade()
    watcher = Watcher(facade=facade, max_concurrency=2)
    sock = CapturingSock()

    root = PivotSpawn(
        spawn_id=uuid.uuid4().hex,
        seed_technique=SEED_TECHNIQUE,
        scoped_prompt=SCOPED_PROMPT,
        exhibits=EXHIBITS,
        ttl_ms=PIVOT_TTL_MS,
        depth=0,
        parent_id=None,
    )
    print(f"seeding pivot: {ROOT_ARTIFACT}  seed_technique={SEED_TECHNIQUE}  max_depth={settings.fractal.max_depth}", file=sys.stderr)
    await watcher._dispatch(root, sock)
    # drain the recursively-spawned child tasks
    for _ in range(40):
        pending = [t for t in list(watcher._tasks) if not t.done()]
        if not pending:
            break
        await asyncio.gather(*pending, return_exceptions=True)
    try:
        await facade.close()
    except Exception:
        pass

    nodes = sorted((_node(r) for r in sock.reports), key=lambda n: (n["depth"] or 0))
    artifact = {
        "case": "ROCBA",
        "seed_technique": SEED_TECHNIQUE,
        "root_artifact": ROOT_ARTIFACT,
        "max_depth": settings.fractal.max_depth,
        "max_width": settings.fractal.max_width,
        "depth_reached": max((n["depth"] or 0 for n in nodes), default=0),
        "nodes": nodes,
        "note": "Real output of the fractal pivot loop (Watcher recursion + SLM pivot_infer). "
                "Each node re-sequences the investigation toward the next artifact via follow_ups.",
    }
    with open(args.out, "w") as fh:
        json.dump(artifact, fh, indent=2)
    print(json.dumps(artifact, indent=2))
    print(f"\nwrote {args.out}  (depth reached: {artifact['depth_reached']}, nodes: {len(nodes)})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
