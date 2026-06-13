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
    const b = Number(d.bel); const t = Number(d.tau);
    return Math.max(Number.isFinite(b) ? b : 0, Number.isFinite(t) ? t * 0.9 : 0);
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
    controls.enablePan = false;
    controls.minDistance = 50;
    controls.maxDistance = 320;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.55;
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
    window.addEventListener('resize', onResize);

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

    iocs.slice(0, 80).forEach((d) => {
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
      n.severity = d.severity || 'low';
      n.targetColor = beliefColor(bel);
      n.baseSize = 6 + Math.min(1, tau) * 16;        // 6..22 world units
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
    const count = Math.min(160, Math.max(24, edges.length * 3));
    for (let i = 0; i < count; i++) {
      const e = edges[(Math.random() * edges.length) | 0];
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
    if (hovered) {
      selected = hovered.id;
      // immediate blackboard feedback (live layer re-asserts within ~800ms)
      try {
        if (!hovered.isNucleus) {
          setTxt('focus-art', hovered.value);
          setTxt('bel-val', (hovered.bel || 0).toFixed(3));
          setTxt('pl-val', Math.max(hovered.bel || 0, hovered.tau || 0).toFixed(3));
          setTxt('k-val', (hovered.k || 0).toFixed(3));
          setTxt('sensor-div', hovered.sensor || 'swarm');
        }
      } catch (_) {}
    } else { selected = null; }
  }
  function setTxt(id, v) { const el = document.getElementById(id); if (el) el.textContent = v; }
  function esc(s) { return String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c])); }

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
      const gscale = size * (n.hoverBoost = (hovered === n ? 1.25 : selected === n.id ? 1.18 : 1));
      n.glow.scale.set(gscale, gscale, 1);
      n.core.scale.set(size * 0.42, size * 0.42, 1);
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
      if (p.t > 1) { p.t -= 1; if (Math.random() < 0.3 && edges.length) { p.e = edges[(Math.random() * edges.length) | 0]; } }
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

    controls.update();
    renderer.render(scene, camera);
    updateLabels();
  }

  function removeNode(n) {
    scene.remove(n.glow); scene.remove(n.core);
    n.glow.material.dispose(); n.core.material.dispose();
    nodes.delete(n.id);
  }

  // ── HTML labels (near hemisphere / high-tau / hovered only) ──────────────
  const labelPool = [];
  const MAX_LABELS = 14;
  function updateLabels() {
    // Always label the nucleus + hovered + selected; otherwise the top-N
    // artifacts by tau, so a dense live field stays legible (no label soup).
    const arts = [];
    nodes.forEach((n) => { if (!n.dead && !n.isNucleus) arts.push(n); });
    arts.sort((a, b) => (b.tau || 0) - (a.tau || 0));
    const cands = [];
    const push = (n) => { if (n && !n.dead && cands.indexOf(n) === -1) cands.push(n); };
    push(nodes.get(NUC));
    push(hovered);
    if (selected && nodes.has(selected)) push(nodes.get(selected));
    for (let i = 0; i < arts.length && cands.length < MAX_LABELS; i++) push(arts[i]);
    let li = 0;
    const v = new THREE.Vector3();
    for (const n of cands) {
      v.copy(n.pos).project(camera);
      if (v.z > 1) continue;
      const x = (v.x * 0.5 + 0.5) * W, y = (-v.y * 0.5 + 0.5) * H;
      let el = labelPool[li];
      if (!el) { el = document.createElement('div'); el.className = 'holo-label'; labelLayer.appendChild(el); labelPool[li] = el; }
      const depth = 1 - Math.min(1, Math.max(0, (camera.position.distanceTo(n.pos) - 50) / 260));
      el.style.display = 'block';
      el.style.transform = 'translate(-50%,-140%) translate(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px)';
      el.style.opacity = (n.isNucleus || n === hovered || n.id === selected) ? 1 : (0.35 + depth * 0.5).toFixed(2);
      const tau = (n.tau || 0).toFixed(2);
      el.innerHTML = n.isNucleus
        ? '<span class="ll-t">MCP</span><span class="ll-v">BLACKBOARD</span>'
        : '<span class="ll-t">' + esc(n.type) + '</span><span class="ll-v">' + esc(n.value) + '</span><span class="ll-tau">τ ' + tau + '</span>';
      li++;
    }
    for (; li < labelPool.length; li++) labelPool[li].style.display = 'none';
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
  window.__FE_GRAPH = { boot, sync: () => { if (booted) sync(); }, onResize, get booted() { return booted; } };
  window.fireConsensusRipple = function (color) { if (booted) fireRipple(color); };

  // live layer dispatches 'resize' every snapshot tick → refresh data too
  window.addEventListener('resize', () => { if (booted) sync(); });

  // if the classic delegator already asked for boot before this module loaded
  if (window.__FE_GRAPH_WANTED) boot();
})();
