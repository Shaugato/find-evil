# Stigmergy — one-click launcher

Standalone launchers that get Stigmergy running locally with one step. They
work **whether or not you've already cloned the repo** — if run on their own,
they fetch the repo for you, then check Docker, start the
[`deploy/`](../deploy) Compose stack, optionally download the LLM, and open the
dashboard.

## Fastest — one line (macOS / Linux)

```bash
curl -fsSL https://raw.githubusercontent.com/Shaugato/find-evil/main/installer/install.sh | bash
```

Installs Docker if missing (Linux), clones the repo to `~/find-evil`, and starts
the stack. This is the standard 2026 self-hosted pattern (Dify, Ollama, LocalAI
all use a curl|bash bootstrap).

## Double-click launchers

| OS | File | How |
|---|---|---|
| Windows | `find-evil-windows.cmd` | Download from the [release](https://github.com/Shaugato/find-evil/releases) and double-click |
| macOS / Linux | `find-evil-unix.sh` | `chmod +x find-evil-unix.sh` then `./find-evil-unix.sh` |

## What the launcher does

1. Verifies **Docker** is installed (offers `get.docker.com` install on Linux;
   links Docker Desktop on Windows/macOS) and that the engine is running.
2. **Locates the stack**: uses a sibling `deploy/` if the launcher is inside a
   clone; otherwise clones `github.com/Shaugato/find-evil` to `~/find-evil`
   (or `%USERPROFILE%\find-evil`).
3. Copies `deploy/.env.example` → `deploy/.env` if absent.
4. Asks whether to enable the AI planes (narrator + pivot agents). Yes downloads
   a ~2 GB GGUF model on first run, with your consent.
5. Runs `docker compose up -d --build`.
6. Waits for the dashboard, opens **http://localhost:9400**, and tails logs.

## Container runtime alternatives

Docker Desktop is the default, but the stack is plain Compose v2, so these work
too: **Podman** (`podman compose`), **Rancher Desktop**, and **OrbStack** (Mac).
Point your runtime's `docker`/`docker compose` shim at the stack and the
launchers behave identically.

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
