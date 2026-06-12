(function () {
  const LIVE = {
    connectedStreams: new Set(),
    lastLoopMs: 0,
    lastSnapshotAt: 0,
    lastConsensus: null,
    liveIocCount: 0,
    liveThreatCount: 0,
    liveTauMax: 0,
    liveEventTotal: 0,
    liveConsensusTotal: 0,
    liveLedgerTip: null,
    liveReports: [],
    liveTechniques: [],
    liveCacao: [],
    started: false,
  };

  const design = {
    renderAgents,
    renderIOCs,
    renderLedger,
    renderMitre: typeof renderMitre === 'function' ? renderMitre : function () {},
    renderDebate,
    initPheromoneCanvas,
    initThreatGraphCanvas,
    initSparklines,
    drawSparkline,
    addEvent,
    playThreatSound,
  };

  const byId = (id) => document.getElementById(id);
  const num = (value, fallback = 0) => {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  };
  const severityFor = (score) => {
    if (score >= 0.85) return 'critical';
    if (score >= 0.55) return 'high';
    if (score >= 0.25) return 'medium';
    return 'low';
  };
  const colorFor = (score) => {
    if (score >= 0.85) return 'red';
    if (score >= 0.55) return 'amber';
    if (score >= 0.25) return 'blue';
    return 'green';
  };
  const replaceArray = (target, rows) => target.splice(0, target.length, ...rows);
  const short = (value, front = 14, back = 6) => {
    const s = String(value ?? '');
    return s.length <= front + back + 1 ? s : `${s.slice(0, front)}…${s.slice(-back)}`;
  };

  function decodePherKey(key) {
    const raw = String(key || 'pher:unknown:idle');
    if (raw.startsWith('pher:ip:')) return { type: 'IP', value: raw.slice(8) };
    if (raw.startsWith('pher:hash:')) return { type: 'SHA-256', value: short(raw.slice(10), 12, 8) };
    if (raw.startsWith('pher:domain:')) return { type: 'DOMAIN', value: raw.slice(12) };
    if (raw.startsWith('pher:proc:')) return { type: 'PID', value: raw.slice(10) };
    return { type: 'PHER', value: raw.replace(/^pher:/, '') };
  }

  function normalizePherNode(node) {
    const key = node.pher_key || node.key || node.id || 'pher:unknown:idle';
    const decoded = decodePherKey(key);
    const tau = num(node.tau);
    const bel = num(node.bel_evil, num(node.bel, tau));
    const pl = Math.max(bel, num(node.plausibility_evil, num(node.pl, bel)));
    const k = num(node.conflict_K, num(node.K));
    const score = Math.max(tau, bel);
    return {
      key,
      type: decoded.type,
      value: decoded.value,
      tau,
      bel,
      pl,
      k,
      sensor: node.sensor || node.kind || 'swarm',
      severity: node.isPlaceholder ? 'low' : severityFor(score),
      isPlaceholder: Boolean(node.isPlaceholder),
    };
  }

  function idleIoc() {
    return normalizePherNode({
      pher_key: 'pher:idle:awaiting-live-evidence',
      tau: 0.05,
      bel_evil: 0,
      plausibility_evil: 0,
      conflict_K: 0,
      sensor: 'awaiting evidence',
      isPlaceholder: true,
    });
  }

  async function getJson(url, fallback) {
    const started = performance.now();
    try {
      const res = await fetch(url, { cache: 'no-store' });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      LIVE.lastLoopMs = performance.now() - started;
      return await res.json();
    } catch (err) {
      design.addEvent({ src: 'ui', level: 'info', msg: `${url} unavailable: ${err.message || err}` });
      return fallback;
    }
  }

  function tryJson(value) {
    if (value == null || typeof value === 'object') return value;
    if (typeof value !== 'string') return null;
    try { return JSON.parse(value); } catch (_) {}
    try {
      const bin = atob(value);
      const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
      return JSON.parse(new TextDecoder().decode(bytes));
    } catch (_) {}
    return null;
  }

  function decodeSsePayload(data) {
    const envelope = tryJson(data);
    if (!envelope) return null;
    if (Object.prototype.hasOwnProperty.call(envelope, 'payload')) {
      return tryJson(envelope.payload) || envelope.payload;
    }
    return envelope;
  }

  function ledgerSummary(row) {
    const entry = row.entry || {};
    const consensus = entry.consensus || null;
    const claim = Array.isArray(entry.reasoning_trace) && entry.reasoning_trace[0]
      ? entry.reasoning_trace[0].claim
      : '';
    return {
      seq: `#${String(row.seq || 0).padStart(3, '0')}`,
      type: entry.severity === 'critical' || consensus ? 'critical' : 'info-block',
      hash: `blake3:${short(row.entry_hash || '-', 16, 10)}`,
      event: consensus ? 'Dempster-Shafer consensus committed' : (entry.agent_id || 'ledger entry'),
      detail: claim || entry.primary_artifact_key || row.finding_id || '-',
      sig: entry.signature ? `Ed25519:${short(entry.signature, 12, 8)}` : `finding:${short(row.finding_id || '-', 12, 8)}`,
      raw: row,
    };
  }

  function updateAgentsFromIocs(iocs, reports) {
    const sensors = new Map();
    for (const ioc of iocs) {
      if (ioc.isPlaceholder) continue;
      String(ioc.sensor || 'swarm').split(',').map((s) => s.trim()).filter(Boolean).forEach((sensor) => {
        const row = sensors.get(sensor) || { name: sensor, tau: 0, count: 0 };
        row.tau = Math.max(row.tau, ioc.tau, ioc.bel);
        row.count += 1;
        sensors.set(sensor, row);
      });
    }
    for (const report of reports || []) {
      const sensor = report.sensor || report.agent_id || 'agent';
      const row = sensors.get(sensor) || { name: sensor, tau: 0, count: 0 };
      row.tau = Math.max(row.tau, num(report.confidence));
      row.count += 1;
      sensors.set(sensor, row);
    }
    const rows = Array.from(sensors.values()).sort((a, b) => b.tau - a.tau).map((a, idx) => ({
      id: `A${idx + 1}`,
      name: a.name,
      src: a.name,
      color: colorFor(a.tau),
      tau: a.tau,
      ops: a.count * 1000,
    }));
    if (!rows.length) {
      rows.push({ id: 'A1', name: 'awaiting-evidence', src: 'swarm', color: 'green', tau: 0.05, ops: 0 });
    }
    replaceArray(AGENT_DEFS, rows);
  }

  function deriveDebateFromLedger(rows) {
    const red = [];
    const blue = [];
    for (const row of rows.slice(0, 12).reverse()) {
      const entry = row.entry || {};
      const claim = Array.isArray(entry.reasoning_trace) && entry.reasoning_trace[0]
        ? entry.reasoning_trace[0].claim
        : entry.primary_artifact_key;
      if (!claim) continue;
      const msg = { ts: `#${row.seq}`, text: claim };
      if (String(entry.agent_id || '').toLowerCase().includes('red')) red.push(msg);
      else if (entry.consensus || String(entry.agent_id || '').includes('narrator')) blue.push(msg);
    }
    replaceArray(RED_MSGS, red.length ? red : [
      { ts: 'LIVE', text: 'No adversary emulator assertions have been recorded in the ledger yet.' },
    ]);
    replaceArray(BLUE_MSGS, blue.length ? blue : [
      { ts: 'LIVE', text: 'Waiting for consensus or narrator findings from the live ledger.' },
    ]);
  }

  async function refreshSnapshot() {
    const started = performance.now();
    const [pher, ledger, tip, attack, cacao] = await Promise.all([
      getJson('/api/pher/snapshot', { nodes: [], valkey_available: false }),
      getJson('/api/ledger/recent?n=32', []),
      getJson('/api/ledger/tip', {}),
      getJson('/api/attack_path', { techniques: [] }),
      getJson('/api/cacao/instances', { instances: [] }),
    ]);

    const iocs = (pher.nodes || []).map(normalizePherNode)
      .sort((a, b) => Math.max(b.tau, b.bel) - Math.max(a.tau, a.bel));
    replaceArray(IOC_DEFS, iocs.length ? iocs : [idleIoc()]);
    replaceArray(LEDGER_DEFS, Array.isArray(ledger) ? ledger.map(ledgerSummary) : []);

    LIVE.liveIocCount = iocs.length;
    LIVE.liveThreatCount = iocs.filter((ioc) => ioc.severity === 'critical').length;
    LIVE.liveTauMax = iocs.reduce((m, ioc) => Math.max(m, ioc.tau), 0);
    LIVE.liveLedgerTip = tip || {};
    LIVE.liveTechniques = attack.techniques || [];
    LIVE.liveCacao = cacao.instances || [];
    LIVE.lastSnapshotAt = Date.now();
    LIVE.lastLoopMs = performance.now() - started;

    updateAgentsFromIocs(IOC_DEFS, LIVE.liveReports);
    deriveDebateFromLedger(Array.isArray(ledger) ? ledger : []);
    window.LIVE_TECHNIQUES = LIVE.liveTechniques;
    design.renderAgents();
    design.renderIOCs();
    design.renderLedger();
    design.renderMitre();
    design.renderDebate();
    updateStats();
    updateMetrics();
    updateThreatLevel();
    window.dispatchEvent(new Event('resize'));
  }

  function consensusToIoc(frame) {
    if (!frame || !frame.pher_key) return null;
    return normalizePherNode({
      pher_key: frame.pher_key,
      kind: frame.kind,
      tau: frame.tau,
      bel_evil: frame.belief_evil,
      plausibility_evil: frame.plausibility_evil,
      conflict_K: frame.conflict_K,
      sensor: (frame.reports || []).map((r) => r.sensor).filter(Boolean).join(', ') || 'consensus',
    });
  }

  function addLiveConsensus(frame) {
    if (!frame || !frame.pher_key) return;
    LIVE.lastConsensus = frame;
    LIVE.liveConsensusTotal += 1;
    LIVE.liveReports = frame.reports || [];

    const ioc = consensusToIoc(frame);
    if (ioc) {
      const idx = IOC_DEFS.findIndex((row) => row.key === ioc.key);
      if (idx >= 0) IOC_DEFS.splice(idx, 1, ioc);
      else IOC_DEFS.unshift(ioc);
      LIVE.liveIocCount = IOC_DEFS.filter((row) => !row.isPlaceholder).length;
      LIVE.liveThreatCount = IOC_DEFS.filter((row) => row.severity === 'critical').length;
      LIVE.liveTauMax = IOC_DEFS.reduce((m, row) => Math.max(m, row.tau || 0), 0);
    }

    const techniques = [];
    for (const report of frame.reports || []) {
      for (const tech of report.attack_techniques || []) {
        if (!techniques.includes(tech)) techniques.push(tech);
      }
    }
    if (techniques.length) {
      LIVE.liveTechniques = Array.from(new Set([...techniques, ...LIVE.liveTechniques])).slice(0, 24);
      window.LIVE_TECHNIQUES = LIVE.liveTechniques;
      design.renderMitre();
    }

    design.addEvent({
      src: 'consensus',
      level: frame.action === 'mitigate' ? 'alert' : 'info',
      msg: `${frame.action || 'observe'} ${frame.pher_key} Bel=${num(frame.belief_evil).toFixed(3)} K=${num(frame.conflict_K).toFixed(3)}`,
    });

    updateAgentsFromIocs(IOC_DEFS, LIVE.liveReports);
    design.renderAgents();
    design.renderIOCs();
    updateStats();
    updateMetrics();
    updateThreatLevel();

    // Fire a pheromone-field ripple when a decision crosses consensus:
    // red burst for a mitigation, amber for a Yager conflict routed to debate.
    if (typeof window.fireConsensusRipple === 'function') {
      if (frame.action === 'mitigate' || num(frame.belief_evil) >= 0.8) {
        window.fireConsensusRipple('#ff1744');
      } else if (frame.action === 'conflict_ledger' || num(frame.conflict_K) >= 0.3) {
        window.fireConsensusRipple('#ffab00');
      }
    }
    if (num(frame.belief_evil) >= 0.85 || frame.action === 'mitigate') showThreatOverlayFor(frame);
  }

  function showThreatOverlayFor(frame) {
    const overlay = byId('threat-overlay');
    if (!overlay || !frame || !frame.pher_key) return;
    byId('overlay-detail').textContent =
`ARTIFACT: ${frame.pher_key}
τ = ${num(frame.tau).toFixed(3)}  Bel(evil) = ${num(frame.belief_evil).toFixed(3)}  Pl(evil) = ${num(frame.plausibility_evil).toFixed(3)}
SENSOR DIVERSITY: ${frame.sensor_diversity || 0}  K(conflict) = ${num(frame.conflict_K).toFixed(3)}

MCP / CACAO:
  ${frame.action === 'mitigate' ? 'CACAO mitigation playbook queued or executed through MCP' : frame.action || 'observation recorded'}

MERKLE LEDGER:
  Signed consensus entries are visible in the Merkle Ledger tab.`;
    overlay.classList.add('visible');
    design.playThreatSound();
  }

  function connectStream(name, url, onPayload) {
    const es = new EventSource(url);
    es.onopen = () => {
      LIVE.connectedStreams.add(name);
      updateMetrics();
    };
    es.onmessage = (ev) => {
      const payload = decodeSsePayload(ev.data);
      if (!payload) return;
      LIVE.liveEventTotal += 1;
      onPayload(payload);
    };
    es.onerror = () => {
      LIVE.connectedStreams.delete(name);
      updateMetrics();
    };
  }

  function connectLiveStreams() {
    connectStream('consensus', '/stream/consensus', addLiveConsensus);
    connectStream('pher', '/stream/pher', (payload) => {
      const ioc = consensusToIoc(payload) || normalizePherNode(payload);
      const idx = IOC_DEFS.findIndex((row) => row.key === ioc.key);
      if (idx >= 0) IOC_DEFS.splice(idx, 1, ioc);
      else IOC_DEFS.unshift(ioc);
      design.renderIOCs();
      updateStats();
    });
    connectStream('ledger', '/stream/ledger', (payload) => {
      const summary = ledgerSummary(payload);
      if (!LEDGER_DEFS.some((row) => row.raw?.seq === payload.seq)) LEDGER_DEFS.unshift(summary);
      if (LEDGER_DEFS.length > 32) LEDGER_DEFS.pop();
      design.addEvent({ src: 'ledger', level: summary.type === 'critical' ? 'alert' : 'info', msg: `${summary.seq} ${summary.event}: ${summary.detail}` });
      design.renderLedger();
    });
    connectStream('fractal', '/stream/fractal', (payload) => {
      const text = payload.summary || payload.claim || payload.pher_key || JSON.stringify(payload).slice(0, 160);
      BLUE_MSGS.unshift({ ts: 'FRACTAL', text });
      if (BLUE_MSGS.length > 8) BLUE_MSGS.pop();
      design.addEvent({ src: 'fractal', level: 'info', msg: text });
      design.renderDebate();
    });
    connectStream('mitigation', '/stream/mitigation', (payload) => {
      const text = payload.action || payload.status || JSON.stringify(payload).slice(0, 160);
      design.addEvent({ src: 'cacao', level: 'alert', msg: text });
    });
  }

  updateClock = function () {
    const now = new Date();
    byId('sys-time').textContent =
      String(now.getUTCHours()).padStart(2, '0') + ':' +
      String(now.getUTCMinutes()).padStart(2, '0') + ':' +
      String(now.getUTCSeconds()).padStart(2, '0') + ' UTC';
  };

  updateStats = function () {
    const loop = Math.max(0.1, LIVE.lastLoopMs).toFixed(1);
    byId('stat-loop').textContent = loop + ' ms';
    byId('stat-loop').style.color = parseFloat(loop) < 250 ? 'var(--green)' : 'var(--amber)';
    byId('stat-agents').textContent = AGENT_DEFS.length;
    byId('agent-count-badge').textContent = AGENT_DEFS.length + ' LIVE';
    byId('stat-ioc').textContent = LIVE.liveIocCount;
    byId('stat-threats').textContent = LIVE.liveThreatCount;
    byId('stat-tau').textContent = LIVE.liveTauMax.toFixed(3);
  };

  updateMetrics = function () {
    byId('m-zmq').textContent = `${LIVE.liveEventTotal}/session`;
    byId('m-redis').textContent = LIVE.lastSnapshotAt ? 'available' : 'pending';
    byId('m-ds').textContent = `${LIVE.liveConsensusTotal}/session`;
    byId('m-mcp').textContent = `${LIVE.connectedStreams.size}/5 SSE`;
    byId('m-vllm').textContent = BLUE_MSGS.length > 1 ? 'narrating' : 'idle';

    const selected = IOC_DEFS.find((ioc) => !ioc.isPlaceholder) || IOC_DEFS[0];
    if (selected) {
      byId('focus-art').textContent = selected.value;
      byId('bel-val').textContent = selected.bel.toFixed(3);
      byId('pl-val').textContent = selected.pl.toFixed(3);
      byId('k-val').textContent = selected.k.toFixed(3);
      byId('sensor-div').textContent = selected.sensor || 'swarm';
    }
    byId('merkle-tip').textContent = short(LIVE.liveLedgerTip?.entry_hash || LIVE.liveLedgerTip?.last_merkle_root || '-', 8, 6);
  };

  updateThreatLevel = function () {
    const blocks = document.querySelectorAll('.tl-block');
    const score = Math.max(LIVE.liveTauMax, ...IOC_DEFS.map((ioc) => ioc.bel || 0));
    state.threatLevel = Math.max(1, Math.min(10, Math.ceil(score * 10)));
    blocks.forEach((b, i) => {
      b.className = 'tl-block';
      if (i < state.threatLevel) {
        if (i < 3) b.classList.add('active-green');
        else if (i < 6) b.classList.add('active-amber');
        else b.classList.add('active-red');
      }
    });
  };

  startLiveUpdates = function () {
    if (LIVE.started) return;
    LIVE.started = true;
    connectLiveStreams();
    setInterval(refreshSnapshot, 5000);
    setInterval(() => {
      updateStats();
      updateMetrics();
      updateThreatLevel();
    }, 800);
    setInterval(() => {
      const values = {
        zmq: Math.min(1, LIVE.liveEventTotal / 100),
        redis: Math.min(1, LIVE.liveTauMax),
        ds: Math.min(1, LIVE.liveConsensusTotal / 20),
        mcp: Math.min(1, LIVE.connectedStreams.size / 5),
        vllm: BLUE_MSGS.length > 1 ? 0.7 : 0.1,
      };
      Object.keys(sparklineConfigs).forEach((key) => {
        const data = state.sparklineData[key];
        data.push(values[key] ?? 0);
        if (data.length > 40) data.shift();
        design.drawSparkline(key);
      });
    }, 500);
  };

  showThreatOverlay = function () {
    if (LIVE.lastConsensus) showThreatOverlayFor(LIVE.lastConsensus);
  };

  initApp = async function () {
    await refreshSnapshot();
    design.initPheromoneCanvas();
    design.initThreatGraphCanvas();
    design.initSparklines();
    startLiveUpdates();
    updateClock();
    setInterval(updateClock, 1000);

    document.querySelectorAll('.view-tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.view-tab').forEach((t) => t.classList.remove('active'));
        document.querySelectorAll('.view').forEach((v) => v.classList.remove('active'));
        tab.classList.add('active');
        const view = byId('view-' + tab.dataset.view);
        if (view) view.classList.add('active');
        state.activeView = tab.dataset.view;
      });
    });
  };
})();
