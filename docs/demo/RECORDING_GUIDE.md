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
4. **Confirm the ROCBA live segment is ready** (the real evidence + carve scripts):
   ```bash
   ls -lh /opt/findevil/data/cases/rocba/Rocba-Memory.raw    # → 18G real image
   ls /opt/findevil/repo/scripts/demo_rocba_carve.sh /opt/findevil/repo/scripts/demo_rocba_conflict.py
   ```
   Optionally do **one dry‑run** of `demo_rocba_carve.sh` before recording so the
   slice is warm and the carve is snappy on camera. See
   [LIVE_SEGMENT_NOTES.md](LIVE_SEGMENT_NOTES.md).
5. Full OBS / window setup: see [OBS_AND_RECORDING_SETUP.md](OBS_AND_RECORDING_SETUP.md).

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

**VOICEOVER** (`vo_02_overview.wav`) — lands the **speed / no‑LLM** point (GAP 2) and
the **live swarm** (GAP 3):
> "This is Stigmergy — a local, defensive DFIR platform. Sixty micro‑agents — you can
> watch them ticking here — act like an ant colony: each continuously scores artifacts
> and drops 'pheromone' on the IPs, domains, and processes it finds suspicious, on a
> shared blackboard. A deterministic hot path fuses those deposits with Dempster–Shafer
> evidence theory and decides in well under a millisecond — with no language model in
> the loop — fast enough to keep pace with attacks that reach domain control in
> minutes. The model only debates and explains afterward, off the critical path. And
> it all runs on this one machine."
>
> Tone: confident, explanatory; hit "well under a millisecond" and "no language model
> in the loop." Save as `vo_02_overview.wav`.

**SCREEN**:
- Starting state: dashboard, **Pheromone Field** tab.
- Actions:
  - `[0:00]` Show the whole dashboard. Mouse rests bottom‑center.
  - `[0:05]` Sweep to the **MICRO‑AGENT SWARM** panel (left, badge **60 LIVE**) and
    **hold ~5 s** — let the viewer see the per‑agent **ops/s counters ticking** and the
    **τ** values changing. This is the swarm visibly working (GAP 3). Optionally hover
    one agent row → its popover (role + sparkline).
  - `[0:14]` Sweep to the right **MCP BLACKBOARD** panel (`bb://ioc`) — pause 2 s.
  - `[0:22]` Sweep back to the center **3‑D field**; gently **drag to orbit** once.
- Focus: the **ticking ops/s in the swarm panel**, then blackboard → field (the flow).
- Don't: don't click individual entries yet; don't zoom in hard.
- End state: field centered, slowly orbiting.

---

## PART 3 — LIVE Real‑Data Execution: the ROCBA case  (target: 55 s)  ⟵ TERMINAL (required core)

> See [LIVE_SEGMENT_NOTES.md](LIVE_SEGMENT_NOTES.md) for exactly what's live vs
> pre‑computed. This is the hackathon's required "agent working against real case
> data" — shown live.

**VOICEOVER** (`vo_03_live_rocba.wav`):
> "And this isn't a mock‑up — this is the official SANS ROCBA case, an eighteen‑
> gigabyte Windows memory image from a real intrusion at stark‑research‑labs. The
> full forensic carve I ran ahead of time — here's its output, real indicators
> pulled straight from memory. Now watch me carve a slice of that same evidence
> live, with bulk_extractor — and there it is, real IPs extracted in seconds,
> including one‑forty‑two‑two‑fifty, the address the swarm will flag. And every
> finding it produces is hash‑chained and Ed25519‑signed — the ledger verifies ok,
> zero tainted, across eleven hundred findings."
>
> Tone: matter‑of‑fact, credible, a little proud. Save as `vo_03_live_rocba.wav`.

**SCREEN + TERMINAL** (switch to the **WSL2** tab — `shaugato@AetherX`, **NOT**
PowerShell; font 18–20 pt):
- `[0:00]` Terminal full‑frame. Run the live carve (TERMINAL_COMMANDS.md **C1**):
  ```bash
  bash /opt/findevil/repo/scripts/demo_rocba_carve.sh
  ```
- `[0:02]` It prints the **18G** evidence path, then the **PROOF** block — real
  carved IPs and **stark‑research‑labs.com**. Let the viewer read it (2–3 s).
- `[0:10]` The **LIVE carve** runs — `bulk_extractor … finished in ~12 s`. Narrate
  over the wait. Then it prints the freshly carved IPs and **"142.250.64.106
  extracted from the real image, live."** Pause 3 s on that line.
- `[0:40]` Run the integrity check (**C2**) — fold it into the same breath:
  ```bash
  findevil verify
  ```
  Output (pause 3 s): `{ "ok": true, "tainted_seqs": [] }`
