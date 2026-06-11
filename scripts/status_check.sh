#!/usr/bin/env bash
# FIND EVIL — full status battery (Section 4 fresh check)
echo "=== systemd availability ==="
ps -p 1 -o comm=
command -v systemctl || echo "NO systemctl"

echo "=== services ==="
for svc in findevil-valkey findevil-nats findevil-otel findevil-llamacpp \
           findevil-mcp findevil-dashboard findevil-decay findevil-narrator \
           findevil-watcher findevil-bytewax findevil-verify.timer; do
  printf "%-25s active=%-10s\n" "$svc" "$(systemctl is-active "$svc" 2>/dev/null)"
done

echo "=== ledger ==="
sqlite3 /opt/findevil/data/ledger/ledger.sqlite \
  "SELECT COUNT(*) AS entries, MAX(seq) AS max_seq FROM ledger;" 2>&1

echo "=== findevil verify ==="
command -v findevil
findevil verify 2>&1 | tail -5

echo "=== repo layout ==="
ls /opt/findevil/repo/ | head -30
echo "--- git? ---"
git -C /opt/findevil/repo rev-parse --is-inside-work-tree 2>&1
ls -la /opt/findevil/repo | head -5

echo "=== pytest ==="
cd /opt/findevil/repo && /opt/findevil/venv/bin/python -m pytest tests/ -q --tb=no 2>&1 | tail -5

echo "=== sudo check ==="
sudo -n true 2>&1 && echo "passwordless sudo OK" || echo "sudo needs password"

echo "=== gpu ==="
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>&1 | head -2
