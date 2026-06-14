# Stigmergy — Live ROCBA Segment: what's live vs pre-computed

> The demo's centrepiece (PARTS 3–4) shows the agent working **against real case
> data** — the official **SANS ROCBA** Windows memory image — and producing a
> **real self-correction** live. This note states exactly what runs live on camera
> versus what was computed beforehand, so the framing is honest, and gives the
> rehearsed command sequence with **real captured output**.

## ⭐ CANONICAL NUMBERS — single source of truth (pulled live 2026‑06‑14)
> Every demo doc cites these. Confirm they still match before recording by re‑running
> the **Fix‑1 pull** (below). If you reseed, update here first, then the other docs.

| What the narrator/screen shows | Canonical value | Spoken as |
|---|---|---|
| Signed ledger findings (tip) | **1085** (advances ~+4 each conflict run) | "**more than a thousand** signed findings" |
| Artifacts on the pheromone field | **203** | "over two hundred artifacts" / "203" |
| Live micro‑agents (swarm badge) | **60 LIVE** | "sixty micro‑agents" |
| Distinct ATT&CK techniques | **13** | "thirteen techniques" |
| Typed MCP tools (guardrail) | **62** | "sixty‑two typed functions" |
| Ephemeral fractal pivot agents (signed `fractal.*` findings) | **5** (seq 321/935/936/1010/1047) | "ephemeral fractal pivot agents … depth 3, width 16" |
| Yager conflict on 142.250.64.106 | **conflict_K = 0.354 → conflict_ledger** | "point three five … it raises a conflict" |
| Pre‑signed narrator verdict on 142.250.64.106 | ledger **#985** | "the verdict it already signed" |

**The ledger tip moves.** It is **1085 now**; each `demo_rocba_conflict.py` run adds
~4 (1085→1089→1093…). So the narration says **"more than a thousand,"** which stays
true across re‑takes — never a fixed "eleven hundred" that the screen could contradict.

**Re‑pull command (run before recording to confirm):**
```bash
source /opt/findevil/venv/bin/activate && findevil verify \
 && echo "tip: $(sqlite3 /opt/findevil/data/ledger/ledger.sqlite 'SELECT MAX(seq) FROM ledger;')" \
 && curl -s http://127.0.0.1:9400/api/pher/snapshot | python3 -c "import sys,json;print('artifacts:',len(json.load(sys.stdin)['nodes']))" \
 && curl -s http://127.0.0.1:9400/api/mitre/coverage | python3 -c "import sys,json;j=json.load(sys.stdin);print('techniques:',len(j['techniques']))"
```

## What is REAL (all of it)
- **The evidence is real.** `/opt/findevil/data/cases/rocba/Rocba-Memory.raw` —
  the genuine **18 GB** SANS ROCBA memory image (victim org *stark-research-labs.com*).
- **The forensic tool is real.** `bulk_extractor 2.1.1` (`/usr/local/bin/bulk_extractor`).
- **The indicators are real.** 142.250.64.106, 52.249.198.56, 192.168.1.5,
  stark-research-labs.com — all carved from that image.
- **The findings are real.** Every consensus/conflict/verdict is computed by the
  live pipeline and Ed25519-signed into the ledger; `findevil verify` stays `ok`.

