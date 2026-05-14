"""Ledger append helpers for pipeline-produced evidence.

These helpers keep service code from hand-building `LedgerEntry` payloads. They
turn consensus frames, malformed input, and late input into first-class signed
ledger records as required by the implementation guide.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterable
from typing import Any

import blake3

from findevil.config.settings import settings
from findevil.ingest.events import ParsedEvent

from .schema import (
    ArtifactRef,
    ArtifactType,
    ConsensusInput,
    ConsensusMethod,
    ReasoningMethod,
    ReasoningStep,
    Severity,
)
from .writer import LedgerWriter


ACTION_LEDGER_STATES = {"observe", "mitigate", "conflict_ledger", "escalate_human"}


def _model_hash(label: str) -> str:
    return blake3.blake3(label.encode()).hexdigest()


def _severity(confidence: float, *, action: str | None = None) -> Severity:
    if action == "mitigate" or confidence >= 0.8:
        return Severity.HIGH
    if confidence >= 0.5:
        return Severity.MEDIUM
    if confidence >= 0.2:
        return Severity.LOW
    return Severity.INFORMATIONAL


def artifact_for_pher_key(pher_key: str) -> ArtifactRef:
    """Map an internal pheromone key to a ledger ArtifactRef."""
    if pher_key.startswith("pher:ip:"):
        ip = pher_key.removeprefix("pher:ip:")
        typ = ArtifactType.IPV6 if ":" in ip else ArtifactType.IPV4
        return ArtifactRef(type=typ, uri=f"{typ.value}:{ip}")
    if pher_key.startswith("pher:domain:"):
        domain = pher_key.removeprefix("pher:domain:")
        return ArtifactRef(type=ArtifactType.DOMAIN, uri=f"domain-name:{domain}")
    if pher_key.startswith("pher:hash:"):
        sha = pher_key.removeprefix("pher:hash:")
        return ArtifactRef(type=ArtifactType.FILE, uri=f"sha256:{sha}", sha256=sha)
    if pher_key.startswith("pher:proc:"):
        proc = pher_key.removeprefix("pher:proc:")
        return ArtifactRef(type=ArtifactType.PROCESS, uri=f"process:{proc}")
    if pher_key.startswith("pher:user://"):
        user = pher_key.removeprefix("pher:user://")
        return ArtifactRef(type=ArtifactType.USER, uri=f"user-account:{user}")
    if pher_key.startswith("pher:reg://"):
        reg_key = pher_key.removeprefix("pher:reg://")
        return ArtifactRef(type=ArtifactType.REG_KEY, uri=f"windows-registry-key:{reg_key}")
    if pher_key.startswith("pher:task://"):
        task = pher_key.removeprefix("pher:task://")
        return ArtifactRef(
            type=ArtifactType.REG_KEY,
            uri=f"windows-registry-key:scheduled-task:{task}",
        )
    if pher_key.startswith("pher:url://"):
        url = pher_key.removeprefix("pher:url://")
        return ArtifactRef(type=ArtifactType.URL, uri=f"url:{url}")
    if pher_key.startswith("pher:file://"):
        file_uri = pher_key.removeprefix("pher:file://")
        return ArtifactRef(
            type=ArtifactType.FILE,
            uri=f"file:{file_uri}",
            blake3=blake3.blake3(file_uri.encode()).hexdigest(),
        )
    return ArtifactRef(type=ArtifactType.NETFLOW, uri=f"pheromone:{pher_key}")


def _techniques_from_events(events: Iterable[ParsedEvent] | None) -> list[str]:
    if not events:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for ev in events:
        for t in ev.attack_techniques:
            if t.startswith("T") and t not in seen:
                seen.add(t)
                out.append(t)
    return out[:32]


def append_consensus_frame(
    frame: dict[str, Any],
    *,
    events: Iterable[ParsedEvent] | None = None,
) -> list[uuid.UUID]:
    """Append agent-report parents and the fused consensus finding.

    Returns the UUIDs written, parent report entries first and consensus last.
    """
    action = str(frame.get("action", ""))
    if action not in ACTION_LEDGER_STATES:
        return []

    pher_key = str(frame.get("pher_key", ""))
    evidence = [artifact_for_pher_key(pher_key)]
    belief = float(frame.get("belief_evil", 0.0))
    pl = float(frame.get("plausibility_evil", belief))
    uncertainty = float(frame.get("uncertainty", max(0.0, 1.0 - pl)))
    conflict = float(frame.get("conflict_K", 0.0))
    reports = list(frame.get("reports") or [])[:16]
    techniques = _techniques_from_events(events)
    written: list[uuid.UUID] = []

    writer = LedgerWriter(
        settings.ledger.sqlite_path,
        settings.ledger.ed25519_sk_path,
        settings.ledger.ed25519_pk_path,
    )
    try:
        for idx, report in enumerate(reports):
            agent_id = str(report.get("agent_id") or f"agent-report-{idx}")
            confidence = float(report.get("confidence", belief))
            entry = writer.append(
                agent_id=agent_id,
                agent_version="0.1.0",
                agent_model_hash=_model_hash(agent_id),
                host_id=settings.host_id,
                evidence_refs=evidence,
                primary_artifact_key=pher_key,
                confidence=confidence,
                severity=_severity(confidence),
                mitre=techniques,
                reasoning_trace=[
                    ReasoningStep(
                        step_index=0,
                        claim=(
                            f"{agent_id} contributed confidence={confidence:.3f} "
                            f"to Dempster-Shafer consensus for {pher_key}"
                        ),
                        method=ReasoningMethod.STATISTICAL_ANOM,
                        confidence=max(0.0, min(1.0, confidence)),
                        params={
                            "sensor": str(report.get("sensor", "")),
                            "declared_ignorance": str(
                                report.get("declared_ignorance", "")
                            ),
                        },
                    )
                ],
            )
            written.append(entry.finding_id)

        method = (
            ConsensusMethod.DEMPSTER_SHAFER_YAGER
            if action == "conflict_ledger" or conflict >= settings.swarm.k_yager_lo
            else ConsensusMethod.DEMPSTER_SHAFER
        )
        parent_ids = written or [uuid.uuid4()]
        entry = writer.append(
            agent_id="swarm.consensus",
            agent_version="0.1.0",
            agent_model_hash=_model_hash("swarm.consensus"),
            host_id=settings.host_id,
            evidence_refs=evidence,
            primary_artifact_key=pher_key,
            confidence=belief,
            severity=_severity(belief, action=action),
            mitre=techniques,
            reasoning_trace=[
                ReasoningStep(
                    step_index=0,
                    claim=(
                        f"Fused {len(reports)} agent reports for {pher_key}; "
                        f"action={action}, belief_evil={belief:.3f}, "
                        f"conflict_K={conflict:.3f}"
                    ),
                    method=ReasoningMethod.STATISTICAL_ANOM,
                    confidence=max(0.0, min(1.0, belief)),
                    params={
                        "action": action,
                        "sensor_diversity": str(frame.get("sensor_diversity", "")),
                    },
                )
            ],
            consensus=ConsensusInput(
                method=method,
                contributing_finding_ids=parent_ids,
                belief_evil=belief,
                plausibility_evil=pl,
                uncertainty=uncertainty,
                conflict_K=conflict,
            ),
            chain_of_custody=parent_ids,
        )
        written.append(entry.finding_id)
        return written
    finally:
        writer.close()


def append_raw_record(
    *,
    subject: str,
    reason: str,
    payload: bytes | dict[str, Any],
    source: str = "ingest",
) -> uuid.UUID:
    """Append malformed or late raw input as an informational ledger record."""
    data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    digest = blake3.blake3(data).hexdigest()
    evidence = [
        ArtifactRef(
            type=ArtifactType.NETFLOW,
            uri=f"nats://{subject}/{digest}",
            blake3=digest,
            size_bytes=len(data),
            extra={"reason": reason},
        )
    ]
    writer = LedgerWriter(
        settings.ledger.sqlite_path,
        settings.ledger.ed25519_sk_path,
        settings.ledger.ed25519_pk_path,
    )
    try:
        entry = writer.append(
            agent_id=f"ingest.{source}",
            agent_version="0.1.0",
            agent_model_hash=_model_hash(f"ingest.{source}"),
            host_id=settings.host_id,
            evidence_refs=evidence,
            primary_artifact_key=f"{subject}:{digest}",
            confidence=0.0,
            severity=Severity.INFORMATIONAL,
            reasoning_trace=[
                ReasoningStep(
                    step_index=0,
                    claim=f"Raw input routed to {subject}: {reason}",
                    method=ReasoningMethod.HUMAN_ASSERTION,
                    confidence=0.0,
                    params={"subject": subject, "reason": reason},
                )
            ],
        )
        return entry.finding_id
    finally:
        writer.close()
