# Stigmergy — Try It Out (Deliverable 7)

Three ways to evaluate Stigmergy, fastest first.

> **▶ Watch the 5-minute demo (no install):** **https://youtu.be/4xOz7jFWh9s**
> Live ROCBA carve on the real memory image → a real self-correction → the MCP
> typed-tool guardrail → the dashboard.
>
> **Live companion site (no install):** **https://web-eight-sage-34.vercel.app**
> Explore the architecture and replay the real ROCBA run in your browser with
> zero setup.

---

## Option A — Companion website (zero install, ~1 min)

Open **https://web-eight-sage-34.vercel.app**. It hosts:

- an interactive architecture explainer (architectural vs prompt guardrails),
- a **replay viewer** of the real ROCBA run driven by exported ledger JSON —
  scrub the timeline, watch the pheromone graph / ledger feed / MITRE matrix
  update, and see the highlighted **self-correction** moment,
- the demo video (once recorded) and download links.

This satisfies the "explore before installing" path and shows the actual
real-data evidence without a local stack.

---

## Option B — Docker Compose (one command, ~10 min + model download)

> Requires Docker Desktop (Windows/Mac) or Docker Engine (Linux).

```bash
git clone https://github.com/Shaugato/find-evil.git
cd find-evil/deploy
cp .env.example .env          # review; defaults work for a local demo
docker compose up -d          # pulls images, builds services, starts the stack
# first run downloads the ~2 GB Llama-3.2-3B GGUF with visible progress
docker compose logs -f findevil-dashboard
```

Then open the dashboard at **http://localhost:9400** and the MCP blackboard at
**http://localhost:9310/mcp**.

Run the bundled validation against synthetic telemetry (no external data):

```bash
docker compose exec findevil python scripts/whitehat_validation.py
docker compose exec findevil findevil verify     # -> ok=true, tainted_seqs=[]
```

The installer (Option D) is a double-clickable wrapper around exactly this
stack — see the GitHub Releases page.

---

## Option C — Native on the SANS SIFT Workstation (full fidelity)

This is the environment the platform was validated on: WSL2 Ubuntu 24.04 with
systemd, on a SIFT-tooled host.

### Dependencies

| Component | Version | Purpose |
|---|---|---|
| Ubuntu | 24.04 (WSL2 or native), **systemd enabled** | service host |
| Python | 3.12 | runtime |
| Valkey | 8.x | pheromone field |
| NATS | 2.11 (JetStream) | event streams |
| SIFT forensic tools | YARA 4.5, Zeek 8.1, tshark 4.2, Sleuth Kit 4.12, Volatility 3, Plaso, bulk_extractor 2.1 | MCP tool shims |
| OpenTelemetry Collector | latest | metrics/traces |
| llama.cpp (CPU) | via llama-cpp-python | local inference |

### Bring-up

```bash
git clone https://github.com/Shaugato/find-evil.git
cd find-evil
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e .

# generate signing keys + seed streams (idempotent)
bash scripts/bootstrap.sh

# install + start services (systemd unit files in etc/)
sudo cp etc/systemd/*.service etc/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start findevil.target

# verify
findevil verify                 # -> {"ok": true, "tainted_seqs": []}
python scripts/whitehat_validation.py
```

Dashboard: **http://127.0.0.1:9400** · MCP: **http://127.0.0.1:9310/mcp**

### Run it on real case data (the centrepiece)

```bash
# 1. obtain the official SANS Find Evil! sample (Standard Forensic Case)
#    -> Rocba-Memory.zip ; unzip + un-7z to Rocba-Memory.raw
# 2. carve real indicators (corruption-tolerant; works even on a damaged image)
bulk_extractor -x all -e net -e email -o be_out/run1 Rocba-Memory.raw
# 3. drive the LIVE pipeline on the carved real indicators
python scripts/real_data_carve_run.py --be-dir be_out/run1 \
    --export docs/hackathon/execution-logs/rocba_carve_run.json
# 4. confirm the new signed findings chain-verify
findevil verify
```

Inspect any MCP tool directly:

```bash
python scripts/mcp_probe.py volatility.version yara.version bulk_extractor.version
python scripts/mcp_read_resource.py bb://ledger/tip
python scripts/mcp_read_resource.py bb://cti/diamond
```

---

## Option D — One-click installer

