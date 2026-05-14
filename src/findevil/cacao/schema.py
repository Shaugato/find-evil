"""CACAO 2.0 playbook Pydantic schema + Ed25519 sign/verify.

We follow OASIS CS02 (CACAO Security Playbooks v2.0) using the subset required for
this lab: `playbook` object with `workflow` of `action` steps, references to
actuators that map to our MCP tools (see blueprint Appendix C), and a detached
Ed25519 signature (RFC 8032) over the canonical JSON bytes.

Field parity is intentional — identifiers (`playbook--<uuid>`, `action--<uuid>`)
match CACAO 2.0 vocab so our outputs will round-trip into ArangoDB, STIX
workbench, or any CACAO-native consumer.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal, Optional

import nacl.exceptions
import nacl.signing
from pydantic import BaseModel, ConfigDict, Field, computed_field


def _utc_now() -> str:
    # CACAO uses RFC3339; Pydantic's own serialization is close but we pin the format.
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _new_id(kind: str) -> str:
    return f"{kind}--{uuid.uuid4()}"


class CacaoStep(BaseModel):
    """One action step within the workflow."""

    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=lambda: _new_id("action"))
    name: str
    type: Literal["action", "if-condition", "while-condition", "end"] = "action"
    # actuator = MCP tool id (e.g. "edr.network_isolate")
    actuator: str
    commands: list[dict[str, Any]] = Field(default_factory=list)
    on_completion: Optional[str] = None
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    agent: Optional[str] = None
    timeout_s: float = 30.0


class CacaoStepType(str, Enum):
    START = "start"
    END = "end"
    ACTION = "action"
    PLAYBOOK_ACTION = "playbook-action"
    PARALLEL = "parallel"
    IF_CONDITION = "if-condition"
    WHILE_CONDITION = "while-condition"
    SWITCH_CONDITION = "switch-condition"


class CommandData(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: str = "manual"
    command: str
    target: dict[str, Any] = Field(default_factory=dict)


class Step(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(default_factory=lambda: _new_id("action"))
    name: str
    type: CacaoStepType
    commands: list[CommandData] = Field(default_factory=list)
    on_completion: Optional[str] = None
    next_steps: list[str] = Field(default_factory=list)
    cases: dict[str, str] = Field(default_factory=dict)


class CacaoSignature(BaseModel):
    type: Literal["jws"] = "jws"
    value: str


class Playbook(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["playbook"] = "playbook"
    spec_version: Literal["cacao-2.0"] = "cacao-2.0"
    id: str = Field(default_factory=lambda: _new_id("playbook"))
    name: str
    created_by: str = "findevil"
    created: str = Field(default_factory=_utc_now)
    modified: str = Field(default_factory=_utc_now)
    workflow_start: str
    workflow: dict[str, Step]
    signatures: list[CacaoSignature] = Field(default_factory=list)

    def canonical_bytes(self, *, include_signatures: bool = False) -> bytes:
        d = self.model_dump(mode="json")
        if not include_signatures:
            d.pop("signatures", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


class CacaoPlaybook(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["playbook"] = "playbook"
    spec_version: Literal["2.0"] = "2.0"
    id: str = Field(default_factory=lambda: _new_id("playbook"))
    name: str
    description: str = ""
    playbook_types: list[str] = Field(default_factory=lambda: ["notification"])
    created_by: str = "findevil"
    created: str = Field(default_factory=_utc_now)
    modified: str = Field(default_factory=_utc_now)
    valid_from: str = Field(default_factory=_utc_now)
    valid_until: Optional[str] = None
    priority: int = 50
    severity: int = 50
    impact: int = 50
    labels: list[str] = Field(default_factory=list)
    external_references: list[dict[str, Any]] = Field(default_factory=list)
    workflow_start: str  # step id
    workflow: dict[str, CacaoStep]

    # detached signature fields (produced by sign_playbook)
    signature: Optional[str] = None  # base64(Ed25519 sig)
    signer_public_key: Optional[str] = None  # base64(pk)

    @computed_field  # type: ignore[misc]
    @property
    def workflow_ids(self) -> list[str]:
        return list(self.workflow.keys())

    # ----- canonicalization ------------------------------------------------
    def canonical_bytes(self, *, include_signature: bool = False) -> bytes:
        """Bytes that the signature covers — JSON with sorted keys, no whitespace."""
        d = self.model_dump(mode="json")
        if not include_signature:
            d.pop("signature", None)
            d.pop("signer_public_key", None)
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


def sign_playbook(pb: CacaoPlaybook, sk: nacl.signing.SigningKey) -> CacaoPlaybook:
    """Return a COPY of pb with `signature` + `signer_public_key` set."""
    import base64

    body = pb.model_copy(update={"signature": None, "signer_public_key": None})
    msg = body.canonical_bytes(include_signature=False)
    sig = sk.sign(msg).signature
    pk = sk.verify_key.encode()
    return pb.model_copy(
        update={
            "signature": base64.b64encode(sig).decode(),
            "signer_public_key": base64.b64encode(pk).decode(),
        }
    )


def verify_playbook(pb: CacaoPlaybook, *, expected_pk: Optional[bytes] = None) -> bool:
    """Verify the Ed25519 signature. If expected_pk is provided it must match."""
    import base64

    if pb.signature is None or pb.signer_public_key is None:
        return False
    sig = base64.b64decode(pb.signature)
    pk = base64.b64decode(pb.signer_public_key)
    if expected_pk is not None and pk != expected_pk:
        return False
    try:
        vk = nacl.signing.VerifyKey(pk)
        vk.verify(pb.canonical_bytes(include_signature=False), sig)
        return True
    except nacl.exceptions.BadSignatureError:
        return False
    except Exception:
        return False
