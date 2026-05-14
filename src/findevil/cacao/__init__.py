"""CACAO 2.0 playbook plane (blueprint Part 11).

Schema + sign/verify stay eagerly importable (pure Pydantic + pynacl). The
executor is lazy because it drags in Valkey, ZeroMQ, and the tool registry,
which unit tests for sign/verify should not require at collection time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .factory import build_playbook
from .schema import CacaoPlaybook, CacaoStep, sign_playbook, verify_playbook

__all__ = [
    "CacaoPlaybook",
    "CacaoStep",
    "build_playbook",
    "execute_playbook",
    "run_executor",
    "sign_playbook",
    "verify_playbook",
]


if TYPE_CHECKING:  # pragma: no cover
    from .executor import execute_playbook, run as run_executor


def __getattr__(name: str):
    if name == "execute_playbook":
        from .executor import execute_playbook

        return execute_playbook
    if name == "run_executor":
        from .executor import run as run_executor

        return run_executor
    raise AttributeError(f"module 'findevil.cacao' has no attribute {name!r}")
