"""Configuration package.

Exports both the `AppSettings` pydantic model and the module-level `settings`
instance. We deliberately DO NOT rebind `findevil.config.settings` to the
instance — the submodule of that name is the authoritative location for the
singleton (and tests need to reach it as a module to rebuild after env
overrides). Call sites use `from findevil.config.settings import settings`.
"""

from .settings import AppSettings  # re-export only the class

__all__ = ["AppSettings"]
