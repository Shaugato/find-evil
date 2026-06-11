#!/usr/bin/env bash
D=/opt/findevil/data/cases/rocba/be_out/run1
echo "=== be.log tail ==="
tail -20 /opt/findevil/data/cases/rocba/be_out/be.log
echo "=== output dir ==="
ls -la "$D" 2>/dev/null | head -30
echo "=== feature counts ==="
for f in ip.txt domain.txt url.txt email.txt ether.txt ip_histogram.txt domain_histogram.txt; do
  if [ -f "$D/$f" ]; then
    printf '%-24s %s features\n' "$f" "$(grep -vc '^#' "$D/$f")"
  fi
done
echo "=== bulk_extractor running? ==="
pgrep -x bulk_extractor && echo "RUNNING" || echo "stopped"
