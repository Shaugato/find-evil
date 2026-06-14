# Stigmergy — Terminal Commands (copy‑paste ready)

> ⚠️ **Use the WSL2 tab, NOT PowerShell.** Your prompt must read
> **`shaugato@AetherX`**. PowerShell 7.6 is the default tab and these Linux
> commands (`sqlite3`, `curl … | python3`, the `/opt/...` paths) will **fail**
> there. In Windows Terminal: open the **Ubuntu/WSL** profile (Ctrl+Shift+`5` or
> the dropdown ▾).
>
> 🔠 **Font size for recording: 18–20 pt** (Windows Terminal → Settings → Profiles →
> Appearance → Font size). Big enough to read at 1080p.
>
> Every command below was **dry‑run on the live system**; the output shown is the
> **real** output. If you reseed/restart, re‑run to refresh the numbers.

---

## C0 — One‑time, before recording (don't record this)
Activate the environment so `findevil` is on your PATH, and restart the dashboard
to load the full per‑artifact MITRE index:
```bash
source /opt/findevil/venv/bin/activate
sudo systemctl restart findevil-dashboard
```
> `findevil` is **not** on the PATH until you `source` the venv. After `activate`,
> your prompt shows `(venv)` and bare `findevil …` works. (Alternatively, prefix
> every command with `/opt/findevil/venv/bin/findevil`.)

---

## C1 — Verify ledger integrity  → pairs with **vo_03 (PART 3)**
```bash
findevil verify
```
**Real output** (pause **4 s**):
```json
{
  "ok": true,
  "tainted_seqs": []
}
```
*Say while it shows:* "ok — zero tainted entries."

---

## C2 — Show the scale of the signed chain  → pairs with **vo_03 (PART 3)**
```bash
sqlite3 /opt/findevil/data/ledger/ledger.sqlite \
  "SELECT MAX(seq)||' signed findings in the chain' FROM ledger;"
```
**Real output** (pause **2 s**):
```
1077 signed findings in the chain
```

---

## C3 — The self‑correction: narrator verdicts in the signed ledger  → pairs with **vo_04 (PART 4)**
```bash
sqlite3 -header -column /opt/findevil/data/ledger/ledger.sqlite \
  "SELECT seq, substr(primary_artifact_key,1,28) AS artifact, substr(agent_id,1,14) AS agent
   FROM (SELECT seq,
                json_extract(CAST(payload AS TEXT),'\$.primary_artifact_key') AS primary_artifact_key,
                json_extract(CAST(payload AS TEXT),'\$.agent_id') AS agent_id
         FROM ledger)
   WHERE agent_id LIKE '%narrator%' ORDER BY seq DESC LIMIT 5;"
```
**Real output** (pause **5 s**; read **985** and **941** aloud):
```
seq  artifact                      agent
---  ----------------------------  --------------
985  pher:ip:142.250.64.106        narrator.judge
941  pher:ip:203.0.113.207         narrator.judge
332  pher:domain:narrator-refresh  narrator.judge
317  pher:domain:totalconflict-ru  narrator.judge
316  pher:hash:8f34779b66bec20c06  narrator.judge
```
> These are real prosecutor→defense→judge verdicts signed back into the ledger.
> You'll show #941 (203.0.113.207) visually in the Adversarial Debate tab (PART 6).

---

## C4 — MITRE ATT&CK coverage from real findings  → pairs with **vo_03 (PART 3)**
> (No `jq` on this box — use `python3 -m json.tool`.)
```bash
curl -s http://127.0.0.1:9400/api/mitre/coverage | python3 -m json.tool | head -20
```
**Real output** (pause **4 s**) — 13 techniques; the head shows, e.g.:
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
    ...
}
```
*Compact alternative* (nicer one‑liner if you prefer):
```bash
curl -s http://127.0.0.1:9400/api/mitre/coverage \
  | python3 -c "import sys,json;j=json.load(sys.stdin);print(len(j['techniques']),'ATT&CK techniques across',j['total_findings'],'findings')"
```
→ `13 ATT&CK techniques across 1077 findings`

---

## C5 — (OPTIONAL) Live execution: push events and watch the ledger grow  → pairs with **vo_03**
> Use this if you want to show the pipeline ingesting in real time (the ledger tip
> advances). Safe, synthetic events.
```bash
cd /opt/findevil/repo && python scripts/diag_publish_one.py
```
**Real output** (the tip moves within a few seconds):
```
tip before: 1077
published 3 events, last ack seq: ...
  [2s] tip MOVED: 1077 -> 1081  ✓ bytewax consuming
```
*Say:* "Live events in — the deterministic pipeline fuses and signs them in seconds."

---

## Command order on camera
1. `findevil verify`  (C1) — PART 3
2. the `MAX(seq)` count  (C2) — PART 3
3. the MITRE coverage  (C4) — PART 3
4. the narrator‑verdict table  (C3) — PART 4
5. *(optional)* `diag_publish_one.py`  (C5) — PART 3 if you want live ingest

**Don't** clear the screen between C1–C4 — let the proof stack on one screen.
