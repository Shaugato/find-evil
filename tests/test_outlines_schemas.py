"""Outlines schema validation — must reject unknown exhibit refs."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from findevil.inference.outlines_schemas import (
    DebateArgument,
    ExhibitCitation,
    PivotFinding,
    Verdict,
    validate_pivot_citations,
)


def test_exhibit_citation_shape():
    ExhibitCitation(exhibit_id="ex_abcd1234")
    ExhibitCitation(exhibit_id="ex_abcd1234", sha256="a" * 64)
    with pytest.raises(ValidationError):
        ExhibitCitation(exhibit_id="not-ok")
    with pytest.raises(ValidationError):
        ExhibitCitation(exhibit_id="ex_abcd1234", sha256="short")


def test_pivot_finding_requires_evidence():
    with pytest.raises(ValidationError):
        PivotFinding(
            artifact_uri="file:///t.bin",
            artifact_type="file",
            verdict="evil",
            confidence=0.5,
            declared_ignorance=0.1,
            mitre_attack_technique=[],
            evidence_refs=[],  # empty; must fail min_length=1
            reasoning="x",
            follow_ups=[],
        )


def test_pivot_finding_happy_path():
    pf = PivotFinding(
        artifact_uri="file:///t.bin",
        artifact_type="file",
        verdict="evil",
        confidence=0.8,
        declared_ignorance=0.1,
        mitre_attack_technique=["T1059.001"],
        evidence_refs=[{"exhibit_id": "ex_12345678"}],
        reasoning="because",
    )
    assert pf.verdict == "evil"


def test_verdict_bounds():
    with pytest.raises(ValidationError):
        Verdict(
            guilty=True,
            score=1.5,
            winning_argument="prosecutor",
            rationale="x",
        )


def test_debate_argument_role_enum():
    DebateArgument(role="prosecutor", text="x", exhibit_ids_cited=[])
    with pytest.raises(ValidationError):
        DebateArgument(role="jury", text="x", exhibit_ids_cited=[])


def test_pivot_citation_must_be_in_scope():
    pf = PivotFinding(
        artifact_uri="file:///t.bin",
        artifact_type="file",
        verdict="evil",
        confidence=0.8,
        declared_ignorance=0.1,
        mitre_attack_technique=["T1059.001"],
        evidence_refs=[{"exhibit_id": "ex_deadbeef"}],
        reasoning="because",
    )
    with pytest.raises(ValueError, match="fabricated exhibit_id"):
        validate_pivot_citations(pf, [{"exhibit_id": "ex_12345678"}])
