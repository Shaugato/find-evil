# Stigmergy — Master Recording Guide

> **How to use this guide.** You record in two passes, then Claude Code assembles:
> 1. **Voiceover first** — record each PART's narration as its own short audio clip
>    (`vo_NN_title.wav`). Re-record any clip freely; they're independent.
> 2. **Screen second** — with OBS **Display Capture**, follow each PART's SCREEN
>    block, roughly matching the voiceover length. One continuous take is fine.
> 3. **Matching last** — Claude Code lays each `vo_NN` under its matching segment
>    using [MATCHING_PLAN.md](MATCHING_PLAN.md).
>
> Companion docs: [VOICEOVER_PARTS.md](VOICEOVER_PARTS.md) (scripts only),
> [TERMINAL_COMMANDS.md](TERMINAL_COMMANDS.md) (copy‑paste commands + real output),
> [OBS_AND_RECORDING_SETUP.md](OBS_AND_RECORDING_SETUP.md) (setup),
> [MATCHING_PLAN.md](MATCHING_PLAN.md) (assembly table).
>
> **Total runtime target: ~4:30** (hard cap 5:00).
> **All data below is REAL and current** — pulled from the live system on
> 2026‑06‑14. If you reseed/restart, re-pull with the commands in TERMINAL_COMMANDS.md.

## ⚙️ Before you record (do this once)
1. **In WSL2** (`shaugato@AetherX`, **not** PowerShell), restart the dashboard so
   the full per‑artifact MITRE index is live:
   ```bash
   sudo systemctl restart findevil-dashboard
   ```
2. Open **http://127.0.0.1:9400** in the browser; confirm the **Pheromone Field**
   shows glowing atoms (not "idle"). The atoms are now **rock‑stable — no flicker**.
3. Confirm the field's top artifacts are the lateral‑movement hosts
   **10.1.0.43, 10.1.0.32, 10.1.0.18, 10.1.0.6** (belief ≈ 0.99).
4. Full OBS / window setup: see [OBS_AND_RECORDING_SETUP.md](OBS_AND_RECORDING_SETUP.md).

**Live numbers you will reference (real, as of recording):** 203 artifacts on the
field · **1,077** signed ledger findings · **60** live micro‑agents · **13**
ATT&CK techniques · self‑correction verdicts at ledger **#985** and **#941**.

---

## PART 1 — The Problem (hook)  (target: 25 s)

**VOICEOVER** (record as `vo_01_problem.wav`):
> "A modern intrusion throws thousands of weak signals at a SOC — endpoint,
> network, memory, signatures — and analysts drown in alerts while the clock runs.
> What if a swarm of agents could fuse those signals, decide, and prove its
> reasoning — locally, with no cloud, and a tamper‑evident record of every call?"
>
> Tone: calm, serious → building. Save as `vo_01_problem.wav`.

**SCREEN** (match the voiceover):
- Starting state: a **title card** (a slide reading **STIGMERGY — Autonomous
  DFIR / Agentic SOC**) *or* the dashboard's boot screen.
- Actions:
  - `[0:00]` Hold on the title card / boot logo.
  - `[0:12]` Let the boot text ("62 typed tools…") finish, *or* slowly fade the
    title into the dashboard with the 3‑D field already glowing.
- Focus: the product name and the glowing field behind it.
- Don't: don't click anything yet; don't show the desktop.
- End state: dashboard open, **Pheromone Field** tab active.

---

## PART 2 — What Stigmergy Is  (target: 35 s)

**VOICEOVER** (`vo_02_overview.wav`):
> "This is Stigmergy — a local‑first, defensive DFIR platform. Sixty micro‑agents
> act like an ant colony: each sensor drops 'pheromone' on the artifacts it finds
> suspicious — IPs, domains, processes, hashes — on a shared blackboard. A
> deterministic hot path fuses those deposits with Dempster–Shafer evidence
> theory into a single belief, signs the decision into a cryptographic ledger, and
> only then does a language‑model debate explain it. Everything you'll see runs on
> this one machine."
>
> Tone: confident, explanatory. Save as `vo_02_overview.wav`.

