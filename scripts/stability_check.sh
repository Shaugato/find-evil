#!/usr/bin/env bash
# Post-crash stability check: uptime, OOM evidence, service health, metrics.
echo "=== uptime ==="
uptime -p
echo "=== oom/panic evidence (dmesg) ==="
dmesg 2>/dev/null | grep -iE 'oom|out of memory|killed process' | tail -5 || echo "(none readable)"
echo "=== mcp status ==="
systemctl is-active findevil-mcp
systemctl show findevil-mcp -p NRestarts -p ActiveEnterTimestamp
echo "=== all services ==="
systemctl is-active findevil-valkey findevil-nats findevil-otel findevil-llamacpp \
  findevil-mcp findevil-dashboard findevil-decay findevil-narrator \
  findevil-watcher findevil-bytewax | sort | uniq -c
echo "=== metrics 8890-8894 ==="
for p in 8890 8891 8892 8893 8894; do
  n=$(curl -s --max-time 3 "http://127.0.0.1:$p/metrics" | grep -cE '^(findevil_|backpressure_)')
  echo "port $p: $n findevil metric lines"
done
echo "=== TABLE11 names visible anywhere ==="
for p in 8890 8891 8892 8893 8894; do
  curl -s --max-time 3 "http://127.0.0.1:$p/metrics"
done | grep -oE '^(findevil_ds_fusion_seconds|findevil_ds_conflict_K|findevil_mcp_write_tps|findevil_ledger_append_seconds|findevil_rekor_anchor_age_seconds|findevil_vllm_ttft_seconds|backpressure_drops_total|findevil_fractal_live_agents|findevil_consensus_fire_total|findevil_schema_validation_fail_total)' | sort -u
echo "=== ledger ==="
sqlite3 /opt/findevil/data/ledger/ledger.sqlite "SELECT COUNT(*), MAX(seq) FROM ledger;"
echo "=== memory ==="
free -h | head -2
