"use client";

import { useEffect, useMemo, useRef, useState } from "react";

/**
 * Replay viewer — plays the real ROCBA run from exported ledger JSON, syncing a
 * pheromone graph + ledger feed + MITRE matrix. The Yager-conflict
 * self-correction is marked on the timeline.
 */

interface Frame {
  seq: number;
  finding_id?: string;
  agent_id?: string;
  artifact?: string;
  severity?: string;
  mitre?: string[];
  claim?: string;
  belief?: number;
  conflict_K?: number;
  action?: string;
  ts_ns?: number;
  self_correction?: boolean;
}

interface RunData {
  dataset: string;
  tool: string;
  frames: Frame[];
}

const SEV_COLOR: Record<string, string> = {
  CRITICAL: "#ff3b5c",
  HIGH: "#ff3b5c",
  MEDIUM: "#ffb020",
  LOW: "#46c6ff",
  INFORMATIONAL: "#8a93a6",
};

const ATTCK = [
  "T1059.001",
  "T1003.001",
  "T1055",
  "T1071.001",
  "T1078",
  "T1547.001",
  "T1053.005",
  "T1562.001",
  "T1218.011",
  "T1569.002",
];

export default function ReplayViewer({ data }: { data: RunData }) {
  const frames = data.frames || [];
  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (playing) {
      timer.current = window.setInterval(() => {
        setIdx((i) => {
          if (i >= frames.length - 1) {
            setPlaying(false);
            return i;
          }
          return i + 1;
        });
      }, 700);
    }
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [playing, frames.length]);

  const visible = frames.slice(0, idx + 1);
  const current = frames[idx];

  const firedTechniques = useMemo(() => {
    const s = new Set<string>();
    visible.forEach((f) => (f.mitre || []).forEach((m) => s.add(m)));
    return s;
  }, [visible]);

  // pheromone nodes: one per distinct artifact, glowing by latest belief
  const nodes = useMemo(() => {
    const map = new Map<string, { belief: number; sev: string; conflict: boolean }>();
    visible.forEach((f) => {
      if (!f.artifact) return;
      map.set(f.artifact, {
        belief: f.belief ?? (f.severity === "MEDIUM" || f.severity === "HIGH" ? 0.7 : 0.4),
        sev: f.severity || "LOW",
        conflict: !!f.self_correction || (f.conflict_K ?? 0) > 0.3,
      });
    });
    return Array.from(map.entries()).slice(-24);
  }, [visible]);

  if (!frames.length) {
    return (
      <div className="rounded-xl border border-edge bg-panel p-8 text-center text-muted">
        Replay data not yet exported. Run{" "}
        <code className="mono text-cyan">scripts/real_data_carve_run.py</code> and
        copy <code className="mono">rocba_carve_run.json</code> into{" "}
        <code className="mono">web/public/data/</code>.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-edge bg-panel/80 p-5 shadow-glow backdrop-blur">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm text-muted">
          <span className="text-good">●</span> {data.dataset}
          <span className="mx-2 text-edge">|</span>
          <span className="mono text-cyan">{data.tool}</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              if (idx >= frames.length - 1) setIdx(0);
              setPlaying((p) => !p);
            }}
            className="rounded-md border border-edge bg-ink px-3 py-1 text-sm hover:border-cyan"
          >
            {playing ? "❚❚ Pause" : "▶ Play"}
          </button>
          <button
            onClick={() => {
              setPlaying(false);
              setIdx(0);
            }}
            className="rounded-md border border-edge bg-ink px-3 py-1 text-sm hover:border-cyan"
          >
            ↺ Reset
          </button>
        </div>
      </div>

      {/* timeline scrubber */}
      <div className="relative mb-5">
        <input
          type="range"
          min={0}
          max={Math.max(0, frames.length - 1)}
          value={idx}
          onChange={(e) => {
            setPlaying(false);
            setIdx(Number(e.target.value));
          }}
          className="w-full accent-cyan"
        />
        <div className="pointer-events-none absolute inset-x-0 top-0 h-full">
          {frames.map((f, i) =>
            f.self_correction ? (
              <div
                key={i}
                title="Yager conflict → re-investigation → resolved"
                className="absolute -top-1 h-4 w-0.5 bg-warn"
                style={{ left: `${(i / Math.max(1, frames.length - 1)) * 100}%` }}
              />
            ) : null,
          )}
        </div>
        <div className="mt-1 flex justify-between text-xs text-muted">
          <span>seq {frames[0]?.seq}</span>
          <span className="text-warn">▲ self-correction</span>
          <span>seq {frames[frames.length - 1]?.seq}</span>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {/* pheromone graph */}
        <div className="rounded-xl border border-edge bg-ink/60 p-3">
          <div className="mb-2 text-xs uppercase tracking-wider text-muted">
            Pheromone field
          </div>
          <div className="relative h-44 overflow-hidden rounded-lg">
            <svg viewBox="0 0 200 160" className="h-full w-full">
              {nodes.map((n, i) => {
                const angle = (i / nodes.length) * Math.PI * 2;
                const radius = 30 + (i % 4) * 16;
                const cx = 100 + Math.cos(angle) * radius;
                const cy = 80 + Math.sin(angle) * radius;
                const [name, info] = n;
                const color = info.conflict ? "#ffb020" : SEV_COLOR[info.sev] || "#46c6ff";
                return (
                  <g key={name}>
                    {i > 0 && (
                      <line
                        x1={100}
                        y1={80}
                        x2={cx}
                        y2={cy}
                        stroke={color}
                        strokeOpacity={0.18 + info.belief * 0.4}
                        strokeWidth={0.5 + info.belief}
                      />
                    )}
                    <circle
                      cx={cx}
                      cy={cy}
                      r={2 + info.belief * 5}
                      fill={color}
                      fillOpacity={0.35 + info.belief * 0.6}
                    >
                      {info.conflict && (
                        <animate
                          attributeName="r"
                          values={`${2 + info.belief * 5};${4 + info.belief * 6};${2 + info.belief * 5}`}
                          dur="1.1s"
                          repeatCount="indefinite"
                        />
                      )}
                    </circle>
                  </g>
                );
              })}
              <circle cx={100} cy={80} r={3} fill="#e6e9f0" fillOpacity={0.5} />
            </svg>
          </div>
          <div className="mt-1 text-xs text-muted">
            {nodes.length} live artifacts
          </div>
        </div>

        {/* ledger feed */}
        <div className="rounded-xl border border-edge bg-ink/60 p-3">
          <div className="mb-2 text-xs uppercase tracking-wider text-muted">
            Forensic ledger
          </div>
          <div className="h-44 space-y-1 overflow-y-auto pr-1 text-xs">
            {visible
              .slice()
              .reverse()
              .slice(0, 16)
              .map((f, i) => (
                <div
                  key={`${f.seq}-${i}`}
                  className={`flex items-start gap-2 rounded border-l-2 bg-panel/60 px-2 py-1 ${
                    f.self_correction ? "border-warn" : "border-edge"
                  }`}
                >
                  <span className="mono text-muted">#{f.seq}</span>
                  <span className="flex-1 truncate text-[11px]">
                    <span style={{ color: SEV_COLOR[f.severity || "LOW"] }}>
                      {f.agent_id}
                    </span>{" "}
                    <span className="text-muted">{f.claim}</span>
                  </span>
                </div>
              ))}
          </div>
        </div>

        {/* MITRE matrix */}
        <div className="rounded-xl border border-edge bg-ink/60 p-3">
          <div className="mb-2 text-xs uppercase tracking-wider text-muted">
            MITRE ATT&CK
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {ATTCK.map((t) => {
              const fired = firedTechniques.has(t);
              return (
                <div
                  key={t}
                  className={`mono rounded px-1.5 py-1 text-[10px] transition-colors ${
                    fired
                      ? "bg-evil/20 text-evil shadow-evilglow"
                      : "bg-panel/60 text-muted"
                  }`}
                >
                  {t}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* current finding detail */}
      {current && (
        <div
          className={`mt-4 rounded-xl border p-3 text-sm ${
            current.self_correction
              ? "border-warn bg-warn/5"
              : "border-edge bg-ink/50"
          }`}
        >
          {current.self_correction && (
            <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-warn">
              ⚠ Self-correction — Yager conflict detected → re-investigation → resolved
            </div>
          )}
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
            <span className="mono">seq #{current.seq}</span>
            <span className="mono text-cyan">{current.agent_id}</span>
            {current.artifact && (
              <span className="mono">{current.artifact}</span>
            )}
            {(current.mitre || []).map((m) => (
              <span key={m} className="rounded bg-evil/15 px-1.5 text-evil">
                {m}
              </span>
            ))}
          </div>
          <p className="mt-1 text-[13px] text-gray-200">{current.claim}</p>
        </div>
      )}
    </div>
  );
}
