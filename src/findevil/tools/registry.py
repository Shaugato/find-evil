"""Central registry for actuator-callable tool shims.

Every shim module registers itself via `@register("edr.kill_process")` etc. The
CACAO executor resolves actuator ids to callables through `resolve(name)`.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any, Awaitable, Callable

ToolFn = Callable[[list[dict[str, Any]]], Awaitable[dict[str, Any]]]

_REGISTRY: dict[str, ToolFn] = {}
_BOOTSTRAPPED = False


def register(name: str) -> Callable[[ToolFn], ToolFn]:
    """Decorator: register a tool function under `name`.

    Re-registrations with the same name overwrite the previous entry — this lets
    tests swap in fakes via monkeypatch + re-import.
    """

    def _decorator(fn: ToolFn) -> ToolFn:
        _REGISTRY[name] = fn
        return fn

    return _decorator


def resolve(name: str) -> ToolFn | None:
    if not _BOOTSTRAPPED:
        bootstrap()
    return _REGISTRY.get(name)


def registered() -> list[str]:
    if not _BOOTSTRAPPED:
        bootstrap()
    return sorted(_REGISTRY.keys())


def bootstrap() -> None:
    """Import every submodule of `findevil.tools.shims` so decorators fire."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    import findevil.tools.shims as shims_pkg

    for _finder, name, _ispkg in pkgutil.iter_modules(shims_pkg.__path__):
        importlib.import_module(f"{shims_pkg.__name__}.{name}")
    _BOOTSTRAPPED = True