## What is LIVE on camera vs PRE-COMPUTED
| Element | Status | Why |
|---|---|---|
| The 18 GB image existing & being the real ROCBA evidence | **real, on disk** | shown via `du -h` |
| **Full** bulk_extractor carve of all 18 GB (ip/domain/email/pcap) | **pre-computed** | the full carve takes **~17 min** (1005 s) — too long for a ≤5 min demo; its output is shown as proof in `be_out/run1/` |
| **Live carve of a 320 MiB real slice** → re-extracts real IPs incl. 142.250.64.106 | **LIVE** (~10–16 s) | fast enough for camera; same tool, same image |
| **Live ingest** of the carved 142.250.64.106 → consensus finding signed | **LIVE** (~4 s) | bytewax fuses + signs in seconds; tip advances on camera |
| **Live self-correction**: Yager `conflict_K=0.354` → `action=conflict_ledger` on 142.250.64.106 | **LIVE** (~4 s) | the deterministic swarm raises the conflict live |
| The prosecutor/defense/judge **LLM verdict** text | **pre-computed** (signed at ledger **#985**) | the LLM debate runs off the hot path and is slow on CPU; the conflict_ledger trigger is shown live, the signed verdict is shown on the Debate tab |
| **MCP typed-tool catalog** (62 tools, no execute_shell) — PART 3B | **LIVE read** (~3 s) | `demo_mcp_tools.sh` reads the real `findevil.tools.registry` at run time — nothing hardcoded; the GUARDRAIL ✓ line is computed from the actual registered names |
| **Fractal pivot agents** existing & having run — PART 4 | **real, pre-existing** | bounds `max_depth=3, max_width=16` are real (`config/settings.py`, enforced by `fractal/watcher.py`); 5 real `fractal.*` findings are in the ledger (seq 321/935/936/1010/1047). Narrated accurately; the rich `spawner.js` spawn animation is **not wired into the current dashboard**, so it is **not shown** (only the event‑stream `fractal` lines + the ledger proof via C6) |
| **CACAO containment** + **Rekor anchor** — PART 7 | **real** | CACAO actuators are real typed tools (`edr.network_isolate`, …); the ledger is anchored to the public Sigstore Rekor log — anchor batch #3 has real `rekor_log_index = 1492269391` (C7) |

**Honest one-liner to say on camera (optional):** *"The full 17-minute carve I ran
ahead of time — here's its output; now watch me carve a slice of the same real
image live, and feed a carved indicator into the swarm."*

## The rehearsed command sequence (WSL2 — `shaugato@AetherX`, NOT PowerShell)

### Setup (once, before recording — don't film)
```bash
source /opt/findevil/venv/bin/activate
sudo systemctl restart findevil-dashboard      # loads per-artifact MITRE index
```

### PART 3 — live carve (on camera, ~10–16 s of run time)
```bash
bash /opt/findevil/repo/scripts/demo_rocba_carve.sh
```
**Real captured output:**
```
════════════════════════════════════════════════════════════════════
 STIGMERGY · LIVE FORENSIC CARVE — official SANS ROCBA memory image
════════════════════════════════════════════════════════════════════
 evidence : /opt/findevil/data/cases/rocba/Rocba-Memory.raw
 size     : 18G   (real Windows memory image)

── 1. PROOF: the full image was carved with bulk_extractor 2.1.1 ──────
   real carved IPs (feature: struct ip … from packets in memory):
     n=793   192.168.1.5
     n=206   52.249.198.56
     n=146   192.168.30.10
     n=124   172.217.10.74
   the conflict IP, carved from the real image:
     n=9     142.250.64.106
   the victim org, carved from the real image:
     n=2896  stark-research-labs.com  (utf16=1723)

── 2. LIVE carve of a real 320 MiB slice of the evidence ─────────────
   sliced 321M of real evidence → carving now…
   ✓ bulk_extractor finished in 12 s

   REAL indicators just carved live from the slice:
     n=78    192.168.1.5
     n=32    52.249.198.56
     n=17    172.217.10.74
     n=9     192.168.30.10
   → conflict IP present in the live carve?
     YES — 142.250.64.106 extracted from the real image, live.
```

### PART 3B — MCP architectural guardrail (on camera, ~3 s; LIVE registry read)
```bash
bash /opt/findevil/repo/scripts/demo_mcp_tools.sh
```
Prints the **62** real registered typed tools (Volatility, YARA, bulk_extractor,
plaso, tshark, tsk … + bounded CACAO response tools) and the **GUARDRAIL ✓ — NO
execute_shell** banner. Read live from `findevil.tools.registry`, not hardcoded.

### PART 4 — live ingest → self-correction (on camera, ~4–6 s)
```bash
python /opt/findevil/repo/scripts/demo_rocba_conflict.py
```
**Representative output (tip is 1085 now → your first run shows ~1085 → 1089; it
climbs ~+4 each run):**
```
  carved indicator under analysis : 142.250.64.106
  ledger tip before               : 1085
  depositing 2 CONFLICTING sensor reports (Suricata=malicious, EDR=benign)…
  [4s] ledger tip MOVED 1085 → 1089  ✓ real findings signed live
  ── SELF-CORRECTION ─────────────────────────────────────────
     consensus finding #1089 on 142.250.64.106
       Yager conflict_K = 0.354   belief_evil = 0.130
       action           = conflict_ledger
     → sensors disagree → escalated to the prosecutor/defense/
       judge debate (narrator), whose verdict is signed back in.
```
> The `tip before/after` numbers **advance every run** — that advancing tip is the
> proof the pipeline is processing live. Re-running is safe (it appends). The
> `conflict_K = 0.354` and `action = conflict_ledger` are deterministic and stable.
>
> **HONESTY (Fix 2):** the **conflict** above is detected and escalated **LIVE** on
> camera. The **prosecutor/defense/judge verdict** you then show on the Debate tab
> for this same IP was produced **earlier, off the hot path,** and signed at ledger
> **#985** — narration must say "the verdict it *already signed*," not imply it was
> generated live. See vo_04.

### Integrity (fold into PART 3 narration, or show after)
```bash
findevil verify
```
→ `{ "ok": true, "tainted_seqs": [] }`  (stays ok after the live run)

## Repeatability / troubleshooting
- The carve script **clears its scratch dir** (`/tmp/be_demo`) each run — safe to
  re-run for multiple takes.
- The conflict script **appends** new findings each run; the tip just keeps
  climbing (1085→1089→1093…). That's expected and is the proof.
- **Fractal pivots (Fix 3):** the rich spawn animation isn't wired into the current
  dashboard, so back the pivot line with **C6** on screen — the 5 real `fractal.*`
  signed findings (seq 321/935/936/1010/1047). Bounds depth≤3/width≤16 are real
  (`config/settings.py`). Keep the 60 persistent sensor agents distinct from these
  ephemeral spawned investigators.
- If `bulk_extractor` feels slow on your machine under OBS load, lower the slice:
  `ROCBA_COUNT_MIB=200 bash …/demo_rocba_carve.sh` (still contains 142.250.64.106).
- If the tip doesn't move: confirm the dashboard/pipeline is up
  (`curl -s http://127.0.0.1:9400/api/health`) and you're in **WSL2**, not PowerShell.
- After the live run, the Adversarial Debate tab shows the signed verdict on
  142.250.64.106 (ledger **#985**) — cut to it in PART 4/6.
