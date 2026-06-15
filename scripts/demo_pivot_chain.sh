#!/usr/bin/env bash
# Stigmergy demo — print ONE real fractal pivot chain as a CONNECTED lineage,
# the Criterion-1 evidence that the agent re-sequences its own investigation.
#
# Renders the artifact produced by `run_pivot_chain.py` (the real Watcher recursion
# + SLM pivot_infer on the ROCBA-carved C2 indicator). Each deeper pivot is seeded
# by its parent finding's follow_ups (parent_id lineage), bounded at max_depth.
# Fast on camera — it prints a pre-generated REAL result, it does not re-infer.
set -euo pipefail

ART="${PIVOT_CHAIN:-/opt/findevil/repo/docs/hackathon/execution-logs/pivot_chain.json}"
[ -f "$ART" ] || ART="docs/hackathon/execution-logs/pivot_chain.json"

python3 - "$ART" <<'PYEOF'
import json, sys
MITRE = {"T1071": "Web/App-layer C2", "T1071.001": "Web C2", "T1055": "Process Injection",
         "T1003.001": "LSASS Memory", "T1078": "Valid Accounts", "T1059.001": "PowerShell"}
d = json.load(open(sys.argv[1]))
nodes = sorted(d["nodes"], key=lambda n: n.get("depth") or 0)
bar = "═" * 70
print(bar)
print(" STIGMERGY · AUTONOMOUS RE-SEQUENCING — fractal pivot chain (case ROCBA)")
print(bar)
print(f" seed technique : {d['seed_technique']} ({MITRE.get(d['seed_technique'],'ATT&CK')})")
print(f" root artifact  : {d['root_artifact']}")
print(f" bound          : depth ≤ {d['max_depth']}, width ≤ 16 (production)   (ephemeral pivot agents — NOT the 60 persistent sensors)")
print(f" this demo path : a single linear branch (one follow-up per level) for a clear depth 0→{d['depth_reached']} view")
print(f" depth reached  : {d['depth_reached']}   ({len(nodes)} connected pivots)")
print()
for n in nodes:
    depth = n.get("depth") or 0
    ind = "   " * depth + ("└─ " if depth else "")
    sid = (n.get("spawn_id") or "")[:8]
    pid = (n.get("parent_id") or "—")
    pid = pid[:8] if pid != "—" else "root finding"
    mitre = ",".join(n.get("mitre") or []) or "—"
    fu = n.get("follow_ups") or 0
    nxt = f"→ emitted {fu} follow-up(s): re-sequence deeper" if fu and depth < d["max_depth"] - 1 else "→ STOP (max_depth boundary)"
    print(f" {ind}depth {depth}  fractal.{sid}  (parent: {pid})")
    print(f" {'   '*depth}     seeded_by={d['seed_technique']}  verdict={n.get('verdict')}  mitre={mitre}  artifact={n.get('artifact')}")
    print(f" {'   '*depth}     {nxt}")
print()
print(bar)
print(" The agent re-sequenced its OWN investigation: each finding's follow_ups")
print(" re-entered the spawn queue as a deeper pivot (parent_id lineage), so the")
print(" plan adapted to what it found — depth 0 → " + str(d['depth_reached']) +
      f", bounded at max_depth={d['max_depth']}. This is Criterion-1 autonomous execution.")
print(bar)
PYEOF
