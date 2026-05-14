/* =====================================================================
   FIND EVIL — Ephemeral Agent Spawner
   ---------------------------------------------------------------------
   Visualizes the birth, labor, and death of fractal investigative agents.

   When a fractal.spawn event is observed, a frosted-glass panel "grows"
   outward from the targeted node's projected position. The panel
   continuously chases the projected node each frame, so the tether
   appears physically attached to the moving 3D node.

   The agent's reasoning is rendered with a streaming typewriter effect.
   When fractal.report arrives (or TTL expires), the panel doesn't simply
   vanish — it dissolves into a localized burst of fading particles,
   making compute-resource release legible at a glance.

   Public API:
     init(layerEl, swarm)   — pass DOM container + swarm module
     onSpawn(payload)       — fractal.spawn body
     onReport(payload)      — fractal.report body
     stepProjection()       — call every render tick to chase nodes
     activeCount()
   ===================================================================== */

const PANELS = new Map();         // spawn_id -> Panel
const MAX_PANELS = 24;
const TYPEWRITER_CHARS_PER_TICK = 2;
const TYPEWRITER_INTERVAL_MS = 24;

let _layer = null;
let _swarm = null;

class Panel {
  constructor(spawn_id, payload) {
    this.spawn_id = spawn_id;
    this.pher_key = payload.pher_key || payload.target_key || null;
    this.depth = payload.depth ?? 0;
    this.parent = payload.parent_id || payload.parent || null;
    this.startedAt = performance.now();
    this.terminated = false;
    this.dissolved = false;
    this.target = payload.target || payload.target_artifact || this.pher_key || '—';
    this.thoughtsBuffer = '';      // committed text already shown
    this.thoughtsQueue = [];        // pending chunks to type out
    this._typeIdx = 0;

    this.el = document.createElement('div');
    this.el.className = 'spawn-panel';
    this.el.setAttribute('data-spawn-id', spawn_id);
    this.el.innerHTML = `
      <header>
        <span class="agent-id">⌬ frac-${_short(spawn_id)}</span>
        <span class="depth-tag">d${this.depth}${this.parent ? ' · child' : ''}</span>
      </header>
      <div class="target">${_escape(this.target)}</div>
      <div class="thoughts"></div>
    `;
    this.thoughtsEl = this.el.querySelector('.thoughts');
    this.thoughtsEl.innerHTML = '<span class="caret"></span>';

    // Initial position — anchored, hidden until first projection step
    this.el.style.left = '-9999px';
    this.el.style.top  = '-9999px';

    _layer.appendChild(this.el);

    // Seed initial thought from the spawn prompt summary
    const seed = payload.prompt_summary || payload.prompt || payload.scope_question;
    if (seed) this.pushThought(seed);

    // Trigger growth after layout
    requestAnimationFrame(() => requestAnimationFrame(() => {
      this.el.classList.add('in');
    }));
  }

  pushThought(text) {
    if (!text) return;
    // Chunk by sensible boundaries to avoid one huge blob landing in one tick.
    const chunks = String(text).split(/(?<=[.!?])\s+|\n+/);
    for (const c of chunks) {
      if (c.trim()) this.thoughtsQueue.push(c.trim());
    }
  }

  _typewriterTick() {
    if (this.dissolved) return;
    if (this.thoughtsQueue.length === 0) return;

    const head = this.thoughtsQueue[0];
    const next = head.slice(this._typeIdx, this._typeIdx + TYPEWRITER_CHARS_PER_TICK);
    this._typeIdx += TYPEWRITER_CHARS_PER_TICK;
    this.thoughtsBuffer += next;
    this.thoughtsEl.innerHTML =
      _escape(this.thoughtsBuffer).replace(/\n/g, '<br>') +
      '<span class="caret"></span>';

    if (this._typeIdx >= head.length) {
      this.thoughtsQueue.shift();
      this._typeIdx = 0;
      this.thoughtsBuffer += ' ';
    }
  }

