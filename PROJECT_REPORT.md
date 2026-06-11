# FIND EVIL Project Report

## Executive Summary

FIND EVIL is a defensive autonomous Security Operations Center platform. It is
designed to help detect, correlate, explain, and safely respond to cyberattack
signals faster than a human analyst could manually inspect every alert.

The system takes security telemetry, such as process events, network signals,
YARA matches, EDR-style findings, and memory-analysis indicators, then combines
that evidence into a clear decision: observe, mitigate, escalate, or record a
conflict. Every decision is written into a tamper-evident forensic ledger so the
system can later prove what it saw, what it decided, and why.

The key achievement is that FIND EVIL is not just a dashboard or a collection of
scripts. It is an integrated defensive platform with live services, mathematical
evidence fusion, automated safe-mode response, standards-based exports, local
AI-assisted explanation, and a validated test suite.

## What Was Built

FIND EVIL is an end-to-end autonomous SOC research platform. It includes:

- A telemetry ingestion pipeline for synthetic and owned security events.
- A Dempster-Shafer evidence fusion engine that combines sensor confidence
  mathematically.
- A pheromone-style blackboard in Valkey that tracks live suspicion around
  indicators such as processes, files, IP addresses, domains, users, registry
  keys, and tasks.
- A deterministic threshold evaluator that decides when to observe, mitigate,
  escalate, or record conflicting evidence.
- A cryptographic forensic ledger using BLAKE3 hashes, Ed25519 signatures, and
  UUIDv7 finding IDs.
- CACAO 2.0-style safe-mode response playbooks.
- STIX 2.1 and OCSF Detection Finding emission.
- A local MCP blackboard server that exposes platform state and forensic tool
  shims.
- A narrator service that uses an LLM out of band to explain decisions after the
  deterministic detection decision has already been made.
- Fractal pivot agents that investigate high-interest artifacts while enforcing
  depth and concurrency limits.
- OpenTelemetry observability and a live dashboard.
- A validation harness with synthetic attack scenarios and automated tests.

## Why It Matters

Modern security teams receive more alerts than humans can triage manually.
Attackers can move from initial execution to credential access or lateral
movement in minutes. Traditional SOC workflows often depend on a human analyst
reading isolated alerts and manually connecting the dots.

FIND EVIL addresses that gap by automating the hot path:

1. Collect evidence.
2. Fuse the evidence mathematically.
3. Decide whether the evidence is strong, conflicting, or uncertain.
4. Record the decision immutably.
5. Trigger a safe response when the evidence crosses a defined threshold.

This makes the system valuable as a defensive research platform, a SOC
automation prototype, and a reproducible environment for validating detection
logic before using it in a real operational setting.

## High-Level Architecture

At a high level, FIND EVIL works like this:

```text
Security telemetry
  -> NATS / ZeroMQ ingest
  -> parsing and normalization
  -> Dempster-Shafer evidence fusion
  -> Valkey pheromone field
  -> threshold evaluation
  -> forensic ledger
  -> CACAO response, dashboard, narrator, fractal pivots, STIX/OCSF exports
```

The most important architectural principle is that the LLM is not in the
containment decision path. Mathematical fusion decides whether the platform
should observe, mitigate, escalate, or record conflict. The LLM is used later to
explain the decision and help analysts understand the evidence.

## Technical Explanation

### Telemetry Ingestion

The ingest layer accepts JSON events from local message buses. Events contain
fields such as:

- `event_id`
- `event_time_ns`
- `source`
- `indicator_key`
- `confidence`
- `artifact_type`
- optional MITRE ATT&CK technique metadata

Supported sources include EDR-style events, Sysmon-like events, Zeek,
Suricata, YARA, Volatility, and other forensic signals.

### Evidence Fusion

Each sensor contributes a confidence value. Instead of using a simple average or
weighted vote, FIND EVIL uses Dempster-Shafer theory. This lets the platform
track not only belief that something is malicious, but also uncertainty and
conflict between sensors.

The fusion engine computes:

- `belief_evil`
- `plausibility_evil`
- `conflict_K`
- `uncertainty`
- sensor diversity

This matters because real security telemetry is often incomplete or
contradictory. A good SOC platform must distinguish between strong consensus,
normal uncertainty, and genuine sensor conflict.

### Pheromone Blackboard

The pheromone field stores live suspicion state by indicator key. For example,
an IP address, process, user account, or registry key can accumulate evidence
over time.

Each pheromone entry records:

- current suspicion score
- belief and plausibility
- conflict level
- number of contributing sensors
- decay-adjusted state

This gives the platform memory without requiring every component to share a
large relational model.

### Forensic Ledger

Every important decision becomes a ledger entry. The ledger is designed for
chain-of-custody style auditability.

Each entry includes:

- a time-ordered UUIDv7 finding ID
- a canonical payload
- evidence references
- reasoning trace
- previous hash
- BLAKE3 content hash
- Ed25519 signature

The result is a tamper-evident record. If any prior entry is changed, chain
verification fails.

### Safe-Mode CACAO Response

When evidence crosses the mitigation threshold, FIND EVIL generates safe-mode
CACAO-style playbooks. These simulate response actions such as process
containment, account reset, or network isolation without touching real
production EDR or network infrastructure.

This makes the platform suitable for controlled research and validation because
the response path can be tested without creating operational risk.

