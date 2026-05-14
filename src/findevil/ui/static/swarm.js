/* =====================================================================
   FIND EVIL — 3D Pheromone Swarm
   ---------------------------------------------------------------------
   A force-directed constellation in a deep void. Each pher_key from the
   backend is a node; nodes drift continuously (Brownian motion + spring
   topology) and react viscerally as threat scores compound.

   Physics is bespoke (no d3-force-3d) so it remains lightweight and easy
   to tune for the "alive" feeling — the gravitational center is soft, the
   repulsion uses an O(N) neighbor cap to keep it cheap, and every node
   pulses on its own internal clock seeded from its identity hash.

   Public API (used by app.js):
     init(canvas)
     updatePher({ pher_key, kind, tau, bel_evil })
     addEdgeFromConsensus(pher_keys[])
     onConsensusEvent({ pher_key, action, belief_evil })
     onMitigationEvent({ pher_key })
     getNodeScreenPosition(pher_key) -> {x,y,visible} | null
     getActiveCount() -> { nodes, edges }
   ===================================================================== */

import * as THREE from 'three';

let renderer, scene, camera;
let nodeMesh;                 // InstancedMesh of icospheres
let haloPoints;               // additive points for emissive halo
let edgeLines;                // LineSegments for the topology
let starField;                // distant background dust

const NODES = new Map();      // pher_key -> NodeRecord
const EDGES = new Set();      // 'a||b' (canonical-ordered) pher_key pairs

const MAX_NODES = 256;
const MAX_EDGES = 1024;

const FIELD_RADIUS = 28;      // soft sphere bounds
const NEIGHBOR_K = 12;        // top-K nearest for repulsion
const _tmpV = new THREE.Vector3();
const _tmpV2 = new THREE.Vector3();
const _tmpColor = new THREE.Color();
const _tmpMatrix = new THREE.Matrix4();

const KIND_COLORS = {
  ip:       new THREE.Color(0x6ad1ff),
  domain:   new THREE.Color(0x8de9ff),
  hash:     new THREE.Color(0xb98dff),
  process:  new THREE.Color(0xffc36a),
  unknown:  new THREE.Color(0x9aa7b2),
};
const COLOR_THREAT = new THREE.Color(0xff2030);
const COLOR_THREAT_MID = new THREE.Color(0xf7b955);

// Camera drift (slow Ken-Burns parallax over the void)
let cameraT = 0;

// Hover/raycast (re-used by spawner.js for projection)
const _proj = new THREE.Vector3();

// ---------------------------------------------------------------------
// Internal types
// ---------------------------------------------------------------------

class NodeRecord {
  constructor(pher_key, kind) {
    this.pher_key = pher_key;
    this.kind = kind || 'unknown';
    // initial position: spherical shell with mild jitter
    const r = FIELD_RADIUS * (0.55 + Math.random() * 0.35);
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    this.pos = new THREE.Vector3(
      r * Math.sin(phi) * Math.cos(theta),
      r * Math.sin(phi) * Math.sin(theta),
      r * Math.cos(phi),
    );
    this.vel = new THREE.Vector3(0, 0, 0);
    this.tau = 0;             // pheromone weight, drives size
    this.bel = 0;             // belief_evil, drives color/glow
    this.kindColor = (KIND_COLORS[this.kind] || KIND_COLORS.unknown).clone();
    this.lastUpdateMs = performance.now();
    this.pulsePhase = Math.random() * Math.PI * 2;
    this.pulseRate = 0.8 + Math.random() * 0.6;  // base Hz multiplier
    this.flashEnergy = 0;     // boosted by updatePher; decays per frame
    this.index = -1;          // assigned when added to InstancedMesh
  }

  // Smooth merge of incoming state — never snap, always lerp.
  ingest({ tau, bel_evil }) {
    if (typeof tau === 'number')      this.tau = THREE.MathUtils.lerp(this.tau, tau, 0.45);
    if (typeof bel_evil === 'number') this.bel = THREE.MathUtils.lerp(this.bel, bel_evil, 0.45);
    this.flashEnergy = Math.min(1.0, this.flashEnergy + 0.6 + 0.4 * (bel_evil || 0));
    this.lastUpdateMs = performance.now();
  }