**SCREEN**:
- Starting state: dashboard, **Pheromone Field** tab.
- Actions:
  - `[0:00]` Show the whole dashboard. Mouse rests bottom‑center.
  - `[0:06]` Slowly sweep the mouse left to the **MICRO‑AGENT SWARM** panel
    (badge reads **60 LIVE**) — pause 2 s.
  - `[0:14]` Sweep to the right **MCP BLACKBOARD** panel (`bb://ioc`) — the
    artifact list — pause 2 s.
  - `[0:22]` Sweep back to the center **3‑D field**; gently **drag to orbit** once
    so the viewer sees it's a real 3‑D scene.
- Focus: left swarm → right blackboard → center field (the data flow).
- Don't: don't click individual entries yet; don't zoom in hard.
- End state: field centered, slowly orbiting.

---

## PART 3 — Live Execution Against Case Data  (target: 40 s)  ⟵ TERMINAL (required core)

**VOICEOVER** (`vo_03_live_exec.wav`):
> "This isn't a mock‑up. Here's the live engine. I'll verify the integrity of the
> evidence ledger — every finding is hash‑chained and Ed25519‑signed. It returns
> 'ok', with zero tainted entries, across eleven hundred signed findings. And the
> ATT&CK coverage is computed from those real findings: thirteen techniques, led
> by PowerShell execution and web command‑and‑control."
>
> Tone: matter‑of‑fact, credible. Save as `vo_03_live_exec.wav`.

**SCREEN + TERMINAL** (switch to the **WSL2** tab — `shaugato@AetherX`, **NOT**
PowerShell):
- `[0:00]` Show the terminal full‑frame. Type and run (see TERMINAL_COMMANDS.md C1):
  ```bash
  findevil verify
  ```
  Expected output (pause 4 s on it):
  ```json
  { "ok": true, "tainted_seqs": [] }
  ```
- `[0:14]` Run (C2):
  ```bash
  sqlite3 /opt/findevil/data/ledger/ledger.sqlite \
    "SELECT MAX(seq)||' signed findings in the chain' FROM ledger;"
  ```
  Output: `1077 signed findings in the chain` — pause 2 s.
- `[0:22]` Run (C4):
  ```bash
  curl -s http://127.0.0.1:9400/api/mitre/coverage | python3 -m json.tool | head -20
  ```
  Output shows the **13** techniques — pause 4 s on the list.
- Focus: the `"ok": true`, the `1077`, the technique list.
- Don't: don't run commands in PowerShell (the Linux paths fail there); don't
  clear the screen between commands — let them stack so the proof is visible.
- End state: terminal showing the MITRE JSON.

---

## PART 4 — The Self‑Correction Sequence  (target: 35 s)  ⟵ TERMINAL (the heart)

**VOICEOVER** (`vo_04_self_correction.wav`):
> "Here's what makes it autonomous. When the swarm hits a conflict — sensors
> disagree, or belief is borderline — it escalates to an out‑of‑band debate: an
> LLM prosecutor argues the artifact is malicious, a defense rebuts, and a judge
> rules, with position‑swap to cancel bias. The verdict is written back into the
> same signed ledger. Here are real verdicts — at entries nine‑eighty‑five and
> nine‑forty‑one, the judge found the artifacts *not guilty*. The system caught
> its own overreach and corrected it — and signed the correction."
>
> Tone: this is the climax — confident, a little slower. Save as
> `vo_04_self_correction.wav`.

