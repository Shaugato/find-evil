"""STIX 2.1 indicators → pheromone priors (FOR578).

A CTI indicator is treated as one more (low-diversity, decaying) sensor:
each parsed IOC becomes a Valkey pheromone deposit under the same
`pher:<kind>:<value>` keys the hot path fuses over, so threat intel raises
baseline suspicion *before* any local sensor fires — literal "pheromone
priors" per the implementation document, Appendix D.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Iterable

# `[ipv4-addr:value = '1.2.3.4']`, `[domain-name:value = 'evil.io' OR ...]`,
# `[file:hashes.'SHA-256' = 'ab…']` — the practical subset of STIX patterning
# used by indicator feeds. Composites are handled by findall over the pattern.
_PATTERN_RE = re.compile(
    r"(?P<otype>ipv4-addr|ipv6-addr|domain-name|url|file)"
    r"(?::value|:hashes\.'?(?P<hash_alg>SHA-256|SHA-1|MD5)'?)"
    r"\s*=\s*'(?P<value>[^']+)'"
)

_SENSOR = "cti.taxii"
# Priors are deliberately modest: enough to bias triage ordering, never
# enough to cross a mitigation threshold on their own.
_PRIOR_TAU_MAX = 0.35
_PRIOR_BEL_CAP = 0.45


@dataclass(frozen=True)
class Ioc:
    kind: str  # ip | domain | hash | url
    value: str
    confidence: float  # 0..1
    source_id: str  # STIX indicator id
    name: str = ""


def _kind_for(otype: str) -> str | None:
    return {
        "ipv4-addr": "ip",
        "ipv6-addr": "ip",
        "domain-name": "domain",
        "file": "hash",
        "url": "url",
    }.get(otype)


def iocs_from_stix_objects(objects: Iterable[dict[str, Any]]) -> list[Ioc]:
    """Extract IOCs from STIX 2.1 `indicator` objects (bundle['objects'])."""
    out: list[Ioc] = []
    for obj in objects:
        if obj.get("type") != "indicator" or obj.get("revoked"):
            continue
        pattern = obj.get("pattern", "")
        if obj.get("pattern_type", "stix") != "stix":
            continue
        confidence = float(obj.get("confidence", 50)) / 100.0
        for m in _PATTERN_RE.finditer(pattern):
            kind = _kind_for(m.group("otype"))
            if kind is None:
                continue
            value = m.group("value").strip().lower()
            if not value:
                continue
            out.append(
                Ioc(
                    kind=kind,
                    value=value,
                    confidence=max(0.0, min(1.0, confidence)),
                    source_id=str(obj.get("id", "")),
                    name=str(obj.get("name", "")),
                )
            )
    return out


def prior_for_ioc(ioc: Ioc) -> dict[str, Any]:
    """Deposit arguments for ValkeyClient.deposit() for one CTI prior."""
    from findevil.transport.valkey import (
        pher_domain_key,
        pher_hash_key,
        pher_ip_key,
    )

    if ioc.kind == "ip":
        key = pher_ip_key(ioc.value)
    elif ioc.kind == "domain":
        key = pher_domain_key(ioc.value)
    elif ioc.kind == "hash":
        key = pher_hash_key(ioc.value)
    else:  # url → keyed as domain-of-url when parseable, else skipped
        host = re.sub(r"^[a-z]+://", "", ioc.value).split("/")[0]
        if not host:
            return {}
        key = pher_domain_key(host)

    bel = min(_PRIOR_BEL_CAP, 0.2 + 0.3 * ioc.confidence)
    return {
        "key": key,
        "tau_delta": round(0.1 + 0.25 * ioc.confidence, 4),
        "bel": round(bel, 4),
        "pl": round(min(1.0, bel + 0.4), 4),
        "K": 0.0,
        "sensor": _SENSOR,
        "tau_max": _PRIOR_TAU_MAX,
        "now_ns": time.time_ns(),
    }


async def deposit_priors(iocs: Iterable[Ioc]) -> dict[str, Any]:
    """Deposit all IOCs as pheromone priors; returns a summary."""
    from findevil.transport.valkey import get_valkey

    vc = await get_valkey()
    deposited: list[dict[str, str]] = []
    skipped = 0
    for ioc in iocs:
        args = prior_for_ioc(ioc)
        if not args:
            skipped += 1
            continue
        key = args.pop("key")
        await vc.deposit(key, **args)
        await vc.hset(key, "cti_source", ioc.source_id or "unknown")
        deposited.append({"key": key, "kind": ioc.kind, "source": ioc.source_id})
    return {"deposited": len(deposited), "skipped": skipped, "keys": deposited[:50]}
