# Iteration trace — the self-correction sequence

This is the iteration-over-iteration trace the brief asks for: how the system's
read of one indicator *changed* as evidence accumulated. It walks the **Yager
conflict → re-investigation → resolution** path on a **real IP carved from the
official ROCBA memory image.**

> **Provenance & honesty:** the conflicting evidence is *deliberately
> constructed* on a real carved IP (a high-confidence YARA "malicious" signal vs
> a high-confidence EDR "benign" signal), because the carved indicators alone did
> not produce an organic sensor conflict. This is the brief-sanctioned approach
> and is disclosed here and in [accuracy-report.md](../accuracy-report.md §5.2).
> The *mechanism* exercised — Dempster–Shafer conflict detection, suppression of
> auto-mitigation, and the prosecutor/defense/judge debate — is real, unmodified
> platform behavior. The exact `seq` numbers below are populated by
> `scripts/real_data_carve_run.py --export`; see
> [rocba_carve_run.json](rocba_carve_run.json) for the machine record.

## The mechanism (always true, in code)

1. **Ingest** (`findevil.ingest.flow`): per-IOC reports are collected into a
   2-second tumbling window.
2. **Fuse** (`findevil.swarm.ds_fusion`): Dempster–Shafer combination computes
   `belief_evil`, `plausibility_evil`, and conflict mass `conflict_K`. Two
   strongly opposing sensors drive `K` high.
3. **Evaluate** (`findevil.swarm.evaluator`): when `K_YAGER_LO ≤ K ≤ K_YAGER_HI`
   the action is **`conflict_ledger`** — the platform **does not auto-mitigate.**
   It writes a conflict finding and routes to the narrator.
4. **Debate** (`findevil.narrator.graph`): a prosecutor argues malicious, a
   defense argues benign, and a judge rules — then the positions are **swapped**
   and the judge re-runs (Zheng-2023 bias mitigation). Citations are validated;
   output is schema-constrained.
5. **Record**: the judge's verdict is appended as a signed ledger entry with
   `chain_of_custody` referencing the conflict finding. `findevil verify` covers
   it.

## Worked example (regenerated from the real run)

| Iteration | seq | agent | action / verdict | reasoning (claim) |
|---|---|---|---|---|
| 0 — first read | `{{conflict_seq}}` | `swarm.consensus` | **conflict_ledger** (K≈`{{K}}`) | "Yager conflict on real carved IP `{{ip}}`: YARA malicious vs EDR benign — auto-mitigation suppressed, routed to narrator." |
| 1 — prosecutor | (debate) | `narrator.prosecutor` | argues malicious | cites the YARA hit exhibit |
| 2 — defense | (debate) | `narrator.defense` | argues benign | cites the EDR reputation exhibit |
| 3 — judge | (debate) | `narrator.judge` | weighs both | initial lean |
| 4 — position swap | (debate) | `narrator.judge` | re-runs swapped | bias check |
| 5 — resolution | `{{verdict_seq}}` | `narrator.judge` | **verdict recorded** | "`{{verdict_claim}}`" |

**What changed:** the system's *first* deterministic reaction was *not* "block
it" and *not* "ignore it" — it was "I have contradictory evidence, I will not act
automatically, I will investigate." The narrator then produced a reasoned,
bias-checked verdict, and the whole arc — conflict, debate, resolution — is in
the signed ledger with custody links. That is the platform correcting its own
first impression instead of confidently acting on noisy evidence.

## Reproduce

```bash
python scripts/real_data_carve_run.py --be-dir <bulk_extractor output> \
    --export docs/hackathon/execution-logs/rocba_carve_run.json \
    --replay-out web/public/data/rocba_run.json
findevil verify     # ok=true, tainted_seqs=[]  — the conflict + verdict included
```