**SCREEN + TERMINAL** (WSL2 tab):
- `[0:00]` In the terminal, run (TERMINAL_COMMANDS.md C3):
  ```bash
  sqlite3 -header -column /opt/findevil/data/ledger/ledger.sqlite \
    "SELECT seq, substr(primary_artifact_key,1,28) AS artifact, substr(agent_id,1,14) AS agent
     FROM (SELECT seq,
                  json_extract(CAST(payload AS TEXT),'\$.primary_artifact_key') AS primary_artifact_key,
                  json_extract(CAST(payload AS TEXT),'\$.agent_id') AS agent_id
           FROM ledger)
     WHERE agent_id LIKE '%narrator%' ORDER BY seq DESC LIMIT 5;"
  ```
  Output (pause 5 s — read seq 985 and 941 aloud):
  ```
  seq  artifact                      agent
  ---  ----------------------------  --------------
  985  pher:ip:142.250.64.106        narrator.judge
  941  pher:ip:203.0.113.207         narrator.judge
  ...
  ```
- Focus: rows **985** and **941** — these are the self‑correction findings.
- Don't: don't worry that some artifacts look synthetic — these are real signed
  verdicts; point at 985/941.
- End state: terminal showing the verdict table (you'll show these same verdicts
  visually in the dashboard in PART 6).

---

## PART 5 — Dashboard: the Pheromone Field (3‑D)  (target: 35 s)

**VOICEOVER** (`vo_05_field.wav`):
> "Back to the command shell. Every glowing atom is one suspect artifact, bonded
> to the central blackboard. Size is how much evidence has piled up; colour is the
> swarm's belief it's evil — red is bad. The hot cluster here is internal lateral
> movement — ten‑dot‑one‑dot‑zero hosts at ninety‑nine percent belief. I can dive
> into any atom to see its full case."
>
> Tone: guided‑tour, engaged. Save as `vo_05_field.wav`.

**SCREEN** (browser, **Pheromone Field** tab):
- `[0:00]` Field centered. **Drag slowly to orbit** — show depth.
- `[0:08]` **Hover** a red atom — the compact tooltip appears (belief, τ, conflict,
  sensors). Pause 2 s.
- `[0:14]` **Double‑click** that red atom (e.g. **10.1.0.43**). Camera flies in;
  the **green center popup** opens (belief gauge, sensors, ledger tip, verdict).
  Pause 4 s.
- `[0:24]` Click empty space / the nucleus to fly back out.
- `[0:28]` **Click an MCP Blackboard entry** on the right (e.g. **10.1.0.32**) —
  point out the **bright ring** that snaps onto the matching atom in the field
  **and** the detail inspector opening on the right. (This is the stable, no‑flicker
  selection.)
