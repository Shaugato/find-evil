# Stigmergy — Voiceover Scripts

> Record each block as its own audio file, in order. They're independent — re‑record
> any one freely. Speak at a normal, unhurried pace; the durations assume ~150 wpm.
> Save all clips in the same folder (suggested: `D:\Autonomous DFIR - Agentic SOC\docs\demo\audio\`).
> Total target ≈ **4:50** (cap 5:00). All numbers are real and match the live system.
> PARTS 3–4 are the **live ROCBA real‑data segment**; PART 3B is the **MCP
> architectural‑guardrail** beat — see [LIVE_SEGMENT_NOTES.md](LIVE_SEGMENT_NOTES.md).

---

### vo_01_problem.wav — ~25 s — tone: calm, serious, building
> A modern intrusion throws thousands of weak signals at a SOC — endpoint, network,
> memory, signatures — and analysts drown in alerts while the clock runs. What if a
> swarm of agents could fuse those signals, decide, and prove its reasoning —
> locally, with no cloud, and a tamper‑evident record of every call?

---

### vo_02_overview.wav — ~38 s — tone: confident, explanatory  (GAP 2 speed + GAP 3 swarm)
> This is Stigmergy — a local, defensive DFIR platform. Sixty micro‑agents — you can
> watch them ticking here — act like an ant colony: each continuously scores artifacts
> and drops "pheromone" on the IPs, domains, and processes it finds suspicious, on a
> shared blackboard. A deterministic hot path fuses those deposits with Dempster–Shafer
> evidence theory and decides in well under a millisecond — with no language model in
> the loop — fast enough to keep pace with attacks that reach domain control in minutes.
> The model only debates and explains afterward, off the critical path, where it can't
> slow or corrupt the decision. And it all runs on this one machine.

---

### vo_03_live_rocba.wav — ~55 s — tone: matter‑of‑fact, credible, a little proud  ⟵ LIVE real data
> And this isn't a mock‑up — this is the official SANS ROCBA case, an eighteen‑
> gigabyte Windows memory image from a real intrusion at stark‑research‑labs. The
> full forensic carve I ran ahead of time — here's its output, real indicators
> pulled straight from memory. Now watch me carve a slice of that same evidence
> live, with bulk_extractor — and there it is, real IPs extracted in seconds,
> including one‑forty‑two‑dot‑two‑fifty, the address the swarm will flag. And every
> finding it produces is hash‑chained and Ed25519‑signed — the ledger verifies ok,
> zero tainted, across more than a thousand signed findings.

---

### vo_03b_mcp.wav — ~16 s — tone: pointed, this is the architecture flex  ⟵ GAP 1 (MCP guardrail)
> And notice — the agent only ever calls typed forensic tools. This is Approach #2:
> a purpose‑built MCP server. Sixty‑two typed functions — Volatility, YARA,
> bulk_extractor — and no execute_shell, no arbitrary command. It physically cannot
> run a destructive command, because the architecture never exposes one. That's a
> guardrail by construction, not a prompt.

---

### vo_04_self_correction.wav — ~45 s — tone: the climax; slower on "raises a conflict … live"  ⟵ LIVE self‑correction + GAP 5 pivots (honest: live conflict, pre‑signed verdict)
> Now feed that carved indicator into the swarm. Two sensors disagree — Suricata says
> malicious command‑and‑control, the endpoint agent says benign. Watch the ledger
> advance live: the consensus engine computes a Yager conflict — point three five —
> and instead of guessing, it raises a conflict and escalates, live. And suspicious
> artifacts also spawn ephemeral fractal pivot agents — bounded autonomous
> investigators, depth three, width sixteen — that chase related evidence and then
> dissolve; here are their signed findings in the ledger. The prosecutor‑defense‑judge
> debate runs off the hot path, so here's the verdict it already signed for this same
> address, on the dashboard.

---

### vo_05_field.wav — ~30 s — tone: guided tour, engaged
> Back to the command shell. Every glowing atom is one suspect artifact, bonded to
> the central blackboard. Size is how much evidence has piled up; colour is the
> swarm's belief it's evil — red is bad. The hot cluster here is internal lateral
> movement — ten‑dot‑one‑dot‑zero hosts at ninety‑nine percent belief. I can dive
> into any atom to see its full case.

---

### vo_06_graph.wav — ~35 s — tone: narrative, guiding the eye
> Stigmergy doesn't just score artifacts — it reconstructs the story. The Threat
> Graph lays the incident out as a kill chain: a drive‑by, encoded PowerShell,
> injection into svchost, an LSASS credential dump, a Run‑key for persistence, a
> Meterpreter beacon, then lateral movement and exfiltration. I can scrub the
> timeline to replay exactly how the attack unfolded, step by step.

---

### vo_07_mitre_ledger.wav — ~38 s — tone: precise, closing the technical case  (GAP 4 CACAO + Rekor)
> ATT&CK mapping is per‑threat, not just a global heatmap — select one host and the
> matrix collapses to exactly what that artifact did; this validation host only ran
> PowerShell. And on a confident malicious verdict the platform doesn't just alert —
> it fires an automated CACAO containment playbook: detection through response,
> autonomously. Every decision is court‑defensible too — each finding is BLAKE3‑hashed,
> Ed25519‑signed, hash‑chained, and anchored to a public Sigstore transparency log,
> so anyone can verify the record wasn't altered.

---

### vo_08_close.wav — ~20 s — tone: warm, confident close
> Stigmergy: a local, defensive SOC that senses, fuses, decides, debates, and proves
> — autonomously, and entirely on your own hardware. It's open source, and the
> architecture, the standards, and a live demo are all in the repo. Thanks for
> watching.

---

**Word counts (for pacing):** parts run ~55–105 words each; at ~150 wpm that's
~22–42 s. If a clip runs long, the first sentence of each is the most cuttable.
