# Stigmergy — Dataset Documentation (Deliverable 5)

## Primary dataset — official SANS Find Evil! sample case

| Field | Value |
|---|---|
| Source | Official Find Evil! starter resources, SANS Egnyte share `HACKATHON-2026`, shared by Rob Lee |
| Share URL | `https://sansorg.egnyte.com/fl/HhH7crTYT4JK` (accessible until 2026-06-17) |
| Folder | `Standard Forensic Case` |
| Files in folder | `ROCBA-BACKGROUND.pptx` (38.3 MB, case briefing), `rocba-cdrive.e01` (22.1 GB disk image), `Rocba-Memory.zip` (5.3 GB) |
| File used | `Rocba-Memory.zip` → inner `Rocba-Memory.7z` → `Rocba-Memory.raw` (18.7 GB raw Windows physical memory image, acquired 2020-11-20) |
| Why this file | A memory image is the canonical SIFT/Volatility demonstration target and the densest source of live IOCs for the pheromone pipeline |
| Acquisition into env | Downloaded via browser to the Windows host, staged into WSL2 ext4 at `/opt/findevil/data/cases/rocba/` |

### Integrity note (important — see also accuracy-report.md)

The downloaded `Rocba-Memory.zip` failed its ZIP CRC-32 check, and the inner
`.7z` reported one data-error block on extraction (`7z t` → `Sub items Errors:
1`). The 18.7 GB `.raw` extracted but **Volatility 3 could not locate the
kernel layer** on it (`A translation layer requirement was not fulfilled` after
a full PageMap + PDB scan; first 32 bytes all-zero). This is consistent with
download corruption damaging a structure Volatility needs for OS detection.

We did **not** treat this as a dead end. `bulk_extractor` performs
**stream-carving** — it recovers features (IPs, domains, URLs, emails) directly
from raw bytes without parsing the kernel or filesystem, so it is tolerant of
the localized corruption. We therefore ran the real pipeline on the
bulk_extractor output. Every indicator below came out of the **official image**.

## What was found (real bulk_extractor output)

`bulk_extractor 2.1.1 -x all -e net -e email -o be_out/run1 Rocba-Memory.raw`
(full 18.7 GB scan, 1005 s, 16 worker threads)

| Feature file | Count (real, full scan) |
|---|---|
| `ip.txt` (carved IPv4) | **1,914** |
| `domain.txt` | **471,689** |
| `url.txt` | **475,152** |
| `email.txt` | **17,451** |
| `ether.txt` (MACs) | 1,254 |

**The case at a glance (from the carved data):** the dominant carved domains
name the victim organisation — `stark-research-labs.com`,
`starkresearchlabs-my.sharepoint.com`, `starkresearchlabs.sharepoint.com` — and
its SaaS footprint (`login.windows.net`, `outlook.office365.com`,
`a.slack-edge.com`). The top carved external IPs are predominantly Azure/Office
365 and Google ranges (52.x, 13.107.x, 172.217.x), i.e. **legitimate
infrastructure** — which is exactly why the platform recorded them as low-grade
observations, not threats (see [accuracy-report.md](accuracy-report.md)).

The pipeline ingested the top 12 public IPs and 12 case-relevant domains
(Microsoft/CDN/OS telemetry filtered as noise) as correlated `edr` + `suricata`
sensor events. These flowed through the live Dempster–Shafer fusion and produced
**12 new signed ledger findings** (ledger seq **954→969**, then the
self-correction to **985**), all `action=observe` at LOW severity with
`belief_evil ≈ 0.50–0.62` — recorded for chain-of-custody, never escalated to
mitigation. Exact seqs + the self-correction in
[execution-logs/rocba_carve_run.json](execution-logs/rocba_carve_run.json);
FP / hallucination analysis in [accuracy-report.md](accuracy-report.md). Final
`findevil verify` → `ok=true, tainted_seqs=[]`.

## Secondary dataset — synthetic validation telemetry (supporting evidence only)

The platform's 33-scenario detection battery
(`scripts/whitehat_validation.py`) and 87-test suite run on **synthetic**
telemetry generated in-process. These establish the deterministic baseline
(hot-path p50 0.567 ms, 936-entry clean ledger) but are explicitly **not** the
hackathon-facing real-data evidence. They are reproducible by any cloner with no
external downloads. Provenance: generated locally; no third-party data.

## Other available official cases (not used, with reason)

| Case | Contents | Why not used |
|---|---|---|
| `Standard Forensics Case 2` | `VANKO.zip` (40.7 GB) + scenario doc | Size prohibitive for the sprint window |
| `Compromised APT Attack Scenarios` | `SRL-2015` + `SRL-2018`, four host disk images 11–16 GB each | Multi-host disk-image correlation is future work; memory image gives faster IOC density |
| `rocba-cdrive.e01` | 22.1 GB NTFS disk image (same ROCBA case) | The Sleuth Kit (`tsk.fls`) and `bulk_extractor` shims support it; deferred for time. A judge can run `tsk.fls` against it directly via the MCP tool |

## Reproducibility

A judge with the SANS share can reproduce the exact run:

```bash
# 1. download Rocba-Memory.zip from the official share, unzip + un-7z to .raw
# 2. carve real indicators (corruption-tolerant)
bulk_extractor -x all -e net -e email -o be_out/run1 Rocba-Memory.raw
# 3. drive the live pipeline on the carved indicators
python scripts/real_data_carve_run.py --be-dir be_out/run1 \
    --export docs/hackathon/execution-logs/rocba_carve_run.json
# 4. confirm the new signed ledger entries verify
findevil verify
```
