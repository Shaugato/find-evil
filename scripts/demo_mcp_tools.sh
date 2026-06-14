#!/usr/bin/env bash
# Stigmergy demo — the Custom MCP Server architectural guardrail (Approach #2).
#
# Reads the LIVE tool registry (findevil.tools.registry) and prints the typed
# forensic/response tool catalog the agent can call — proving there is NO
# execute_shell / no arbitrary command. The guardrail is architectural (the
# server only exposes these typed functions), not a prompt instruction.
#
# Real read of the registered tools — nothing hardcoded. No sudo. WSL2.
set -euo pipefail

PY="${FINDEVIL_PY:-/opt/findevil/venv/bin/python}"
cd "${FINDEVIL_REPO:-/opt/findevil/repo}"

"$PY" - <<'PYEOF'
from findevil.tools.registry import bootstrap, registered
bootstrap()
names = sorted(registered())

def group(prefixes):
    return [n for n in names if n.split(".")[0] in prefixes]

no_version = [n for n in names if not n.endswith(".version")]
forensic = group({"volatility", "yara", "bulk_extractor", "plaso", "tshark", "tsk",
                  "mftecmd", "evtxecmd", "regripper", "capa", "floss", "ghidra",
                  "pescan", "ole", "memprocfs", "rita", "arkime", "suricata", "analyst"})
forensic = [n for n in forensic if not n.endswith(".version")
            and n not in ("yara.quarantine", "yara.quarantine_file", "yara.block_hash")]
# lead with the recognizable headline tools so they always show on camera
HEAD = ["volatility.pslist", "volatility.malfind", "volatility.netscan", "volatility.pstree",
        "yara.scan", "bulk_extractor.scan", "plaso.extract", "tshark.summary",
        "tsk.fls", "tsk.icat", "mftecmd.parse", "evtxecmd.parse", "regripper.run",
        "capa.analyze", "floss.extract", "suricata.query"]
forensic = [n for n in HEAD if n in forensic] + [n for n in forensic if n not in HEAD]
response = group({"edr", "iam"}) + [n for n in names if n in
                 ("yara.quarantine", "yara.quarantine_file", "yara.block_hash")]
standards = group({"stix", "ocsf", "taxii", "diamond", "ledger", "findevil"})

shell = [n for n in names if any(k in n.lower() for k in ("shell", "exec", "bash", "system", "eval", "subprocess"))]

bar = "═" * 68
print(bar)
print(" STIGMERGY · CUSTOM MCP SERVER (Approach #2) — typed tool catalog")
print(bar)
print(f" server : findevil.blackboard (FastMCP)")
print(f" tools  : {len(names)} typed functions — the ONLY things the agent can call")
print()
print(" ── Forensic analysis (read / parse the evidence) ──")
for n in forensic[:18]:
    print(f"     {n}")
print()
print(" ── Bounded response (CACAO containment actions, each audited) ──")
for n in response:
    print(f"     {n}")
print()
print(" ── Standards / provenance ──")
for n in standards:
    print(f"     {n}")
print()
print(bar)
if shell:
    print(f" ⚠ shell-like tools exposed: {shell}")
else:
    print(" GUARDRAIL ✓  NO execute_shell · NO arbitrary command exposed.")
    print(" Every action is a typed, audited function — enforced by the MCP server")
    print(" architecture, NOT by a prompt. The agent physically cannot run a raw")
    print(" or destructive shell command: the server simply does not expose one.")
print(bar)
PYEOF
