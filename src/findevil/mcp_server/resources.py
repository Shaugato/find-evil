"""Blackboard resource Pydantic models (blueprint Part 5.3, Table 4).

MCP exposes a typed URI namespace on top of Valkey + the ledger. Clients MUST NOT
reach into Valkey directly — every access is mediated by these resources, which
(a) normalize keys, (b) enforce outlines-style typing, and (c) let the server emit
`notify_resource_updated` on keyspace-notification events for client subscribers.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IPPheromone(_Base):
    """bb://ioc/ip/{addr} — swarm pheromone for an IPv4/IPv6 address."""

    addr: str
    tau: float = Field(ge=0.0)
    bel_evil: float = Field(ge=0.0, le=1.0)
    pl_evil: float = Field(ge=0.0, le=1.0)
    conflict_K: float = Field(ge=0.0, le=1.0)
    sensor_diversity: int = Field(ge=0)
    last_update_ns: int = Field(ge=0)
    version: int = Field(ge=0)


class HashPheromone(_Base):
    """bb://ioc/hash/{sha256}."""

    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    tau: float = Field(ge=0.0)
    bel_evil: float = Field(ge=0.0, le=1.0)
    pl_evil: float = Field(ge=0.0, le=1.0)
    conflict_K: float = Field(ge=0.0, le=1.0)
    sensor_diversity: int = Field(ge=0)
    last_update_ns: int = Field(ge=0)
    version: int = Field(ge=0)


class DomainPheromone(_Base):
    """bb://ioc/domain/{name}."""

    domain: str = Field(min_length=1, max_length=253)
    tau: float = Field(ge=0.0)
    bel_evil: float = Field(ge=0.0, le=1.0)
    pl_evil: float = Field(ge=0.0, le=1.0)
    conflict_K: float = Field(ge=0.0, le=1.0)
    sensor_diversity: int = Field(ge=0)
    last_update_ns: int = Field(ge=0)
    version: int = Field(ge=0)


class HostProcessesResource(_Base):
    """bb://host/{id}/processes — suspicious-process snapshot."""

    host_id: str
    pids: list[int] = Field(default_factory=list, max_length=512)
    flagged: list[dict] = Field(default_factory=list, max_length=512)
    last_update_ns: int = 0


class AttackPathResource(_Base):
    """bb://attack/current_path — best-effort current ATT&CK kill-chain path."""

    techniques: list[str] = Field(default_factory=list, max_length=32)
    first_seen_ns: int = 0
    last_update_ns: int = 0


class ControlFocusResource(_Base):
    """bb://control/focus — human-triaged focus key (optional).

    Setting focus biases Bytewax prioritization of events touching it.
    """

    kind: Literal["ip", "hash", "domain", "process", "host"] | None = None
    value: Optional[str] = None
    set_by: Optional[str] = None
    set_ns: int = 0


class CacaoInstanceResource(_Base):
    """bb://cacao/instance/{uuid} — runtime state of a CACAO 2.0 playbook."""

    instance_id: str
    playbook_id: str
    status: Literal["pending", "running", "succeeded", "failed", "rolled_back"]
    started_ns: int = 0
    finished_ns: int = 0
    step_cursor: int = 0
    errors: list[str] = Field(default_factory=list)


class LedgerTip(_Base):
    """bb://ledger/tip — current tip seq, hashes, last Rekor anchor."""

    seq: int
    finding_id: Optional[str] = None
    entry_hash: Optional[str] = None
    prev_hash: Optional[str] = None
    ts_ns: Optional[int] = None
    last_merkle_root: Optional[str] = None
    last_rekor_log_index: Optional[int] = None
