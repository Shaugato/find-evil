"""Scoped-prompt builder for H3 pivot agents (blueprint Part 9.4).

Produces a prompt string + exhibit list from a consensus frame. Scoping rules:

  * NO free-form host/user data; only the attested exhibits are in scope
  * all exhibit dicts MUST carry `exhibit_id` matching `^ex_[a-z0-9]{8}$`
    (`outlines_schemas.ExhibitCitation` enforces this on the output side too)
  * the prompt explicitly forbids inventing hashes, IPs, or user accounts
  * `seed_technique` is the MITRE ATT&CK technique that caused the spawn,
    so the model can specialize its search (see ATTCK_MAP for pivots)
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable

from findevil.swarm.attck_map import lookup


def _exhibit_id(payload: dict[str, Any]) -> str:
    """Derive a deterministic `ex_xxxxxxxx` id from payload hash."""
    canonical = str(sorted(payload.items())).encode()
    return "ex_" + hashlib.blake2b(canonical, digest_size=4).hexdigest()


def make_exhibits(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for it in items:
        d = dict(it)
        d["exhibit_id"] = d.get("exhibit_id") or _exhibit_id(d)
        out.append(d)
    return out


def build_scoped_prompt(
    consensus_frame: dict[str, Any],
    exhibits: list[dict[str, Any]],
    seed_technique: str | None = None,
) -> str:
    attack_hint = ""
    if seed_technique and (entry := lookup(seed_technique)) is not None:
        attack_hint = (
            f"The parent consensus fires for MITRE ATT&CK {entry.technique} "
            f"({entry.signal}). Likely agents: {entry.agent}. "
            f"Suggested pivots: {', '.join(entry.mcp_tools)}."
        )

    pher_key = consensus_frame.get("pher_key", "<unknown>")
    bel = consensus_frame.get("belief_evil", 0.0)
    K = consensus_frame.get("conflict_K", 0.0)

    return (
        "SCOPE-CONSTRAINED PIVOT.\n"
        f"Parent pheromone: {pher_key}\n"
        f"Parent fused belief(evil)={bel:.3f}, conflict_K={K:.3f}.\n"
        f"{attack_hint}\n\n"
        "Tasks:\n"
        " 1. Pick ONE concrete next pivot for this artifact.\n"
        " 2. Cite every claim by exhibit_id from the provided list.\n"
        " 3. NEVER invent hashes, IPs, registry keys, user names, or PIDs.\n"
        " 4. If evidence is thin, return verdict='insufficient' and a large "
        "declared_ignorance.\n"
        " 5. Optionally emit up to 4 `follow_ups`; each must itself carry only "
        "in-scope exhibit references.\n"
    )
