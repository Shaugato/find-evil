# Stigmergy — Demo Walkthrough

> A tab-by-tab, panel-by-panel guide to demoing the **Stigmergy** Autonomous
> DFIR Command Shell, written against the **live data currently loaded** in the
> system. Open the dashboard at **http://127.0.0.1:9400** and follow along — the
> IPs, sequence numbers, and technique IDs below match what you'll see on screen.
>
> Stigmergy is a **local, defensive** autonomous SOC/DFIR platform: a
> deterministic hot path (sensors → pheromone field → Dempster–Shafer consensus →
> cryptographic ledger) with an out-of-band reasoning plane (LLM fractal pivots +
> a prosecutor/defense/judge debate narrator). Everything below is synthetic
> telemetry — no offensive tooling, no live targets.

---

## ⚙️ One-time setup before recording

> **Activate the full per-artifact MITRE index.** The matrix's per-artifact
> filtering is exact for every artifact once the backend `by_artifact` route is
> live. It ships in the code but the dashboard process must be restarted to load
> it (the server runs without hot-reload). In WSL2:
>
> ```bash
> sudo systemctl restart findevil-dashboard
> ```
>
> After the restart, selecting any IP lights *its* techniques (e.g. 10.1.0.7 → 5
> tiles, 10.1.0.9 → 3 tiles). Without the restart the matrix still filters for
> recently-active artifacts and the header always names the selected artifact,
> but older artifacts show a "full ATT&CK map after dashboard restart" note.

