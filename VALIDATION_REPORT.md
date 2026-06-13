# Stigmergy Validation Report

Date: 2026-05-10  
Environment: WSL2 Ubuntu 24.04 on a local workstation  
Scope: local defensive validation with synthetic JSON telemetry only

## Overall Verdict

Conditionally compliant for public research and local defensive SOC validation.

The core platform claims are validated: deterministic hot-path detection,
Dempster-Shafer evidence fusion, tamper-evident ledger, safe-mode CACAO
execution, STIX/OCSF emission, MCP tool exposure, narrator debate, fractal pivot
agents, and Rekor public anchoring.

Remaining gaps are operational hardening items around optional binaries and GPU
inference offload.

## Core Results

| Area | Result |
|---|---|
| Hot path p50 | 0.567 ms |
| Hot path p99 | 1.071 ms |
| Ledger entries | 936 |
| Ledger verification | `ok=true`, `tainted_seqs=[]` |
| D-S fusion tests | 15/15 passed |
| CACAO structural tests | 10/10 passed |
| Pytest suite | 73 passed, 1 skipped |
| Rekor anchoring | batch 3, `rekor_log_index=1492269391` |

## Performance

| Metric | Target | Measured | Status |
|---|---:|---:|---|
| Hot path p50 | <= 6 ms | 0.567 ms | PASS |
| Hot path p99 | <= 20 ms | 1.071 ms | PASS |
| Ledger append p50 | ~800 us | 235 us | PASS |
| D-S fusion p50 | ~40 us | 9.42 us | PASS |
| Sustained load injection | not fixed | 1,524 events/s | PASS |

## Standards Validation

| Standard | Evidence | Status |
|---|---|---|
| STIX 2.1 | emitted bundle with Indicator, Observed Data, and Sighting objects | PASS |
| OCSF | emitted Detection Finding with `class_uid=2004` and `category_uid=2` | PASS |
| CACAO 2.0 | generated playbook structure and safe-mode execution ledger entries | PASS |
| BLAKE3 ledger chain | full chain verification clean | PASS |
| Ed25519 signatures | full chain verification clean | PASS |
| UUIDv7 finding IDs | schema stress validation passed | PASS |
| Rekor | public log index `1492269391` verified | PASS |

## Scenario Coverage

Validated scenario families:

- PowerShell execution, T1059.001
- LSASS credential access, T1003.001
- Process injection, T1055
- C2 beaconing, T1071.001
- Yager conflict handling
- late telemetry routing
- malformed telemetry rejection
- duplicate and replay suppression
- total conflict human escalation
- Valkey service failure and recovery
- lateral movement correlation, T1078
- persistence, T1547.001 and T1053.005
- defense evasion, T1562.001
- extended ATT&CK coverage including T1105, T1036, T1566.001, T1486, T1071.004

## Binary Status

| Binary | Status | Version / Evidence |
|---|---|---|
| YARA | Present | 4.5.0 |
| Zeek | Present | 8.1.2 under `/opt/zeek/bin/zeek` |
| TShark | Present | 4.2.2 |
| Sleuth Kit `fls` | Present | 4.12.1 |
| Volatility 3 | Present | `vol3` CLI |
| SQLite CLI | Present | 3.45.1 |
| Plaso | Partial | Python module and venv script present, CLI not on PATH |
| bulk_extractor | Missing | not available in current package sources |

## Known Gaps

| ID | Gap | Severity | Resolution |
|---|---|---|---|
| G1 | MCP service needs restart to load the latest Zeek/Plaso shim fallback changes | P2 | `sudo systemctl restart findevil-mcp.service` |
| G2 | `log2timeline.py` is not on PATH although the Plaso module and script exist | P2 | expose the venv script on PATH or use the patched shim fallback |
| G3 | `bulk_extractor` is missing | P1 | install from the SIFT package set or source build |
| G4 | GPU inference offload is inactive | P2 | rebuild `llama-cpp-python` with CUDA for the local GPU architecture |

## Final Ledger State

```text
entries=936
max_seq=936
verify={"ok": true, "tainted_seqs": []}

anchors:
batch 1: local Merkle root, no Rekor index, legacy timestamp precision
batch 2: local Merkle root, no Rekor index
batch 3: Rekor index 1492269391, 19-digit nanosecond timestamp
```

## Final Test Suite

```text
73 passed, 1 skipped
```

## Readiness Statement

Stigmergy is ready for public cloning, local defensive validation, and research
review. Operators should install optional forensic binaries and configure local
model inference according to their hardware before using it as a production SOC
component.
