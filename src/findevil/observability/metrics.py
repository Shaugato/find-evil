"""Prometheus metrics for FIND EVIL (blueprint Part 14).

Exposes a dedicated CollectorRegistry so multiprocess workers can share or bind
per-service, and a small helper to start an HTTP exporter on the configured port.

Naming convention: `findevil_<subsystem>_<metric>_<unit>` per Prometheus guidelines.
"""

from __future__ import annotations

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Summary,
    start_http_server,
)

from findevil.config.settings import settings

REGISTRY = CollectorRegistry()

# ----- hot-path latencies (SLO: p50 6ms, p99 20ms) --------------------------
DECISION_LATENCY = Histogram(
    "findevil_decision_latency_seconds",
    "End-to-end decision latency (sensor -> consensus action).",
    buckets=(
        0.001, 0.002, 0.003, 0.005, 0.008, 0.013, 0.020, 0.035, 0.055,
        0.090, 0.150, 0.250, 0.500, 1.0, 2.0, 5.0,
    ),
    registry=REGISTRY,
)
MITIGATION_LATENCY = Histogram(
    "findevil_mitigation_latency_seconds",
    "Consensus action -> CACAO executor dispatch.",
    buckets=(0.001, 0.003, 0.008, 0.020, 0.050, 0.100, 0.500, 2.0),
    registry=REGISTRY,
)

# ----- consensus ------------------------------------------------------------
CONSENSUS_ACTIONS = Counter(
    "findevil_consensus_actions_total",
    "Count of consensus outcomes by action class.",
    labelnames=("action",),  # mitigate, escalate_human, conflict_ledger, observe
    registry=REGISTRY,
)
CONSENSUS_DURATION = Histogram(
    "findevil_consensus_duration_seconds",
    "Dempster-Shafer fuse() wall-clock time.",
    buckets=(0.00005, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.010),
    registry=REGISTRY,
)
CONSENSUS_CONFLICT_K = Histogram(
    "findevil_consensus_conflict_k",
    "Distribution of D-S conflict mass K (0..1).",
    buckets=(0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.7, 0.9, 1.0),
    registry=REGISTRY,
)

# ----- pheromone field ------------------------------------------------------
PHEROMONE_GAUGE = Gauge(
    "findevil_pheromone_tau",
    "Current tau value per key (sampled on deposit/decay).",
    labelnames=("kind",),  # ip, hash, domain, process
    registry=REGISTRY,
)
LONG_WINDOW_ZSCORE_ALERTS = Counter(
    "findevil_pheromone_long_window_zscore_alerts_total",
    "Cumulative-delta anomaly alerts from the decay worker.",
    labelnames=("key",),
    registry=REGISTRY,
)

# ----- fractal / inference --------------------------------------------------
FRACTAL_SPAWNS = Counter(
    "findevil_fractal_spawns_total",
    "Ephemeral H3 pivot agents spawned.",
    labelnames=("seed_technique",),
    registry=REGISTRY,
)
FRACTAL_TTL_EXCEEDED = Counter(
    "findevil_fractal_ttl_exceeded_total",
    "H3 pivots terminated by TTL/budget without reporting.",
    registry=REGISTRY,
)
INFERENCE_LATENCY = Histogram(
    "findevil_inference_latency_seconds",
    "SLM inference wall-clock (pivot/debate/judge).",
    labelnames=("role",),  # pivot, prosecutor, defense, judge
    buckets=(0.05, 0.1, 0.2, 0.35, 0.5, 0.65, 0.9, 1.3, 2.0, 3.5, 6.0, 12.0),
    registry=REGISTRY,
)
NARRATOR_DEBATES = Counter(
    "findevil_narrator_debates_total",
    "Completed H2 debates.",
    labelnames=("verdict",),  # evil, benign, insufficient
    registry=REGISTRY,
)

