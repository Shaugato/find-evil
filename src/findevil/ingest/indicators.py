"""Indicator URI helpers shared by the ingest parser and window evaluator."""

from __future__ import annotations

import re

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RAW_SCHEMES = ("user://", "reg://", "task://", "url://", "file://")


def indicator_tuple(indicator_key: str | None) -> tuple | None:
    """Map validation indicator URIs onto the internal pheromone tuple keyspace."""
    if not indicator_key:
        return None
    key = indicator_key.strip()
    if key.startswith("ipv4-addr://"):
        return (key.removeprefix("ipv4-addr://"), None, None, None)
    if key.startswith("domain://"):
        return (None, key.removeprefix("domain://"), None, None)
    if key.startswith("domain-name://"):
        return (None, key.removeprefix("domain-name://"), None, None)
    if key.startswith("hash://sha256:"):
        sha = key.removeprefix("hash://sha256:").lower()
        return (None, None, sha, None) if _SHA256_RE.match(sha) else None
    if key.startswith("sha256://"):
        sha = key.removeprefix("sha256://").lower()
        return (None, None, sha, None) if _SHA256_RE.match(sha) else None
    if key.startswith("proc://"):
        return (None, None, None, key.removeprefix("proc://"))
    if key.startswith(_RAW_SCHEMES):
        return (None, None, None, f"__raw__:{key}")
    return None
