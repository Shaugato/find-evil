"""Pydantic v2 forensic ledger schema.

Per blueprint Part 6: UUIDv7, BLAKE3 chain, Ed25519, canonical-JSON, strict validators.
Every agent-produced finding passes through model_validate here before any side-effect.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid
from enum import Enum
from typing import Annotated, Optional

import blake3
import uuid_utils
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = "1.0.0"

# -- Annotated primitive constraints -----------------------------------------
Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Blake3Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Ed25519Fpr = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Base64Str = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9+/=]+$")]
SemVer = Annotated[
    str,
    StringConstraints(pattern=r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$"),
]
MitreTech = Annotated[str, StringConstraints(pattern=r"^T\d{4}(?:\.\d{3})?$")]
CVSSScore = Annotated[float, Field(ge=0.0, le=10.0)]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class Severity(str, Enum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ArtifactType(str, Enum):
    FILE = "file"
    PROCESS = "process"
    IPV4 = "ipv4-addr"
    IPV6 = "ipv6-addr"
    DOMAIN = "domain-name"
    URL = "url"
    REG_KEY = "windows-registry-key"
    MEMORY_REG = "memory-region"
    NETFLOW = "network-traffic"
    YARA_MATCH = "yara-match"
    USER = "user-account"


class ReasoningMethod(str, Enum):
    YARA_MATCH = "yara_match"
    BEHAVIORAL_ML = "behavioral_ml"
    STATISTICAL_ANOM = "statistical_anomaly"
    THREAT_INTEL_HIT = "threat_intel_correlation"
    MEMORY_HEURISTIC = "memory_heuristic"
    LLM_INFERENCE = "slm_inference"
    HUMAN_ASSERTION = "human_assertion"


class ConsensusMethod(str, Enum):
    DEMPSTER_SHAFER = "dempster_shafer"
    DEMPSTER_SHAFER_YAGER = "dempster_shafer_yager"
    BAYESIAN_LOG_ODDS = "bayesian_log_odds"
    WEIGHTED_MAJORITY = "weighted_majority"


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: ArtifactType
    uri: Annotated[str, StringConstraints(min_length=1, max_length=4096)]
    sha256: Optional[Sha256Hex] = None
    blake3: Optional[Blake3Hex] = None
    size_bytes: Optional[int] = Field(default=None, ge=0)
    extra: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _file_needs_hash(self) -> "ArtifactRef":
        if self.type == ArtifactType.FILE and not (self.sha256 or self.blake3):
            raise ValueError("file ArtifactRef requires sha256 or blake3")
        return self


class ReasoningStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    step_index: int = Field(ge=0)
    claim: Annotated[str, StringConstraints(min_length=1, max_length=2048)]
    evidence_ref: Optional[int] = Field(default=None, ge=0)
    method: ReasoningMethod
    confidence: Confidence
    params: dict[str, str] = Field(default_factory=dict)


class ConsensusInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    method: ConsensusMethod
    contributing_finding_ids: list[uuid.UUID] = Field(min_length=1, max_length=16)
    belief_evil: Confidence
    plausibility_evil: Confidence
    uncertainty: Confidence
    conflict_K: Confidence
    shapley_attribution: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _bel_le_pl(self) -> "ConsensusInput":
        if self.belief_evil > self.plausibility_evil + 1e-9:
            raise ValueError("belief_evil must be <= plausibility_evil")
        return self


class LedgerEntry(BaseModel):
    """Single immutable forensic finding.

    Signed with Ed25519 over canonical JSON with the placeholder signature removed;
    entry_hash is BLAKE3 over canonical JSON including the signature.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        json_schema_extra={"x-schema-version": SCHEMA_VERSION},
    )

    finding_id: uuid.UUID
    schema_version: SemVer = SCHEMA_VERSION
    timestamp: dt.datetime
    timestamp_ns: int = Field(ge=0, lt=10**9)

    agent_id: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    agent_version: SemVer
    agent_model_hash: Blake3Hex
    host_id: Annotated[str, StringConstraints(min_length=1, max_length=128)]

    evidence_refs: list[ArtifactRef] = Field(min_length=1, max_length=64)
    primary_artifact_key: Annotated[str, StringConstraints(min_length=1, max_length=512)]

    confidence: Confidence
    severity: Severity
    cvss_v3_1_base: Optional[CVSSScore] = None
    mitre_attack_technique: list[MitreTech] = Field(default_factory=list, max_length=32)

    reasoning_trace: list[ReasoningStep] = Field(min_length=1, max_length=64)
    consensus: Optional[ConsensusInput] = None
    chain_of_custody: list[uuid.UUID] = Field(default_factory=list, max_length=128)

    prev_hash: Optional[Blake3Hex] = None
    merkle_root: Optional[Blake3Hex] = None
    nonce: Base64Str
    signing_pubkey_fpr: Ed25519Fpr
    signature: Base64Str

    @field_validator("finding_id")
    @classmethod
    def _must_be_v7(cls, v: uuid.UUID) -> uuid.UUID:
        if ((v.int >> 76) & 0xF) != 7:
            raise ValueError("finding_id must be UUIDv7 per RFC 9562")
        return v

    @field_validator("timestamp")
    @classmethod
    def _must_be_utc(cls, v: dt.datetime) -> dt.datetime:
        if v.tzinfo is None or v.utcoffset() != dt.timedelta(0):
            raise ValueError("timestamp must be tz-aware UTC")
        return v

    @model_validator(mode="after")
    def _consensus_requires_parents(self) -> "LedgerEntry":
        if self.consensus is not None and not self.chain_of_custody:
            raise ValueError("consensus entries must reference parents via chain_of_custody")
        return self

    def canonical_bytes(self, *, include_signature: bool = False) -> bytes:
        """Canonical JSON: sorted keys, compact separators, UTF-8.

        Excluding the signature produces the pre-image Ed25519 signs over.
        Including it produces the pre-image BLAKE3 hashes for the chain.
        """
        d = self.model_dump(mode="json", exclude_none=False, exclude={"content_hash_blake3"})
        if not include_signature:
            d.pop("signature", None)
        return json.dumps(
            d, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def content_hash_blake3(self) -> str:
        return blake3.blake3(self.canonical_bytes(include_signature=True)).hexdigest()


def new_uuid_v7() -> uuid.UUID:
    """Mint a UUIDv7 compatible with uuid.UUID (uuid_utils returns its own type)."""
    return uuid.UUID(bytes=uuid_utils.uuid7().bytes)
