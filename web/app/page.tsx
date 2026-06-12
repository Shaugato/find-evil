import PheromoneField from "@/components/PheromoneField";
import ReplaySection from "@/components/ReplaySection";
import Reveal from "@/components/Reveal";

const REPO = "https://github.com/Shaugato/find-evil";

export default function Home() {
  return (
    <main className="relative">
      {/* ───────────────────────── hero ───────────────────────── */}
      <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden grid-faint">
        <PheromoneField />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-ink" />
        <div className="relative z-10 mx-auto max-w-4xl px-6 text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-edge bg-panel/60 px-3 py-1 text-xs text-muted backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-good" />
            SANS Find Evil! — Custom MCP Server (Approach #2)
          </div>
          <h1 className="text-5xl font-bold leading-tight tracking-tight sm:text-7xl">
            FIND <span className="text-gradient">EVIL</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-gray-300 sm:text-xl">
            Autonomous DFIR at machine speed.{" "}
            <span className="text-white">Math decides</span>, a signed ledger
            records, and the LLM <span className="text-white">only explains</span>{" "}
            — so a hallucination can never cause a wrong decision or forge an
            evidence trail.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <a
              href="#replay"
              className="rounded-lg bg-cyan/90 px-5 py-2.5 font-medium text-ink shadow-glow transition hover:bg-cyan"
            >
              Watch the real run ▶
            </a>
            <a
              href={REPO}
              className="rounded-lg border border-edge bg-panel/60 px-5 py-2.5 font-medium text-gray-200 backdrop-blur transition hover:border-cyan"
            >
              View on GitHub
            </a>
          </div>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-x-8 gap-y-2 text-sm text-muted">
            <span><span className="text-good mono">0.567ms</span> hot-path p50</span>
            <span><span className="text-good mono">87</span> tests passing</span>
            <span><span className="text-good mono">BLAKE3+Ed25519</span> ledger</span>
            <span><span className="text-good mono">60</span> typed MCP tools</span>
          </div>
        </div>
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 text-xs text-muted">
          scroll ↓
        </div>
      </section>

      {/* ───────────────────────── thesis ───────────────────────── */}
      <section className="mx-auto max-w-6xl px-6 py-24">
        <Reveal>
          <h2 className="text-center text-3xl font-bold sm:text-4xl">
            The agent can&apos;t hallucinate its way into a wrong decision
          </h2>
          <p className="mx-auto mt-4 max-w-3xl text-center text-gray-400">
            Connecting an LLM to 200 forensic tools makes it fast — and makes it
            hallucinate. FIND EVIL fixes that <em>architecturally</em>, not with
            prompts. Three planes, one rule: the model is never in the decision
            path.
          </p>
        </Reveal>
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {[
            {
              t: "Hot path — deterministic",
              c: "#46c6ff",
              d: "Sensors deposit Dempster–Shafer evidence on a pheromone field. Belief / Plausibility / conflict_K decide observe · mitigate · conflict · escalate. No LLM. p50 0.567ms.",
            },
            {
              t: "Forensic ledger — provable",
              c: "#34e2b0",
              d: "Every decision: UUIDv7 + BLAKE3 hash chain + Ed25519 signature, Merkle-batched to Sigstore Rekor. One command re-verifies the whole chain.",
            },
            {
              t: "Reasoning plane — off the hot path",
              c: "#ff3b5c",
              d: "Fractal pivot agents and a prosecutor/defense/judge narrator explain findings after the ledger entry exists. Citations are validated; output is schema-constrained.",
            },
          ].map((x, i) => (
            <Reveal key={x.t} delay={i * 0.08}>
              <div className="h-full rounded-2xl border border-edge bg-panel/60 p-6">
                <div
                  className="mb-3 h-1 w-10 rounded-full"
                  style={{ background: x.c }}
                />
                <h3 className="text-lg font-semibold">{x.t}</h3>
                <p className="mt-2 text-sm text-gray-400">{x.d}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ───────────────────────── guardrails ───────────────────────── */}
      <section className="border-y border-edge bg-panel/30">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <Reveal>
            <h2 className="text-3xl font-bold sm:text-4xl">
              Architectural guardrails, not prompt guardrails
            </h2>
            <p className="mt-3 max-w-3xl text-gray-400">
              The difference the brief asks for. If every prompt-based control
              failed at once, FIND EVIL would still emit a correct, signed,
              tamper-evident decision.
            </p>
          </Reveal>
          <div className="mt-10 grid gap-6 lg:grid-cols-2">
            <Reveal>
              <div className="rounded-2xl border border-good/30 bg-good/5 p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-good">
                  ◆ Architectural — cannot be prompted away
                </h3>
                <ul className="space-y-3 text-sm text-gray-300">
                  {[
                    "Typed MCP tools only — no execute_shell_cmd exists",
                    "Reference-resolved exhibit IDs, not free-form paths",
                    "LLM excluded from the decision path entirely",
                    "outlines/xgrammar FSM-constrained JSON output",
                    "BLAKE3 + Ed25519 ledger; tampering breaks verify",
                    "Fabricated citations rejected before the ledger",
                  ].map((x) => (
                    <li key={x} className="flex gap-2">
                      <span className="text-good">✓</span>
                      {x}
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
            <Reveal delay={0.08}>
              <div className="rounded-2xl border border-edge bg-ink/40 p-6">
                <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-muted">
                  ○ Prompt-based — defense in depth only
                </h3>
                <ul className="space-y-3 text-sm text-gray-400">
                  {[
                    "Narrator role instructions (prosecutor/defense/judge)",
                    "Zheng-2023 position-swap to reduce ordering bias",
                    "System-prompt scope limits for pivot agents",
                  ].map((x) => (
                    <li key={x} className="flex gap-2">
                      <span className="text-muted">•</span>
                      {x}
                    </li>
                  ))}
                </ul>
                <p className="mt-6 text-xs text-muted">
                  These improve explanation quality. They are not relied on for
                  evidence integrity.
                </p>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* ───────────────────────── replay ───────────────────────── */}
      <section id="replay" className="mx-auto max-w-6xl px-6 py-24">
        <Reveal>
          <h2 className="text-3xl font-bold sm:text-4xl">
            Replay: the real ROCBA run
          </h2>
          <p className="mt-3 max-w-3xl text-gray-400">
            Real indicators carved from the official SANS Find Evil! memory image,
            driven through the live pipeline into the signed ledger. Scrub the
            timeline; the amber marker is the self-correction — a Yager conflict
            the system refused to auto-mitigate.
          </p>
        </Reveal>
        <div className="mt-8">
          <ReplaySection />
        </div>
      </section>

      {/* ───────────────────────── demo video ───────────────────────── */}
      <section className="mx-auto max-w-5xl px-6 pb-24">
        <Reveal>
          <div className="rounded-2xl border border-edge bg-panel/50 p-2">
            <div className="flex aspect-video items-center justify-center rounded-xl border border-dashed border-edge bg-ink/60 text-center">
              <div>
                <div className="text-2xl">▶</div>
                <div className="mt-2 text-sm text-muted">
                  Demo video — embedded after recording
                </div>
              </div>
            </div>
          </div>
        </Reveal>
      </section>

      {/* ───────────────────────── get it ───────────────────────── */}
      <section className="border-t border-edge bg-panel/30">
        <div className="mx-auto max-w-6xl px-6 py-24">
          <Reveal>
            <h2 className="text-3xl font-bold sm:text-4xl">Run it yourself</h2>
            <p className="mt-3 max-w-3xl text-gray-400">
              Three paths. The site you&apos;re on needs no install; the others
              get the full stack on your machine.
            </p>
          </Reveal>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {[
              {
                t: "Docker Compose",
                d: "One command. valkey + nats + otel + the FIND EVIL services.",
                cmd: "docker compose up -d",
                href: `${REPO}/tree/main/deploy`,
                cta: "deploy/ →",
              },
              {
                t: "One-click launcher",
                d: "Double-click for Windows / macOS / Linux. Wraps the Docker stack.",
                cmd: "find-evil-windows.cmd",
                href: `${REPO}/releases`,
                cta: "Download →",
              },
              {
                t: "Native on SIFT",
                d: "Full fidelity on the SANS SIFT Workstation under systemd.",
                cmd: "bash scripts/bootstrap.sh",
                href: `${REPO}/blob/main/docs/hackathon/try-it-out.md`,
                cta: "Instructions →",
              },
            ].map((x, i) => (
              <Reveal key={x.t} delay={i * 0.08}>
                <a
                  href={x.href}
                  className="block h-full rounded-2xl border border-edge bg-ink/40 p-6 transition hover:border-cyan"
                >
                  <h3 className="text-lg font-semibold">{x.t}</h3>
                  <p className="mt-2 text-sm text-gray-400">{x.d}</p>
                  <code className="mono mt-4 block rounded bg-ink px-3 py-2 text-xs text-cyan">
                    {x.cmd}
                  </code>
                  <span className="mt-4 inline-block text-sm text-cyan">
                    {x.cta}
                  </span>
                </a>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-edge px-6 py-10 text-center text-sm text-muted">
        FIND EVIL — local, defensive DFIR. MIT licensed. No offensive tooling;
        validated on synthetic telemetry and legitimate sample forensic images.
        <div className="mt-2">
          <a href={REPO} className="text-cyan hover:underline">
            github.com/Shaugato/find-evil
          </a>
        </div>
      </footer>
    </main>
  );
}
