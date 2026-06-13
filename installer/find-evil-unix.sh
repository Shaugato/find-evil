#!/usr/bin/env bash
# ============================================================================
#  Stigmergy — one-click launcher for macOS / Linux
#  Make executable (chmod +x) and double-click, or run from a terminal.
#  Checks Docker, builds/starts the Compose stack, opens the dashboard.
# ============================================================================
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
say() { echo -e "${GREEN}[find-evil]${NC} $*"; }
die() { echo -e "${RED}[find-evil] ERROR:${NC} $*" >&2; exit 1; }

REPO_URL="https://github.com/Shaugato/find-evil.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo
echo "  ============================================"
echo "    Stigmergy - autonomous DFIR SOC (local)"
echo "  ============================================"
echo

# --- Docker (engine + compose v2) -------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  say "Docker is not installed."
  case "$(uname -s)" in
    Linux)
      read -r -p "Install Docker Engine now via get.docker.com? [y/N]: " yn
      if [[ "${yn:-}" =~ ^[Yy]$ ]]; then
        curl -fsSL https://get.docker.com | sh || die "Docker install failed."
      else
        die "Docker required. See https://docs.docker.com/get-docker/"
      fi ;;
    Darwin) die "Install Docker Desktop for Mac: https://www.docker.com/products/docker-desktop/ then re-run." ;;
    *)      die "Docker required. See https://docs.docker.com/get-docker/" ;;
  esac
fi
docker compose version >/dev/null 2>&1 || die "Docker Compose v2 required (update Docker)."

# --- Locate the deploy/ stack: use a sibling repo, else clone ----------------
if [ -d "$SCRIPT_DIR/../deploy" ]; then
  DEPLOY_DIR="$(cd "$SCRIPT_DIR/../deploy" && pwd)"
  say "Using existing repo at $(dirname "$DEPLOY_DIR")"
else
  command -v git >/dev/null 2>&1 || die "git required to fetch Stigmergy. Install git and re-run."
  TARGET="${FIND_EVIL_HOME:-$HOME/find-evil}"
  if [ -d "$TARGET/deploy" ]; then
    say "Updating existing checkout at $TARGET"
    git -C "$TARGET" pull --ff-only || say "pull skipped (local changes); using current checkout"
  else
    say "Cloning Stigmergy into $TARGET ..."
    git clone --depth 1 "$REPO_URL" "$TARGET" || die "git clone failed."
  fi
  DEPLOY_DIR="$TARGET/deploy"
fi
cd "$DEPLOY_DIR"

if ! docker info >/dev/null 2>&1; then
  say "Docker is installed but the engine isn't running."
  case "$(uname -s)" in
    Darwin) say "Starting Docker Desktop..."; open -a Docker || true ;;
    *)      say "Start the Docker daemon (e.g. 'sudo systemctl start docker') and re-run." ;;
  esac
  say "Waiting up to 90s for the engine..."
  for _ in $(seq 1 18); do sleep 5; docker info >/dev/null 2>&1 && break; done
  docker info >/dev/null 2>&1 || die "Docker engine did not start."
fi
say "Docker engine is running."

[ -f .env ] || cp .env.example .env

read -r -p "Enable the AI narrator/pivot agents? Downloads ~2 GB model on first run [y/N]: " llm
if [[ "${llm:-}" =~ ^[Yy]$ ]]; then export ENABLE_LLM=1; else export ENABLE_LLM=0; fi

say "Building and starting the stack (first run may take a few minutes)..."
docker compose up -d --build

say "Waiting for the dashboard..."
for _ in $(seq 1 20); do
  curl -s -o /dev/null http://localhost:9400/ 2>/dev/null && break
  sleep 3
done

echo
echo "  ============================================"
echo "    Stigmergy is up."
echo "      Dashboard : http://localhost:9400"
echo "      MCP       : http://localhost:9310/mcp"
echo "  ============================================"
echo
say "Verify the forensic ledger:  docker compose exec findevil findevil verify"

case "$(uname -s)" in
  Darwin) open http://localhost:9400 || true ;;
  Linux)  xdg-open http://localhost:9400 >/dev/null 2>&1 || true ;;
esac

say "Tailing logs (Ctrl+C to stop watching; the stack keeps running)."
docker compose logs -f findevil
