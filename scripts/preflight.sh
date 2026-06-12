#!/usr/bin/env bash
echo "=== services ==="
systemctl is-active findevil-valkey findevil-nats findevil-mcp findevil-dashboard \
  findevil-bytewax findevil-decay findevil-narrator findevil-watcher findevil-llamacpp 2>/dev/null | tr '\n' ' '
echo
echo "=== dashboard api ==="
curl -s --max-time 5 http://127.0.0.1:9400/api/ledger/tip
echo
echo "=== llamacpp health (narrator dep) ==="
curl -s --max-time 8 http://127.0.0.1:8080/v1/models 2>&1 | head -c 200
echo
echo "=== ledger verify ==="
/opt/findevil/venv/bin/findevil verify 2>&1 | tail -3
