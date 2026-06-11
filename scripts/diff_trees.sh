#!/usr/bin/env bash
# Compare Windows git tree vs WSL runtime tree (excluding pycache)
WIN="/mnt/d/Autonomous DFIR - Agentic SOC"
for d in tests scripts etc docs; do
  echo "== $d =="
  diff -rq "$WIN/$d" "/opt/findevil/repo/$d" 2>&1 | grep -v __pycache__ | head -15
done
echo "== top-level files =="
for f in pyproject.toml README.md implementation_document.txt; do
  if diff -q "$WIN/$f" "/opt/findevil/repo/$f" >/dev/null 2>&1; then
    echo "$f: identical"
  else
    echo "$f: DIFFERS or missing"
  fi
done
