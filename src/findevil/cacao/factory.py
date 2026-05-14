"""CACAO playbook factory — turns a consensus frame into a signed playbook.

Blueprint Appendix C maps each MITRE ATT&CK technique to CACAO actions. We pick
the first matching technique from the frame's reports (or the seed technique on
a fractal spawn), look up the action list, and chain them linearly with
`on_success -> next`, `on_failure -> rollback`.

All issued playbooks are signed with the CACAO Ed25519 key — the executor
refuses to run anything that doesn't verify.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import nacl.signing

from findevil.config.settings import settings
from findevil.swarm.attck_map import lookup

from .schema import (
    CacaoPlaybook,
    CacaoStep,
    CacaoStepType,
    CommandData,
    Playbook,
    Step,
    sign_playbook,
)


def _load_signing_key(path: Path | None = None) -> nacl.signing.SigningKey:
    p = path or settings.ledger.cacao_sk_path
    return nacl.signing.SigningKey(p.read_bytes())


def _action_commands(actuator: str, target: dict[str, Any]) -> list[dict]:
    """Build CACAO `commands[]` for a given actuator + target indicator dict."""
    body = {"name": actuator, "arguments": {"commands": [{"target": target}]}}
    return [
        {
            "type": "manual" if actuator.startswith("analyst.") else "http-api",
            "command": f"POST /mcp/tools/call BODY {json.dumps(body, sort_keys=True)}",
            "target": target,
        }
    ]


def build_playbook(
    *,
    consensus_frame: dict[str, Any],
    target: dict[str, Any],
    technique: str | None = None,
    labels: list[str] | None = None,
    sk: nacl.signing.SigningKey | None = None,
) -> CacaoPlaybook:
    """Build a signed CACAO 2.0 playbook from a consensus frame.

    Args:
      consensus_frame: raw ZMQ consensus frame (dict) that triggered this.
      target: {"type": "ipv4-addr"|..., "value": ...}.
      technique: MITRE ATT&CK id (T####.###). If None we pick the first from
                 consensus_frame['reports'][*]['attack_techniques'] (if present).
      labels: extra CACAO labels to attach.
      sk: Ed25519 signing key; defaults to the configured CACAO key.
    """
    if technique is None:
        # best-effort: first technique mentioned by any agent report
        for r in consensus_frame.get("reports", []):
            ats = r.get("attack_techniques")
            if ats:
                technique = ats[0] if isinstance(ats, list) else str(ats)
                break
    entry = lookup(technique) if technique else None
    actuators = list(entry.cacao_actions) if entry is not None else []
    if not actuators:
        actuators = ["analyst.review"]

    # Build one action step per actuator; chain with on_success.
    steps: dict[str, CacaoStep] = {}
    first_id: str | None = None
    prev: CacaoStep | None = None
    for i, actuator in enumerate(actuators):
        step = CacaoStep(
            name=f"{actuator} ({i + 1}/{len(actuators)})",
            actuator=actuator,
            commands=_action_commands(actuator, target),
        )
        if prev is not None:
            prev.on_success = step.id
            prev.on_failure = step.id  # continue on failure — better partial remediation than none
        if first_id is None:
            first_id = step.id
        steps[step.id] = step
        prev = step

    if prev is not None:
        end = CacaoStep(
            name="end",
            type="end",
            actuator="findevil.end",
        )
        prev.on_success = end.id
        steps[end.id] = end

    external_references = (
        [
            {
                "source_name": "MITRE ATT&CK",
                "external_id": technique,
            }
        ]
        if technique
        else []
    )
    parent_finding_id = consensus_frame.get("parent_finding_id")
    if parent_finding_id is None:
        ledger_ids = consensus_frame.get("ledger_finding_ids") or []
        if ledger_ids:
            parent_finding_id = ledger_ids[-1]
    if parent_finding_id:
        external_references.append(
            {
                "source_name": "findevil-ledger",
                "external_id": str(parent_finding_id),
            }
        )

    pb = CacaoPlaybook(
        name=f"findevil auto-playbook for {technique or 'unknown-technique'}",
        description=(
            "Auto-generated from consensus frame "
            f"(action={consensus_frame.get('action')}, "
            f"bel={consensus_frame.get('belief_evil')})."
        ),
        labels=(labels or [])
        + ([f"mitre-attack:{technique}"] if technique else []),
        workflow_start=first_id or "",
        workflow=steps,
        priority=80 if consensus_frame.get("action") == "mitigate" else 50,
        severity=int(min(100, 100 * float(consensus_frame.get("belief_evil", 0.0)))),
        external_references=external_references,
    )
    sk = sk or _load_signing_key()
    return sign_playbook(pb, sk)


def build_triage_playbook(ctx: dict[str, Any]) -> Playbook:
    """Build a CACAO 2.0 compatibility triage playbook for validation/export."""
    review = Step(
        name="threshold-check",
        type=CacaoStepType.IF_CONDITION,
        cases={"true": "parallel-containment"},
    )
    fanout = Step(
        id="parallel-containment",
        name="containment-fanout",
        type=CacaoStepType.PARALLEL,
        next_steps=["kill-process", "isolate-host", "reset-identities"],
    )
    kill = Step(
        id="kill-process",
        name="kill suspicious process",
        type=CacaoStepType.ACTION,
        commands=[
            CommandData(
                type="http-api",
                command="POST /mcp/tools/call edr.kill_process",
                target={"pid": ctx.get("pid"), "host_id": ctx.get("host_id")},
            )
        ],
        on_completion="end",
    )
    isolate = Step(
        id="isolate-host",
        name="isolate endpoint",
        type=CacaoStepType.ACTION,
        commands=[
            CommandData(
                type="http-api",
                command="POST /mcp/tools/call edr.network_isolate",
                target={"host_id": ctx.get("host_id"), "remote_ip": ctx.get("remote_ip")},
            )
        ],
        on_completion="end",
    )
    reset = Step(
        id="reset-identities",
        name="force credential reset",
        type=CacaoStepType.ACTION,
        commands=[
            CommandData(
                type="http-api",
                command="POST /mcp/tools/call iam.force_reset",
                target={"sids": ctx.get("sids", [])},
            )
        ],
        on_completion="end",
    )
    end = Step(id="end", name="end", type=CacaoStepType.END)
    workflow = {
        review.id: review,
        fanout.id: fanout,
        kill.id: kill,
        isolate.id: isolate,
        reset.id: reset,
        end.id: end,
    }
    return Playbook(
        name="findevil triage and containment",
        workflow_start=review.id,
        workflow=workflow,
    )
