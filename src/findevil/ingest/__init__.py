"""Bytewax stream ingest pipeline (Part 8).

`events` is lightweight (pure dataclasses + msgspec) and always safe to import.
`flow` drags in Bytewax, NATS, Valkey, ZeroMQ — kept lazy so unit tests that
only touch parsers/threshold logic don't need those extras installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .events import ParsedEvent, RawEvent

__all__ = ["ParsedEvent", "RawEvent", "build_flow"]


if TYPE_CHECKING:  # pragma: no cover
    from .flow import build_flow


def __getattr__(name: str):
    if name == "build_flow":
        from .flow import build_flow

        return build_flow
    raise AttributeError(f"module 'findevil.ingest' has no attribute {name!r}")
