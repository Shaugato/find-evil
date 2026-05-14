"""Canonical event envelopes for the ingest pipeline (blueprint Part 8.2).

`RawEvent` is what lands on NATS `find.raw`: a minimally-parsed wrapper around a
source record (Zeek conn.log row, Sysmon event, YARA hit...). `ParsedEvent` is
the normalized form the rest of the pipeline consumes.

We use msgspec.Struct (not Pydantic) for zero-copy decode at 100k msg/s rates.
"""

from __future__ import annotations

from typing import Any, Optional

import msgspec


class RawEvent(msgspec.Struct, kw_only=True, frozen=True):
    source: str  # "zeek", "suricata", "sysmon", "yara", "edr", ...
    sensor: str  # concrete sensor id ("zeek-01", "sysmon-wsl", ...)
    # Implementation-guide dual-clock invariant:
    #   event_time_ns = when the phenomenon happened
    #   ingest_time_ns = monotonic timestamp at the pipeline boundary
    # `ts_ns` is retained as a backward-compatible alias for existing replay
    # fixtures; new producers should send event_time_ns.
    event_time_ns: Optional[int] = None
    ingest_time_ns: Optional[int] = None
    ts_ns: Optional[int] = None
    host_id: str
    body: dict[str, Any]
    event_id: Optional[str] = None

    @property
    def timestamp_ns(self) -> int | None:
        return self.event_time_ns if self.event_time_ns is not None else self.ts_ns


class ParsedEvent(msgspec.Struct, kw_only=True, frozen=True):
    ts_ns: int
    ingest_time_ns: Optional[int] = None
    source: str
    sensor: str
    host_id: str
    kind: str  # "conn", "proc_create", "reg_set", "yara_hit", "ssl", "dns", ...
    # indicators — any may be None; pheromone keys derive from these
    ip: Optional[str] = None
    domain: Optional[str] = None
    sha256: Optional[str] = None
    url: Optional[str] = None
    pid: Optional[int] = None
    process_image: Optional[str] = None
    registry_key: Optional[str] = None
    # Original validation/demo indicator URI when the source already did the
    # normalization, e.g. proc://foo, hash://sha256:<hex>, ipv4-addr://1.2.3.4.
    indicator_key: Optional[str] = None
    # per-event score hints (0..1); threshold evaluator calibrates these
    confidence: float = 0.0
    # MITRE ATT&CK technique ids if the source emits them
    attack_techniques: tuple[str, ...] = ()
    # opaque structured attributes (e.g. Zeek fields) for later pivots
    attrs: dict[str, Any] = msgspec.field(default_factory=dict)
