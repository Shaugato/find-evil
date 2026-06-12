# FIND EVIL — companion website (`web/`)

A zero-backend Next.js site that explains the FIND EVIL architecture and
**replays the real ROCBA run** from exported ledger JSON. It does **not** host
the backend (Valkey/NATS/SQLite/local-LLM are incompatible with serverless) —
it's a static explainer + client-side replay viewer.

See [DESIGN_NOTES.md](DESIGN_NOTES.md) for the research → design decision.

## Develop

```bash
cd web
npm install
npm run dev      # http://localhost:3000
```

## The replay data

The replay viewer reads `public/data/rocba_run.json`. A placeholder ships in the
repo; the **real** run overwrites it:

```bash
# from the repo root, with the live platform running
python scripts/real_data_carve_run.py --be-dir <bulk_extractor output> \
    --export docs/hackathon/execution-logs/rocba_carve_run.json \
    --replay-out web/public/data/rocba_run.json
```

## Deploy (Vercel)

Root directory = `web/`.

```bash
cd web
vercel link
vercel --prod
# auto-deploy on push:
vercel git connect
```

## Stack

Next.js 14 (App Router) · React 18 · Tailwind · Framer Motion. The pheromone
hero is a hand-written 2D `<canvas>` network (no heavy 3D dependency) — see
DESIGN_NOTES for why.
