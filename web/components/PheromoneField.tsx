"use client";

import { useEffect, useRef } from "react";

/**
 * Stigmergic pheromone field — a live force-directed artifact network.
 * Nodes = artifacts (IP/domain/process/hash); node glow = belief_evil;
 * edges = sensor correlations. Pure 2D canvas, deterministic, GPU-cheap.
 */

type Kind = "ip" | "domain" | "proc" | "hash";

interface Node {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  kind: Kind;
  belief: number; // 0..1 suspicion
  target: number; // belief target (decays toward 0)
  pulse: number;
}

// Aligned to the live dashboard's holographic palette so the hero reads as a
// preview of the 3-D molecular field.
const KIND_COLORS: Record<Kind, string> = {
  ip: "0,212,255", // holographic cyan
  domain: "0,255,159", // phosphor green
  proc: "255,184,108", // warning amber
  hash: "108,198,255", // blue
};

export default function PheromoneField({
  density = 1,
  interactive = true,
}: {
  density?: number;
  interactive?: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouse = useRef({ x: -9999, y: -9999 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    let w = 0;
    let h = 0;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    const nodes: Node[] = [];
    const kinds: Kind[] = ["ip", "domain", "proc", "hash"];

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const build = () => {
      nodes.length = 0;
      const count = Math.round(
        Math.max(28, Math.min(90, (w * h) / 16000)) * density,
      );
      for (let i = 0; i < count; i++) {
        nodes.push({
          x: Math.random() * w,
          y: Math.random() * h,
          vx: (Math.random() - 0.5) * 0.12,
          vy: (Math.random() - 0.5) * 0.12,
          r: 1.6 + Math.random() * 2.2,
          kind: kinds[(Math.random() * kinds.length) | 0],
          belief: 0,
          target: 0,
          pulse: Math.random() * Math.PI * 2,
        });
      }
    };

    resize();
    build();

    // Periodically "deposit evidence": a random node's suspicion spikes and
    // diffuses to nearby nodes — the stigmergic mechanic, visualised.
    const deposit = () => {
      if (!nodes.length) return;
      const n = nodes[(Math.random() * nodes.length) | 0];
      n.target = 0.65 + Math.random() * 0.35;
      n.pulse = 0;
    };
    const depositTimer = window.setInterval(deposit, 1100);

    const onMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouse.current.x = e.clientX - rect.left;
      mouse.current.y = e.clientY - rect.top;
    };
    const onLeave = () => {
      mouse.current.x = -9999;
      mouse.current.y = -9999;
    };
    if (interactive) {
      window.addEventListener("mousemove", onMove);
      canvas.addEventListener("mouseleave", onLeave);
    }
    const onResize = () => {
      resize();
      build();
    };
    window.addEventListener("resize", onResize);

    const LINK = 132;
    const draw = () => {
      ctx.clearRect(0, 0, w, h);

      // physics
      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < 0 || n.x > w) n.vx *= -1;
        if (n.y < 0 || n.y > h) n.vy *= -1;
        n.x = Math.max(0, Math.min(w, n.x));
        n.y = Math.max(0, Math.min(h, n.y));
        // belief eases toward target; target decays (pheromone evaporation)
        n.belief += (n.target - n.belief) * 0.04;
        n.target *= 0.992;
        n.pulse += 0.05;

        // light mouse repulsion for "interactive" feel
        if (interactive) {
          const dx = n.x - mouse.current.x;
          const dy = n.y - mouse.current.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < 120 * 120 && d2 > 1) {
            const f = (1 - Math.sqrt(d2) / 120) * 0.6;
            n.vx += (dx / Math.sqrt(d2)) * f * 0.05;
            n.vy += (dy / Math.sqrt(d2)) * f * 0.05;
          }
        }
        // velocity damping
        n.vx *= 0.995;
        n.vy *= 0.995;
      }

      // edges
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d = Math.hypot(dx, dy);
          if (d < LINK) {
            const heat = Math.max(a.belief, b.belief);
            const base = (1 - d / LINK) * 0.5;
            const r = Math.round(70 + heat * 185);
            const g = Math.round(140 - heat * 110);
            const bl = Math.round(200 - heat * 120);
            ctx.strokeStyle = `rgba(${r},${g},${bl},${base * (0.4 + heat)})`;
            ctx.lineWidth = 0.6 + heat * 1.2;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      // nodes
      for (const n of nodes) {
        const c = KIND_COLORS[n.kind];
        const glow = 0.25 + n.belief * 0.75;
        const rad = n.r + n.belief * 4 + (n.belief > 0.1 ? Math.sin(n.pulse) * n.belief * 1.5 : 0);
        // halo
        if (n.belief > 0.05) {
          const grd = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, rad * 6);
          grd.addColorStop(0, `rgba(255,56,100,${n.belief * 0.35})`);
          grd.addColorStop(1, "rgba(255,56,100,0)");
          ctx.fillStyle = grd;
          ctx.beginPath();
          ctx.arc(n.x, n.y, rad * 6, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.fillStyle = `rgba(${c},${glow})`;
        ctx.beginPath();
        ctx.arc(n.x, n.y, rad, 0, Math.PI * 2);
        ctx.fill();
      }

      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(raf);
      window.clearInterval(depositTimer);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("resize", onResize);
      canvas.removeEventListener("mouseleave", onLeave);
    };
  }, [density, interactive]);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 h-full w-full"
      aria-hidden
    />
  );
}
