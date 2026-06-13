# Stigmergy — Agent Execution Logs (Deliverable 8)

Structured, reproducible traces of Stigmergy acting on the **real** SANS ROCBA
case data: finding → tool execution → reasoning trace → chain of custody, with
timestamps and ledger sequence numbers.

## Files

| File | What it is |
|---|---|
| `rocba_carve_run.json` | The real-data run summary: carved indicators (real IPs/domains from the official image), events published, new signed ledger seqs, and the self-correction (Yager conflict → narrator verdict). Produced by `scripts/real_data_carve_run.py`. |
| `ledger_export.json` | Sanitised export of the ledger entries created by the run (finding_id, timestamps, agent_id, artifact, reasoning trace, chain-of-custody refs, MITRE). No private keys, no raw evidence bytes. |
| `iteration_trace.md` | Human-readable walkthrough of the iteration-over-iteration self-correction: the prosecutor's initial read, the defense rebuttal, and the judge's overturning verdict, with before/after ledger seqs. |

## How these were produced (reproducible)

```bash
# real indicators carved from the official image (corruption-tolerant)
bulk_extractor -x all -e net -e email -o be_out/run1 Rocba-Memory.raw
# drive the live pipeline + capture the self-correction
python scripts/real_data_carve_run.py --be-dir be_out/run1 \
    --export docs/hackathon/execution-logs/rocba_carve_run.json
# sanitised ledger export for the entries the run created
python scripts/export_ledger.py --since <tip_before> \
    --out docs/hackathon/execution-logs/ledger_export.json
# integrity proof over everything
findevil verify    # -> ok=true, tainted_seqs=[]
```

Chain of custody: every entry carries a UUIDv7 `finding_id`, a `prev_hash` link,
a BLAKE3 `entry_hash`, an Ed25519 signature, and `chain_of_custody` references to
parent findings. `findevil verify` walks the whole chain; Merkle batches are
anchored to Sigstore Rekor.
