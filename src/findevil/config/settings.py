"""Pydantic-settings loader — single source of configuration truth.

All components import from here. Env prefix FINDEVIL_, nested delimiter __.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TransportCfg(BaseModel):
    zmq_ipc_dir: Path = Path("/opt/findevil/run/zmq")
    valkey_sock: Path = Path("/opt/findevil/run/valkey.sock")
    valkey_host: str = "127.0.0.1"
    valkey_port: int = 6379
    nats_url: str = "nats://127.0.0.1:4222"
    nats_jsdomain: str = "findevil"
    nats_user: str = "writer"
    nats_password: str = ""


class InferenceCfg(BaseModel):
    profile: str = Field("A", pattern="^[ABC]$")
    model_path: Path = Path(
        "/opt/findevil/data/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    )
    model_name: str = "llama-3.2-3b-instruct"
    ctx: int = 2048
    n_gpu_layers: int = 28
    llamacpp_host: str = "127.0.0.1"
    llamacpp_port: int = 8080
    vllm_host: str = "127.0.0.1"
    vllm_port: int = 8000
    gpu_mem_util: float = 0.85


class LedgerCfg(BaseModel):
    sqlite_path: Path = Path("/opt/findevil/data/ledger/ledger.sqlite")
    ed25519_sk_path: Path = Path("/opt/findevil/etc/keys/ledger_ed25519.sk")
    ed25519_pk_path: Path = Path("/opt/findevil/etc/keys/ledger_ed25519.pk")
    cacao_sk_path: Path = Path("/opt/findevil/etc/keys/cacao_ed25519.sk")
    cacao_pk_path: Path = Path("/opt/findevil/etc/keys/cacao_ed25519.pk")
    rekor_url: str = "https://rekor.sigstore.dev"
    anchor_every_n: int = 256


class SwarmCfg(BaseModel):
    decay_rho: float = 0.05
    tick_ms: int = 10
    theta_mitigate: float = 0.80
    theta_finding: float = 0.40
    k_yager_lo: float = 0.30
    k_yager_hi: float = 0.70
    k_escalate: float = 0.70
    sensor_diversity_min: int = 2
    tau_max: float = 10.0
    tau_min: float = 0.0


class FractalCfg(BaseModel):
    max_depth: int = 3
    max_width: int = 16
    ttl_ms: int = 2000
    pivot_bar: float = 0.50


class McpCfg(BaseModel):
    host: str = "127.0.0.1"
    port: int = 9310
    path: str = "/mcp"


class UiCfg(BaseModel):
    http_host: str = "127.0.0.1"
    http_port: int = 9400


class ObservabilityCfg(BaseModel):
    otlp_endpoint: str = "127.0.0.1:4317"
    prometheus_port: int = 8889
    service_name: str = "findevil"


class AppSettings(BaseSettings):
    """Root settings object — load via `from findevil.config.settings import settings`."""

    model_config = SettingsConfigDict(
        env_prefix="FINDEVIL_",
        env_nested_delimiter="__",
        env_file="/opt/findevil/etc/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    host_id: str = "findevil-wsl"
    transport: TransportCfg = TransportCfg()
    inference: InferenceCfg = InferenceCfg()
    ledger: LedgerCfg = LedgerCfg()
    swarm: SwarmCfg = SwarmCfg()
    fractal: FractalCfg = FractalCfg()
    mcp: McpCfg = McpCfg()
    ui: UiCfg = UiCfg()
    observability: ObservabilityCfg = ObservabilityCfg()


# ---------------------------------------------------------------------------
# Live singleton proxy
#
# Every call site does `from findevil.config.settings import settings`, which
# captures the `settings` binding at import time. If tests (or a SIGHUP handler)
# want to reload after env changes, rebinding the module attribute alone would
# NOT propagate to the already-imported names in other modules. A proxy solves
# this: all call sites hold a reference to the same proxy, and every attribute
# read hits the current `_instance`. Call `reload()` to rebuild after env
# mutations.
# ---------------------------------------------------------------------------

_instance: AppSettings = AppSettings()


def reload() -> AppSettings:
    """Rebuild the settings singleton — call this after mutating env vars."""
    global _instance
    _instance = AppSettings()
    return _instance


def current() -> AppSettings:
    """Return the current concrete AppSettings instance (not the proxy)."""
    return _instance


class _SettingsProxy:
    """Transparent proxy that forwards every attr access to the live instance.

    Intentionally implements only `__getattr__` — no caching — so tests can
    rebuild the underlying instance and every subsequent access sees the new
    values. `__repr__` is overridden so logs remain legible.
    """

    __slots__ = ()

    def __getattr__(self, name: str):  # noqa: D401
        return getattr(_instance, name)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<SettingsProxy → {_instance!r}>"


settings = _SettingsProxy()
