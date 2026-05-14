"""Regression: every FINDEVIL_* key in etc/.env.example maps to a real settings field.

Previously the env template referenced sections that did not exist in AppSettings
(FINDEVIL_PATHS__*, FINDEVIL_CACAO__*) and used the wrong default port for
Prometheus. This test walks every uncommented KEY=VALUE in the template and
confirms the corresponding pydantic field resolves.
"""

from __future__ import annotations

from pathlib import Path

from findevil.config.settings import AppSettings


REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = REPO_ROOT / "etc" / ".env.example"


def _env_keys(text: str) -> list[str]:
    keys: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        keys.append(line.split("=", 1)[0].strip())
    return keys


def test_env_example_keys_resolve_to_settings_fields():
    assert ENV_EXAMPLE.exists(), ".env.example is missing"
    keys = _env_keys(ENV_EXAMPLE.read_text(encoding="utf-8"))
    assert keys, "no env keys parsed"

    # Build a defaults instance that is NOT loading the real /opt/findevil/etc/.env.
    s = AppSettings(_env_file=None)  # type: ignore[arg-type]

    unresolved: list[str] = []
    for key in keys:
        assert key.startswith("FINDEVIL_"), f"{key} missing FINDEVIL_ prefix"
        path = key[len("FINDEVIL_") :].split("__")
        cur = s
        for segment in path:
            attr = segment.lower()
            if hasattr(cur, attr):
                cur = getattr(cur, attr)
            else:
                unresolved.append(key)
                break

    assert not unresolved, f"unknown settings paths in .env.example: {unresolved}"


def test_env_example_has_no_phantom_sections():
    """Catch drift like FINDEVIL_PATHS__* that used to live here."""
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    for phantom in (
        "FINDEVIL_PATHS__",
        "FINDEVIL_CACAO__",  # CACAO lives under LEDGER in the schema
        "FINDEVIL_INFERENCE__BASE_URL",  # removed in current schema
        "FINDEVIL_INFERENCE__API_KEY",
        "FINDEVIL_INFERENCE__MODEL=",  # now MODEL_NAME
    ):
        assert phantom not in text, f"phantom setting still in .env.example: {phantom}"
