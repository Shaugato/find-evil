"""TABLE 11 metric inventory (implementation doc Part 14.2).

Every doc-named metric must exist in the shared registry under its exact
published name so the blueprint alarm thresholds apply verbatim.
"""

from __future__ import annotations

from prometheus_client import generate_latest

from findevil.observability import metrics as m

DOC_NAMED = [
    "findevil_ds_fusion_seconds",
    "findevil_ds_conflict_K",
    "findevil_mcp_write_tps",
    "findevil_ledger_append_seconds",
    "findevil_rekor_anchor_age_seconds",
    "findevil_vllm_ttft_seconds",
    "backpressure_drops_total",
    "findevil_fractal_live_agents",
    "findevil_consensus_fire_total",
    "findevil_schema_validation_fail_total",
    "findevil_pheromone_tau",
]


def test_doc_named_metrics_registered() -> None:
    registered = {
        name
        for collector in m.REGISTRY._collector_to_names  # noqa: SLF001
        for name in m.REGISTRY._collector_to_names[collector]  # noqa: SLF001
    }
    missing = [
        name
        for name in DOC_NAMED
        # Counters register as <name>_total internally; accept either form.
        if name not in registered and name.removesuffix("_total") not in registered
    ]
    assert not missing, f"doc-named metrics missing from registry: {missing}"


def test_metrics_observable_and_exposable() -> None:
    m.DS_FUSION_SECONDS.labels(n_reports="3").observe(0.0001)
    m.DS_CONFLICT_K.labels(indicator_kind="ip").observe(0.42)
    m.MCP_WRITE_TPS.labels(resource_prefix="shadow:consensus").inc()
    m.LEDGER_APPEND_SECONDS.observe(0.0004)
    m.REKOR_ANCHOR_AGE.set(12.5)
    m.VLLM_TTFT_SECONDS.labels(model="test", cached="false").observe(0.2)
    m.BACKPRESSURE_DROPS.labels(source="find.zeek").inc()
    m.FRACTAL_LIVE_AGENTS.set(2)
    m.CONSENSUS_FIRE.labels(action="mitigate").inc()
    m.SCHEMA_VALIDATION_FAIL.labels(failure_class="decode_failed").inc()

    payload = generate_latest(m.REGISTRY).decode()
    for name in DOC_NAMED:
        assert name in payload, f"{name} absent from /metrics exposition"


def test_ledger_append_observed_via_writer(ed25519_keys, tmp_path) -> None:
    """LedgerWriter.append must feed findevil_ledger_append_seconds."""
    import os
    from pathlib import Path

    import blake3

    from findevil.ledger.schema import (
        ArtifactRef,
        ArtifactType,
        ReasoningMethod,
        ReasoningStep,
        Severity,
    )
    from findevil.ledger.writer import LedgerWriter

    sk_path = Path(os.environ["FINDEVIL_LEDGER__ED25519_SK_PATH"])
    pk_path = Path(os.environ["FINDEVIL_LEDGER__ED25519_PK_PATH"])

    before = m.LEDGER_APPEND_SECONDS._sum.get()  # noqa: SLF001
    writer = LedgerWriter(tmp_path / "metrics-ledger.sqlite", sk_path, pk_path)
    try:
        writer.append(
            agent_id="test.metrics",
            agent_version="0.1.0",
            agent_model_hash=blake3.blake3(b"metrics-test").hexdigest(),
            host_id="test-host",
            evidence_refs=[
                ArtifactRef(
                    type=ArtifactType.PROCESS,
                    uri="proc://test-host/4242",
                    extra={"name": "metrics-test.exe"},
                )
            ],
            primary_artifact_key="proc:test-host:4242",
            confidence=0.7,
            severity=Severity.LOW,
            reasoning_trace=[
                ReasoningStep(
                    step_index=0,
                    claim="metrics smoke entry",
                    method=ReasoningMethod.BEHAVIORAL_ML,
                    confidence=0.7,
                )
            ],
        )
    finally:
        writer.close()
    assert m.LEDGER_APPEND_SECONDS._sum.get() > before  # noqa: SLF001
