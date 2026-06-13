# Stigmergy — Docker deployment

A judge-friendly Compose stack for Stigmergy. This is the foundation the
one-click installer wraps (see the repo's `installer/` and GitHub Releases).

## Quick start

```bash
cp .env.example .env
docker compose up -d
# dashboard:     http://localhost:9400
# MCP blackboard http://localhost:9310/mcp
docker compose logs -f findevil
```

Verify the ledger and run the synthetic validation (no external data needed):

```bash
docker compose exec findevil findevil verify
docker compose exec findevil python scripts/whitehat_validation.py
```

## With the LLM planes (narrator + pivot agents)

The deterministic hot path runs **without** any model. To also exercise the
prosecutor/defense/judge narrator and fractal pivots, enable the LLM — the
container downloads a ~2 GB GGUF on first start:

```bash
ENABLE_LLM=1 docker compose up -d
```

## Architecture notes

- **Infra containers:** `valkey` (pheromone field, keyspace events on), `nats`
  (JetStream), `otel` (metrics).
- **`findevil` container:** runs all Stigmergy Python services under
  `supervisord`. They are co-located because the hot path uses ZeroMQ `ipc://`
  sockets, which need a shared filesystem namespace. This is demo packaging —
  the native systemd deployment (see repo `etc/systemd/`) is the production
  topology.
- **Forensic tools:** the image installs `yara`, `tshark`, `sleuthkit`,
  `sqlite3`, and `volatility3`. Heavier tools (`zeek`, `bulk_extractor`,
  `plaso`) are optional; their MCP shims return a structured "binary missing"
  result rather than failing, so the platform runs without them. Build with
  `--build-arg INSTALL_HEAVY_TOOLS=1` to add them.

## Volumes

| Volume | Holds |
|---|---|
| `findevil-data` | ledger SQLite, models, tool cache |
| `findevil-keys` | Ed25519 signing keys (generated on first boot) |
| `valkey-data`   | Valkey AOF/RDB |

## Stop / reset

```bash
docker compose down            # stop, keep data
docker compose down -v         # stop and wipe volumes (fresh ledger next time)
```
