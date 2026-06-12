# FIND EVIL

FIND EVIL is a local-first autonomous Security Operations Center platform for
defensive detection, evidence fusion, and safe-mode response automation. It
ingests synthetic or owned telemetry, correlates evidence with deterministic
Dempster-Shafer fusion, records every decision in a cryptographically verified
ledger, and can emit CACAO, STIX, and OCSF artifacts for interoperability.

The hot path is deterministic and does not depend on an LLM. LLM-backed narrator
and fractal pivot agents run out of band after the mathematical decision has
already been written to the ledger.

> **License:** MIT (see [LICENSE](LICENSE)).

## SANS "Find Evil!" Hackathon

This repository is a Find Evil! submission built as a **Custom MCP Server
(Approach #2)**: 60 typed, schema-validated MCP tools with reference-resolved
exhibit IDs and server-side output parsing — there is no `execute_shell_cmd`, so
the agent cannot run arbitrary commands. **Math decides, the ledger records, the
LLM only explains.**

The eight required deliverables live under [`docs/hackathon/`](docs/hackathon):

| # | Deliverable | Location |
|---|---|---|
| 1 | Code repository (MIT) | this repo |
| 2 | Demo video script | [demo-video-script.md](docs/hackathon/demo-video-script.md) |
| 3 | Architecture diagram | [architecture-diagram.md](docs/hackathon/architecture-diagram.md) |
| 4 | Project description | [project-description.md](docs/hackathon/project-description.md) |
| 5 | Dataset documentation | [dataset.md](docs/hackathon/dataset.md) |
| 6 | Accuracy report | [accuracy-report.md](docs/hackathon/accuracy-report.md) |
| 7 | Try-it-out instructions | [try-it-out.md](docs/hackathon/try-it-out.md) · [Docker](deploy/README.md) · [installer](installer/README.md) |
| 8 | Agent execution logs | [execution-logs/](docs/hackathon/execution-logs) |

Fastest paths to evaluate: the **Docker stack** (`deploy/`, one command), the
**one-click launcher** (`installer/`), or the companion **website** (live URL in
the deliverables once deployed).

## What This Repository Contains

- Python package under `src/findevil`
- Systemd unit files and service configs under `etc/`
- Bootstrap, key generation, validation, and utility scripts under `scripts/`
- Unit, integration, benchmark, and contract tests under `tests/`
- Public product documentation:
  - `README.md` for setup and daily usage
  - `PLATFORM.md` for architecture and subsystem behavior
  - `VALIDATION_REPORT.md` for the current validation evidence

This public repository intentionally excludes local runtime data, private keys,
model files, forensic evidence, extracted research drafts, rendered analysis
artifacts, and workstation-specific UI design sources.

## Safety Scope

FIND EVIL is defensive infrastructure. The validation harness uses locally
generated JSON telemetry published to local NATS/Valkey services. It does not
require real malware, exploit traffic, or unauthorized access to any external
system.

## Requirements

- Ubuntu 24.04 on WSL2 or bare-metal Linux
- Python 3.12
- Valkey
- NATS
- OpenTelemetry Collector
- Optional but recommended forensic tools:
  - YARA
  - Zeek
  - TShark
  - Sleuth Kit
  - Volatility 3
  - Plaso
  - bulk_extractor
- Optional local inference server:
  - `llama-cpp-python` serving an OpenAI-compatible API on `127.0.0.1:8080`

## Quick Start

Clone the repository into the expected runtime location:

```bash
sudo install -d -m 0755 -o "$USER" -g "$USER" /opt/findevil
git clone https://github.com/<your-user>/<your-repo>.git /opt/findevil/repo
cd /opt/findevil/repo
```

Run the bootstrap script:

```bash
bash scripts/bootstrap.sh
```

Create or review the environment file:

```bash
sudo install -d -m 0750 -o findevil -g findevil /opt/findevil/etc
sudo cp -n etc/.env.example /opt/findevil/etc/.env
sudoedit /opt/findevil/etc/.env
```

Install and start the service units:

```bash
sudo cp etc/systemd/*.service etc/systemd/*.timer etc/systemd/*.target /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now findevil.target
```

Verify the platform:

```bash
/opt/findevil/venv/bin/findevil verify
/opt/findevil/venv/bin/findevil status
/opt/findevil/venv/bin/findevil tip
```

Run the test suite:

```bash
cd /opt/findevil/repo
/opt/findevil/venv/bin/python -m pytest tests/ -q
```

## Main Services

| Service | Purpose |
|---|---|
| `findevil-ingest` / `findevil-bytewax` | NATS/ZMQ telemetry ingest, parsing, D-S fusion, threshold evaluation |
| `findevil-cacao` | Safe-mode CACAO playbook generation and execution logging |
| `findevil-mcp` | MCP blackboard resources and forensic tool shims |
| `findevil-narrator` | Out-of-band prosecutor/defense/judge explanation path |
| `findevil-watcher` | Fractal pivot agent watcher with depth/width budgets |
| `findevil-dashboard` | FastAPI dashboard and live SSE views |
| `findevil-verify.timer` | Scheduled ledger chain verification |
| `findevil-otel` | OpenTelemetry collector |

## Useful Commands

```bash
findevil verify
findevil tip
findevil recent -n 20
findevil list-tools
findevil ingest
findevil cacao
findevil mcp
findevil narrator
findevil watcher
findevil dashboard
```

Run the public validation harness:

```bash
/opt/findevil/venv/bin/python scripts/whitehat_validation.py
findevil verify
```

## Dashboard

When `findevil-dashboard.service` is running, open:

```text
http://127.0.0.1:9400/
```

Key endpoints:

```text
/api/health
/api/pheromones
/api/ledger/tip
/api/cacao/recent
/sse/pheromones
```

## Documentation

- `PLATFORM.md` explains how the platform is assembled.
- `VALIDATION_REPORT.md` records the current validation status and known gaps.
- `docs/runbook.md` contains operational notes.

## Public Release Notes

Do not commit:

- `/opt/findevil/data/ledger/*.sqlite*`
- `/opt/findevil/etc/keys/*`
- `/opt/findevil/data/models/*`
- forensic evidence, generated captures, private logs, or local screenshots
- private research drafts or extracted document artifacts

The repository is intended to publish the product implementation and reproducible
validation workflow, not local evidence, credentials, model weights, or private
workstation artifacts.