  setProjection(proj) {
    if (!proj || this.dissolved) return;
    if (!proj.visible) {
      // Off-screen — keep panel rendered but pinned to the nearest edge with tether shrunk.
      this.el.style.opacity = '0.18';
    } else {
      this.el.style.opacity = '';
    }
    // Anchor to the right of the node, with a small offset.
    const offset = (proj.radius || 1) * 18 + 30;
    const left = Math.min(window.innerWidth - 320, Math.max(20, proj.x + offset));
    const top  = Math.max(80, Math.min(window.innerHeight - 100, proj.y));
    this.el.style.left = `${left}px`;
    this.el.style.top  = `${top}px`;
  }

  markTerminated(payload) {
    this.terminated = true;
    this.el.classList.add('terminated');
    if (payload && payload.finding) {
      const f = payload.finding;
      const line = typeof f === 'string'
        ? f
        : (f.summary || f.claim || JSON.stringify(f).slice(0, 120));
      this.pushThought('▸ ' + line);
    } else if (payload && payload.terminated_by_ttl) {
      this.pushThought('▸ TTL expired — surrendering compute');
    } else {
      this.pushThought('▸ Reported');
    }
  }

  dissolve() {
    if (this.dissolved) return;
    this.dissolved = true;
    this.el.classList.add('dissolving');

    // Spawn dissolution particles at panel center
    const r = this.el.getBoundingClientRect();
    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;
    const count = 14 + Math.round(Math.random() * 6);
    for (let i = 0; i < count; i++) {
      const p = document.createElement('div');
      p.className = 'dissolve-particle';
      const angle = (Math.PI * 2) * (i / count) + Math.random() * 0.4;
      const dist = 26 + Math.random() * 32;
      p.style.left = `${cx}px`;
      p.style.top  = `${cy}px`;
      p.style.setProperty('--dx', `${Math.cos(angle) * dist}px`);
      p.style.setProperty('--dy', `${-Math.abs(Math.sin(angle) * dist) - 18}px`);
      if (this.terminated) {
        p.style.background = '#ff5d5d';
        p.style.boxShadow = '0 0 8px rgba(255,93,93,0.9)';
      }
      _layer.appendChild(p);
      setTimeout(() => p.remove(), 1000);
    }

    // After the dissolve transition completes, remove the DOM node.
    setTimeout(() => {
      this.el.remove();
      PANELS.delete(this.spawn_id);
    }, 760);
  }
}

// ---------------------------------------------------------------------
// Module API
// ---------------------------------------------------------------------

export function init(layerEl, swarm) {
  _layer = layerEl;
  _swarm = swarm;
  // Per-panel typewriter ticker
  setInterval(() => {
    for (const p of PANELS.values()) p._typewriterTick();
  }, TYPEWRITER_INTERVAL_MS);
}

export function onSpawn(payload) {
  if (!payload) return;
  const id = payload.spawn_id || payload.id;
  if (!id) return;
  if (PANELS.has(id)) {
    // Update of an existing spawn — append any streamed prompt text.
    const p = PANELS.get(id);
    if (payload.prompt_summary) p.pushThought(payload.prompt_summary);
    if (payload.thought) p.pushThought(payload.thought);
    return;
  }
  // Soft cap — evict the oldest non-terminated panel if we're at the ceiling
  if (PANELS.size >= MAX_PANELS) {
    let oldest = null, oldestT = Infinity;
    for (const p of PANELS.values()) {
      if (!p.terminated && p.startedAt < oldestT) {
        oldestT = p.startedAt; oldest = p;
      }
    }
    if (oldest) oldest.dissolve();
  }
  const panel = new Panel(id, payload);
  PANELS.set(id, panel);
}

export function onReport(payload) {
  if (!payload) return;
  const id = payload.spawn_id || payload.id;
  if (!id) return;
  const p = PANELS.get(id);
  if (!p) return;
  p.markTerminated(payload);
  // Hold the terminated state visible briefly so the operator can read the finding,
  // then dissolve.
  setTimeout(() => p.dissolve(), 1100);
}

export function stepProjection() {
  if (!_swarm) return;
  for (const p of PANELS.values()) {
    if (!p.pher_key) continue;
    const proj = _swarm.getNodeScreenPosition(p.pher_key);
    p.setProjection(proj);
  }
}

export function activeCount() {
  let active = 0;
  for (const p of PANELS.values()) if (!p.terminated && !p.dissolved) active++;
  return active;
}

// ---------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------

function _short(s) {
  return String(s || '').replace(/[^a-zA-Z0-9]/g, '').slice(0, 6);
}

function _escape(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
