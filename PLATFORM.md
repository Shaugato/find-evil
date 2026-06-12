# FIND EVIL Platform

FIND EVIL is a defensive autonomous SOC platform built around deterministic
evidence fusion, a blackboard-style shared state model, and a tamper-evident
forensic ledger. It is designed for local or on-prem operation where telemetry,
models, response shims, and audit artifacts stay under the operator's control.

## Design Goals

- Keep the detection and containment decision path deterministic.
- Fuse independent sensor confidence using Dempster-Shafer belief functions.
- Store every decision in a signed BLAKE3 hash chain.
- Keep LLM reasoning off the hot path.
- Use safe-mode CACAO playbooks for local response simulation.
- Provide standards-aligned outputs: STIX 2.1, OCSF Detection Finding, CACAO 2.0.
- Expose state through an MCP blackboard so tools and agents share the same view.

## Data Flow

```text
Telemetry
  -> NATS / ZeroMQ ingest
  -> parser and indicator normalization
  -> per-source Basic Probability Assignment
  -> Dempster-Shafer fusion
  -> Valkey pheromone field update
  -> threshold evaluation
  -> ledger append
  -> CACAO, narrator, fractal watcher, dashboard, and exports
```

## Hot Path

The hot path is the deterministic path from event arrival to consensus action.

1. Sensor telemetry arrives as JSON.
2. The ingest pipeline validates required fields such as `event_id`,
   `event_time_ns`, `source`, `indicator_key`, `confidence`, and
   `artifact_type`.
3. Each sensor contributes a Basic Probability Assignment.
4. Dempster-Shafer fusion computes:
   - `belief_evil`
   - `plausibility_evil`
   - `conflict_K`
   - `uncertainty`
5. The pheromone field stores the current belief state by indicator key.
6. Threshold evaluation selects observe, mitigate, conflict, or human escalation.
7. The forensic ledger records the decision.

The LLM is not consulted before mitigation decisions. It explains and enriches
after the ledger entry exists.

## Pheromone Field

Valkey stores per-indicator hashes under `pher:*`.

Required fields:

- `tau`
- `bel_evil`
- `pl_evil`
- `conflict_K`
- `sensor_diversity`

The important invariant is:

```text
belief_evil <= plausibility_evil
```

The field also drives dashboard visualization and fractal pivot spawning.

## Threshold Behavior

The default behavior is:

- High belief with enough sensor diversity triggers a CACAO mitigation playbook.
- Moderate conflict enters Yager conflict handling and writes a conflict entry.
- Total conflict escalates to a human and suppresses automated mitigation.
- Late, duplicate, and malformed telemetry are routed separately for audit.

## Forensic Ledger

The ledger is an append-only SQLite-backed chain. Each entry includes:

- UUIDv7 finding identifier
- canonical JSON payload
- BLAKE3 entry hash
- previous hash link
- Ed25519 signature
- reasoning trace
- evidence references
- chain-of-custody references
- STIX / OCSF / CACAO-aligned fields where applicable

`findevil verify` walks the chain and reports tainted sequence numbers if hash
or signature verification fails.

## CACAO Safe-Mode Response

CACAO execution is intentionally safe-mode in this public release. The executor
generates and records actions such as process containment, IAM reset, and
network isolation as local shims rather than touching production EDR or network
infrastructure.

This makes the system useful for validation, training, research, and local SOC
automation development without creating unsafe side effects.

## MCP Blackboard

The MCP service exposes live platform state and registered forensic tools.

Examples:

- ledger tip and recent entries
- pheromone state
- CACAO execution history
- YARA scan
- Volatility version and memory-analysis wrappers
- Sleuth Kit wrappers
- Zeek/TShark wrappers
- STIX and OCSF emitters

Tool shims call real local binaries when installed and return explicit
structured failures when the binary is missing.

## Narrator Debate

The narrator is an out-of-band explanation plane. It uses a
prosecutor/defense/judge pattern to generate analyst-facing reasoning after the
deterministic decision is complete.

Quality controls include:

- structured JSON output
- exhibit citation validation
- chain-of-custody references to the parent finding
- position-swap judging to reduce ordering bias

## Fractal Pivot Agents

The fractal watcher spawns bounded pivot tasks for high-interest artifacts.

Budgets:

- maximum depth: 3
- maximum concurrent width: 16

Pivot results are written back to the ledger with their own finding IDs and
custody references.

## CTI Plane (FOR578)

Threat intelligence is treated as one more decaying, low-diversity sensor. The
`findevil.cti` package parses STIX 2.1 indicator patterns (from an offline
bundle file or a live TAXII 2.1 collection) and deposits each IOC as a bounded
**pheromone prior** under the same `pher:<kind>:<value>` keys the hot path fuses
over. Priors are deliberately modest (`sensor=cti.taxii`, belief capped at 0.45,
`tau_max=0.35`) so intel biases triage ordering without ever crossing a
mitigation threshold on its own.

A **Diamond Model** relationship graph (adversary / capability / infrastructure
/ victim) is built from ledger findings and published to the blackboard at
`bb://cti/diamond`. MCP tools: `taxii.ingest`, `taxii.push`, `diamond.graph`.

## Forensic Carving

`bulk_extractor` is exposed as `bulk_extractor.scan` — stream-carving of
IPs/domains/URLs/emails from raw images. Because it does not parse a filesystem
or kernel, it tolerates damaged images that defeat structured tools, and its
output is summarised to a bounded feature set before reaching the LLM plane.

## Observability — TABLE 11 metric inventory

Every blueprint-named Prometheus metric is emitted under its exact published
name so the documented alarm thresholds apply verbatim:
`findevil_ds_fusion_seconds`, `findevil_ds_conflict_K`,
`findevil_ledger_append_seconds`, `findevil_rekor_anchor_age_seconds`,
`findevil_vllm_ttft_seconds`, `backpressure_drops_total`,
`findevil_fractal_live_agents`, `findevil_consensus_fire_total`,
`findevil_schema_validation_fail_total`, `findevil_mcp_write_tps`, plus the
pheromone/consensus/ledger gauges. Served per-service on ports 8890–8894.

## Local Inference Hardware Note

The reference workstation's GPU (Quadro P620, Pascal sm_61) was investigated for
offload: a from-source CUDA 12.6 build of llama-cpp-python runs, but is 2–3×
slower than CPU for short completions (no tensor cores; modern ggml kernels are
not Pascal-optimised). The platform runs CPU inference. Because the LLM is off
the hot path, this does not affect the detection/containment SLA.

## Standards Interop

FIND EVIL supports:

- STIX 2.1 bundle emission
- OCSF Detection Finding, `class_uid=2004`
- CACAO 2.0 playbook structure (Ed25519 + compact JWS via joserfc)
- MITRE ATT&CK technique mapping
- TAXII 2.1 CTI ingest/push and a Diamond Model graph
- Rekor public transparency log anchoring
- OpenTelemetry metrics and traces

## Public Repository Boundary

This public repository contains implementation, templates, tests, and
reproducible validation logic. It does not contain local keys, model weights,
forensic evidence, ledger databases, private screenshots, or source research
drafts.