  // Threat color: cool baseline → amber → siren red as bel rises.
  emissiveColor(out) {
    const b = THREE.MathUtils.clamp(this.bel, 0, 1);
    if (b < 0.35) {
      out.copy(this.kindColor);
    } else if (b < 0.7) {
      out.copy(this.kindColor).lerp(COLOR_THREAT_MID, (b - 0.35) / 0.35);
    } else {
      out.copy(COLOR_THREAT_MID).lerp(COLOR_THREAT, (b - 0.7) / 0.3);
    }
    // Flash boost on fresh ingest (decays in step()).
    if (this.flashEnergy > 0) {
      out.lerp(new THREE.Color(0xffffff), 0.45 * this.flashEnergy);
    }
    return out;
  }

  radius() {
    // tau ~ [0..10], bel ~ [0..1] both push size; flash adds a transient swell
    const base = 0.55 + 0.18 * Math.min(this.tau, 5) + 0.6 * this.bel;
    const swell = 0.18 * this.flashEnergy;
    return base + swell;
  }
}

// ---------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------

export function init(canvas) {
  renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance',
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight, false);
  renderer.setClearColor(0x000000, 0);

  scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x02050a, 0.018);

  camera = new THREE.PerspectiveCamera(
    52, window.innerWidth / window.innerHeight, 0.1, 200,
  );
  camera.position.set(0, 2, 56);
  camera.lookAt(0, 0, 0);

  // Cool ambient + a soft rim from below to kiss the underside of nodes
  scene.add(new THREE.AmbientLight(0x6ad1ff, 0.35));
  const rim = new THREE.DirectionalLight(0x88c8ff, 0.55);
  rim.position.set(8, -10, 12);
  scene.add(rim);

  _buildStarField();
  _buildNodeMesh();
  _buildHaloPoints();
  _buildEdgeLines();

  window.addEventListener('resize', _onResize);
}

function _onResize() {
  if (!renderer || !camera) return;
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight, false);
}

function _buildStarField() {
  const N = 1400;
  const geo = new THREE.BufferGeometry();
  const pos = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) {
    const r = 80 + Math.random() * 110;
    const t = Math.random() * Math.PI * 2;
    const p = Math.acos(2 * Math.random() - 1);
    pos[i * 3]     = r * Math.sin(p) * Math.cos(t);
    pos[i * 3 + 1] = r * Math.sin(p) * Math.sin(t);
    pos[i * 3 + 2] = r * Math.cos(p);
  }
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const mat = new THREE.PointsMaterial({
    size: 0.45,
    color: 0x6ad1ff,
    transparent: true,
    opacity: 0.45,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  starField = new THREE.Points(geo, mat);
  scene.add(starField);
}

function _buildNodeMesh() {
  const geo = new THREE.IcosahedronGeometry(1.0, 1);
  const mat = new THREE.MeshStandardMaterial({
    color: 0x6ad1ff,
    emissive: 0x6ad1ff,
    emissiveIntensity: 0.65,
    roughness: 0.35,
    metalness: 0.15,
    flatShading: true,
  });
  nodeMesh = new THREE.InstancedMesh(geo, mat, MAX_NODES);
  nodeMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  // Per-instance color buffer
  nodeMesh.instanceColor = new THREE.InstancedBufferAttribute(
    new Float32Array(MAX_NODES * 3), 3,
  );
  nodeMesh.instanceColor.setUsage(THREE.DynamicDrawUsage);
  // Hide all instances initially (zero-scale)
  for (let i = 0; i < MAX_NODES; i++) {
    _tmpMatrix.makeScale(0, 0, 0);
    nodeMesh.setMatrixAt(i, _tmpMatrix);
  }
  scene.add(nodeMesh);
}

function _buildHaloPoints() {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(MAX_NODES * 3), 3));
  geo.setAttribute('size',     new THREE.BufferAttribute(new Float32Array(MAX_NODES), 1));
  geo.setAttribute('color',    new THREE.BufferAttribute(new Float32Array(MAX_NODES * 3), 3));

  const tex = _generateHaloTexture();

  const mat = new THREE.ShaderMaterial({
    uniforms: { uMap: { value: tex }, uTime: { value: 0 } },
    vertexShader: `
      attribute float size;
      attribute vec3  color;
      varying vec3 vColor;
      void main() {
        vColor = color;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = size * (300.0 / -mv.z);
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: `
      uniform sampler2D uMap;
      varying vec3 vColor;
      void main() {
        vec4 t = texture2D(uMap, gl_PointCoord);
        if (t.a < 0.01) discard;
        gl_FragColor = vec4(vColor, 1.0) * t;
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });

  haloPoints = new THREE.Points(geo, mat);
  haloPoints.frustumCulled = false;
  scene.add(haloPoints);
}

