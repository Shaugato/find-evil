#!/usr/bin/env bash
# Confirm TABLE 11 doc-named metrics are exposed by the live services.
# Ports: base=settings.observability.prometheus_port; mcp=+1 bytewax=+2
# watcher=+3 narrator=+4 cacao=+5
BASE=$(grep -oP 'PROMETHEUS_PORT\D*\K\d+' /opt/findevil/etc/.env 2>/dev/null || echo 8889)
echo "base port: $BASE"
for off in 1 2 3 4; do
  port=$((BASE + off))
  echo "=== :$port ==="
  curl -s "http://127.0.0.1:$port/metrics" | grep -oE '^(findevil_[a-zA-Z_]+|backpressure_drops[a-zA-Z_]*)' | sort -u | head -25
done
