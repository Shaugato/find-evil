# Stigmergy — Live ROCBA Segment: what's live vs pre-computed

> The demo's centrepiece (PARTS 3–4) shows the agent working **against real case
> data** — the official **SANS ROCBA** Windows memory image — and producing a
> **real self-correction** live. This note states exactly what runs live on camera
> versus what was computed beforehand, so the framing is honest, and gives the
> rehearsed command sequence with **real captured output**.

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

### PART 4 — live ingest → self-correction (on camera, ~4–6 s)
```bash
python /opt/findevil/repo/scripts/demo_rocba_conflict.py
```
**Real captured output:**
```
  carved indicator under analysis : 142.250.64.106
  ledger tip before               : 1081
  depositing 2 CONFLICTING sensor reports (Suricata=malicious, EDR=benign)…
  [4s] ledger tip MOVED 1081 → 1085  ✓ real findings signed live
  ── SELF-CORRECTION ─────────────────────────────────────────
     consensus finding #1085 on 142.250.64.106
       Yager conflict_K = 0.354   belief_evil = 0.130
       action           = conflict_ledger
     → sensors disagree → escalated to the prosecutor/defense/
       judge debate (narrator), whose verdict is signed back in.
```
> The `tip before/after` numbers **advance every run** — that advancing tip is the
> proof the pipeline is processing live. Re-running is safe (it appends).

### Integrity (fold into PART 3 narration, or show after)
```bash
findevil verify
```
→ `{ "ok": true, "tainted_seqs": [] }`  (stays ok after the live run)

## Repeatability / troubleshooting
- The carve script **clears its scratch dir** (`/tmp/be_demo`) each run — safe to
  re-run for multiple takes.
- The conflict script **appends** new findings each run; the tip just keeps
  climbing (1081→1085→1089…). That's expected and is the proof.
- If `bulk_extractor` feels slow on your machine under OBS load, lower the slice:
  `ROCBA_COUNT_MIB=200 bash …/demo_rocba_carve.sh` (still contains 142.250.64.106).
- If the tip doesn't move: confirm the dashboard/pipeline is up
  (`curl -s http://127.0.0.1:9400/api/health`) and you're in **WSL2**, not PowerShell.
- After the live run, the Adversarial Debate tab shows the signed verdict on
  142.250.64.106 (ledger **#985**) — cut to it in PART 4/6.