Download the launcher for your OS from the
[GitHub Releases page](https://github.com/Shaugato/find-evil/releases). It checks
for Docker, pulls/builds the Compose stack, handles the model download with
consent, generates signing keys, and opens the dashboard. See the release notes
for the exact tier built and per-OS instructions.

---

## Option E — Connect any MCP client (Claude Desktop / Claude Code / OpenClaw / Cursor / Cline / Aider)

This is **Approach #2** in the judge's own client: connect a standard MCP client to
Stigmergy's custom server and confirm the **typed forensic tool catalog** appears —
and that there is **no `execute_shell`/arbitrary command**. The guardrail is
architectural (the server only exposes typed functions), visible live in your client.

**Prereqs.** Clone the repo and install it into a venv so the server is importable:
```bash
git clone https://github.com/Shaugato/find-evil.git && cd find-evil
python -m venv .venv && . .venv/bin/activate     # WSL2 / Linux / macOS
pip install -e .
```
Tool **discovery** works with just this. Tool **invocation** of live blackboard
resources needs the stack up (Option B/C); the forensic tools operate on the
sample/official case data per [dataset.md](dataset.md). No keys of ours are required.

Two transports are supported (same single tool catalog, same guardrail):
- **stdio** — the client spawns the server. Simplest for "clone and connect".
  `python -m findevil.mcp_server`  (equivalently `findevil mcp --stdio`)
- **streamable-http** — connect to the already-running service by URL.
  `http://127.0.0.1:9310/mcp`  (started by `findevil mcp`, Docker, or systemd)

### Claude Code
```bash
# stdio (recommended) — everything after `--` is the command Claude Code runs:
claude mcp add stigmergy -- "$(pwd)/.venv/bin/python" -m findevil.mcp_server

# …or connect to the running HTTP service by URL:
claude mcp add --transport http stigmergy http://127.0.0.1:9310/mcp

# confirm it connected and list the tools:
claude mcp get stigmergy
```
Project-scoped form (checked-in `.mcp.json` at the repo root):
```json
{
  "mcpServers": {
    "stigmergy": {
      "command": "${CLAUDE_PROJECT_DIR:-.}/.venv/bin/python",
      "args": ["-m", "findevil.mcp_server"]
    }
  }
}
```

### Claude Desktop
Edit `claude_desktop_config.json` (macOS: `~/Library/Application Support/Claude/`;
Windows: `%APPDATA%\Claude\`), then fully restart Claude Desktop:
```json
{
  "mcpServers": {
    "stigmergy": {
      "command": "/ABSOLUTE/PATH/TO/find-evil/.venv/bin/python",
      "args": ["-m", "findevil.mcp_server"]
    }
  }
}
```
> Use an **absolute** interpreter path (Claude Desktop does not inherit your shell
> `PATH`/venv). On Windows point `command` at the venv's `python.exe`. To use the
> remote HTTP service instead, add it as a **custom connector** (Settings →
> Connectors → Add) with URL `http://127.0.0.1:9310/mcp`, or bridge with
> `npx mcp-remote http://127.0.0.1:9310/mcp` as the stdio `command`.

### OpenClaw
OpenClaw nests servers under `mcp.servers` in `~/.openclaw/openclaw.json` (then
restart the gateway), or use `openclaw mcp add`:
```bash
# stdio:
openclaw mcp add stigmergy --command /ABSOLUTE/PATH/find-evil/.venv/bin/python \
  --arg -m --arg findevil.mcp_server
# …or the running HTTP service:
openclaw mcp add stigmergy --url http://127.0.0.1:9310/mcp --transport streamable-http
```
Equivalent `openclaw.json`:
```json
{
  "mcp": {
    "servers": {
      "stigmergy": {
        "command": "/ABSOLUTE/PATH/find-evil/.venv/bin/python",
        "args": ["-m", "findevil.mcp_server"]
      }
    }
  }
}
```
(For the HTTP form: `{ "url": "http://127.0.0.1:9310/mcp", "transport": "streamable-http" }`.)

### Generic MCP client (Cursor / Cline / Aider / others)
Most clients use the standard top-level `mcpServers` block — `command`+`args` for
stdio, or for HTTP:
```json
{ "mcpServers": { "stigmergy": { "type": "http", "url": "http://127.0.0.1:9310/mcp" } } }
```
(`type` accepts `streamable-http` as an alias for `http`. Cursor: Settings → MCP →
Add; Cline: the `cline_mcp_settings.json` `mcpServers` block; Aider: `--mcp-server`
/ its MCP config — all accept this same shape.)

### What you should see (verified)
- The client lists the **full typed catalog — ~64 tools** (the 62 forensic/response
  actuators plus a couple of server-native control tools): e.g. `volatility.pslist`,
  `volatility.malfind`, `yara.scan`, `bulk_extractor.scan`, `tshark.summary`,
  `tsk.fls`, `plaso.extract`, alongside bounded response tools (`edr.network_isolate`,
  `iam.disable_account`).
- **No `execute_shell`, no arbitrary-command tool** — the architectural guardrail.
- Try a safe call: ask the client to run **`ledger.tip`** → returns a structured
  `{ "ok": true, "tip": { "seq": …, "entry_hash": … } }`, or **`volatility.version`**.

### Troubleshooting
- **No tools / handshake fails:** make sure `command` is the **venv** interpreter
  (absolute path) and the package is installed (`pip install -e .`). The stdio server
  keeps `stdout` for JSON-RPC and logs to `stderr` — a stray stdout print breaks it;
  use the provided entry point, don't wrap it in a shell that echoes.
- **HTTP `url` refused:** start the service (`findevil mcp` / Docker / systemd) and
  confirm `ss -tlnp | grep 9310`; the path is `/mcp`.
- **WSL2:** run all of this in the **Ubuntu/WSL** shell, not PowerShell.

---

## What a judge should see

1. `findevil verify` → `ok=true, tainted_seqs=[]` — the ledger is intact.
2. The dashboard's six panes updating live (pheromone graph, agent swim-lanes,
   blackboard diff feed, ledger, MITRE matrix, CACAO queue).
3. New ledger entries appearing from **real** carved ROCBA indicators.
4. A **self-correction**: a Yager conflict on a real IP, resolved by the
   prosecutor/defense/judge narrator — preserved in
   [execution-logs/](execution-logs/).
5. **From your own MCP client** (Option E): the typed Stigmergy tool catalog
   (~64 tools, no `execute_shell`) and a working `ledger.tip` / `volatility.version`
   call — the Approach #2 architectural guardrail, demonstrated in the judge's client.
