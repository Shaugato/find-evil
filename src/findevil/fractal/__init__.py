"""Fractal ephemeral agents — H3 tier (Part 9).

Lazy re-exports via PEP 562 so that sibling imports (e.g. the scoped-prompt
module under `findevil.fractal.scoped_prompt`) don't force the whole Watcher +
transport stack to load at collection time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["Watcher", "run_pivot", "run_watcher"]


if TYPE_CHECKING:  # pragma: no cover
    from .agent import run_pivot
    from .watcher import Watcher, run as run_watcher


def __getattr__(name: str):
    if name == "run_pivot":
        from .agent import run_pivot

        return run_pivot
    if name == "Watcher":
        from .watcher import Watcher

        return Watcher
    if name == "run_watcher":
        from .watcher import run as run_watcher

        return run_watcher
    raise AttributeError(f"module 'findevil.fractal' has no attribute {name!r}")