- Focus: the **18G** size, **stark‑research‑labs.com**, **142.250.64.106 … live**,
  and `"ok": true`.
- Don't: don't run in PowerShell (Linux paths fail); don't clear the screen — let
  the carve output stay visible. If the carve feels long, that's fine — narrate over it.
- End state: terminal showing the carved indicators + `verify` ok. (Stay in the
  terminal — PART 3B continues here.)

---

## PART 3B — The MCP Architectural Guardrail (Approach #2)  (target: 15 s)  ⟵ TERMINAL (GAP 1 — must‑add)

> The single highest‑value addition for SANS/DFIR judges: show — not just say — that
> guardrails are **architectural, not prompt‑based**. The agent just used these typed
> tools on the real evidence; now reveal the catalog.

**VOICEOVER** (`vo_03b_mcp.wav`):
> "And notice — the agent only ever calls typed forensic tools. This is Approach #2:
> a purpose‑built MCP server. Sixty‑two typed functions — Volatility, YARA,
> bulk_extractor — and no execute_shell, no arbitrary command. It physically cannot
> run a destructive command, because the architecture never exposes one. That's a
> guardrail by construction, not a prompt."
>
> Tone: pointed, the architecture flex. Save as `vo_03b_mcp.wav`.

**SCREEN + TERMINAL** (same WSL2 terminal):
- `[0:00]` Run (TERMINAL_COMMANDS.md **C1B**):
  ```bash
  bash /opt/findevil/repo/scripts/demo_mcp_tools.sh
  ```
- `[0:02]` It prints the **62 typed tools** grouped — *Forensic* (volatility.pslist,
  volatility.malfind, yara.scan, bulk_extractor.scan, tshark.summary, tsk.fls…),
  *Bounded response* (edr.network_isolate, edr.kill_process, iam.disable_account…),
  *Standards* (stix.bundle, ocsf.finding) — then the **GUARDRAIL ✓** banner:
  *"NO execute_shell · NO arbitrary command exposed."* Pause 4 s on that banner.
- Focus: the typed forensic tool names, then the **GUARDRAIL ✓** line. Say
  "Approach #2 … architectural guardrail, not a prompt."
- Don't: don't scroll past the GUARDRAIL banner — it's the point.
- End state: terminal showing the catalog + GUARDRAIL ✓. (Stay in the terminal — PART 4
  continues here.)

---

## PART 4 — The Self‑Correction, on the Real ROCBA Data  (target: 45 s)  ⟵ TERMINAL + dashboard (the heart)

**VOICEOVER** (`vo_04_self_correction.wav`) — lands the self‑correction **and** the
ephemeral **fractal pivot agents** (GAP 5, distinct from the 60 persistent sensors):
> "Now feed that carved indicator into the swarm. Two sensors disagree — Suricata says
> malicious command‑and‑control, the endpoint agent says benign. Watch the ledger
> advance live: the consensus engine computes a Yager conflict — point three five —
> and instead of guessing, it raises a conflict and escalates. That's the
> self‑correction: the swarm knows when it doesn't know. And suspicious artifacts
> spawn ephemeral fractal pivot agents — bounded autonomous investigators, depth
> three, width sixteen — that chase the related evidence and then dissolve. The
> conflict goes to a prosecutor, defense, and judge debate, and the signed verdict on
> one‑forty‑two‑two‑fifty lands in the immutable ledger."
>
> Tone: the climax — slower on "the swarm knows when it doesn't know." Save as
> `vo_04_self_correction.wav`.

**SCREEN + TERMINAL** (WSL2 tab, then browser):
- `[0:00]` In the terminal, run (TERMINAL_COMMANDS.md **C3**):
  ```bash
  python /opt/findevil/repo/scripts/demo_rocba_conflict.py
  ```
- `[0:03]` It prints the carved IP under analysis, then **"ledger tip MOVED 1081 →
  1085 ✓ real findings signed live"**, then the **SELF‑CORRECTION** block:
  `Yager conflict_K = 0.354 … action = conflict_ledger`. Pause 4 s — read the
  conflict_K and `conflict_ledger` aloud.
- `[0:18]` *(optional, while saying the "fractal pivot agents" line)* the **EVENT
  STREAM** (bottom‑left) tails `fractal` pivot lines when they fire; or run **C6** to
  show the real `fractal.*` spawned‑pivot findings in the ledger. Keep it brief.
- `[0:24]` **Alt+Tab to the browser.** Click the **ADVERSARIAL DEBATE** tab.
- `[0:28]` Find the card for **142.250.64.106** (or another **⚖ debated** card) and
  **click it** → the amber debate inspector shows PROSECUTION, DEFENSE·JUDGE, and
  the **⚖ JUDGE RULING**. Pause 4 s.
