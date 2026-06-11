#!/usr/bin/env bash
# Sync source from the Windows git tree to the WSL runtime tree.
# Excludes caches, docs source files, and local-only artifacts.
set -euo pipefail
WIN="/mnt/d/Autonomous DFIR - Agentic SOC"
DST="/opt/findevil/repo"

rsync -a --delete \
  --exclude '__pycache__/' \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude '.claude/' \
  --exclude '.codex_analysis/' \
  --exclude 'Find Evil UI design/' \
  --exclude 'validation-artifacts/' \
  --exclude 'docs/' \
  --exclude 'data/' \
  --exclude 'web/' \
  "$WIN/src/" "$DST/src/"

rsync -a --delete --exclude '__pycache__/' "$WIN/tests/" "$DST/tests/"
rsync -a --exclude '__pycache__/' "$WIN/scripts/" "$DST/scripts/"
rsync -a "$WIN/etc/" "$DST/etc/"
cp "$WIN/pyproject.toml" "$DST/pyproject.toml"
echo "sync complete: $(date -Is)"
