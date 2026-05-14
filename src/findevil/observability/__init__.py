"""Observability plane — Prometheus metrics, OpenTelemetry tracing, structlog."""

from .metrics import (
    CONSENSUS_ACTIONS,
    CONSENSUS_CONFLICT_K,
    CONSENSUS_DURATION,
    DECISION_LATENCY,
    FRACTAL_SPAWNS,
    FRACTAL_TTL_EXCEEDED,
    INFERENCE_LATENCY,
    LEDGER_APPENDS,
    LEDGER_CHAIN_LENGTH,
    LEDGER_VERIFY_FAILURES,
    LONG_WINDOW_ZSCORE_ALERTS,
    MITIGATION_LATENCY,
    NARRATOR_DEBATES,
    PHEROMONE_GAUGE,
    REGISTRY,
    SHADOW_DROPS,
    start_metrics_server,
)
from .tracing import init_tracing, span

__all__ = [
    "CONSENSUS_ACTIONS",
    "CONSENSUS_CONFLICT_K",
    "CONSENSUS_DURATION",
    "DECISION_LATENCY",
    "FRACTAL_SPAWNS",
    "FRACTAL_TTL_EXCEEDED",
    "INFERENCE_LATENCY",
    "LEDGER_APPENDS",
    "LEDGER_CHAIN_LENGTH",
    "LEDGER_VERIFY_FAILURES",
    "LONG_WINDOW_ZSCORE_ALERTS",
    "MITIGATION_LATENCY",
    "NARRATOR_DEBATES",
    "PHEROMONE_GAUGE",
    "REGISTRY",
    "SHADOW_DROPS",
    "init_tracing",
    "span",
    "start_metrics_server",
]
