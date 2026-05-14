"""UI plane — FastAPI dashboard (Living Cybernetic Organism) + Textual TUI.

Both transports are lazy: the dashboard does not need `textual`, and the TUI
does not need the FastAPI/uvicorn stack. Importing one no longer drags in the
other.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["FindEvilApp", "http_app", "run_http", "run_tui"]


if TYPE_CHECKING:  # pragma: no cover
    from .http import app as http_app, run as run_http
    from .tui import FindEvilApp, run as run_tui


def __getattr__(name: str):
    if name in ("http_app", "run_http"):
        from .http import app as http_app, run as run_http
        return {"http_app": http_app, "run_http": run_http}[name]
    if name in ("FindEvilApp", "run_tui"):
        from .tui import FindEvilApp, run as run_tui
        return {"FindEvilApp": FindEvilApp, "run_tui": run_tui}[name]
    raise AttributeError(f"module 'findevil.ui' has no attribute {name!r}")
