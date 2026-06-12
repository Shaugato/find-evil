# FIND EVIL — Accuracy Report (Deliverable 6)

This report is deliberately honest about what FIND EVIL gets right, what it gets
wrong, and — most importantly — *which errors can and cannot affect the evidence
record.* The central claim is that **evidence integrity is architectural, not
behavioral**: the LLM's mistakes are structurally prevented from corrupting a
decision or the ledger.

## 1. Evidence integrity: architectural vs prompt-based

| Control | Type | What it guarantees |
|---|---|---|
| Typed MCP tools (no `execute_shell_cmd`) | **Architectural** | The agent cannot run arbitrary commands or touch evidence outside registered, schema-validated tools. |
| Reference-resolved exhibit IDs | **Architectural** | Tools act on registered evidence handles, not free-form paths the model invents. |
| LLM excluded from the decision path | **Architectural** | Dempster–Shafer math + threshold evaluator choose mitigate/conflict/escalate **before** any model runs. A hallucinated "verdict" cannot trigger containment. |
| `outlines`/`xgrammar` FSM-constrained output | **Architectural** | Agent/judge output is schema-valid JSON by construction; malformed free-text can't parse into a finding. |
| Citation validation | **Architectural** | Exhibit references the model fabricates are rejected before reaching the ledger. |
| BLAKE3 hash chain + Ed25519 signatures | **Architectural** | Any post-hoc tampering breaks `findevil verify`, independent of the LLM. |
| Narrator role instructions (prosecutor/defense/judge) | Prompt-based | Improves *explanation quality*; not relied on for integrity. |
| Zheng-2023 position-swap | Prompt-based | Reduces ordering bias in the judge; quality, not integrity. |

**The test we hold ourselves to:** if every prompt-based control failed at once
(the model ignored all instructions), FIND EVIL would still emit a correct,
signed, tamper-evident decision — because the decision was never the model's.

## 2. Spoliation / tamper testing

Spoliation = destruction or alteration of evidence. We tested whether the ledger
detects it.

| Test | Method | Result |
|---|---|---|
| Post-hoc payload edit | Mutate a committed entry's bytes, re-run `findevil verify` | **Detected** — verify reports the tainted seq; chain breaks at the edit. (See `tests/test_ledger_chain.py`, `test_metrics_inventory.py`.) |
| Signature forgery | Re-sign a tampered playbook/entry with a different key | **Detected** — `verify_playbook` / `verify_chain` reject wrong-key signatures (`tests/test_cacao_sign.py`). |
| JWS tamper | Flip a byte in a CACAO JWS payload | **Detected** — `verify_playbook_jws` returns None (`tests/test_cacao_sign.py`). |
| Hallucinated exhibit citation | Narrator cites an exhibit not in the finding | **Rejected** pre-ledger by citation validation (`tests/test_scoped_prompt.py`). |
| Out-of-band Merkle/Rekor anchor | Recompute root, compare to anchored value | Anchored root `rekor_log_index=1492269391` resolves; `findevil_rekor_anchor_age_seconds` alarms if anchoring stalls. |

**Honest failure mode found:** the ledger proves *its own* integrity, but it
cannot prove that a sensor *upstream* of ingest didn't lie. If a sensor feeds a
false indicator, FIND EVIL faithfully records a finding about a false indicator.
This is inherent to any evidence system — garbage in is recorded as
provenance-tagged garbage, not silently "fixed." We surface the source sensor on
every finding so a reviewer can audit the chain back to its origin.

## 3. The real-data run — false positives, misses, hallucinations

**Dataset:** official SANS Find Evil! ROCBA memory image (see
[dataset.md](dataset.md)). **Tool:** `bulk_extractor` carving (the image was
corrupt for Volatility — see §5).

<!-- RESULTS_PLACEHOLDER: filled from execution-logs/rocba_carve_run.json -->

### False positives

Carving a memory image surfaces every string that *looks* like an IP/domain,
including OS/CDN telemetry (Microsoft, Akamai, DigiCert…) and in-memory
documentation. These are **not** indicators of compromise. We mitigate two ways:

1. **Noise filtering** — known-benign domain suffixes and non-public/RFC-1918 IP
   ranges are excluded before ingest (`scripts/real_data_carve_run.py`).
2. **Modest priors** — a carved indicator enters as a *low-confidence* sensor.
   It cannot cross the mitigation threshold alone; it needs corroboration. This
   is the whole point of Dempster–Shafer fusion: one weak source ≠ consensus.

Residual false positives that survive filtering are recorded as *observations*,
not mitigations — exactly the conservative behavior we want.

### Missed artefacts

Because the image was corrupt for Volatility, we did **not** recover
process-level artefacts (injected code via malfind, hidden DLLs via ldrmodules,
process tree anomalies). On a clean image these are the richest signal; their
absence here is a *data limitation, not a platform limitation* — the
`volatility.pslist/malfind/netscan/...` shims are implemented and version-verified
(`ok=true`), they simply had no parseable kernel to run against. A judge with a
clean image gets the full structured analysis.

### Hallucinated claims

The narrator runs on a local 3B model and *can* produce imperfect prose. What it
**cannot** do:

- cite evidence not in the finding (citation validation rejects it),
- emit malformed output that becomes a finding (FSM-constrained JSON),
- change the deterministic decision (it runs after the ledger entry exists).

So narrator hallucinations degrade *readability*, never *integrity*. Any
verdict in the ledger is signed and traceable to the exhibits it was allowed to
see.

## 4. Detection accuracy on validated scenarios (synthetic baseline)

The 33-scenario battery (`scripts/whitehat_validation.py`) exercises known TTPs
with known-correct outcomes:

- True positives: PowerShell exec (T1059.001), LSASS access (T1003.001), process
  injection (T1055), C2 beacon (T1071.001), lateral movement (T1078),
  persistence (T1547.001/T1053.005), defense evasion (T1562.001), ransomware,
  DNS tunneling — all fire the expected action.
- Conflict handling: contradictory sensors → `conflict_ledger` (no auto-mitigate).
- Escalation: total conflict → `escalate_human`.
- Negative controls: malformed/late/duplicate telemetry routed correctly, not
  mitigated.

These are synthetic and thus *supporting* evidence — but they establish that the
fusion + threshold logic behaves correctly when ground truth is known.

## 5. Known limitations (stated plainly)

1. **Corrupt official image.** Our `Rocba-Memory.zip` download failed CRC and the
   inner `.7z` had a data-error block; the extracted `.raw` defeated Volatility
   kernel detection. We pivoted to corruption-tolerant carving. Honest provenance
   in [dataset.md](dataset.md).
2. **Self-correction is constructed.** The Yager-conflict self-correction in the
   real-data run is **deliberately induced** on a real carved IP (conflicting
   sensors), because organic conflict didn't arise from the carved indicators
   alone. This is disclosed in the execution log and is the brief-sanctioned
   approach. The *mechanism* exercised is real and unmodified.
3. **GPU inference unavailable.** Pascal P620 + modern ggml kernels are slower
   than CPU; we run CPU inference. Narrator latency is seconds, not the 25–40 ms
   target. Hot path unaffected (no LLM).
4. **Local sample data only.** No real-target scanning, no offensive tooling.

## 6. Bottom line

FIND EVIL will occasionally surface a benign carved string or write imperfect
narrator prose. It will **not** auto-mitigate on weak evidence, accept a
fabricated citation, let the LLM override the math, or fail to detect tampering.
The errors it makes are the *safe* kind; the errors it structurally prevents are
the *dangerous* kind.
