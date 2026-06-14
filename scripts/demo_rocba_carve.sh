#!/usr/bin/env bash
# Stigmergy demo — LIVE forensic carve of the official SANS ROCBA memory image.
#
# Shows (on camera, in ~10 s): (1) proof the full 18 GB image was carved with
# bulk_extractor, then (2) a LIVE carve of a real slice that re-extracts real
# indicators — including the conflict IP 142.250.64.106 and victim org
# stark-research-labs.com — from the genuine evidence. Real tool, real image.
#
# Defensive DFIR only: read-only over a sample/official forensic image.
# Repeatable: clears its scratch output each run. No sudo required.
set -euo pipefail

CASE="${ROCBA_CASE:-/opt/findevil/data/cases/rocba}"
RAW="$CASE/Rocba-Memory.raw"
FULL="$CASE/be_out/run1"                 # the real full-image carve (proof)
SLICE=/tmp/rocba_slice.raw
OUT=/tmp/be_demo
# slice window (MiB) chosen to contain the real conflict IP 142.250.64.106
SKIP_MIB="${ROCBA_SKIP_MIB:-4770}"
COUNT_MIB="${ROCBA_COUNT_MIB:-320}"

echo "════════════════════════════════════════════════════════════════════"
echo " STIGMERGY · LIVE FORENSIC CARVE — official SANS ROCBA memory image"
echo "════════════════════════════════════════════════════════════════════"
echo " evidence : $RAW"
echo " size     : $(du -h "$RAW" | cut -f1)   (real Windows memory image)"
echo

echo "── 1. PROOF: the full image was carved with bulk_extractor 2.1.1 ──────"
echo "   real carved IPs (feature: struct ip … from packets in memory):"
grep -v '^#' "$FULL/ip_histogram.txt" | head -6 | sed 's/^/     /'
echo "   the conflict IP, carved from the real image:"
grep '142.250.64.106' "$FULL/ip_histogram.txt" | sed 's/^/     /'
echo "   the victim org, carved from the real image:"
grep -i 'stark-research-labs.com' "$FULL/domain_histogram.txt" | head -1 | sed 's/^/     /'
echo

echo "── 2. LIVE carve of a real ${COUNT_MIB} MiB slice of the evidence ─────────────"
dd if="$RAW" of="$SLICE" bs=1M skip="$SKIP_MIB" count="$COUNT_MIB" status=none
echo "   sliced $(du -h "$SLICE" | cut -f1) of real evidence → carving now…"
rm -rf "$OUT"
t0=$(date +%s)
bulk_extractor -E net -o "$OUT" "$SLICE" >/tmp/be_demo.log 2>&1
t1=$(date +%s)
echo "   ✓ bulk_extractor finished in $((t1 - t0)) s"
echo
echo "   REAL indicators just carved live from the slice:"
grep -v '^#' "$OUT/ip_histogram.txt" | head -8 | sed 's/^/     /'
echo
echo "   → conflict IP present in the live carve? "
if grep -q '142.250.64.106' "$OUT/ip.txt"; then
  echo "     YES — 142.250.64.106 extracted from the real image, live."
else
  echo "     (not in this slice; present in the full carve above)"
fi
echo "════════════════════════════════════════════════════════════════════"
echo " Next: feed this carved indicator into the live swarm →  demo_rocba_conflict.py"