function _generateHaloTexture() {
  const size = 128;
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(size/2, size/2, 1, size/2, size/2, size/2);
  g.addColorStop(0.0, 'rgba(255,255,255,1.0)');
  g.addColorStop(0.18, 'rgba(255,255,255,0.55)');
  g.addColorStop(0.45, 'rgba(255,255,255,0.12)');
  g.addColorStop(1.0, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.minFilter = THREE.LinearFilter;
  tex.magFilter = THREE.LinearFilter;
  return tex;
}

function _buildEdgeLines() {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(MAX_EDGES * 6), 3));
  geo.setAttribute('color',    new THREE.BufferAttribute(new Float32Array(MAX_EDGES * 6), 3));
  const mat = new THREE.LineBasicMaterial({
    vertexColors: true,
    transparent: true,
    opacity: 0.35,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  edgeLines = new THREE.LineSegments(geo, mat);
  edgeLines.frustumCulled = false;
  scene.add(edgeLines);
}

// ---------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------

export function updatePher({ pher_key, kind, tau, bel_evil }) {
  if (!pher_key) return;
  let n = NODES.get(pher_key);
  if (!n) {
    if (NODES.size >= MAX_NODES) {
      // Evict the lowest-tau node — graceful degradation under flood.
      let lowest = null, minScore = Infinity;
      for (const [k, v] of NODES) {
        const score = v.tau + 2 * v.bel;
        if (score < minScore) { minScore = score; lowest = k; }
      }
      if (lowest) NODES.delete(lowest);
    }
    n = new NodeRecord(pher_key, kind);
    NODES.set(pher_key, n);
  }
  if (kind && kind !== 'unknown') {
    n.kind = kind;
    n.kindColor = (KIND_COLORS[kind] || KIND_COLORS.unknown).clone();
  }
  n.ingest({ tau, bel_evil });
}

export function addEdgeFromConsensus(pher_keys) {
  if (!Array.isArray(pher_keys) || pher_keys.length < 2) return;
  for (let i = 0; i < pher_keys.length; i++) {
    for (let j = i + 1; j < pher_keys.length; j++) {
      const a = pher_keys[i], b = pher_keys[j];
      if (!a || !b || a === b) continue;
      const k = a < b ? a + '||' + b : b + '||' + a;
      EDGES.add(k);
    }
  }
}

export function onConsensusEvent(frame) {
  // Spike the involved node's flash, mark the related neighbours by attack tech
  if (frame && frame.pher_key) {
    const n = NODES.get(frame.pher_key);
    if (n) n.flashEnergy = Math.min(1, n.flashEnergy + 0.8);
  }
}

export function onMitigationEvent(frame) {
  // A mitigation fire is a system-wide event; pulse all currently-hot nodes.
  for (const n of NODES.values()) {
    if (n.bel > 0.5) n.flashEnergy = Math.min(1, n.flashEnergy + 0.7);
  }
  if (frame && frame.pher_key) {
    const n = NODES.get(frame.pher_key);
    if (n) n.flashEnergy = 1.0;
  }
}

export function getNodeScreenPosition(pher_key) {
  const n = NODES.get(pher_key);
  if (!n || !camera) return null;
  _proj.copy(n.pos).project(camera);
  const x = (_proj.x * 0.5 + 0.5) * window.innerWidth;
  const y = (-_proj.y * 0.5 + 0.5) * window.innerHeight;
  const visible = _proj.z > -1 && _proj.z < 1 && x >= 0 && x <= window.innerWidth && y >= 0 && y <= window.innerHeight;
  return { x, y, visible, radius: n.radius() };
}

export function getActiveCount() {
  return { nodes: NODES.size, edges: EDGES.size };
}

// ---------------------------------------------------------------------
// Frame loop — physics + render
// ---------------------------------------------------------------------

let _lastT = 0;
export function step(nowMs) {
  if (!renderer || !scene || !camera) return;
  const dt = Math.min(0.05, (nowMs - _lastT) / 1000);
  _lastT = nowMs;
  cameraT += dt * 0.04;

  // Soft Ken-Burns drift
  camera.position.x = Math.sin(cameraT * 0.7) * 4.0;
  camera.position.y = 2.0 + Math.cos(cameraT * 0.5) * 1.8;
  camera.position.z = 56 + Math.sin(cameraT * 0.3) * 3.2;
  camera.lookAt(0, 0, 0);

  if (starField) starField.rotation.y += dt * 0.005;

  _physicsStep(dt);
  _drawNodes(nowMs);
  _drawEdges();

  if (haloPoints && haloPoints.material.uniforms) {
    haloPoints.material.uniforms.uTime.value = nowMs * 0.001;
  }

  renderer.render(scene, camera);
}

// O(N*K) repulsion via simple top-K neighbor sample (random sample is fine here).
function _physicsStep(dt) {
  const nodes = Array.from(NODES.values());
  const N = nodes.length;
  if (N === 0) return;

  // Build a quick spatial sample for repulsion neighbors.
  for (let i = 0; i < N; i++) {
    const a = nodes[i];
    a.flashEnergy = Math.max(0, a.flashEnergy - dt * 0.45);

    // 1) center gravity (soft)
    _tmpV.copy(a.pos).multiplyScalar(-0.06);
    a.vel.addScaledVector(_tmpV, dt);

    // 2) Brownian impulse — tiny random kick keeps the field "alive"
    a.vel.x += (Math.random() - 0.5) * 0.08;
    a.vel.y += (Math.random() - 0.5) * 0.08;
    a.vel.z += (Math.random() - 0.5) * 0.08;

    // 3) repulsion against K random neighbors
    for (let s = 0; s < NEIGHBOR_K; s++) {
      const j = (i + 1 + ((Math.random() * (N - 1)) | 0)) % N;
      if (j === i) continue;
      const b = nodes[j];
      _tmpV.subVectors(a.pos, b.pos);
      const d2 = _tmpV.lengthSq() + 0.4;
      if (d2 > 100) continue;
      _tmpV.multiplyScalar(2.5 / d2);
      a.vel.add(_tmpV);
    }

    // 4) drag — keeps the system from runaway oscillation
    a.vel.multiplyScalar(0.92);

    // 5) integrate
    a.pos.addScaledVector(a.vel, dt);

    // 6) soft clamp to field
    const r = a.pos.length();
    if (r > FIELD_RADIUS * 1.4) {
      a.pos.multiplyScalar(FIELD_RADIUS * 1.4 / r);
      a.vel.multiplyScalar(0.6);
    }
  }

  // 7) edge spring attraction — keeps related nodes loosely tethered
  for (const ek of EDGES) {
    const [ka, kb] = ek.split('||');
    const a = NODES.get(ka), b = NODES.get(kb);
    if (!a || !b) continue;
    _tmpV.subVectors(b.pos, a.pos);
    const d = _tmpV.length();
    if (d < 1e-3) continue;
    const target = 8.0;
    const k = 0.22;
    _tmpV.multiplyScalar(((d - target) / d) * k * dt);
    a.vel.add(_tmpV);
    b.vel.add(_tmpV.negate());
  }
}

function _drawNodes(nowMs) {
  // Iterate NODES, write per-instance matrix + color into the InstancedMesh.
  let idx = 0;
  const haloPos   = haloPoints.geometry.attributes.position.array;
  const haloSize  = haloPoints.geometry.attributes.size.array;
  const haloColor = haloPoints.geometry.attributes.color.array;

  for (const n of NODES.values()) {
    if (idx >= MAX_NODES) break;
    n.index = idx;

    // Internal pulse: f(time, tau)
    const pulse = 1 + 0.07 * Math.sin(
      (nowMs * 0.001) * (1.6 + 1.2 * n.bel) * n.pulseRate + n.pulsePhase,
    );
    const r = n.radius() * pulse;

    _tmpMatrix.makeScale(r, r, r);
    _tmpMatrix.setPosition(n.pos);
    nodeMesh.setMatrixAt(idx, _tmpMatrix);

    n.emissiveColor(_tmpColor);
    nodeMesh.setColorAt(idx, _tmpColor);

    // Halo size grows with threat; halo color tracks emissive
    haloPos[idx * 3]     = n.pos.x;
    haloPos[idx * 3 + 1] = n.pos.y;
    haloPos[idx * 3 + 2] = n.pos.z;
    haloSize[idx]         = (3.5 + 8 * n.bel + 6 * n.flashEnergy) * Math.min(1.6, r);
    haloColor[idx * 3]     = _tmpColor.r;
    haloColor[idx * 3 + 1] = _tmpColor.g;
    haloColor[idx * 3 + 2] = _tmpColor.b;

    idx++;
  }
  // Hide unused slots
  for (let k = idx; k < MAX_NODES; k++) {
    _tmpMatrix.makeScale(0, 0, 0);
    nodeMesh.setMatrixAt(k, _tmpMatrix);
    haloSize[k] = 0;
  }
  nodeMesh.count = MAX_NODES;
  nodeMesh.instanceMatrix.needsUpdate = true;
  if (nodeMesh.instanceColor) nodeMesh.instanceColor.needsUpdate = true;

  haloPoints.geometry.attributes.position.needsUpdate = true;
  haloPoints.geometry.attributes.size.needsUpdate     = true;
  haloPoints.geometry.attributes.color.needsUpdate    = true;
  haloPoints.geometry.setDrawRange(0, idx);
}

function _drawEdges() {
  if (EDGES.size > MAX_EDGES) {
    // Drop excess edges deterministically — keep the most recent set bounded.
    let i = 0;
    for (const k of EDGES) {
      if (i++ >= MAX_EDGES) EDGES.delete(k);
    }
  }
  const pos = edgeLines.geometry.attributes.position.array;
  const col = edgeLines.geometry.attributes.color.array;
  let idx = 0;
  for (const ek of EDGES) {
    if (idx >= MAX_EDGES) break;
    const [ka, kb] = ek.split('||');
    const a = NODES.get(ka), b = NODES.get(kb);
    if (!a || !b) continue;
    pos[idx * 6]     = a.pos.x; pos[idx * 6 + 1] = a.pos.y; pos[idx * 6 + 2] = a.pos.z;
    pos[idx * 6 + 3] = b.pos.x; pos[idx * 6 + 4] = b.pos.y; pos[idx * 6 + 5] = b.pos.z;

    a.emissiveColor(_tmpColor);
    col[idx * 6]     = _tmpColor.r * 0.6;
    col[idx * 6 + 1] = _tmpColor.g * 0.6;
    col[idx * 6 + 2] = _tmpColor.b * 0.6;
    b.emissiveColor(_tmpColor);
    col[idx * 6 + 3] = _tmpColor.r * 0.6;
    col[idx * 6 + 4] = _tmpColor.g * 0.6;
    col[idx * 6 + 5] = _tmpColor.b * 0.6;
    idx++;
  }
  edgeLines.geometry.setDrawRange(0, idx * 2);
  edgeLines.geometry.attributes.position.needsUpdate = true;
  edgeLines.geometry.attributes.color.needsUpdate    = true;
}

// ---------------------------------------------------------------------
// Synthetic seed — used until the first /api/pher/snapshot returns
// a non-empty list, so the void is never empty on first paint.
// ---------------------------------------------------------------------

export function seedSynthetic(n = 14) {
  if (NODES.size > 0) return;
  const KINDS = ['ip', 'domain', 'hash', 'process'];
  for (let i = 0; i < n; i++) {
    const kind = KINDS[i % KINDS.length];
    updatePher({
      pher_key: `pher:${kind}:seed-${i}`,
      kind,
      tau: 0.2 + Math.random() * 1.2,
      bel_evil: Math.random() * 0.18,
    });
  }
  // a few seed edges
  const keys = Array.from(NODES.keys());
  for (let i = 0; i < keys.length - 1; i++) {
    if (Math.random() < 0.55) addEdgeFromConsensus([keys[i], keys[i + 1]]);
  }
}
