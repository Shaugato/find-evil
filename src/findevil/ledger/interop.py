"""Ledger -> STIX 2.1 / OCSF 1.3 / CACAO 2.0 export adapters.

Blueprint Part 6.1 interop anchors:
  - STIX 2.1 Indicator + Observed-Data + Sighting
  - OCSF Detection Finding (class_uid=2004, category_uid=2)
  - NIST SP 800-86 chain-of-custody (reasoning_trace + evidence_refs)
"""

from __future__ import annotations

from typing import Any

from .schema import ArtifactType, LedgerEntry, Severity

_OCSF_SEVERITY = {
    Severity.INFORMATIONAL: 1,
    Severity.LOW: 2,
    Severity.MEDIUM: 3,
    Severity.HIGH: 4,
    Severity.CRITICAL: 5,
}

_STIX_OBSERVABLE_TYPE = {
    ArtifactType.FILE: "file",
    ArtifactType.PROCESS: "process",
    ArtifactType.IPV4: "ipv4-addr",
    ArtifactType.IPV6: "ipv6-addr",
    ArtifactType.DOMAIN: "domain-name",
    ArtifactType.URL: "url",
    ArtifactType.REG_KEY: "windows-registry-key",
    ArtifactType.NETFLOW: "network-traffic",
    ArtifactType.USER: "user-account",
}


def to_ocsf_detection_finding(entry: LedgerEntry) -> dict[str, Any]:
    """Return an OCSF 1.3 class_uid=2004 Detection Finding dict."""
    confidence_pct = int(entry.confidence * 100)
    return {
        "class_uid": 2004,
        "category_uid": 2,
        "activity_id": 1,  # Create
        "time": int(entry.timestamp.timestamp() * 1000),
        "severity_id": _OCSF_SEVERITY[entry.severity],
        "confidence": confidence_pct,
        "confidence_id": _ocsf_confidence_id(confidence_pct),
        "finding_info": {
            "uid": str(entry.finding_id),
            "title": entry.primary_artifact_key,
            "analytic": {
                "name": entry.agent_id,
                "version": entry.agent_version,
                "type_id": 3,  # Signature
            },
            "types": ["forensic"],
        },
        "metadata": {
            "version": "1.3.0",
            "product": {"name": "FIND EVIL", "version": "0.1.0"},
        },
        "resources": [
            {"uid": r.uri, "type": r.type.value, "hashes": _hashes(r)}
            for r in entry.evidence_refs
        ],
        "attacks": [{"technique": {"uid": t}} for t in entry.mitre_attack_technique],
        "raw_data": entry.model_dump_json(),
    }


def _ocsf_confidence_id(confidence_pct: int) -> int:
    """Map FIND EVIL confidence to OCSF confidence_id ordinal buckets."""
    if confidence_pct >= 80:
        return 3  # High
    if confidence_pct >= 50:
        return 2  # Medium
    if confidence_pct > 0:
        return 1  # Low
    return 0  # Unknown


def _hashes(ref: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if ref.sha256:
        out.append({"algorithm_id": 3, "value": ref.sha256})  # SHA-256
    if ref.blake3:
        out.append({"algorithm_id": 99, "value": ref.blake3})  # vendor BLAKE3
    return out


def to_stix_bundle(entry: LedgerEntry) -> dict[str, Any]:
    """Return a minimal STIX 2.1 bundle (Indicator + Observed-Data + Sighting)."""
    import uuid as _uuid

    indicator_id = f"indicator--{_uuid.uuid4()}"
    observed_id = f"observed-data--{_uuid.uuid4()}"
    sighting_id = f"sighting--{_uuid.uuid4()}"
    ts = entry.timestamp.isoformat().replace("+00:00", "Z")

    observables: dict[str, dict[str, Any]] = {}
    for i, ref in enumerate(entry.evidence_refs):
        stix_type = _STIX_OBSERVABLE_TYPE.get(ref.type, "artifact")
        obj: dict[str, Any] = {"type": stix_type}
        if ref.sha256:
            obj["hashes"] = {"SHA-256": ref.sha256}
        if ref.type == ArtifactType.IPV4:
            obj["value"] = ref.uri
        elif ref.type == ArtifactType.DOMAIN:
            obj["value"] = ref.uri
        elif ref.type == ArtifactType.URL:
            obj["value"] = ref.uri
        elif ref.type == ArtifactType.FILE:
            obj["name"] = ref.uri
        observables[str(i)] = obj

    pattern = " OR ".join(
        f"[{_STIX_OBSERVABLE_TYPE.get(r.type, 'artifact')}:value = '{r.uri}']"
        for r in entry.evidence_refs
    )
    return {
        "type": "bundle",
        "id": f"bundle--{_uuid.uuid4()}",
        "objects": [
            {
                "type": "indicator",
                "spec_version": "2.1",
                "id": indicator_id,
                "created": ts,
                "modified": ts,
                "pattern_type": "stix",
                "pattern": pattern,
                "valid_from": ts,
                "labels": [entry.severity.value],
                "confidence": int(entry.confidence * 100),
                "name": entry.primary_artifact_key,
            },
            {
                "type": "observed-data",
                "spec_version": "2.1",
                "id": observed_id,
                "created": ts,
                "modified": ts,
                "first_observed": ts,
                "last_observed": ts,
                "number_observed": 1,
                "objects": observables,
            },
            {
                "type": "sighting",
                "spec_version": "2.1",
                "id": sighting_id,
                "created": ts,
                "modified": ts,
                "sighting_of_ref": indicator_id,
                "observed_data_refs": [observed_id],
                "count": 1,
            },
        ],
    }
