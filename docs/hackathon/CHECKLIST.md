# FIND EVIL — 8/8 Deliverable Checklist (the judges' checklist)

> "Missing any one means elimination." One line per deliverable: present /
> location / status.

| # | Deliverable | Present | Location | Status |
|---|---|:--:|---|---|
| 1 | **Code repository** (public, MIT or Apache 2.0) | ✅ | [github.com/Shaugato/find-evil](https://github.com/Shaugato/find-evil) — **MIT** ([LICENSE](../../LICENSE)) | Public, pushed |
| 2 | **Demo video** (≤5 min, real data, self-correction) | ◻️→📝 | Pre-staged script: [demo-video-script.md](demo-video-script.md) | **Requires user to record** (only item needing direct user action) |
| 3 | **Architecture diagram** (components, pattern name, arch-vs-prompt guardrails) | ✅ | [architecture-diagram.md](architecture-diagram.md) (Mermaid) | Done — names "Custom MCP Server (Approach #2)" |
| 4 | **Written project description** (Devpost story) | ✅ | [project-description.md](project-description.md) | Done |
| 5 | **Dataset documentation** (source, provenance, findings) | ✅ | [dataset.md](dataset.md) | Done — official ROCBA image + provenance |
| 6 | **Accuracy report** (FPs, misses, hallucinations, evidence integrity, spoliation) | ✅ | [accuracy-report.md](accuracy-report.md) | Done |
| 7 | **Try-it-out instructions** (judge runs locally, deps listed) | ✅ | [try-it-out.md](try-it-out.md) · [Docker](../../deploy/README.md) · [installer](../../installer/README.md) · live website | Done — 4 paths |
| 8 | **Agent execution logs** (finding→tool→reasoning→custody, timestamps, iterations) | ✅ | [execution-logs/](execution-logs/) | Done — real-run export + iteration trace |

## Supporting evidence (beyond the 8)

- **Compliance traceability:** [docs/COMPLIANCE_LIVE.md](../COMPLIANCE_LIVE.md) — every P0/P1 requirement, status + evidence.
- **Run log:** [docs/AUTONOMOUS_RUN_LOG.md](../AUTONOMOUS_RUN_LOG.md) — per-task verification evidence.
- **Companion website:** `web/` (Next.js, deployed to Vercel) — architecture explainer + real-run replay viewer.
- **Validation baseline:** [VALIDATION_REPORT.md](../../VALIDATION_REPORT.md) — 87 tests, hot-path SLA, standards proven live.

## The one item requiring you (the user)

**Deliverable 2 — the demo video.** Everything is pre-staged in
[demo-video-script.md](demo-video-script.md): exact commands, expected output,
and narration for a ≤5-minute screencast. An AI agent cannot record
screen/audio; you run the script and hit record. The narrator step can be
pre-run so the verdict is already in the ledger to show.
