#!/usr/bin/env bash
# ============================================================================
#  FIND EVIL — one-click launcher for macOS / Linux
#  Make executable (chmod +x) and double-click, or run from a terminal.
#  Checks Docker, builds/starts the Compose stack, opens the dashboard.
# ============================================================================
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
say() { echo -e "${GREEN}[find-evil]${NC} $*"; }
die() { echo -e "${RED}[find-evil] ERROR:${NC} $*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$SCRIPT_DIR/../deploy"
[ -d "$DEPLOY_DIR" ] || die "deploy/ folder not found. Run from inside a cloned find-evil repo."
cd "$DEPLOY_DIR"

echo
echo "  ============================================"
echo "    FIND EVIL - autonomous DFIR SOC (local)"
echo "  ============================================"
echo

command -v docker >/dev/null 2>&1 || die "Docker not installed. See https://docs.docker.com/get-docker/"

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
echo "    FIND EVIL is up."
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
