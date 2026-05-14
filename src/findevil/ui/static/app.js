/* =====================================================================
   FIND EVIL — App Bootstrap
   ---------------------------------------------------------------------
   Single orchestrator that:
     1. Initializes the Three.js scene (swarm), DOM layers (spawner, HUD)
        and the Web Audio engine (gated behind a click).
     2. Bootstraps the swarm from /api/pher/snapshot.
     3. Opens five SSE streams and dispatches events:
          /stream/pher        -> swarm.updatePher
          /stream/consensus   -> swarm.onConsensusEvent + flashes + audio
          /stream/fractal     -> spawner.onSpawn / onReport
          /stream/mitigation  -> mitigation flash + audio
          /stream/ledger      -> hud.onLedgerEntry + ledger_lock audio
     4. Drives the render loop (requestAnimationFrame) calling swarm.step
        and spawner.stepProjection every frame.

   Each shadow channel envelope is { ts_ns, subject, payload } where
   payload is bytes — the FastAPI side already decoded msgspec on the wire,
   but the payload itself is still JSON-encoded bytes. We re-parse here.
   ===================================================================== */

import * as Swarm    from '/static/swarm.js';
import * as Spawner  from '/static/spawner.js';
import * as Hud      from '/static/hud.js';
import * as Audio    from '/static/audio.js';

const T = {
  nodes:   document.getElementById('t-nodes'),
  edges:   document.getElementById('t-edges'),
  spawns:  document.getElementById('t-spawns'),
  seq:     document.getElementById('t-seq'),
  K:       document.getElementById('t-k'),
  posture: document.getElementById('t-posture'),
  host:    document.getElementById('t-host'),
  clock:   document.getElementById('t-clock'),
};

let _lastConsensusAt = 0;
let _lastTipSeq = 0;

// =====================================================================
// Boot
// =====================================================================