# ----- ledger ---------------------------------------------------------------
LEDGER_APPENDS = Counter(
    "findevil_ledger_appends_total",
    "LedgerWriter.append() calls by outcome.",
    labelnames=("outcome",),  # ok, conflict, error
    registry=REGISTRY,
)
LEDGER_VERIFY_FAILURES = Counter(
    "findevil_ledger_verify_failures_total",
    "Chain-verification failures detected at runtime.",
    registry=REGISTRY,
)
LEDGER_CHAIN_LENGTH = Gauge(
    "findevil_ledger_chain_length",
    "Current ledger tip sequence number.",
    registry=REGISTRY,
)

# ----- mcp shadow channel ---------------------------------------------------
SHADOW_DROPS = Counter(
    "findevil_mcp_shadow_drops_total",
    "Subscriber-side drops in the MCP high-rate shadow channel.",
    labelnames=("reason",),  # slow_consumer, queue_full, backpressure
    registry=REGISTRY,
)


# ----- blueprint TABLE 11 inventory (doc-named; Part 14.2) ------------------
# Some overlap semantically with the metrics above; the doc-mandated names are
# emitted as well so the published alarm thresholds apply verbatim.
DS_FUSION_SECONDS = Histogram(
    "findevil_ds_fusion_seconds",
    "Dempster-Shafer fusion wall-clock per window (TABLE 11; p99 alarm 500us).",
    labelnames=("n_reports",),
    buckets=(0.00002, 0.00005, 0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005),
    registry=REGISTRY,
)
DS_CONFLICT_K = Summary(
    "findevil_ds_conflict_K",
    "D-S conflict mass K per fusion (TABLE 11; alarm >0.7 sustained).",
    labelnames=("indicator_kind",),
    registry=REGISTRY,
)
MCP_WRITE_TPS = Counter(
    "findevil_mcp_write_tps",
    "MCP blackboard writes by resource prefix (TABLE 11; alarm >8k/s).",
    labelnames=("resource_prefix",),
    registry=REGISTRY,
)
LEDGER_APPEND_SECONDS = Histogram(
    "findevil_ledger_append_seconds",
    "LedgerWriter.append() wall-clock (TABLE 11; p99 alarm 5ms).",
    buckets=(0.0002, 0.0005, 0.0008, 0.0013, 0.002, 0.005, 0.010, 0.025, 0.060),
    registry=REGISTRY,
)
REKOR_ANCHOR_AGE = Gauge(
    "findevil_rekor_anchor_age_seconds",
    "Seconds since the last successful Merkle/Rekor anchor (TABLE 11; alarm >3600).",
    registry=REGISTRY,
)
VLLM_TTFT_SECONDS = Histogram(
    "findevil_vllm_ttft_seconds",
    "Inference time-to-first-token approximation per request (TABLE 11; "
    "non-streaming facade, so observed value is full-response latency).",
    labelnames=("model", "cached"),
    buckets=(0.025, 0.05, 0.1, 0.2, 0.35, 0.5, 0.65, 1.0, 2.0, 5.0, 12.0),
    registry=REGISTRY,
)
BACKPRESSURE_DROPS = Counter(
    "backpressure_drops_total",
    "Events dropped under backpressure by source (TABLE 11; alarm rate >0.1/s).",
    labelnames=("source",),
    registry=REGISTRY,
)
FRACTAL_LIVE_AGENTS = Gauge(
    "findevil_fractal_live_agents",
    "Currently live ephemeral pivot agents (TABLE 11; alarm >14 of 16 budget).",
    registry=REGISTRY,
)
CONSENSUS_FIRE = Counter(
    "findevil_consensus_fire_total",
    "Consensus firings by action (TABLE 11 doc-named twin of consensus_actions_total).",
    labelnames=("action",),
    registry=REGISTRY,
)
SCHEMA_VALIDATION_FAIL = Counter(
    "findevil_schema_validation_fail_total",
    "Schema-validation rejections by failure class (TABLE 11; alarm rate >0).",
    labelnames=("failure_class",),
    registry=REGISTRY,
)


def start_metrics_server(port: int | None = None) -> None:
    """Bind :<port> and serve /metrics. Safe to call once per process."""
    p = port or settings.observability.prometheus_port
    start_http_server(p, registry=REGISTRY)