- Focus: `conflict_K = 0.354`, `action = conflict_ledger`, then the ⚖ ruling.
- Don't: don't expect a fresh LLM verdict in the terminal (the debate runs off the
  hot path) — the live part is the **conflict_ledger** escalation; the signed verdict
  is shown on the dashboard. Don't call the 60 sensors "spawned" — the *pivot* agents
  are the ephemeral spawned ones.
- End state: debate inspector open on the 142.250.64.106 verdict.

---

## PART 5 — Dashboard: the Pheromone Field (3‑D)  (target: 30 s)

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

## PART 6 — Threat Graph: the kill chain  (target: 30 s)

**VOICEOVER** (`vo_06_graph.wav`):
> "Stigmergy doesn't just score artifacts — it reconstructs the story. The Threat
> Graph lays the incident out as a kill chain: a drive‑by, encoded PowerShell,
> injection into svchost, an LSASS credential dump, a Run‑key for persistence, a
> Meterpreter beacon, then lateral movement and exfiltration. I can scrub the
> timeline to replay exactly how the attack unfolded, step by step."
>
> Tone: narrative, guiding the eye along the chain. Save as `vo_06_graph.wav`.

**SCREEN** (browser):
- `[0:00]` Click the **THREAT GRAPH** tab. Show the left‑to‑right kill chain.
- `[0:08]` **Drag the timeline scrubber** at the bottom slowly left→right (or press
  ▶) so nodes materialise in attack order ("step 1 / 9" … "9 / 9"). Pause at the end.
- `[0:22]` **Click a node** (e.g. `powershell.exe -enc`, or the
  `192.168.1.47:4444` C2 node) → its holographic detail card (tactic, MITRE id,
  confidence, sensors). Pause 3 s.
- Focus: the chain left→right; the scrubber animating the reveal.
- Don't: don't re‑show the Debate tab here (already covered in PART 4); keep this
  about the kill chain.
- End state: a kill‑chain node's detail card open.

---

## PART 7 — MITRE Per‑Artifact + Evidence Integrity  (target: 35 s)

**VOICEOVER** (`vo_07_mitre_ledger.wav`) — adds **CACAO containment** and **Rekor
transparency‑log** (GAP 4):
> "ATT&CK mapping is per‑threat, not just a global heatmap — select one host and the
> matrix collapses to exactly what that artifact did; this validation host only ran
> PowerShell. And on a confident malicious verdict the platform doesn't just alert —
> it fires an automated CACAO containment playbook: detection through response,
> autonomously. Every decision is court‑defensible too — each finding is BLAKE3‑hashed,
> Ed25519‑signed, hash‑chained, and anchored to a public Sigstore transparency log, so
> anyone can verify the record wasn't altered."
>
> Tone: precise, closing the technical case. Say "transparency log," not "blockchain."
> Save as `vo_07_mitre_ledger.wav`.

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
  (finding_id, blake3, prev_hash, ed25519 sig, merkle_root). Pause 4 s. *(Optional:
  in the terminal, **C7** shows the real Rekor anchor — log index 1492269391 — as you
  say "anchored to a public transparency log.")*
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
| Part | What | Where | Target | Running |
|---|---|---|---|---|
| 1 | Problem hook | Title/field | 0:25 | 0:25 |
| 2 | What Stigmergy is + **swarm alive** + **speed/no‑LLM** | Dashboard overview | 0:35 | 1:00 |
| 3 | **LIVE ROCBA carve** (real evidence → real indicators) | **Terminal** | 0:55 | 1:55 |
| 3B | **MCP typed‑tool guardrail** (Approach #2) | **Terminal** | 0:15 | 2:10 |
| 4 | **Self‑correction** + **fractal pivots** on the carved IP | **Terminal + dashboard** | 0:45 | 2:55 |
| 5 | Pheromone Field | Dashboard 3‑D | 0:30 | 3:25 |
| 6 | Threat Graph (kill chain) | Dashboard | 0:30 | 3:55 |
| 7 | MITRE per‑artifact + Ledger + **CACAO/Rekor** | Dashboard | 0:35 | 4:30 |
| 8 | Close | Title/site | 0:20 | **4:50** |

**TOTAL ≈ 4:50** (hard cap 5:00). See [MATCHING_PLAN.md](MATCHING_PLAN.md) for the
assembly table and [LIVE_SEGMENT_NOTES.md](LIVE_SEGMENT_NOTES.md) for the live‑vs‑
pre‑computed breakdown (incl. the MCP catalog read and the fractal‑pivot proof).
