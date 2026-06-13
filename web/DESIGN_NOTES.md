# Stigmergy companion site — design notes

## Research → decision (Sections 10 Stage 1–3)

**Stage 1 — landscape.** The reference target was premium interactive/3D sites
(Leonardo AI as the anchor; Awwwards/FWA-class WebGL showcases). The recurring
ingredients that make those feel premium-not-gimmicky: a single strong moving
*concept* in the hero (not decoration), dark high-contrast palette, restrained
type, scroll-driven reveals, and motion that *represents the product's idea*
rather than generic particles. Technically they split into: Three.js / React
Three Fiber scenes, Spline embeds, raw WebGL/GLSL shaders, and 2D motion via
GSAP / Framer Motion + `<canvas>`.

**Stage 2 — Stigmergy's raw material.** The platform's most *visual* concept is
the **stigmergic pheromone field**: a live, evolving graph of artifacts (IPs,
domains, processes, hashes) whose suspicion (`belief_evil`) rises and decays as
sensors deposit evidence. That maps directly to a force-directed particle
network where node glow = belief and edges = sensor correlations. Secondary
motifs: the BLAKE3/Ed25519 hash-chain ledger (a literal chain), and the
prosecutor/defense/judge debate.

**Stage 3 — decision.** Build with **Next.js (App Router) + Tailwind +
Framer Motion**, and render the hero pheromone field with a **hand-written 2D
`<canvas>` force-directed network** rather than React Three Fiber.

Why 2D canvas over R3F here:
- The visual concept (a glowing 2D node graph) does not need real 3D depth; a
  canvas network is the honest representation and looks premium.
- It is **deterministic and debuggable without a browser in the loop** — this
  build happened in a headless agent environment where a single R3F
  camera/shader bug would silently yield a blank canvas with no way to see it.
  A canvas 2D scene I can reason about line-by-line is the lower-risk path to a
  *working* premium result, which the time-box prioritises over maximal 3D.
- It's GPU-cheap and battery-friendly, so it won't jank on a judge's laptop.

This lands at **Tier 1 of the 2D path** in the project plan's fallback ladder
(full researched 2D design + replay viewer), which the plan explicitly rates as
"still strong."

## What's built

- Animated pheromone-field hero (canvas), reacting to scroll.
- Architecture explainer with the architectural-vs-prompt guardrail split.
- **Replay viewer**: a timeline scrubber that plays the real ROCBA run from
  exported ledger JSON, syncing a pheromone graph + ledger feed + MITRE matrix,
  with the Yager-conflict self-correction marked on the timeline.
- Download / local-setup CTA linking to the repo, Docker stack, and installer.
- Demo-video placeholder slot.

## Stack

`next@14` (App Router), `react@18`, `tailwindcss@3`, `framer-motion`. No heavy
3D dependency. Deployed on Vercel with root directory `web/`.
