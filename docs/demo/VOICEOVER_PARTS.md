# Stigmergy — Voiceover Scripts

> Record each block as its own audio file, in order. They're independent — re‑record
> any one freely. Speak at a normal, unhurried pace; the durations assume ~150 wpm.
> Save all clips in the same folder (suggested: `D:\Autonomous DFIR - Agentic SOC\docs\demo\audio\`).
> Total target ≈ **4:35**. All numbers are real and match the live dashboard.
> PARTS 3–4 are the **live ROCBA real‑data segment** — see
> [LIVE_SEGMENT_NOTES.md](LIVE_SEGMENT_NOTES.md).

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

### vo_03_live_rocba.wav — ~55 s — tone: matter‑of‑fact, credible, a little proud  ⟵ LIVE real data
> And this isn't a mock‑up — this is the official SANS ROCBA case, an eighteen‑
> gigabyte Windows memory image from a real intrusion at stark‑research‑labs. The
> full forensic carve I ran ahead of time — here's its output, real indicators
> pulled straight from memory. Now watch me carve a slice of that same evidence
> live, with bulk_extractor — and there it is, real IPs extracted in seconds,
> including one‑forty‑two‑dot‑two‑fifty, the address the swarm will flag. And every
> finding it produces is hash‑chained and Ed25519‑signed — the ledger verifies ok,
> zero tainted, across eleven hundred findings.

---

### vo_04_self_correction.wav — ~45 s — tone: the climax; slower on "knows when it doesn't know"  ⟵ LIVE self‑correction
> Now feed that carved indicator into the swarm. Two sensors disagree — Suricata
> calls it malicious command‑and‑control, the endpoint agent says benign. Watch:
> the ledger advances live, and the consensus engine computes a Yager conflict —
> point three five — and instead of guessing, it raises a conflict and escalates.
> That's the self‑correction: the swarm knows when it doesn't know. Off the hot
> path, an LLM prosecutor, defense, and judge debate it and sign a verdict — here
> it is on the dashboard, the judge's ruling on one‑forty‑two‑dot‑two‑fifty,
> recorded in the immutable ledger.

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
