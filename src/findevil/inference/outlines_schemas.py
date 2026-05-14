"""Outlines FSM-constrained output schemas — MANDATORY for every SLM output.

Blueprint Part 4.4: the only way to enforce 'reject verdicts referencing unknown
exhibit IDs before Judge sees them'. Every SLM that writes to the blackboard goes
through one of these schemas.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ExhibitCitation(BaseModel):
    """Citation to an exhibit that must exist in the scoped prompt's exhibit list."""

    model_config = ConfigDict(extra="forbid")
    exhibit_id: str = Field(pattern=r"^ex_[a-z0-9]{8}$")
    sha256: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class PivotFinding(BaseModel):
    """Output of a fractal ephemeral pivot agent (H3)."""

    model_config = ConfigDict(extra="forbid")
    artifact_uri: str = Field(min_length=1, max_length=4096)
    artifact_type: Literal[
        "file",
        "process",
        "ipv4-addr",
        "domain-name",
        "url",
        "windows-registry-key",
        "memory-region",
        "yara-match",
        "network-traffic",
        "user-account",
        "ipv6-addr",
    ]
    verdict: Literal["evil", "benign", "insufficient"]
    confidence: float = Field(ge=0.0, le=1.0)
    declared_ignorance: float = Field(ge=0.0, le=1.0)
    mitre_attack_technique: list[str] = Field(default_factory=list, max_length=8)
    evidence_refs: list[ExhibitCitation] = Field(min_length=1, max_length=8)
    reasoning: str = Field(min_length=1, max_length=800)
    follow_ups: list[dict] = Field(default_factory=list, max_length=4)


class DebateArgument(BaseModel):
    """Single argument from prosecutor or defense (narrator)."""

    model_config = ConfigDict(extra="forbid")
    role: Literal["prosecutor", "defense"]
    text: str = Field(min_length=1, max_length=1500)
    exhibit_ids_cited: list[str] = Field(min_length=0, max_length=8)
    claimed_technique: list[str] = Field(default_factory=list, max_length=8)


class Verdict(BaseModel):
    """Judge's final verdict (narrator)."""

    model_config = ConfigDict(extra="forbid")
    guilty: bool
    score: float = Field(ge=0.0, le=1.0)
    winning_argument: Literal["prosecutor", "defense", "insufficient"]
    rationale: str = Field(min_length=1, max_length=600)
    exhibit_ids_cited: list[str] = Field(default_factory=list, max_length=16)


def allowed_exhibit_ids(exhibits: list[dict]) -> set[str]:
    """Return the scoped exhibit ids available to an SLM call."""
    return {
        str(e.get("exhibit_id"))
        for e in exhibits
        if isinstance(e, dict) and e.get("exhibit_id")
    }


def validate_pivot_citations(pivot: PivotFinding, exhibits: list[dict]) -> None:
    """Reject fabricated pivot citations before downstream consumers see them."""
    allowed = allowed_exhibit_ids(exhibits)
    for ref in pivot.evidence_refs:
        if ref.exhibit_id not in allowed:
            raise ValueError(f"fabricated exhibit_id: {ref.exhibit_id}")


def validate_argument_citations(argument: DebateArgument, exhibits: list[dict]) -> None:
    allowed = allowed_exhibit_ids(exhibits)
    for exhibit_id in argument.exhibit_ids_cited:
        if exhibit_id not in allowed:
            raise ValueError(f"fabricated exhibit_id: {exhibit_id}")


def validate_verdict_citations(verdict: Verdict, exhibits: list[dict]) -> None:
    allowed = allowed_exhibit_ids(exhibits)
    for exhibit_id in verdict.exhibit_ids_cited:
        if exhibit_id not in allowed:
            raise ValueError(f"fabricated exhibit_id: {exhibit_id}")
