#!/usr/bin/env bash
# FIND EVIL container entrypoint: bootstrap keys, optional model download,
# wait for infra, then hand off to supervisord.
set -euo pipefail

KEYS=/opt/findevil/etc/keys
DATA=/opt/findevil/data
MODEL="$DATA/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

mkdir -p "$KEYS" "$DATA/ledger" "$DATA/models" /opt/findevil/run/zmq /opt/findevil/logs

# --- Ed25519 ledger + CACAO keys (idempotent) --------------------------------
if [ ! -f "$KEYS/ledger_ed25519.sk" ]; then
  echo "[entrypoint] generating ledger + CACAO signing keys"
  python scripts/keygen.py all
fi

# --- genesis ledger if empty -------------------------------------------------
if [ ! -f "$DATA/ledger/ledger.sqlite" ]; then
  echo "[entrypoint] seeding genesis ledger"
  python scripts/seed_genesis.py 2>/dev/null || true
fi

# --- NATS JetStream streams --------------------------------------------------
echo "[entrypoint] ensuring NATS streams"
findevil nats-setup 2>/dev/null || true

# --- optional model download for the LLM planes ------------------------------
if [ "${ENABLE_LLM:-0}" = "1" ] && [ ! -f "$MODEL" ]; then
  echo "[entrypoint] downloading Llama-3.2-3B GGUF (~2 GB, first run only)"
  python - <<'PY'
import os
from huggingface_hub import hf_hub_download
dst = "/opt/findevil/data/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
path = hf_hub_download(
    repo_id="bartowski/Llama-3.2-3B-Instruct-GGUF",
    filename="Llama-3.2-3B-Instruct-Q4_K_M.gguf",
    local_dir="/opt/findevil/data/models",
)
print("model at", path)
PY
fi

echo "[entrypoint] starting supervisord"
exec supervisord -c /etc/supervisor/conf.d/findevil.conf -n