**Current live state** (what you'll be looking at): **202** artifacts on the
pheromone field, **~1,069** signed ledger entries, **60** live micro-agents,
**13** distinct ATT&CK techniques detected, peak pheromone τ ≈ **9.08**.

---

## The demo scenario in one sentence

A spear-phishing lure leads to encoded-PowerShell execution, process injection
into `svchost`, LSASS credential theft, a Run-key persistence, a Meterpreter C2
beacon to `192.168.1.47:4444`, and lateral movement — detected by six sensor
classes, fused into belief by stigmergic consensus, signed into a tamper-evident
ledger, debated by an LLM prosecutor/defense/judge, and contained by a CACAO
safe-mode playbook.

---

# Tabs (center stage)

The five tabs across the top of the center panel are: **Pheromone Field**,
**Threat Graph**, **Merkle Ledger**, **MITRE ATT&CK**, **Adversarial Debate**.

## 1. Pheromone Field (default tab)

**What it shows & why it matters.** The 3-D molecular field is the live shared
memory of the swarm. Each glowing **atom is an artifact** (an IP, domain,
process, or file hash) bonded to the central **MCP-blackboard nucleus**. Atom
**size = pheromone τ** (how much corroborating evidence has been deposited);
**colour = belief it is evil** (red ≥ 0.85, orange elevated, amber suspicious,
cyan benign). This is *stigmergy*: agents coordinate by depositing/sensing
pheromone on shared artifacts rather than messaging each other — the same
principle ants use.

**What you're seeing right now.** ~202 atoms orbiting the nucleus; the hottest
are the internal lateral-movement hosts **10.1.0.43, 10.1.0.32, 10.1.0.18,
10.1.0.6** (belief ≈ 0.95–0.98) and the validation process
**victim-win11-validation-lab:6201** (τ ≈ 9.08).

**What to click / expected response.**
- **Drag** to orbit, **scroll** to zoom — it's a real navigable 3-D scene.
- **Double-click an atom** (e.g. a red one) → the camera flies in and a **green
  center popup** opens: belief gauge, contributing sensors, ledger tip, and the
  action verdict (OBSERVED / ESCALATED / MITIGATED / CONFLICT→DEBATE).
- Click the nucleus or empty space → fly back out.

**Narration.** "This is the swarm's shared memory as a living molecule. Every
atom is a suspect artifact; its size is how much evidence has piled up and its
colour is how confident the swarm is that it's malicious. The agents never talk
to each other — they coordinate by leaving pheromone trails on these artifacts,
exactly like an ant colony."

## 2. Threat Graph

**What it shows & why it matters.** The reconstructed **kill chain** — the same
incident laid out left-to-right by ATT&CK tactic, so you can read the attacker's
story end to end. The critical path is raised and animated; a **timeline
scrubber** at the bottom replays the chain step by step.

**What you're seeing right now (9 nodes).**
`msn-cdn.net` (Initial Access, T1189) → `powershell.exe -enc` (Execution,
T1059.001) → `svchost.exe ⟵inject` (Defense Evasion, T1055) → `lsass.exe ⟵dump`
(Credential Access, T1003.001) → `HKLM\…\Run` (Persistence, T1547.001) →
`192.168.1.47:4444` (C2, T1571) → `Meterpreter` (C2, T1219) → `10.0.0.221`
(Lateral Movement, T1021.002) → `Attacker C2 exfil` (Impact, T1041).

**What to click / expected response.**
- **Drag the timeline slider** (or press ▶) → nodes materialise in attack order,
  the phase label updates ("step 1 / 9" …).
- **Click a node** → a holographic detail card (tactic, MITRE id, confidence,
  contributing sensors, action). **Drag a node** to reposition; edges follow.
- Click an **MCP Blackboard** entry while on this tab → the inspector opens and
  **the graph reflows to the left** so nothing is hidden behind it.

**Narration.** "Same incident, told as a kill chain. I can scrub the timeline to
replay how it unfolded — drive-by to encoded PowerShell, process injection, LSASS
credential theft, persistence, a Meterpreter beacon, then lateral movement."

## 3. Merkle Ledger

**What it shows & why it matters.** Every consensus decision is written to a
**tamper-evident, cryptographically signed** ledger — BLAKE3 content hash,
Ed25519 signature, hash-chained `prev_hash`, Merkle root, NIST SP 800-86 chain of
custody. This is what makes the findings court-defensible.

**What you're seeing right now.** A scrolling list of ~200 signed entries up to
seq **#1069**, newest first, authored by `swarm.consensus`, the sensor agents
(`edr`, `yara`, `sysmon`, `suricata`, `zeek`, `volatility`), `cacao.executor`,
and `narrator.judge`.

**What to click / expected response.**
- **Click any entry** → the **forensic provenance surface** opens on the right
  (teal, wider): belief/conflict, the primary artifact, MITRE technique chips,
  evidence refs, **chain of custody (parents)**, and the full cryptographic block
  (finding_id, blake3, prev_hash, Ed25519 sig, merkle_root) — with `‹ prev / next ›`
  to walk the chain. The other ledger entries stay readable beside it.

**Narration.** "Nothing here is hand-wavy. Every decision is hash-chained and
Ed25519-signed — I can click any finding and walk its cryptographic chain of
custody back to the raw evidence. That's the difference between an alert and
something that holds up in an investigation."

## 4. MITRE ATT&CK

**What it shows & why it matters.** Live ATT&CK coverage: a tactic→technique grid
where tiles light and heat up as techniques map to findings. It answers "what is
the adversary actually *doing*?" in a framework analysts already speak.

**What you're seeing right now.** Header: **"13 technique(s) detected · session
global."** Lit tiles include T1059.001 PowerShell, T1071.001 Web C2, T1078 Valid
Accounts, T1055 Process Injection, T1003.001 LSASS Memory, T1566.001
Spearphishing, plus T1053.005, T1562.001, T1547.001, T1486, T1105, T1071.004,
T1036.

**What to click / expected response (the per-artifact story).**
- Select the process **victim-win11-validation-lab:6201** (in the Blackboard) →
  header changes to **"1 technique · artifact 6201"** and only **T1059.001
  PowerShell** stays lit — that host only ran encoded PowerShell.
- Select **10.1.0.7** → **5 techniques** light (T1003.001, T1055, T1059.001,
  T1071.001, T1078) — a full intrusion footprint.
- Select **10.1.0.9** → **3 techniques** (T1055, T1059.001, T1071.001) — a
  narrower footprint. *(Requires the one-time restart above for every artifact;
  the header always names the selected artifact so you can see the filter is
  active.)*
- Click **"show all"** to return to the global view. Click any lit tile for a
  popover of the findings behind it.

**Narration.** "This is per-threat ATT&CK mapping, not just a global heatmap.
Select one host and the matrix collapses to exactly what *that* artifact did —
the validation host only ran PowerShell, while 10.1.0.7 shows the full chain from
credential dumping to C2. Different threats light different tiles."

## 5. Adversarial Debate

**What it shows & why it matters.** When the swarm hits **conflict** or
**escalation**, an out-of-band LLM debate runs **prosecutor → defense → judge**
(with Zheng-2023 position-swap bias mitigation) to argue and rule on the finding.
This is the human-readable "why," and the **self-correction** mechanism: a
contested decision is re-examined and ruled on, not silently trusted.

**What you're seeing right now.** Paired exchange cards, one per artifact:
- **PROSECUTION · MALICIOUS** — the case the artifact is evil (high-belief
  consensus / sensor evidence).
- **DEFENSE · JUDGE** — the counter-case and verdict.
- Cards backed by a **real narrator verdict** carry a ⚖ badge and a **NARRATOR
  VERDICT** ruling line. Right now you can see, e.g., **203.0.113.207 → NOT
  GUILTY · winning: defense** and **142.250.64.106 → NOT GUILTY · winning:
  insufficient** — genuine LLM debate outcomes from the ledger.

**What to click / expected response.**
- **Click an exchange** → a distinct **debate inspector** (amber) opens with the
  prosecution argument, the defense/judge argument, the **judge ruling** (guilty /
  winning argument / rationale), and a link to the underlying ledger finding —
  visibly different from the artifact inspector.

**Narration.** "Stigmergy doesn't just classify — it argues with itself. On a
contested artifact, an LLM prosecutor makes the case for malice, a defense
rebuts, and a judge rules, with position-swap to cancel bias. Here's a real
verdict: the judge found 203.0.113.207 *not guilty*, with the defense winning the
argument. That's the system catching and correcting its own overreach."

---

# Side panels

## Micro-Agent Swarm (left)
**Shows** the live roster of micro-agents (badge: **60 LIVE**) — sensors and
analytic agents — each with throughput and peak τ. **Clickable:** click an agent
row → an anchored popover at the click site (role, recent-activity sparkline, and
the artifacts it has deposited evidence on; click one to cross-select it).

## MCP Blackboard (right, `bb://ioc`)
**Shows** the live pheromone-field artifacts, highest-belief first (the same set
as the field's atoms) — the central coordination surface. **Clickable:** click an
entry (e.g. **10.1.0.43**) → the **right inspector** opens (belief, plausibility,
conflict K, τ, contributing sensors, referencing ledger entries) **and the
corresponding atom in the field gets a bright pulsing selection ring** — without
opening the green center popup. Click a different entry → the ring moves. This is
coordinated selection: one artifact, highlighted everywhere.

## Event Stream (bottom-left)
**Shows** a live tail of system events (ingest, consensus, ledger writes).
**Clickable:** lines that reference a finding `#seq` or a `pher:` artifact are
clickable and cross-select that item across the dashboard.

## System Metrics (bottom-middle)
**Shows** live throughput / latency / loop-time gauges for the hot path —
evidence the deterministic pipeline is keeping up in real time. (Read-only.)

## Consensus Status (bottom-right)
**Shows** the current focus artifact and its Dempster–Shafer numbers — **Belief**,
**Plausibility**, **Conflict K** — i.e. the fusion result driving the action.
**Clickable:** the focus-artifact label cross-selects the top artifact.

---

# Step-by-step demo script

1. **Open on the Pheromone Field.** "Each glowing atom is a suspect artifact;
   size is accumulated evidence, colour is belief it's malicious. The agents
   coordinate through these pheromone trails, not by messaging each other."
2. **Double-click a hot red atom** (e.g. 10.1.0.43). The camera dives; the green
   popup shows belief, sensors, and the action verdict. "One artifact, fully
   resolved — belief 0.98, four sensors agreeing, escalated."
3. **Click an MCP Blackboard entry** (e.g. 10.1.0.32). "Watch the field —" the
   matching atom lights with a pulsing ring, and the right inspector shows the
   detail. "Same artifact, highlighted everywhere. The detail lands in the side
   panel because I clicked in the list; clicking the atom itself gives the
   in-field popup."
4. **Switch to Threat Graph.** Drag the timeline scrubber. "Same incident as a
   kill chain — drive-by, encoded PowerShell, injection, LSASS dump, persistence,
   Meterpreter C2, lateral movement."
5. **Switch to MITRE ATT&CK.** "Thirteen techniques across the session." Select
   **6201** → "this host only ran PowerShell — one tile." Select **10.1.0.7** →
   "this one shows the full chain — five tiles." Click **show all**. "Per-threat
   ATT&CK mapping, not just a global heatmap."
6. **Switch to Merkle Ledger.** Click an entry. "Every decision is BLAKE3-hashed
   and Ed25519-signed — here's the chain of custody back to the raw evidence."
7. **Switch to Adversarial Debate.** Click a ⚖ card. "On contested findings an
   LLM prosecutor, defense, and judge argue it out. Here the judge ruled
   203.0.113.207 *not guilty* — the defense won."
8. **Point out the self-correction sequence** *(the hackathon's key requirement)*:
   a `conflict_ledger`/escalation produces the debate, and the **narrator
   verdict** is written back to the signed ledger as `agent_id="narrator.judge"`
   (visible in the Merkle Ledger tab, e.g. around seq #985 and #941). "The system
   detected its own uncertainty, escalated to a debate, ruled, and signed the
   ruling into the immutable ledger — autonomous self-correction, fully audited."

---

*Stigmergy is local, defensive infrastructure. It contains no offensive tooling
and was validated only against synthetic telemetry and legitimate sample forensic
images.*
