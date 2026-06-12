#!/usr/bin/env bash
# One-shot: drive the live pipeline on the real carved ROCBA indicators,
# export the execution log + website replay JSON + sanitised ledger, verify.
set -uo pipefail
REPO=/opt/findevil/repo
WIN="/mnt/d/Autonomous DFIR - Agentic SOC"
BE=/opt/findevil/data/cases/rocba/be_out/run1

echo "=== sync latest scripts to runtime ==="
bash "$WIN/scripts/sync_to_runtime.sh" >/dev/null 2>&1 || true
cp "$WIN/scripts/real_data_carve_run.py" "$REPO/scripts/" 2>/dev/null || true
cp "$WIN/scripts/export_ledger.py" "$REPO/scripts/" 2>/dev/null || true

echo "=== preflight ==="
bash "$WIN/scripts/preflight.sh"

echo "=== carve feature counts ==="
for f in ip.txt domain.txt url.txt email.txt; do
  [ -f "$BE/$f" ] && printf '%-12s %s\n' "$f" "$(grep -vc '^#' "$BE/$f")"
done

before=$(curl -s http://127.0.0.1:9400/api/ledger/tip | grep -oP '"seq"\s*:\s*\K[0-9]+' | head -1)
echo "ledger tip before: ${before:-?}"

echo "=== REAL-DATA RUN ==="
cd "$REPO"
/opt/findevil/venv/bin/python scripts/real_data_carve_run.py \
  --be-dir "$BE" --max-ips 12 --max-domains 12 --wait 50 \
  --export "$WIN/docs/hackathon/execution-logs/rocba_carve_run.json" \
  --replay-out "$WIN/web/public/data/rocba_run.json"

echo "=== sanitised ledger export (via dashboard API; avoids direct SQLite open) ==="
# IMPORTANT: never open the ledger SQLite directly from this (shaugato) shell —
# doing so creates shaugato-owned -wal/-shm sidecars the findevil services then
# cannot open. The dashboard API is the findevil-owned canonical read path.
/opt/findevil/venv/bin/python scripts/export_ledger.py \
  --via-api --since "${before:-936}" \
  --out "$WIN/docs/hackathon/execution-logs/ledger_export.json"

echo "=== final verify ==="
/opt/findevil/venv/bin/findevil verify 2>&1 | tail -4
