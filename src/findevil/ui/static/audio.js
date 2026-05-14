/* =====================================================================
   FIND EVIL — Ambient & Reactive Audio Engine
   ---------------------------------------------------------------------
   Everything is synthesized at runtime through the Web Audio API. No
   audio files; no licensing. The engine is silent until enable() is
   called from a user gesture (browser autoplay policy).

   Layers:
     1. Continuous dark-ambient drone — two detuned low sawtooths
        through a slow-LFO lowpass + pink-noise bandpass tail.
     2. Reactive cues:
          consensus_reached(intensity)    — sub-bass sweep + heartbeat
          mitigation_fired()              — heavy mechanical lockdown
          ledger_lock()                   — sharp high-freq click
          spawn_birth() / spawn_dissolve() — soft transients

   Public API:
     enable() / disable()   — gate behind user gesture
     isEnabled()
     setMasterGain(g)
     consensus_reached(action, belief)
     mitigation_fired()
     ledger_lock()
     spawn_birth() / spawn_dissolve()
   ===================================================================== */

let ctx = null;
let master = null;
let droneGain = null;
let _enabled = false;

// Drone source nodes — kept on long after first start so toggling is cheap
let drone = {
  osc1: null, osc2: null,
  noise: null,
  lp: null, lpLfo: null, lpLfoGain: null,
  bp: null,
  enabled: false,
};

// ---------------------------------------------------------------------

export function isEnabled() { return _enabled; }

export async function enable() {
  if (_enabled) return;
  if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
  if (ctx.state === 'suspended') await ctx.resume();

  if (!master) {
    master = ctx.createGain();
    master.gain.value = 0.0;
    master.connect(ctx.destination);
  }

  if (!drone.enabled) _buildDrone();

  // Smooth fade-in so engaging audio doesn't pop
  const now = ctx.currentTime;
  master.gain.cancelScheduledValues(now);
  master.gain.setValueAtTime(master.gain.value, now);
  master.gain.linearRampToValueAtTime(0.85, now + 1.4);
  _enabled = true;
}

export function disable() {
  if (!_enabled || !ctx || !master) return;
  const now = ctx.currentTime;
  master.gain.cancelScheduledValues(now);
  master.gain.setValueAtTime(master.gain.value, now);
  master.gain.linearRampToValueAtTime(0.0, now + 0.6);
  _enabled = false;
}

export function setMasterGain(g) {
  if (!master) return;
  const now = ctx.currentTime;
  master.gain.cancelScheduledValues(now);
  master.gain.linearRampToValueAtTime(g, now + 0.2);
}

// ---------------------------------------------------------------------
// Continuous drone
// ---------------------------------------------------------------------

function _buildDrone() {
  // Two detuned sub-fundamentals through a slowly-breathing lowpass.
  const lp = ctx.createBiquadFilter();
  lp.type = 'lowpass';
  lp.frequency.value = 220;
  lp.Q.value = 4.0;

  // LFO drives the cutoff — very slow breathing, ~0.07 Hz
  const lpLfo = ctx.createOscillator();
  lpLfo.frequency.value = 0.07;
  const lpLfoGain = ctx.createGain();
  lpLfoGain.gain.value = 80;
  lpLfo.connect(lpLfoGain).connect(lp.frequency);
  lpLfo.start();

  const o1 = ctx.createOscillator();
  o1.type = 'sawtooth';
  o1.frequency.value = 55;        // low A
  const o2 = ctx.createOscillator();
  o2.type = 'sawtooth';
  o2.frequency.value = 55.4;      // detune slightly for chorus motion

  const droneG = ctx.createGain();
  droneG.gain.value = 0.085;       // subtle, just below conscious threshold

  o1.connect(lp);
  o2.connect(lp);
  lp.connect(droneG).connect(master);

  o1.start();
  o2.start();

  // Pink-noise tail through a wandering bandpass — adds organic hiss
  const noise = _createPinkNoise();
  const bp = ctx.createBiquadFilter();
  bp.type = 'bandpass';
  bp.frequency.value = 800;
  bp.Q.value = 1.2;
  const noiseG = ctx.createGain();
  noiseG.gain.value = 0.018;
  noise.connect(bp).connect(noiseG).connect(master);
  noise.start();

  // Slow random walk on the bandpass center
  setInterval(() => {
    if (!ctx || !_enabled) return;
    const target = 500 + Math.random() * 1400;
    bp.frequency.linearRampToValueAtTime(target, ctx.currentTime + 4.0);
  }, 4200);

  drone = { osc1: o1, osc2: o2, noise, lp, lpLfo, lpLfoGain, bp, enabled: true };
  droneGain = droneG;
}

