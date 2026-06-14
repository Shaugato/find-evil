# Stigmergy — Terminal Commands (copy‑paste ready)

> ⚠️ **Use the WSL2 tab, NOT PowerShell.** Your prompt must read
> **`shaugato@AetherX`**. PowerShell 7.6 is the default tab and these Linux
> commands (`bash`, `sqlite3`, `python`, the `/opt/...` paths) will **fail** there.
> In Windows Terminal: open the **Ubuntu/WSL** profile (dropdown ▾ or Ctrl+Shift+5).
>
> 🔠 **Font size for recording: 18–20 pt** (Settings → Profiles → Ubuntu →
> Appearance → Font size).
>
> Every command was **dry‑run on the live system**; the output shown is **real**.
> The live ROCBA segment (C1/C3) is documented in
> [LIVE_SEGMENT_NOTES.md](LIVE_SEGMENT_NOTES.md) (what's live vs pre‑computed).
> No `jq` on this box — use `python3 -m json.tool`.

---

## C0 — One‑time setup (don't record this)
```bash
source /opt/findevil/venv/bin/activate
sudo systemctl restart findevil-dashboard      # loads the per‑artifact MITRE index
```
After `activate`, your prompt shows `(venv)` and bare `findevil`/`python` work.
*(Optional but recommended: run C1 once before recording so the carve is warm.)*

---

## C1 — LIVE forensic carve of the real ROCBA image  → **PART 3** (vo_03)
```bash
bash /opt/findevil/repo/scripts/demo_rocba_carve.sh
```
**Real output** (on‑camera run time ~10–16 s; narrate over the carve):
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
*Say while it runs:* "Eighteen‑gig real memory image… real indicators… and there's
142.250.64.106, carved live."
> Snappier carve if needed: `ROCBA_COUNT_MIB=200 bash /opt/findevil/repo/scripts/demo_rocba_carve.sh`

---

## C2 — Verify ledger integrity  → **PART 3** (fold into vo_03)
```bash
findevil verify
```
**Real output** (pause 3 s):
```json
{
  "ok": true,
  "tainted_seqs": []
}
```
*Optional scale line:*
```bash
sqlite3 /opt/findevil/data/ledger/ledger.sqlite \
  "SELECT MAX(seq)||' signed findings in the chain' FROM ledger;"
```
→ `1077 signed findings in the chain` (the number grows as you run C3).

---

## C3 — LIVE ingest of the carved indicator → self‑correction  → **PART 4** (vo_04)
```bash
python /opt/findevil/repo/scripts/demo_rocba_conflict.py
```
**Real output** (on‑camera ~4–6 s):
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
*Say:* "Two sensors disagree… Yager conflict point‑three‑five… it raises a conflict
instead of guessing — that's the self‑correction." Then **Alt+Tab to the dashboard →
Adversarial Debate tab** and click the 142.250.64.106 card for the signed verdict.
> The `tip before/after` numbers **advance every run** — that's the live proof.
> Safe to re‑run for multiple takes (it appends).

---

## C4 — (OPTIONAL) MITRE coverage from real findings  → backup detail for PART 3/7
```bash
curl -s http://127.0.0.1:9400/api/mitre/coverage | python3 -m json.tool | head -16
```
**Real output** — 13 techniques; head shows:
```json
{
    "techniques": {
        "T1059.001": 527,
        "T1071.001": 430,
        "T1078": 324,
        "T1055": 316,
        "T1003.001": 299,
        "T1566.001": 158,
        ...
    },
}
```

---

## C5 — (OPTIONAL) The already‑signed ROCBA verdicts (history, if you want to show them)
```bash
sqlite3 -header -column /opt/findevil/data/ledger/ledger.sqlite \
  "SELECT seq, substr(primary_artifact_key,1,22) AS artifact, substr(agent_id,1,14) AS agent
   FROM (SELECT seq,
                json_extract(CAST(payload AS TEXT),'\$.primary_artifact_key') AS primary_artifact_key,
                json_extract(CAST(payload AS TEXT),'\$.agent_id') AS agent_id
         FROM ledger)
   WHERE agent_id LIKE '%narrator%' ORDER BY seq DESC LIMIT 5;"
```
**Real output** — the signed prosecutor/defense/judge verdicts (incl. the ROCBA
conflict IP at **#985**):
```
seq  artifact                agent
---  ----------------------  --------------
985  pher:ip:142.250.64.106  narrator.judge
941  pher:ip:203.0.113.207   narrator.judge
...
```

---

## Command order on camera
1. **C1** — live ROCBA carve  (PART 3)
2. **C2** — `findevil verify`  (PART 3, same breath)
3. **C3** — live conflict ingest → self‑correction  (PART 4) → Alt+Tab to Debate tab
4. *(optional)* C4 / C5 for extra detail

**Don't** clear the screen between C1–C3 — let the carve + verify + conflict stack so
the whole real‑data story stays on one screen.
