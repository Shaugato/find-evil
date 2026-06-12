#!/usr/bin/env bash
# ============================================================================
#  FIND EVIL — one-line installer (macOS / Linux)
#
#    curl -fsSL https://raw.githubusercontent.com/Shaugato/find-evil/main/installer/install.sh | bash
#
#  Installs Docker if missing (Linux), clones the repo, and starts the stack.
#  This is the curl|bash convenience wrapper around find-evil-unix.sh; it makes
#  no destructive changes beyond cloning the repo and starting Docker Compose.
# ============================================================================
set -euo pipefail

REPO_URL="https://github.com/Shaugato/find-evil.git"
TARGET="${FIND_EVIL_HOME:-$HOME/find-evil}"
GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
say() { echo -e "${GREEN}[find-evil]${NC} $*"; }
die() { echo -e "${RED}[find-evil] ERROR:${NC} $*" >&2; exit 1; }

say "FIND EVIL installer — defensive DFIR SOC, runs entirely on your machine."

command -v git >/dev/null 2>&1 || die "git required. Install git and re-run."

if ! command -v docker >/dev/null 2>&1; then
  case "$(uname -s)" in
    Linux)  say "Installing Docker Engine via get.docker.com (sudo may prompt)…"
            curl -fsSL https://get.docker.com | sh || die "Docker install failed." ;;
    Darwin) die "Install Docker Desktop for Mac, then re-run: https://www.docker.com/products/docker-desktop/" ;;
    *)      die "Unsupported OS for auto-install; see https://docs.docker.com/get-docker/" ;;
  esac
fi

if [ -d "$TARGET/.git" ]; then
  say "Updating existing checkout at $TARGET"
  git -C "$TARGET" pull --ff-only || say "pull skipped; using current checkout"
else
  say "Cloning FIND EVIL into $TARGET"
  git clone --depth 1 "$REPO_URL" "$TARGET"
fi

exec bash "$TARGET/installer/find-evil-unix.sh"
