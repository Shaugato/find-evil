# Stigmergy — Voiceover Scripts

> Record each block as its own audio file, in order. They're independent — re‑record
> any one freely. Speak at a normal, unhurried pace; the durations assume ~150 wpm.
> Save all clips in the same folder (suggested: `D:\Autonomous DFIR - Agentic SOC\docs\demo\audio\`).
> Total target ≈ **4:30**. All numbers are real and match the live dashboard.

---

### vo_01_problem.wav — ~25 s — tone: calm, serious, building
> A modern intrusion throws thousands of weak signals at a SOC — endpoint, network,
> memory, signatures — and analysts drown in alerts while the clock runs. What if a
> swarm of agents could fuse those signals, decide, and prove its reasoning —
> locally, with no cloud, and a tamper‑evident record of every call?

---

### vo_02_overview.wav — ~35 s — tone: confident, explanatory
> This is Stigmergy — a local‑first, defensive DFIR platform. Sixty micro‑agents act
> like an ant colony: each sensor drops "pheromone" on the artifacts it finds
> suspicious — IPs, domains, processes, hashes — on a shared blackboard. A
> deterministic hot path fuses those deposits with Dempster–Shafer evidence theory
> into a single belief, signs the decision into a cryptographic ledger, and only then
> does a language‑model debate explain it. Everything you'll see runs on this one
> machine.

---

### vo_03_live_exec.wav — ~40 s — tone: matter‑of‑fact, credible
> This isn't a mock‑up. Here's the live engine. I'll verify the integrity of the
> evidence ledger — every finding is hash‑chained and Ed25519‑signed. It returns
> "ok", with zero tainted entries, across eleven hundred signed findings. And the
> ATT&CK coverage is computed from those real findings: thirteen techniques, led by
> PowerShell execution and web command‑and‑control.

---

### vo_04_self_correction.wav — ~35 s — tone: the climax, slower, confident
> Here's what makes it autonomous. When the swarm hits a conflict — sensors disagree,
> or belief is borderline — it escalates to an out‑of‑band debate: an LLM prosecutor
> argues the artifact is malicious, a defense rebuts, and a judge rules, with
> position‑swap to cancel bias. The verdict is written back into the same signed
> ledger. Here are real verdicts — at entries nine‑eighty‑five and nine‑forty‑one,
> the judge found the artifacts not guilty. The system caught its own overreach and
> corrected it — and signed the correction.

---

### vo_05_field.wav — ~35 s — tone: guided tour, engaged
> Back to the command shell. Every glowing atom is one suspect artifact, bonded to
> the central blackboard. Size is how much evidence has piled up; colour is the
> swarm's belief it's evil — red is bad. The hot cluster here is internal lateral
> movement — ten‑dot‑one‑dot‑zero hosts at ninety‑nine percent belief. I can dive
> into any atom to see its full case.

---

### vo_06_graph_debate.wav — ~40 s — tone: connecting proof to visuals
> The Threat Graph reconstructs the kill chain — drive‑by to encoded PowerShell,
> injection into svchost, an LSASS credential dump, a Run‑key for persistence, a
> Meterpreter beacon, then lateral movement. And the Adversarial Debate tab shows
> those prosecutor‑defense‑judge exchanges I ran in the terminal — here's the judge's
> real verdict on two‑oh‑three‑dot‑zero, not guilty, the defense winning the
> argument. That's the audited self‑correction, on screen.

---

### vo_07_mitre_ledger.wav — ~40 s — tone: precise, closing the technical case
> ATT&CK mapping is per‑threat, not just a global heatmap. Across the session,
> thirteen techniques. But select one host and the matrix collapses to exactly what
> that artifact did — this validation host only ran PowerShell, a single technique.
> And every one of these decisions is court‑defensible: in the Merkle Ledger I can
> open any finding and walk its BLAKE3 hash, Ed25519 signature, and chain of custody
> back to the raw evidence.

---

### vo_08_close.wav — ~20 s — tone: warm, confident close
> Stigmergy: a local, defensive SOC that senses, fuses, decides, debates, and proves
> — autonomously, and entirely on your own hardware. It's open source, and the
> architecture, the standards, and a live demo are all in the repo. Thanks for
> watching.

---

**Word counts (for pacing):** parts run ~55–105 words each; at ~150 wpm that's
~22–42 s. If a clip runs long, the first sentence of each is the most cuttable.
