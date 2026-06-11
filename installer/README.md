# FIND EVIL — one-click launcher

Double-clickable launchers that wrap the [`deploy/`](../deploy) Docker Compose
stack. They check for Docker, build/start the stack, optionally download the
LLM, and open the dashboard.

| OS | File | How |
|---|---|---|
| Windows | `find-evil-windows.cmd` | Double-click it |
| macOS / Linux | `find-evil-unix.sh` | `chmod +x find-evil-unix.sh` then double-click or `./find-evil-unix.sh` |

## What the launcher does

1. Verifies Docker is installed and the engine is running (offers to start
   Docker Desktop on Windows/macOS).
2. Copies `deploy/.env.example` → `deploy/.env` if absent.
3. Asks whether to enable the AI planes (narrator + pivot agents). Saying yes
   downloads a ~2 GB GGUF model on first run, with your consent.
4. Runs `docker compose up -d --build`.
5. Waits for the dashboard, opens **http://localhost:9400**, and tails logs.

## Prerequisite

- **Docker Desktop** (Windows/macOS) or **Docker Engine** (Linux).
  The launcher links you to the installer if it's missing.

## Tier reached

This is the **Tier-1 "double-clickable launcher"** from the project plan,
implemented as native OS launch scripts (the lightest reliable form — no extra
runtime to install, unlike a Tauri/Electron wrapper). It wraps the same Compose
stack the manual instructions use, so there's one code path to maintain.

A signed installer `.exe`/`.pkg` is intentionally out of scope: code-signing
certificates require a paid identity and add no functional value for a local
defensive demo. The launcher is attached to the
[GitHub Releases page](https://github.com/Shaugato/find-evil/releases) for a
stable download URL.

## Without the launcher

Prefer to run it yourself? See [`deploy/README.md`](../deploy/README.md) — it's
two commands.