- Focus: depth on orbit → the green popup → the selection ring tracking the click.
- Don't: don't spam double‑clicks; let each animation finish (it's smooth/stable now).
- End state: one atom selected, ring visible, inspector open.

---

## PART 6 — Threat Graph + the Debate (self‑correction, visualized)  (target: 40 s)

**VOICEOVER** (`vo_06_graph_debate.wav`):
> "The Threat Graph reconstructs the kill chain — drive‑by to encoded PowerShell,
> injection into svchost, an LSASS credential dump, a Run‑key for persistence, a
> Meterpreter beacon, then lateral movement. And the Adversarial Debate tab shows
> those prosecutor‑defense‑judge exchanges I ran in the terminal — here's the
> judge's real verdict on two‑oh‑three‑dot‑zero, *not guilty*, the defense winning
> the argument. That's the audited self‑correction, on screen."
>
> Tone: connecting the terminal proof to the visuals. Save as `vo_06_graph_debate.wav`.

**SCREEN** (browser):
- `[0:00]` Click the **THREAT GRAPH** tab. Show the left‑to‑right kill chain.
- `[0:06]` **Drag the timeline scrubber** at the bottom slowly left→right (or press
  ▶) so nodes materialise in attack order. Pause at the end.
- `[0:16]` **Click a node** (e.g. `powershell.exe -enc`) → its detail card. Pause 2 s.
- `[0:22]` Click the **ADVERSARIAL DEBATE** tab.
- `[0:26]` Find a card with the **⚖ debated** badge (e.g. **203.0.113.207**),
  **click it** → the amber **debate inspector** opens showing PROSECUTION,
  DEFENSE·JUDGE, and the **⚖ JUDGE RULING: NOT GUILTY · winning: defense**.
  Pause 4 s.
- Focus: the scrubber animating the chain; the ⚖ ruling line.
- Don't: don't click a non‑⚖ card for this point — pick one with the ⚖ badge.
- End state: debate inspector open on the 203.0.113.207 verdict.

---

## PART 7 — MITRE Per‑Artifact + Evidence Integrity  (target: 40 s)

**VOICEOVER** (`vo_07_mitre_ledger.wav`):
> "ATT&CK mapping is per‑threat, not just a global heatmap. Across the session,
> thirteen techniques. But select one host and the matrix collapses to exactly
> what *that* artifact did — this validation host only ran PowerShell, a single
> technique. And every one of these decisions is court‑defensible: in the Merkle
> Ledger I can open any finding and walk its BLAKE3 hash, Ed25519 signature, and
> chain of custody back to the raw evidence."
>
> Tone: precise, closing the technical case. Save as `vo_07_mitre_ledger.wav`.

**SCREEN** (browser):
- `[0:00]` Click the **MITRE ATT&CK** tab. Header reads **"13 technique(s)
  detected · session global."** Pause 2 s.
- `[0:06]` In the **MCP Blackboard**, click the process
  **victim‑win11‑validation‑lab:6201** → the matrix changes to **"1 technique ·
  artifact 6201"**, only **T1059.001 PowerShell** lit. Pause 3 s. *(Optional: click
  10.1.0.7 → 5 tiles, then "show all".)*
- `[0:18]` Click the **MERKLE LEDGER** tab.
- `[0:22]` **Click any entry** → the teal **forensic surface** opens: belief,
  primary artifact, technique chips, **chain of custody**, and the crypto block
  (finding_id, blake3, prev_hash, ed25519 sig, merkle_root). Pause 4 s.
- Focus: header changing 13 → 1 on selection; the cryptographic block.
- Don't: don't pick an IP that shows "full ATT&CK map after restart" for the
  per‑artifact point — use **6201** (always 1 tile) or **10.1.0.7** (5 tiles).
- End state: a ledger finding's forensic provenance open.

---

## PART 8 — Close  (target: 20 s)

**VOICEOVER** (`vo_08_close.wav`):
> "Stigmergy: a local, defensive SOC that senses, fuses, decides, debates, and
> proves — autonomously, and entirely on your own hardware. It's open source, and
> the architecture, the standards, and a live demo are all in the repo. Thanks for
> watching."
>
> Tone: warm, confident close. Save as `vo_08_close.wav`.

**SCREEN**:
- `[0:00]` Slowly orbit the 3‑D field one more time *or* show the companion website
  (https://web-eight-sage-34.vercel.app) / the GitHub repo page.
- `[0:10]` End on the **STIGMERGY** title card or the glowing field.
- Focus: the name + the field.
- Don't: don't end on a terminal or a half‑open menu.
- End state: title / field hold for the outro.

---

## Running order & total
| Part | What | Where | Target |
|---|---|---|---|
| 1 | Problem hook | Title/field | 0:25 |
| 2 | What Stigmergy is | Dashboard overview | 0:35 |
| 3 | Live execution | **Terminal** | 0:40 |
| 4 | Self‑correction (verdicts) | **Terminal** | 0:35 |
| 5 | Pheromone Field | Dashboard 3‑D | 0:35 |
| 6 | Threat Graph + Debate | Dashboard | 0:40 |
| 7 | MITRE per‑artifact + Ledger | Dashboard | 0:40 |
| 8 | Close | Title/site | 0:20 |
| | **TOTAL** | | **4:30** |

See [MATCHING_PLAN.md](MATCHING_PLAN.md) for the assembly table.
