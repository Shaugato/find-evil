// ════════════════════════════════════════════════════════════════════════
// FIND EVIL — Holographic Command Interface: 3-D molecular pheromone field
// ------------------------------------------------------------------------
// Raw three.js (vendored, single shared instance). The stigmergic field is a
// living molecular graph: artifacts are glowing "atoms" (size ∝ tau, colour ∝
// belief_evil) bonded by sensor-correlation edges, with evidence streaming as
// particles toward the threat. The whole structure precesses; consensus fires
// a shockwave, Yager conflict splits an atom two-tone, CACAO containment locks
// a ring around it.
//
// Data: reads window.__FE_IOCS (the live IOC_DEFS array, mutated in place by
// find-evil-live.js). No backend / live-layer changes. Public hooks:
//   window.__FE_GRAPH = { boot(), sync(), onResize() }
//   window.fireConsensusRipple(color)   ← decision-fired effect
// ════════════════════════════════════════════════════════════════════════
import * as THREE from 'three';
import { OrbitControls } from '/static/vendor/OrbitControls.js';

(function () {
  'use strict';

  // ── palette (holographic) ──────────────────────────────────────────────
  const C = {
    low:       new THREE.Color('#00d4ff'), // benign / low confidence — cyan
    suspect:   new THREE.Color('#ffb86c'), // suspicious — amber
    elevated:  new THREE.Color('#ff6b35'), // elevated — hot orange
    malicious: new THREE.Color('#ff3864'), // likely malicious — red
    nucleus:   new THREE.Color('#ff3864'),
    benignEdge:new THREE.Color('#1f4a63'),
  };
  function beliefColor(bel) {
    if (bel >= 0.85) return C.malicious;
    if (bel >= 0.60) return C.elevated;
    if (bel >= 0.30) return C.suspect;
    return C.low;
  }
  function beliefOf(d) {
    // belief_evil is a probability in [0,1] — colour + display by it (per spec).
    // tau (pheromone weight) is unbounded and drives SIZE, not belief; use it
    // only as a weak normalised fallback when bel is absent.
    const b = Number(d.bel);
    if (Number.isFinite(b) && b > 0) return Math.min(1, b);
    const t = Number(d.tau);
    return Number.isFinite(t) ? Math.min(1, t / 10) : 0;
  }

  // ── shared textures ─────────────────────────────────────────────────────
  function radialTexture(stops) {
    const s = 128, cv = document.createElement('canvas'); cv.width = cv.height = s;
    const g = cv.getContext('2d');
    const grd = g.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
    stops.forEach(([o, c]) => grd.addColorStop(o, c));
    g.fillStyle = grd; g.fillRect(0, 0, s, s);
    const tex = new THREE.CanvasTexture(cv);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }
  function ringTexture() {
    const s = 256, cv = document.createElement('canvas'); cv.width = cv.height = s;
    const g = cv.getContext('2d');
    g.translate(s / 2, s / 2);
    const grd = g.createRadialGradient(0, 0, s * 0.30, 0, 0, s * 0.5);
    grd.addColorStop(0, 'rgba(255,255,255,0)');
    grd.addColorStop(0.78, 'rgba(255,255,255,0.95)');
    grd.addColorStop(0.85, 'rgba(255,255,255,1)');
    grd.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = grd; g.beginPath(); g.arc(0, 0, s * 0.5, 0, Math.PI * 2); g.fill();
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }

  // ── module state ─────────────────────────────────────────────────────────
  let host, renderer, scene, camera, controls, clock;
  let glowTex, coreTex, ringTex;
  let raycaster, pointer = new THREE.Vector2(-5, -5);
  let labelLayer, tooltip;
  let booted = false, W = 0, H = 0;

  const NUC = '__nucleus__';
  const nodes = new Map();   // id -> node
  let edges = [];            // {a, b, dir, col}
  let edgeLine = null;       // THREE.LineSegments
  let particles = [];        // {edge, t, speed, sprite}
  let particleGroup;
  let ripples = [];          // {sprite, age, life, max}
  let cacao = [];            // {node, ring, age, life, settled}
  let hovered = null, selected = null;
  // click-to-expand atom detail view
  let expanded = null, expandT = 0, detailGroup = null, hud = null;
  const _focus = new THREE.Vector3(), _origin = new THREE.Vector3();
  // camera fly-to tween (double-click dive-in / collapse-out)
  let camTween = { active: false, t: 0, dur: 0.8, fromPos: null, toPos: null, fromTgt: null, toTgt: null, then: null };
  let _hintEl = null;

  // tuning
  const R_SPHERE = 46;       // target layout radius
  const K_REP = 2600;        // repulsion strength
  const K_SPRING = 0.020;    // edge spring
  const K_CENTER = 0.0042;   // mild pull to origin
  const DAMP = 0.86;
  const MAXV = 2.4;

  function getIocs() {
    const a = window.__FE_IOCS;
    if (!Array.isArray(a)) return [];
    return a.filter((d) => d && !d.isPlaceholder);
  }

  // ── init ─────────────────────────────────────────────────────────────────
  function init() {
    host = document.getElementById('holo-stage');
    if (!host) { host = document.createElement('div'); host.id = 'holo-stage'; document.body.appendChild(host); }
    W = host.clientWidth || window.innerWidth;
    H = host.clientHeight || window.innerHeight;

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance', preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(W, H);
    renderer.setClearColor(0x060a10, 1);
    renderer.domElement.style.display = 'block';
    host.appendChild(renderer.domElement);

    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x060a10, 0.0052);

    camera = new THREE.PerspectiveCamera(55, W / H, 0.1, 2000);
    camera.position.set(0, 8, 132);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.rotateSpeed = 0.6;
    controls.enablePan = true;            // right-drag / two-finger pan
    controls.screenSpacePanning = true;
    controls.minDistance = 36;
    controls.maxDistance = 340;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.4;
    controls.zoomSpeed = 0.9;
    controls.target.set(0, 0, 0);

    glowTex = radialTexture([[0, 'rgba(255,255,255,1)'], [0.22, 'rgba(255,255,255,0.8)'], [0.5, 'rgba(255,255,255,0.22)'], [1, 'rgba(255,255,255,0)']]);
    coreTex = radialTexture([[0, 'rgba(255,255,255,1)'], [0.35, 'rgba(255,255,255,0.9)'], [0.7, 'rgba(255,255,255,0.15)'], [1, 'rgba(255,255,255,0)']]);
    ringTex = ringTexture();

    // ambient backdrop — a faint volumetric glow so the void isn't flat black
    const back = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0x0e3146, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, depthTest: false }));
    back.scale.set(520, 520, 1); back.position.set(0, 0, -120); back.renderOrder = -10;
    scene.add(back);

    particleGroup = new THREE.Group(); scene.add(particleGroup);

    raycaster = new THREE.Raycaster();
    raycaster.params.Sprite = { threshold: 0 };

    // label + tooltip overlay
    labelLayer = document.createElement('div'); labelLayer.id = 'holo-labels'; host.appendChild(labelLayer);
    tooltip = document.createElement('div'); tooltip.id = 'holo-tip'; tooltip.style.display = 'none'; host.appendChild(tooltip);

    renderer.domElement.addEventListener('pointermove', onPointerMove);
    renderer.domElement.addEventListener('pointerdown', onPointerDown);
    renderer.domElement.addEventListener('dblclick', onDblClick);
    window.addEventListener('resize', onResize);
    window.addEventListener('keydown', (e) => { if (e.key === 'Escape') collapseDetail(); });

    // navigation hint (auto-fades; hidden on first dive)
    _hintEl = document.createElement('div'); _hintEl.id = 'holo-hint';
    _hintEl.textContent = 'drag to orbit · scroll to zoom · double-click an atom to dive in';
    host.appendChild(_hintEl);
    setTimeout(() => { if (_hintEl) _hintEl.classList.add('fade'); }, 9000);

    clock = new THREE.Clock();
    buildNucleus();
    sync();
    animate();
  }

  function nodeSprite(tex, color, sizeWorld) {
    const m = new THREE.SpriteMaterial({ map: tex, color: color.clone(), blending: THREE.AdditiveBlending, transparent: true, depthWrite: false });
    const s = new THREE.Sprite(m);
    s.scale.set(sizeWorld, sizeWorld, 1);
    return s;
  }

  function buildNucleus() {
    const pos = new THREE.Vector3(0, 0, 0);
    const glow = nodeSprite(glowTex, C.nucleus, 30); glow.renderOrder = 2;
    const core = nodeSprite(coreTex, new THREE.Color('#ffd2dc'), 13); core.renderOrder = 3;
    scene.add(glow); scene.add(core);
    const node = {
      id: NUC, isNucleus: true, pos, vel: new THREE.Vector3(),
      glow, core, tau: 1, bel: 1, k: 0, baseSize: 30, curSize: 30, born: 0,
      type: 'MCP', value: 'BLACKBOARD', sensor: '', severity: 'critical', appear: 1,
    };
    nodes.set(NUC, node);
  }

  // ── data sync (incremental, position-preserving) ─────────────────────────
  function sync() {
    const iocs = getIocs();
    const seen = new Set([NUC]);

    // Rank by belief (real signal) and cap to the most meaningful artifacts so
    // the 3-D scene stays readable and honest — every atom is a real reported
    // artifact; benign low-confidence ones are dimmed (LOD), not decorative.
    const ranked = iocs.slice().sort((a, b) => beliefOf(b) - beliefOf(a)).slice(0, 60);
    ranked.forEach((d) => {
      const id = d.key || (d.type + ':' + d.value);
      seen.add(id);
      const bel = beliefOf(d);
      const tau = Number(d.tau) || 0;
      let n = nodes.get(id);
      if (!n) {
        // materialise near a random point on the shell, then spring inward
        const dir = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).normalize();
        const pos = dir.multiplyScalar(R_SPHERE * (0.7 + Math.random() * 0.6));
        const color = beliefColor(bel);
        const glow = nodeSprite(glowTex, color, 0.1); glow.renderOrder = 2;
        const core = nodeSprite(coreTex, new THREE.Color('#ffffff'), 0.1); core.renderOrder = 3;
        glow.userData.id = id; core.userData.id = id;
        scene.add(glow); scene.add(core);
        n = { id, pos, vel: new THREE.Vector3(), glow, core, born: performance.now(), appear: 0 };
        nodes.set(id, n);
        spawnBurst(pos, color);
      }
      n.type = d.type || 'IOC';
      n.value = String(d.value || '').slice(0, 22);
      n.sensor = d.sensor || '';
      n.tau = tau; n.bel = bel; n.k = Number(d.k) || 0;
      n.pl = Math.min(1, Math.max(bel, Number(d.pl) || bel));   // plausibility ≥ belief
      n.severity = d.severity || 'low';
      n.targetColor = beliefColor(bel);
      n.lod = bel < 0.30;                            // benign / low-confidence → dim LOD
      n.baseSize = (6 + Math.min(1, tau) * 16) * (n.lod ? 0.5 : 1);
      n.dead = false;
    });

    // mark missing nodes for fade-out
    nodes.forEach((n, id) => { if (!seen.has(id)) n.dead = true; });

    deriveEdges();
  }

  function deriveEdges() {
    const arts = [];
    nodes.forEach((n) => { if (!n.isNucleus && !n.dead) arts.push(n); });
    const E = [];
    const nuc = nodes.get(NUC);

    // 1) every artifact bonds to the nucleus (core of the molecule)
    arts.forEach((n) => E.push(mkEdge(n, nuc)));

    // 2) sensor-correlation cross-bonds: within each sensor token, link every
    //    artifact to that token's strongest (highest-tau) artifact.
    const bySensor = new Map();
    arts.forEach((n) => {
      String(n.sensor || '').split(',').map((s) => s.trim()).filter(Boolean).forEach((tok) => {
        if (!bySensor.has(tok)) bySensor.set(tok, []);
        bySensor.get(tok).push(n);
      });
    });
    const linked = new Set();
    bySensor.forEach((list) => {
      if (list.length < 2) return;
      let hub = list[0]; list.forEach((n) => { if (n.tau > hub.tau) hub = n; });
      list.forEach((n) => {
        if (n === hub) return;
        const key = n.id < hub.id ? n.id + '|' + hub.id : hub.id + '|' + n.id;
        if (linked.has(key)) return; linked.add(key);
        E.push(mkEdge(n, hub));
      });
    });

    edges = E;
    rebuildEdgeGeometry();
    reseedParticles();
  }

  function mkEdge(n1, n2) {
    // direction: evidence flows from lower-threat toward higher-threat end
    const a = (n1.bel || 0) <= (n2.bel || 0) ? n1 : n2;
    const b = a === n1 ? n2 : n1;
    return { a, b };
  }

  function rebuildEdgeGeometry() {
    if (edgeLine) { scene.remove(edgeLine); edgeLine.geometry.dispose(); edgeLine.material.dispose(); edgeLine = null; }
    const n = edges.length; if (!n) return;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 6), 3));
    geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(n * 6), 3));
    const mat = new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false });
    edgeLine = new THREE.LineSegments(geo, mat); edgeLine.renderOrder = 1;
    scene.add(edgeLine);
  }

  function updateEdgeGeometry() {
    if (!edgeLine) return;
    const pos = edgeLine.geometry.attributes.position.array;
    const col = edgeLine.geometry.attributes.color.array;
    for (let i = 0; i < edges.length; i++) {
      const e = edges[i], o = i * 6;
      pos[o] = e.a.pos.x; pos[o + 1] = e.a.pos.y; pos[o + 2] = e.a.pos.z;
      pos[o + 3] = e.b.pos.x; pos[o + 4] = e.b.pos.y; pos[o + 5] = e.b.pos.z;
      const ca = e.a.isNucleus ? C.malicious : beliefColor(e.a.bel);
      const cb = e.b.isNucleus ? C.malicious : beliefColor(e.b.bel);
      col[o] = ca.r; col[o + 1] = ca.g; col[o + 2] = ca.b;
      col[o + 3] = cb.r; col[o + 4] = cb.g; col[o + 5] = cb.b;
    }
    edgeLine.geometry.attributes.position.needsUpdate = true;
    edgeLine.geometry.attributes.color.needsUpdate = true;
  }

  // ── particles streaming along bonds ──────────────────────────────────────
  function reseedParticles() {
    particles.forEach((p) => particleGroup.remove(p.sprite));
    particles = [];
    if (!edges.length) return;
    // Particles = evidence flowing toward real threats. Only emit on edges whose
    // artifact endpoint has belief ≥ 0.3 (meaningful signal), not random sparkle.
    const meaningful = edges.filter((e) => {
      const ab = e.a.isNucleus ? 0 : (e.a.bel || 0);
      const bb = e.b.isNucleus ? 0 : (e.b.bel || 0);
      return Math.max(ab, bb) >= 0.3;
    });
    const pool = meaningful.length ? meaningful : edges;
    const count = Math.min(70, Math.max(16, pool.length * 2));
    for (let i = 0; i < count; i++) {
      const e = pool[(Math.random() * pool.length) | 0];
      const col = (e.b.isNucleus ? C.malicious : beliefColor(e.b.bel));
      const sp = nodeSprite(coreTex, col, 1.5); sp.renderOrder = 4;
      particleGroup.add(sp);
      particles.push({ e, t: Math.random(), speed: 0.10 + Math.random() * 0.22, sprite: sp });
    }
  }

  function spawnBurst(pos, color) {
    for (let i = 0; i < 10; i++) {
      const sp = nodeSprite(coreTex, color, 1.6); sp.renderOrder = 5;
      sp.position.copy(pos);
      const v = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).normalize().multiplyScalar(8 + Math.random() * 8);
      particleGroup.add(sp);
      ripples.push({ sprite: sp, age: 0, life: 0.7, burst: v, pos: pos.clone() });
    }
  }

  // ── consensus shockwave + CACAO containment ─────────────────────────────
  function topNode() {
    if (selected && nodes.has(selected) && !nodes.get(selected).dead) return nodes.get(selected);
    let best = null;
    nodes.forEach((n) => { if (!n.isNucleus && !n.dead) { if (!best || n.tau > best.tau) best = n; } });
    return best || nodes.get(NUC);
  }
  function fireRipple(color) {
    const n = topNode();
    const col = new THREE.Color(color || '#ff3864');
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: ringTex, color: col, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, opacity: 0.95 }));
    sp.position.copy(n.pos); sp.scale.set(4, 4, 1); sp.renderOrder = 6;
    scene.add(sp);
    ripples.push({ sprite: sp, age: 0, life: 1.4, max: 120, ring: true });
    // mitigation colours also lock a CACAO containment ring
    const c = (color || '').toLowerCase();
    if (c.includes('17') || c.includes('38') || c === '#ff1744' || c === '#ff3864') startCacao(n);
  }
  function startCacao(n) {
    const ring = new THREE.Sprite(new THREE.SpriteMaterial({ map: ringTex, color: new THREE.Color('#89ddff'), blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, opacity: 0 }));
    ring.scale.set(60, 60, 1); ring.renderOrder = 6; scene.add(ring);
    cacao.push({ node: n, ring, age: 0, life: 4.0 });
  }

  // ── interaction ──────────────────────────────────────────────────────────
  function spriteList() { const a = []; nodes.forEach((n) => { if (!n.dead) a.push(n.glow); }); return a; }
  function onPointerMove(ev) {
    const r = renderer.domElement.getBoundingClientRect();
    pointer.x = ((ev.clientX - r.left) / r.width) * 2 - 1;
    pointer.y = -((ev.clientY - r.top) / r.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(spriteList(), false)[0];
    const id = hit ? hit.object.userData.id : null;
    hovered = (id && nodes.has(id)) ? nodes.get(id) : null;
    if (hovered && !hovered.isNucleus) {
      tooltip.style.display = 'block';
      tooltip.style.left = (ev.clientX - r.left + 14) + 'px';
      tooltip.style.top = (ev.clientY - r.top + 12) + 'px';
      tooltip.innerHTML =
        '<b>' + esc(hovered.type) + '</b> ' + esc(hovered.value) +
        '<span class="tip-row">Belief (evil) <i>' + (hovered.bel || 0).toFixed(3) + '</i></span>' +
        '<span class="tip-row">Pheromone τ <i>' + (hovered.tau || 0).toFixed(3) + '</i></span>' +
        '<span class="tip-row">Conflict K <i>' + (hovered.k || 0).toFixed(3) + '</i></span>' +
        '<span class="tip-row">Sensors <i>' + esc(String(hovered.sensor || '—').slice(0, 28)) + '</i></span>';
      renderer.domElement.style.cursor = 'pointer';
    } else {
      tooltip.style.display = 'none';
      renderer.domElement.style.cursor = hovered ? 'pointer' : 'grab';
    }
  }
  function onPointerDown() {
    // Single click = select (light). Double-click dives in (onDblClick) — this
    // matches the globe model and avoids expanding when the user drags to orbit.
    if (hovered && !hovered.isNucleus) {
      selected = hovered.id;
      try {
        setTxt('focus-art', hovered.value);
        setTxt('bel-val', (hovered.bel || 0).toFixed(3));
        setTxt('pl-val', (hovered.pl != null ? hovered.pl : hovered.bel || 0).toFixed(3));
        setTxt('k-val', (hovered.k || 0).toFixed(3));
        setTxt('sensor-div', hovered.sensor || 'swarm');
      } catch (_) {}
    } else {
      selected = hovered ? hovered.id : null;
      if (expanded) collapseDetail();   // click nucleus / empty space → collapse + fly out
    }
  }
  function onDblClick(ev) {
    const r = renderer.domElement.getBoundingClientRect();
    pointer.x = ((ev.clientX - r.left) / r.width) * 2 - 1;
    pointer.y = -((ev.clientY - r.top) / r.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(spriteList(), false)[0];
    const n = hit && nodes.get(hit.object.userData.id);
    if (n && !n.isNucleus) {
      if (_hintEl) _hintEl.classList.add('fade');
      // route through the shared selection store so the blackboard/ledger/MITRE
      // highlight in sync; SEL → selectArtifact() flies the camera + expands.
      const d = { key: n.id, value: n.value, type: n.type, bel: n.bel, pl: n.pl, tau: n.tau, k: n.k, sensor: n.sensor };
      // source='field' → the routing layer shows the GREEN center popup and keeps
      // the right inspector hidden (atom click → in-field detail).
      if (window.SEL) window.SEL.set('artifact', n.id, d, 'field'); else { selected = n.id; flyToNode(n); }
    }
  }
  // expand=true dives + opens the GREEN center HUD (atom/field detail). expand=false
  // just frames the atom in view (side-panel selection: highlight, no center popup).
  function flyToNode(n, expand) {
    if (expand === undefined) expand = true;
    const dist = expand ? 64 : 108;   // frame-only stays a touch further out
    const dir = camera.position.clone().sub(controls.target).normalize();
    camTween = {
      active: true, t: 0, dur: expand ? 0.8 : 0.6,
      fromPos: camera.position.clone(), toPos: n.pos.clone().add(dir.multiplyScalar(dist)),
      fromTgt: controls.target.clone(), toTgt: n.pos.clone(), then: expand ? () => expandNode(n) : null,
    };
    controls.enabled = false;
  }
  function flyToOverview() {
    const dir = camera.position.clone().sub(controls.target).normalize();
    camTween = {
      active: true, t: 0, dur: 0.7,
      fromPos: camera.position.clone(), toPos: _origin.clone().add(dir.multiplyScalar(150)),
      fromTgt: controls.target.clone(), toTgt: _origin.clone(), then: null,
    };
    controls.enabled = false;
  }
  function setTxt(id, v) { const el = document.getElementById(id); if (el) el.textContent = v; }
  function esc(s) { return String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c])); }

  // ── click-to-expand atom detail ("pull the molecule apart") ──────────────
  function expandNode(n) {
    if (!n || n.isNucleus) return;
    expanded = n.id;
    buildDetailGroup(n);
    showDetailHud(n);
    document.body.classList.add('holo-focus');
  }
  function closeDetailHud() {
    // drop the GREEN center HUD WITHOUT flying the camera back out — used when a
    // side-panel selection supersedes an atom click (the camera then frames the
    // newly selected atom instead of returning to the overview).
    expanded = null;
    if (hud) hud.classList.remove('open');
    document.body.classList.remove('holo-focus');
    // detailGroup is disposed in animate() once expandT eases to 0
  }
  function collapseDetail() {
    const was = expanded;
    closeDetailHud();
    if (was) flyToOverview();          // fly the camera back out to the overview
  }
  function buildDetailGroup(n) {
    destroyDetailGroup();
    const g = new THREE.Group();
    const col = beliefColor(n.bel);
    const mk = (tex, c, op) => new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, color: c.clone(), blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, opacity: op }));
    const gauge = mk(ringTex, col, 0); gauge.renderOrder = 5; g.add(gauge);
    const sensors = String(n.sensor || '').split(',').map((s) => s.trim()).filter(Boolean).slice(0, 8);
    const sg = sensors.map((s) => { const sp = mk(coreTex, C.low, 0); sp.renderOrder = 6; g.add(sp); return sp; });
    const helix = []; const HN = 18;
    for (let i = 0; i < HN; i++) { const sp = mk(coreTex, col, 0); sp.renderOrder = 6; g.add(sp); helix.push(sp); }
    scene.add(g);
    detailGroup = { group: g, gauge, sensors: sg, helix, node: n };
  }
  function destroyDetailGroup() {
    if (!detailGroup) return;
    scene.remove(detailGroup.group);
    detailGroup.group.traverse((o) => { if (o.material) o.material.dispose(); });
    detailGroup = null;
  }
  function showDetailHud(n) {
    if (!hud) {
      hud = document.createElement('div'); hud.id = 'holo-detail'; host.appendChild(hud);
      hud.addEventListener('click', (e) => { if (e.target.classList.contains('hd-close')) collapseDetail(); });
    }
    const bel = n.bel || 0, pl = (n.pl != null ? n.pl : bel), k = n.k || 0;
    const action = k >= 0.3 ? { t: 'CONFLICT → DEBATE', c: '#ffb86c', i: '⚖' }
      : bel >= 0.85 ? { t: 'MITIGATED', c: '#ff3864', i: '🛡' }
      : bel >= 0.55 ? { t: 'ESCALATED', c: '#ff6b35', i: '⚠' }
      : { t: 'OBSERVED', c: '#00d4ff', i: '👁' };
    const sensors = String(n.sensor || '').split(',').map((s) => s.trim()).filter(Boolean);
    const tip = (document.getElementById('merkle-tip') || {}).textContent || '—';
    const deg = Math.round(bel * 360);
    hud.innerHTML =
      '<button class="hd-close">✕</button>' +
      '<div class="hd-type">' + esc(n.type) + '</div>' +
      '<div class="hd-val">' + esc(n.value) + '</div>' +
      '<div class="hd-gauge" style="background:conic-gradient(var(--holo-cyan) ' + deg + 'deg, rgba(255,255,255,0.08) ' + deg + 'deg)"><span>' + (bel * 100).toFixed(0) + '<small>%</small><i>belief</i></span></div>' +
      '<div class="hd-rows">' +
        '<div><label>Belief (evil)</label><b>' + bel.toFixed(3) + '</b></div>' +
        '<div><label>Plausibility</label><b>' + pl.toFixed(3) + '</b></div>' +
        '<div><label>Conflict K</label><b>' + k.toFixed(3) + '</b></div>' +
        '<div><label>Pheromone τ</label><b>' + (n.tau || 0).toFixed(3) + '</b></div>' +
      '</div>' +
      '<div class="hd-sec">CONTRIBUTING SENSORS</div>' +
      '<div class="hd-chips">' + (sensors.length ? sensors.map((s) => '<span>' + esc(s) + '</span>').join('') : '<span class="dim">awaiting evidence</span>') + '</div>' +
      '<div class="hd-action" style="color:' + action.c + ';border-color:' + action.c + '">' + action.i + '  ' + action.t + '</div>' +
      '<div class="hd-hash">ledger tip · blake3:' + esc(String(tip)) + '</div>';
    hud.classList.add('open');
  }

  // ── layout physics (3-D force-directed) ──────────────────────────────────
  function step(dt) {
    const arr = []; nodes.forEach((n) => { if (!n.dead || n.appear > 0.01) arr.push(n); });
    // repulsion
    for (let i = 0; i < arr.length; i++) {
      const a = arr[i]; if (a.isNucleus) continue;
      for (let j = i + 1; j < arr.length; j++) {
        const b = arr[j];
        const dx = a.pos.x - b.pos.x, dy = a.pos.y - b.pos.y, dz = a.pos.z - b.pos.z;
        let d2 = dx * dx + dy * dy + dz * dz; if (d2 < 4) d2 = 4;
        const f = K_REP / d2; const inv = 1 / Math.sqrt(d2);
        const fx = dx * inv * f, fy = dy * inv * f, fz = dz * inv * f;
        a.vel.x += fx; a.vel.y += fy; a.vel.z += fz;
        if (!b.isNucleus) { b.vel.x -= fx; b.vel.y -= fy; b.vel.z -= fz; }
      }
    }
    // springs
    for (const e of edges) {
      const a = e.a, b = e.b;
      const dx = b.pos.x - a.pos.x, dy = b.pos.y - a.pos.y, dz = b.pos.z - a.pos.z;
      const d = Math.sqrt(dx * dx + dy * dy + dz * dz) || 0.001;
      const rest = (a.isNucleus || b.isNucleus) ? R_SPHERE * (0.42 + (1 - (b.tau || 0)) * 0.4) : 22;
      const f = (d - rest) * K_SPRING; const inv = 1 / d;
      const fx = dx * inv * f, fy = dy * inv * f, fz = dz * inv * f;
      if (!a.isNucleus) { a.vel.x += fx; a.vel.y += fy; a.vel.z += fz; }
      if (!b.isNucleus) { b.vel.x -= fx; b.vel.y -= fy; b.vel.z -= fz; }
    }
    // centering + integrate
    for (const n of arr) {
      if (n.isNucleus) { n.pos.set(0, 0, 0); continue; }
      n.vel.x += -n.pos.x * K_CENTER; n.vel.y += -n.pos.y * K_CENTER; n.vel.z += -n.pos.z * K_CENTER;
      n.vel.multiplyScalar(DAMP);
      const sp = n.vel.length(); if (sp > MAXV) n.vel.multiplyScalar(MAXV / sp);
      n.pos.addScaledVector(n.vel, dt * 60 * 0.016 * 60); // dt-normalised step
    }
  }

  // ── render loop ──────────────────────────────────────────────────────────
  let _t = 0;
  function animate() {
    requestAnimationFrame(animate);
    const dt = Math.min(0.05, clock.getDelta()); _t += dt;
    step(dt);

    // node visuals
    nodes.forEach((n) => {
      // appear/disappear easing
      const target = n.dead ? 0 : 1;
      n.appear += (target - (n.appear || 0)) * Math.min(1, dt * 6);
      if (n.dead && n.appear < 0.02) { removeNode(n); return; }
      const breathe = n.isNucleus ? (1 + Math.sin(_t * 1.6) * 0.05)
                                  : (1 + Math.sin(_t * 1.2 + n.pos.x) * 0.06 * Math.min(1, n.tau + 0.2));
      const size = (n.isNucleus ? 30 : n.baseSize) * n.appear * breathe;
      n.glow.position.copy(n.pos); n.core.position.copy(n.pos);
      let boost = hovered === n ? 1.25 : selected === n.id ? 1.18 : 1;
      let dim = 1;
      if (expandT > 0.01) {
        if (n.id === expanded) boost *= (1 + expandT * 2.6);   // pull this atom forward
        else dim = 1 - expandT * 0.72;                          // recede the rest
      }
      n.hoverBoost = boost;
      const gscale = size * boost;
      n.glow.scale.set(gscale, gscale, 1);
      n.core.scale.set(size * 0.42 * boost, size * 0.42 * boost, 1);
      const lodDim = (n.lod && n.id !== expanded) ? 0.4 : 1;   // recede benign LOD
      n.glow.material.opacity = dim * lodDim;
      n.core.material.opacity = dim * lodDim;
      // colour (with Yager two-tone oscillation when K is high)
      if (!n.isNucleus && n.targetColor) {
        if (n.k >= 0.3) {
          const mix = (Math.sin(_t * 4 + n.pos.y) + 1) / 2;
          n.glow.material.color.copy(C.malicious).lerp(C.low, mix);
        } else {
          n.glow.material.color.lerp(n.targetColor, Math.min(1, dt * 3));
        }
      }
    });

    updateEdgeGeometry();

    // particles
    for (const p of particles) {
      p.t += p.speed * dt;
      if (p.t > 1) { p.t -= 1; }   // loop along the same (meaningful) edge
      const a = p.e.a.pos, b = p.e.b.pos;
      p.sprite.position.set(a.x + (b.x - a.x) * p.t, a.y + (b.y - a.y) * p.t, a.z + (b.z - a.z) * p.t);
      const col = p.e.b.isNucleus ? C.malicious : beliefColor(p.e.b.bel);
      p.sprite.material.color.copy(col);
      const fade = Math.sin(p.t * Math.PI);
      p.sprite.material.opacity = 0.35 + fade * 0.6;
      p.sprite.scale.setScalar(1.0 + fade * 1.2);
    }

    // ripples + bursts
    for (let i = ripples.length - 1; i >= 0; i--) {
      const r = ripples[i]; r.age += dt;
      const k = r.age / r.life;
      if (k >= 1) { scene.remove(r.sprite); particleGroup.remove(r.sprite); r.sprite.material.dispose(); ripples.splice(i, 1); continue; }
      if (r.ring) {
        const sz = 4 + k * r.max; r.sprite.scale.set(sz, sz, 1);
        r.sprite.material.opacity = 0.95 * (1 - k);
      } else { // burst particle
        r.sprite.position.copy(r.pos).addScaledVector(r.burst, k);
        r.sprite.material.opacity = 0.9 * (1 - k);
      }
    }

    // CACAO contracting rings
    for (let i = cacao.length - 1; i >= 0; i--) {
      const cc = cacao[i]; cc.age += dt; const k = cc.age / cc.life;
      if (k >= 1 || cc.node.dead) { scene.remove(cc.ring); cc.ring.material.dispose(); cacao.splice(i, 1); continue; }
      cc.ring.position.copy(cc.node.pos);
      const contract = k < 0.4 ? (60 - (60 - cc.node.baseSize * 2.4) * (k / 0.4)) : cc.node.baseSize * 2.4;
      cc.ring.scale.set(contract, contract, 1);
      cc.ring.material.opacity = k < 0.4 ? 0.85 : 0.85 * (1 - (k - 0.4) / 0.6) * (0.6 + 0.4 * Math.sin(_t * 6));
    }

    // ── click-to-expand: drive transition, focus camera, animate sub-scene ──
    if (expanded && !nodes.get(expanded)) collapseDetail();   // expanded node vanished
    expandT += ((expanded ? 1 : 0) - expandT) * Math.min(1, dt * 4);
    const fnode = expanded ? nodes.get(expanded) : null;
    if (!camTween.active) {
      controls.autoRotate = !expanded;
      _focus.lerp(fnode ? fnode.pos : _origin, Math.min(1, dt * 3.2));
      controls.target.copy(_focus);
    }
    if (!expanded && expandT < 0.01 && detailGroup) destroyDetailGroup();
    if (detailGroup && fnode) {
      const base = fnode.baseSize * (1 + expandT * 2.6);
      detailGroup.group.position.copy(fnode.pos);
      // belief gauge ring just outside the expanded core
      detailGroup.gauge.scale.setScalar(base * 3.0);
      detailGroup.gauge.material.opacity = 0.45 * expandT;
      // sensor badges orbit on a tilted ring
      detailGroup.sensors.forEach((sp, i) => {
        const tot = detailGroup.sensors.length;
        const a = _t * 0.8 + (i / tot) * Math.PI * 2;
        const R = base * 2.1;
        sp.position.set(Math.cos(a) * R, Math.sin(a * 2) * R * 0.28, Math.sin(a) * R);
        sp.scale.setScalar(base * 0.5 * expandT + 2);
        sp.material.opacity = 0.95 * expandT;
      });
      // evidence helix wrapping the core (oldest → newest)
      detailGroup.helix.forEach((sp, kk) => {
        const u = kk / detailGroup.helix.length;
        const a = _t * 0.6 + u * Math.PI * 5;
        const R = base * 1.3;
        sp.position.set(Math.cos(a) * R, (u - 0.5) * base * 3.4, Math.sin(a) * R);
        sp.scale.setScalar(base * 0.16 * expandT + 1);
        sp.material.opacity = (0.2 + u * 0.55) * expandT;
      });
    }

    // camera fly-to tween (dive-in / collapse-out) takes over from OrbitControls
    if (camTween.active) {
      camTween.t += dt / camTween.dur;
      const k = camTween.t >= 1 ? 1 : 1 - Math.pow(1 - camTween.t, 3);   // easeOutCubic
      camera.position.lerpVectors(camTween.fromPos, camTween.toPos, k);
      controls.target.copy(camTween.fromTgt).lerp(camTween.toTgt, k);
      _focus.copy(controls.target);
      camera.lookAt(controls.target);
      if (camTween.t >= 1) { camTween.active = false; controls.enabled = true; const f = camTween.then; camTween.then = null; if (f) f(); }
    } else {
      controls.update();
    }
    renderer.render(scene, camera);
    updateLabels();
  }

  function removeNode(n) {
    scene.remove(n.glow); scene.remove(n.core);
    n.glow.material.dispose(); n.core.material.dispose();
    nodes.delete(n.id);
  }

  // ── HTML labels (near hemisphere / high-tau / hovered only) ──────────────
  // Labels are HTML overlays (pixel-crisp). To stop the centre congestion +
  // flicker we: (1) bind one persistent div per node by id so content never
  // swaps frame-to-frame, (2) do priority-ordered greedy screen-space collision
  // avoidance (nucleus reserved first → a clear exclusion zone at centre;
  // hovered/selected forced), (3) fade opacity in/out so show/hide never pops.
  const labelEls = new Map();         // node.id -> { el, op, target, x, y }
  const MAX_LABELS = 16;
  const _lv = new THREE.Vector3();
  function estLabelBox(n, x, y) {
    const txt = n.isNucleus ? 'BLACKBOARD' : (n.value || n.type || '');
    const w = Math.max(54, Math.min(190, txt.length * 6.2 + 14));
    const h = n.isNucleus ? 28 : 36;          // matches translate(-50%,-150%)
    return { x0: x - w / 2, x1: x + w / 2, y0: y - h * 1.5, y1: y - h * 0.4 };
  }
  function updateLabels() {
    labelEls.forEach((r) => { r.target = 0; });   // default: fade out

    const arts = [];
    nodes.forEach((n) => { if (!n.dead && !n.isNucleus) arts.push(n); });
    arts.sort((a, b) => (b.tau || 0) - (a.tau || 0));
    const ordered = [];
    const add = (n) => { if (n && !n.dead && ordered.indexOf(n) === -1) ordered.push(n); };
    add(nodes.get(NUC)); add(hovered);
    if (selected && nodes.has(selected)) add(nodes.get(selected));
    for (let i = 0; i < arts.length && ordered.length < MAX_LABELS + 8; i++) add(arts[i]);

    const placed = []; const PAD = 5;
    for (const n of ordered) {
      let rec = labelEls.get(n.id);
      if (!rec) {
        const el = document.createElement('div'); el.className = 'holo-label';
        labelLayer.appendChild(el); rec = { el, op: 0, target: 0, x: 0, y: 0 };
        labelEls.set(n.id, rec);
      }
      const html = n.isNucleus
        ? '<span class="ll-t">MCP</span><span class="ll-v">BLACKBOARD</span>'
        : '<span class="ll-t">' + esc(n.type) + '</span><span class="ll-v">' + esc(n.value) + '</span><span class="ll-tau">τ ' + (n.tau || 0).toFixed(2) + '</span>';
      if (rec.el._html !== html) { rec.el.innerHTML = html; rec.el._html = html; }

      _lv.copy(n.pos).project(camera);
      const onScreen = _lv.z <= 1 && _lv.x > -1.08 && _lv.x < 1.08 && _lv.y > -1.08 && _lv.y < 1.08;
      if (!onScreen) continue;
      const x = (_lv.x * 0.5 + 0.5) * W, y = (-_lv.y * 0.5 + 0.5) * H;
      rec.x = x; rec.y = y;
      const forced = n.isNucleus || n === hovered || n.id === selected;
      const box = estLabelBox(n, x, y);
      let clash = false;
      if (!forced) {
        for (const b of placed) {
          if (!(box.x1 < b.x0 - PAD || box.x0 > b.x1 + PAD || box.y1 < b.y0 - PAD || box.y0 > b.y1 + PAD)) { clash = true; break; }
        }
      }
      if (forced || !clash) {
        placed.push(box);
        const depth = 1 - Math.min(1, Math.max(0, (camera.position.distanceTo(n.pos) - 50) / 260));
        rec.target = forced ? 1 : (0.5 + depth * 0.45);
      }
    }

    labelEls.forEach((rec, id) => {
      const node = nodes.get(id);
      if (!node || node.dead) rec.target = 0;
      rec.op += (rec.target - rec.op) * 0.18;          // smooth fade
      const el = rec.el;
      if (rec.op < 0.02) {
        el.style.display = 'none';
        if ((!node || node.dead) && rec.target === 0) { el.remove(); labelEls.delete(id); }
        return;
      }
      el.style.display = 'block';
      el.style.opacity = rec.op.toFixed(3);
      el.style.transform = 'translate(-50%,-150%) translate(' + Math.round(rec.x) + 'px,' + Math.round(rec.y) + 'px)';
    });
  }

  function onResize() {
    if (!renderer) return;
    W = host.clientWidth || window.innerWidth;
    H = host.clientHeight || window.innerHeight;
    camera.aspect = W / H; camera.updateProjectionMatrix();
    renderer.setSize(W, H);
  }

  // ── public hooks ─────────────────────────────────────────────────────────
  function boot() {
    if (booted) return; booted = true;
    if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); }
    else init();
  }
  window.__FE_GRAPH = {
    boot, sync: () => { if (booted) sync(); }, onResize,
    focusTop: () => { let best = null; nodes.forEach((n) => { if (!n.isNucleus && !n.dead && (!best || n.tau > best.tau)) best = n; }); if (best) { hovered = best; flyToNode(best); } return best ? best.id : null; },
    collapse: collapseDetail,
    clearDetail: closeDetailHud,    // close GREEN HUD without flying out (routing layer)
    selectArtifact: (key, opts) => {
      const n = nodes.get(key); if (!n || n.isNucleus) return false;
      selected = n.id;
      const dive = !!(opts && opts.dive);
      const onField = (() => { const vp = document.getElementById('view-pheromone'); return vp && vp.classList.contains('active'); })();
      if (dive) {
        if (onField) flyToNode(n, true);            // field click → dive + GREEN center popup
      } else {
        if (expanded) closeDetailHud();             // side-panel click → never leave a GREEN popup open
        if (onField) flyToNode(n, false);           // frame the atom in view (highlight, no popup)
      }
      return true;
    },
    nav: () => (camera && controls) ? {
      dist: +camera.position.distanceTo(controls.target).toFixed(1),
      target: controls.target.toArray().map((v) => +v.toFixed(1)),
      enableRotate: controls.enableRotate !== false,
      enableZoom: controls.enableZoom !== false,
      enablePan: controls.enablePan === true,
      autoRotate: controls.autoRotate, tweening: camTween.active,
    } : null,
    get booted() { return booted; }, get expanded() { return expanded; },
  };
  window.fireConsensusRipple = function (color) { if (booted) fireRipple(color); };

  // live layer dispatches 'resize' every snapshot tick → refresh data too
  window.addEventListener('resize', () => { if (booted) sync(); });

  // if the classic delegator already asked for boot before this module loaded
  if (window.__FE_GRAPH_WANTED) boot();
})();