### AI-Assisted Explanation

The narrator service runs after the deterministic finding is already recorded.
It uses a prosecutor, defense, and judge pattern to produce analyst-facing
explanations. It also validates exhibit references so generated explanations
cannot cite evidence that does not exist in the finding.

This creates a separation of concerns:

- math decides
- ledger records
- AI explains

## What Was Achieved

The project achieved a working, integrated platform rather than an isolated
prototype. The major achievements are:

1. Built a full local SOC automation stack with multiple systemd services.
2. Implemented deterministic evidence fusion using Dempster-Shafer theory.
3. Built a live pheromone blackboard for correlated indicator state.
4. Implemented threshold-based response decisions.
5. Built a cryptographically verifiable forensic ledger.
6. Added CACAO 2.0-style response playbooks.
7. Added STIX 2.1 and OCSF Detection Finding emission.
8. Added an MCP blackboard for tool and state access.
9. Added safe local forensic tool shims for tools such as YARA, Zeek,
   TShark, Sleuth Kit, Volatility, and Plaso.
10. Added an out-of-band narrator debate system.
11. Added fractal pivot agents with enforced depth and width budgets.
12. Added observability through OpenTelemetry and Prometheus-style metrics.
13. Added a web dashboard for live platform visibility.
14. Validated the platform with synthetic attack scenarios.
15. Prepared the codebase for public release with runtime data, keys, private
    docs, and local artifacts excluded.

## Validation Evidence

The system was validated with runtime evidence, not just static inspection.

Key results:

| Area | Result |
|---|---|
| Hot path p50 | 0.567 ms |
| Hot path p99 | 1.071 ms |
| Ledger entries verified | 936 |
| Ledger integrity | `ok=true`, `tainted_seqs=[]` |
| Dempster-Shafer tests | 15/15 passed |
| CACAO structural tests | 10/10 passed |
| Pytest suite | 73 passed, 1 skipped |
| Sustained load injection | 1,524 events/second |
| Rekor public anchoring | batch 3, log index `1492269391` |

Validated scenario coverage included:

- PowerShell execution
- LSASS credential access
- process injection
- C2 beacon behavior
- conflicting evidence
- late telemetry
- malformed telemetry
- duplicate/replay suppression
- total conflict escalation
- Valkey recovery
- lateral movement correlation
- persistence
- defense evasion
- ransomware-like behavior
- DNS tunneling
- suspicious TLS fingerprinting

## Standards and Interoperability

FIND EVIL aligns with several security and evidence standards:

| Standard | Use |
|---|---|
| MITRE ATT&CK | technique mapping for findings |
| STIX 2.1 | bundle emission for threat intel interoperability |
| OCSF | Detection Finding output, class `2004` |
| CACAO 2.0 | playbook-style response structure |
| NIST SP 800-86 | chain-of-custody-oriented evidence handling |
| BLAKE3 | fast cryptographic hashing for ledger entries |
| Ed25519 | compact digital signatures |
| Rekor | public transparency log anchoring |
| OpenTelemetry | traces and metrics |
| MCP | blackboard and tool access interface |

## Current Limitations

The project is strong as a local defensive research platform, but some gaps
remain before claiming broad production readiness.

Known gaps:

- GPU inference offload is not yet active; inference currently falls back to
  CPU mode.
- `bulk_extractor` is not installed in the current local environment.
- Plaso is installed as a Python module/script, but the `log2timeline.py`
  wrapper is not globally exposed on PATH.
- Some service reloads require root access after shim updates.
- The public release excludes private implementation drafts and local evidence
  artifacts by design.

These are operational hardening items. They do not invalidate the core
detection, fusion, ledger, or validation results.

## Public Release Preparation

The repository was prepared for public release by:

- initializing git on `main`
- adding a public-safe `.gitignore`
- excluding ledger databases, private keys, `.env`, model files, runtime data,
  local analysis artifacts, source research drafts, and UI design source files
- adding three public-facing Markdown files:
  - `README.md`
  - `PLATFORM.md`
  - `VALIDATION_REPORT.md`
- committing the initial public release locally

This means other people can clone the product code, read the documentation, run
the tests, and reproduce the validation workflow without receiving private local
artifacts from the original workstation.

## Plain-Language Summary

In plain terms, this project is an automated cyber-defense lab system. It
watches security events, combines evidence from different tools, decides whether
something looks dangerous, records that decision in a way that can be audited,
and safely simulates what a response would look like.

The important achievement is that the system does not merely display alerts. It
connects evidence, makes deterministic decisions, explains those decisions, and
proves afterwards that the record was not tampered with.

For technical reviewers, the achievement is the integration of evidence fusion,
message transport, Valkey state, cryptographic ledgering, CACAO playbooks, MCP
tooling, STIX/OCSF output, LLM explanation, and scenario validation into one
working local platform.

## Conclusion

FIND EVIL demonstrates that a defensive SOC platform can combine deterministic
mathematical evidence fusion with modern agentic workflows while preserving a
clear safety boundary. The system detects and correlates synthetic attack
patterns, records decisions in a verifiable ledger, exposes standards-aligned
outputs, and keeps AI out of the containment decision path.

The result is a credible, reproducible, public-ready defensive security platform
that can be cloned, studied, extended, and validated by others.