(async function main() {
  // 1. Three.js
  const canvas = document.getElementById('swarm-canvas');
  Swarm.init(canvas);

  // 2. Spawner (DOM overlay) + HUD (right rail)
  Spawner.init(document.getElementById('spawn-layer'), Swarm);
  Hud.init(
    document.getElementById('hud-feed'),
    document.getElementById('hud-status'),
    { onSnap: () => Audio.ledger_lock() },
  );

  // 3. Audio toggle (gated behind a user gesture for autoplay policy)
  _wireAudioToggle();

  // 4. Tip / posture preload + clock
  _startClock();
  _refreshTip();
  setInterval(_refreshTip, 2500);

  // 5. Bootstrap pheromone field, then start streams
  await _bootstrapPher();
  _openStream('/stream/pher',       _onPherShadow);
  _openStream('/stream/consensus',  _onConsensusShadow);
  _openStream('/stream/fractal',    _onFractalShadow);
  _openStream('/stream/mitigation', _onMitigationShadow);
  _openStream('/stream/ledger',     _onLedgerEntry);

  // 6. Render loop
  function tick(now) {
    Swarm.step(now);
    Spawner.stepProjection();
    _updateTelemetry();
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
})().catch((e) => {
  console.error('[findevil] boot failed', e);
  Hud.setStatus('boot failed — check console');
});

// =====================================================================
// SSE plumbing
// =====================================================================

function _openStream(path, onMessage) {
  const es = new EventSource(path);
  es.onmessage = (ev) => {
    if (!ev || !ev.data) return;
    let env;
    try { env = JSON.parse(ev.data); }
    catch { return; }
    onMessage(env);
  };
  es.onerror = () => {
    // EventSource will retry automatically; just surface the state in HUD.
    Hud.setStatus(`reconnecting ${path}…`);
  };
  return es;
}

// Shadow-channel envelopes look like:
//   { ts_ns, subject, payload }
// payload is the inner msgspec.json-encoded bytes from the producer; the
// FastAPI shadow forwarder already decoded the OUTER envelope, but the
// inner payload is still a base64-string when serialized that way.
// In practice, msgspec emits payload as a list of ints (bytes) in JSON,
// or sometimes as a base64 string depending on encoder config. We try
// both shapes and fall back to using the envelope as-is.
function _decodePayload(env) {
  if (!env) return null;
  if (env.payload == null && env.subject == null) return env; // already raw
  const p = env.payload;
  try {
    if (typeof p === 'string') {
      // msgspec encodes bytes as base64 string by default in JSON
      const decoded = atob(p);
      return JSON.parse(decoded);
    }
    if (Array.isArray(p)) {
      const u8 = new Uint8Array(p);
      const txt = new TextDecoder().decode(u8);
      return JSON.parse(txt);
    }
    if (typeof p === 'object') return p;
  } catch (_) {}
  return env;
}

// =====================================================================
// Stream handlers
// =====================================================================

function _onPherShadow(env) {
  const body = _decodePayload(env);
  if (!body) return;
  // Pher deposit shape: { pher_key, kind?, tau, bel_evil?, sensor?, ts_ns? }
  Swarm.updatePher({
    pher_key: body.pher_key,
    kind:     body.kind || _kindFromKey(body.pher_key),
    tau:      Number(body.tau || body.new_tau || 0),
    bel_evil: Number(body.bel_evil ?? body.bel ?? body.belief_evil ?? 0),
  });
}

function _onConsensusShadow(env) {
  const body = _decodePayload(env);
  if (!body) return;

  const action = body.action || 'observe';
  const belief = Number(body.belief_evil ?? 0);
  const K      = Number(body.conflict_K  ?? body.K ?? 0);
  const pher   = body.pher_key;
  const kind   = body.kind || _kindFromKey(pher);
  const tau    = Number(body.tau ?? body.pheromone_tau ?? 0);

  // 1) Drive the swarm node
  Swarm.updatePher({ pher_key: pher, kind, tau, bel_evil: belief });
  Swarm.onConsensusEvent({ pher_key: pher, action, belief_evil: belief });

  // 2) Add edges across pher_keys mentioned in this frame's reports (if any)
  const otherKeys = [];
  if (Array.isArray(body.reports)) {
    for (const r of body.reports) {
      if (r && r.pher_key && r.pher_key !== pher) otherKeys.push(r.pher_key);
    }
  }
  if (otherKeys.length) Swarm.addEdgeFromConsensus([pher, ...otherKeys]);

  // 3) Telemetry
  T.K.textContent = K.toFixed(3);
  _setPosture(action);

  // 4) Visual flash for any non-observe consensus
  if (action !== 'observe') _flashOverlay('consensus-flash');

  // 5) Audio cue when a real action threshold lands
  if (action === 'mitigate' || (action === 'escalate_human' && belief > 0.55)) {
    // throttle so a burst of consensus events doesn't stack the sweep
    const now = performance.now();
    if (now - _lastConsensusAt > 700) {
      Audio.consensus_reached(action, belief);
      _lastConsensusAt = now;
    }
  }
}

function _onFractalShadow(env) {
  const body = _decodePayload(env);
  if (!body) return;
  // Spawn frame: { spawn_id, depth, parent_id?, pher_key?, target?, prompt_summary? }
  // Report frame: { spawn_id, finding?, terminated_by_ttl? }
  if (body.finding !== undefined || body.terminated_by_ttl) {
    Spawner.onReport(body);
    Audio.spawn_dissolve();
  } else if (body.spawn_id) {
    Spawner.onSpawn(body);
    Audio.spawn_birth();
  }
}

function _onMitigationShadow(env) {
  const body = _decodePayload(env);
  if (!body) return;
  Swarm.onMitigationEvent({ pher_key: body.pher_key });
  _flashOverlay('mitigation-flash');
  Audio.mitigation_fired();
}

function _onLedgerEntry(row) {
  // /stream/ledger directly emits the row (not the shadow envelope shape).
  if (!row || row.seq == null) return;
  Hud.onLedgerEntry(row);
  if (Number(row.seq) > _lastTipSeq) _lastTipSeq = Number(row.seq);
}

// =====================================================================
// Bootstrap & helpers
// =====================================================================

async function _bootstrapPher() {
  try {
    const r = await fetch('/api/pher/snapshot', { headers: { accept: 'application/json' } });
    if (!r.ok) throw new Error(r.status);
    const data = await r.json();
    if (data && Array.isArray(data.nodes) && data.nodes.length > 0) {
      for (const n of data.nodes) {
        Swarm.updatePher({
          pher_key: n.pher_key,
          kind:     n.kind,
          tau:      n.tau,
          bel_evil: n.bel_evil,
        });
      }
      return;
    }
  } catch (_) { /* ignore — fall through */ }
  // No backend nodes yet — seed synthetic so the void is never empty.
  Swarm.seedSynthetic(16);
}

async function _refreshTip() {
  try {
    const r = await fetch('/api/ledger/tip');
    if (!r.ok) return;
    const j = await r.json();
    if (j && j.seq != null) {
      T.seq.textContent = j.seq;
      _lastTipSeq = Math.max(_lastTipSeq, Number(j.seq));
    }
  } catch (_) {}
}

function _updateTelemetry() {
  const c = Swarm.getActiveCount();
  T.nodes.textContent  = c.nodes;
  T.edges.textContent  = c.edges;
  T.spawns.textContent = Spawner.activeCount();
}

function _startClock() {
  const tick = () => {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    T.clock.textContent = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  };
  tick();
  setInterval(tick, 1000);
}

function _setPosture(action) {
  T.posture.textContent = action;
  T.posture.className = '';
  T.posture.classList.add('posture-' + action.replace('_', '-').replace('escalate-human', 'escalate'));
}

function _flashOverlay(cls) {
  const el = document.createElement('div');
  el.className = cls;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1500);
}

function _kindFromKey(key) {
  if (!key) return 'unknown';
  if (key.startsWith('pher:ip:'))     return 'ip';
  if (key.startsWith('pher:domain:')) return 'domain';
  if (key.startsWith('pher:hash:'))   return 'hash';
  if (key.startsWith('pher:proc:'))   return 'process';
  return 'unknown';
}

function _wireAudioToggle() {
  const btn = document.getElementById('audio-toggle');
  btn.addEventListener('click', async () => {
    if (Audio.isEnabled()) {
      Audio.disable();
      btn.setAttribute('aria-pressed', 'false');
      btn.querySelector('.lbl').textContent = 'audio · off';
    } else {
      try {
        await Audio.enable();
        btn.setAttribute('aria-pressed', 'true');
        btn.querySelector('.lbl').textContent = 'audio · live';
      } catch (e) {
        console.warn('[findevil] audio enable failed', e);
      }
    }
  });
}