function _createPinkNoise() {
  // Voss-McCartney approximation
  const bufSize = 2 * ctx.sampleRate;
  const buf = ctx.createBuffer(1, bufSize, ctx.sampleRate);
  const data = buf.getChannelData(0);
  let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
  for (let i = 0; i < bufSize; i++) {
    const w = Math.random() * 2 - 1;
    b0 = 0.99886 * b0 + w * 0.0555179;
    b1 = 0.99332 * b1 + w * 0.0750759;
    b2 = 0.96900 * b2 + w * 0.1538520;
    b3 = 0.86650 * b3 + w * 0.3104856;
    b4 = 0.55000 * b4 + w * 0.5329522;
    b5 = -0.7616 * b5 - w * 0.0168980;
    data[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362) * 0.11;
    b6 = w * 0.115926;
  }
  const src = ctx.createBufferSource();
  src.buffer = buf;
  src.loop = true;
  return src;
}

// ---------------------------------------------------------------------
// Reactive cues
// ---------------------------------------------------------------------

export function consensus_reached(action, belief = 0.0) {
  if (!_enabled || !ctx) return;
  // Sub-bass sweep: pitch glides downward; gain envelope; intensifies with belief.
  const now = ctx.currentTime;
  const o = ctx.createOscillator();
  o.type = 'sine';
  o.frequency.setValueAtTime(96, now);
  o.frequency.exponentialRampToValueAtTime(28, now + 1.0);

  const g = ctx.createGain();
  const peak = action === 'mitigate' ? 0.55 : 0.32;
  const intensity = Math.max(0.4, Math.min(1.0, belief + 0.2));
  g.gain.setValueAtTime(0, now);
  g.gain.linearRampToValueAtTime(peak * intensity, now + 0.06);
  g.gain.exponentialRampToValueAtTime(0.0001, now + 1.15);

  // A subtle distortion-shaped band gives it body without being a square wave
  const shaper = ctx.createWaveShaper();
  shaper.curve = _saturationCurve(2.0);

  o.connect(shaper).connect(g).connect(master);
  o.start(now);
  o.stop(now + 1.2);

  // Heartbeat layer (two short thumps) for "imminent action"
  if (action === 'mitigate' || belief > 0.7) {
    _thump(now + 0.0, 0.34 * intensity);
    _thump(now + 0.32, 0.30 * intensity);
  }
}

