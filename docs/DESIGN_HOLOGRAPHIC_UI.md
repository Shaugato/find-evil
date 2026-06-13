# FIND EVIL — Holographic Command Interface: Design Decision

**Date:** 2026-06-13
**Scope:** Redesign the operator dashboard so the 3-D pheromone field *is* the
viewport — a living molecular/atomic intelligence — with the functional UI
floating over it as holographic glass overlays. Carry the language to the
companion website.

---

## Research summary

### Phase 3 — codebase (what we're building on)

- The dashboard is a **single static `find-evil.html` + `find-evil-live.js`**,
  served by FastAPI at `/` (read fresh per request). **No JS framework.**
- Boot order: `find-evil.html` (classic script) defines `initApp`,
  `initPheromoneCanvas`, `IOC_DEFS`, `state`, and the render fns. `find-evil-live.js`
  (classic, loaded after) **reassigns** `initApp` and captures the original
  render fns into a `design` object, then the async boot animation calls the
  *live* `initApp`, which calls `design.initPheromoneCanvas()` and the render fns.
- Live data contract: `/api/pher/snapshot` → `{nodes:[{pher_key, kind, tau,
  bel_evil, sensor}]}`. `find-evil-live.js` normalises these into `IOC_DEFS`
  (`{key, type, value, tau, bel, pl, k, sensor, severity}`) and refreshes every
  5 s, dispatching a `resize` event. SSE streams (`/stream/consensus|pher|ledger|
  fractal|mitigation`) push live updates; `window.fireConsensusRipple(color)` is
  the decision-fired hook.
- **No explicit edges exist** in the data. Bonds are *derived* from shared
  sensors (stigmergic correlation) — semantically correct: "bonds = sensor
  correlations between artifacts."

### Phase 1 / 2 — engine options evaluated

| Option | Verdict |
|---|---|
| **Full React/R3F SPA rewrite** | Rejected. Would require re-implementing the entire proven SSE/REST live layer + all six panels in React + a new build pipeline, 2 days from deadline. High risk to a working system for zero *visual* gain — the look is framework-independent. |
| **`3d-force-graph` (vasturiano) UMD** | Considered (the brief's suggested lib). Real strengths: built-in 3-D force layout + directional link particles + controls. But: modern three.js is **ESM-only** (UMD dropped), the official bloom path pulls three from a **CDN/esm.sh** (not air-gap safe), and custom glow sprites + bespoke effects (Yager split, CACAO ring, shockwave) need a **second three instance** → fragile cross-instance bugs I cannot debug headless. Every effect in the spec is custom, so the library's free layout/particles save little against that cost. |
| **Raw three.js, vendored as a single official ESM file** ✅ | **Chosen.** One self-contained `three.module.js` + `OrbitControls.js`, vendored locally (air-gap clean, MIT). One shared three instance → custom glowing sprites, line edges, particle flows, and all event effects use the same renderer with zero cross-instance risk. Full pixel control to match the spec exactly. A lightweight 3-D force layout (O(n²) charge repulsion + spring attraction) is trivial for ≤200 nodes at 60 fps. Verifiable headless via the preview tool (WebGL + pixel sampling). |

## Decision

**Raw three.js (vendored ESM, single instance) drives a full-viewport 3-D
molecular graph; the existing panels become floating holographic-glass
overlays. The FastAPI backend, SSE/REST endpoints, and `find-evil-live.js`
data layer are untouched.**

### Integration design (no live-layer changes)

- New ESM engine `static/fe-holo.js` (`<script type="module">`, three via
  `<script type="importmap">`). It registers `window.__FE_GRAPH = {boot, sync}`
  and overrides `window.fireConsensusRipple`.
- `initPheromoneCanvas()` in `find-evil.html` becomes a **thin delegator**:
  it flags intent and calls `window.__FE_GRAPH.boot()` (guarded for load order).
  Name preserved, so `design.initPheromoneCanvas()` in the live layer still works.
- The engine reads `window.IOC_DEFS` and **incrementally syncs** on each `resize`
  (already dispatched every 5 s by the live layer) — adding new artifacts
  (materialise burst), updating tau/belief, removing stale ones, **preserving
  node positions/velocities** so the field stays alive and continuous.
- Every element ID the live layer writes to is preserved; panels are only
  *restyled and repositioned* as glass overlays.

### Visual mapping (domain → scene)

| Domain | Visual |
|---|---|
| artifact (IP/domain/proc/hash) | glowing additive sprite "atom", size ∝ `tau` |
| `belief_evil` | colour: cyan → amber → orange-red → red |
| sensor correlation | glowing line "bond"; colour inherits higher-threat end |
| evidence deposit | particles streaming along bonds toward the artifact |
| consensus fired | spherical shockwave ripple (`fireConsensusRipple`) |
| Yager conflict (`K≥0.3`) | two-tone oscillating split + jittering bonds |
| CACAO containment | geometric ring contracts and locks around the atom |
| idle | whole structure precesses slowly; drag-to-orbit (OrbitControls) |

### Glow without post-processing

Additive-blended radial sprite halos on a near-black background (`#060a10`)
read as bloom without an `EffectComposer` — keeping the vendor surface to two
MIT files and avoiding the air-gap / dual-instance pitfalls of `UnrealBloomPass`.
(A real bloom pass can be layered later if desired.)

## Non-negotiables honoured

- Backend / SSE / REST / ledger unchanged; all data is real (no mock values).
- Air-gap capable (libraries vendored locally, no CDN at runtime).
- `Find Evil UI design/` untouched.
- `findevil verify` stays `ok=true`; test suite must not regress.
