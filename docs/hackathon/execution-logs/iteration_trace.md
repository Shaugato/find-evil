# Iteration trace — the self-correction sequence

This is the iteration-over-iteration trace the brief asks for: how the system's
read of one indicator *changed* as evidence accumulated. It walks the **Yager
conflict → re-investigation → resolution** path on a **real IP carved from the
official ROCBA memory image.**

> **See also — autonomous re-sequencing (Criterion 1):** beyond this conflict/debate
> path, the agent re-sequences its *own* investigation via the fractal pivot loop —
> each finding's follow-ups seed a deeper pivot (`parent_id` lineage, depth 0→2,
> bounded at `max_depth=3`). The real connected chain is in
> [pivot_chain.md](pivot_chain.md) — `bash scripts/demo_pivot_chain.sh`.

> **Provenance & honesty:** the conflicting evidence is *deliberately
> constructed* on a real carved IP (a severity-1 Suricata "malicious" alert vs a
> high-confidence EDR "benign" reputation), because the carved indicators alone
> did not produce an organic sensor conflict. This is the brief-sanctioned approach
> and is disclosed here and in [accuracy-report.md](../accuracy-report.md §5.2).
> The *mechanism* exercised — Dempster–Shafer conflict detection, suppression of
> auto-mitigation, and the prosecutor/defense/judge debate — is real, unmodified
> platform behavior. The exact `seq` numbers below are populated by
> `scripts/real_data_carve_run.py --export`; see
> [rocba_carve_run.json](rocba_carve_run.json) for the machine record.
>
> **The conflict/self-correction mechanism also fires *organically*** across the
> 33-scenario synthetic validation battery (`scripts/whitehat_validation.py` —
> contradictory sensors → `conflict_ledger`, total conflict → `escalate_human`;
> see [accuracy-report.md §4](../accuracy-report.md)). It is not unique to this one
> induced conflict — the induced conflict simply puts a *real carved IP* on the
> exact same code path so the demo can show it on real evidence.

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

## Worked example — the actual run (2026-06-12)

Real carved IP under conflict: **`142.250.64.106`** (a Google range carved from
the official image). Ledger grew 936 → 985 over the run.

| Iteration | seq | agent | action / verdict | reasoning (claim, verbatim from ledger) |
|---|---|---|---|---|
| 0 — first read | **969** | `swarm.consensus` | **conflict_ledger** (K=0.377) | *"Fused 2 agent reports for pher:ip:142.250.64.106; action=conflict_ledger, belief_evil=0.215, conflict_K=0.377"* |
| 1 — prosecutor | (debate) | `narrator` prosecutor | argues malicious | cites the Suricata alert exhibit |
| 2 — defense | (debate) | `narrator` defense | argues benign | cites the EDR reputation exhibit |
| 3 — judge | (debate) | `narrator` judge | weighs both | initial ruling |
| 4 — position swap | (debate) | `narrator` judge | re-runs with sides swapped | Zheng-2023 bias check |
| 5 — resolution | **985** | `narrator.judge` | **verdict recorded** | *"Argument A and Argument B present conflicting evidence, with high confidence in the malicious agent report but low confidence in the benign agent report … The exhibits do not provide sufficient information to determine the defendant's intent with certainty."* |

The judge's actual verdict — *"insufficient information to determine intent"* —
is the correct self-correction: faced with genuinely contradictory evidence, the
system neither blocked nor cleared the IP automatically; it recorded a reasoned,
signed "needs-more-evidence" ruling with custody back to the conflict finding
(seq 969). `findevil verify` covers both entries: `ok=true, tainted_seqs=[]`.

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