export function mitigation_fired() {
  if (!_enabled || !ctx) return;
  const now = ctx.currentTime;

  // Layer 1 — heavy mechanical CLAMP: short noise burst through a quickly-sweeping bandpass.
  const burst = _createPinkNoise();
  const bp = ctx.createBiquadFilter();
  bp.type = 'bandpass';
  bp.frequency.setValueAtTime(220, now);
  bp.frequency.exponentialRampToValueAtTime(60, now + 0.18);
  bp.Q.value = 6;

  const bg = ctx.createGain();
  bg.gain.setValueAtTime(0.0, now);
  bg.gain.linearRampToValueAtTime(0.55, now + 0.012);
  bg.gain.exponentialRampToValueAtTime(0.0001, now + 0.32);

  burst.connect(bp).connect(bg).connect(master);
  burst.start(now);
  burst.stop(now + 0.4);

  // Layer 2 — the seal: a deep sub thud, very short
  const sub = ctx.createOscillator();
  sub.type = 'sine';
  sub.frequency.setValueAtTime(80, now);
  sub.frequency.exponentialRampToValueAtTime(36, now + 0.18);
  const sg = ctx.createGain();
  sg.gain.setValueAtTime(0, now);
  sg.gain.linearRampToValueAtTime(0.6, now + 0.02);
  sg.gain.exponentialRampToValueAtTime(0.0001, now + 0.22);
  sub.connect(sg).connect(master);
  sub.start(now);
  sub.stop(now + 0.3);

  // Layer 3 — metallic high tick (vault bolt)
  const tick = ctx.createOscillator();
  tick.type = 'square';
  tick.frequency.value = 1450;
  const tg = ctx.createGain();
  tg.gain.setValueAtTime(0, now + 0.04);
  tg.gain.linearRampToValueAtTime(0.16, now + 0.05);
  tg.gain.exponentialRampToValueAtTime(0.0001, now + 0.13);
  tick.connect(tg).connect(master);
  tick.start(now + 0.04);
  tick.stop(now + 0.16);
}

export function ledger_lock() {
  if (!_enabled || !ctx) return;
  const now = ctx.currentTime;
  // High-frequency click — short exponential decay, slight pitch fall
  const o = ctx.createOscillator();
  o.type = 'sine';
  o.frequency.setValueAtTime(1820, now);
  o.frequency.exponentialRampToValueAtTime(1180, now + 0.06);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, now);
  g.gain.linearRampToValueAtTime(0.085, now + 0.005);
  g.gain.exponentialRampToValueAtTime(0.0001, now + 0.09);
  o.connect(g).connect(master);
  o.start(now);
  o.stop(now + 0.1);
}

export function spawn_birth() {
  if (!_enabled || !ctx) return;
  const now = ctx.currentTime;
  // Soft upward chirp, low gain
  const o = ctx.createOscillator();
  o.type = 'triangle';
  o.frequency.setValueAtTime(420, now);
  o.frequency.exponentialRampToValueAtTime(880, now + 0.18);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, now);
  g.gain.linearRampToValueAtTime(0.05, now + 0.04);
  g.gain.exponentialRampToValueAtTime(0.0001, now + 0.22);
  o.connect(g).connect(master);
  o.start(now);
  o.stop(now + 0.24);
}

export function spawn_dissolve() {
  if (!_enabled || !ctx) return;
  const now = ctx.currentTime;
  // Soft downward sigh
  const o = ctx.createOscillator();
  o.type = 'sine';
  o.frequency.setValueAtTime(720, now);
  o.frequency.exponentialRampToValueAtTime(220, now + 0.32);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, now);
  g.gain.linearRampToValueAtTime(0.04, now + 0.06);
  g.gain.exponentialRampToValueAtTime(0.0001, now + 0.36);
  o.connect(g).connect(master);
  o.start(now);
  o.stop(now + 0.38);
}

// ---------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------

function _thump(when, gain = 0.3) {
  const o = ctx.createOscillator();
  o.type = 'sine';
  o.frequency.setValueAtTime(78, when);
  o.frequency.exponentialRampToValueAtTime(38, when + 0.16);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, when);
  g.gain.linearRampToValueAtTime(gain, when + 0.018);
  g.gain.exponentialRampToValueAtTime(0.0001, when + 0.22);
  o.connect(g).connect(master);
  o.start(when);
  o.stop(when + 0.24);
}

function _saturationCurve(amount) {
  const k = amount;
  const n = 256;
  const curve = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const x = (i * 2) / n - 1;
    curve[i] = ((3 + k) * x) / (3 + k * Math.abs(x));
  }
  return curve;
}
