# Stigmergy — Try It Out (Deliverable 7)

Three ways to evaluate Stigmergy, fastest first.

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

## What a judge should see

1. `findevil verify` → `ok=true, tainted_seqs=[]` — the ledger is intact.
2. The dashboard's six panes updating live (pheromone graph, agent swim-lanes,
   blackboard diff feed, ledger, MITRE matrix, CACAO queue).
3. New ledger entries appearing from **real** carved ROCBA indicators.
4. A **self-correction**: a Yager conflict on a real IP, resolved by the
   prosecutor/defense/judge narrator — preserved in
   [execution-logs/](execution-logs/).
