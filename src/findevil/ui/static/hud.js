/* =====================================================================
   FIND EVIL — Cryptographic HUD
   ---------------------------------------------------------------------
   The right-edge persistent overlay. Every committed forensic ledger
   entry enters as a row that snaps into final position with a sharp
   spring (cubic-bezier overshoot+settle) and a brief cryptographic-green
   flash — conveying mechanical precision and irreversible permanence.

   Each entry shows: seq · agent · severity · short hash · timestamp.
   The feed is bounded; older entries fade out as new ones land.

   Public API:
     init(rootEl, statusEl)
     onLedgerEntry(row)   — { seq, finding_id, entry_hash, ts_ns, entry }
     setStatus(text)
   ===================================================================== */

const MAX_ENTRIES = 50;
const _seenSeq = new Set();

let _list = null;
let _status = null;
let _onSnapCallback = null;

export function init(rootEl, statusEl, opts = {}) {
  _list = rootEl;
  _status = statusEl;
  _onSnapCallback = opts.onSnap || null;
}

export function setStatus(text) {
  if (_status) _status.textContent = text;
}

export function onLedgerEntry(row) {
  if (!row || !_list) return;
  const seq = Number(row.seq);
  if (!Number.isFinite(seq) || _seenSeq.has(seq)) return;
  _seenSeq.add(seq);

  const li = _build(row);
  // Insert at top (the feed is reversed visually so newest is at top)
  if (_list.firstChild) _list.insertBefore(li, _list.firstChild);
  else _list.appendChild(li);

  // Trim
  while (_list.children.length > MAX_ENTRIES) {
    _list.removeChild(_list.lastChild);
  }

  // Update HUD foot status
  if (_status) {
    const stamp = new Date().toLocaleTimeString();
    _status.textContent = `seq ${seq} sealed · ${stamp}`;
  }

  // Notify audio engine for the lock click
  if (_onSnapCallback) _onSnapCallback(row);
}

// ---------------------------------------------------------------------

function _build(row) {
  const li = document.createElement('li');
  const e = row.entry || {};
  const sev = String(e.severity || 'informational').toLowerCase();
  const agent = String(e.agent_id || '—');

  li.className = 'hud-entry';
  if (sev === 'high')          li.classList.add('severity-high');
  if (sev === 'critical')      li.classList.add('severity-critical');
  if (agent === 'genesis')     li.classList.add('kind-genesis');
  if (agent.startsWith('cacao')) li.classList.add('kind-cacao');

  const hashFull = String(row.entry_hash || '');
  const hashShort = hashFull.slice(0, 16);

  const ts = _formatTs(row.ts_ns ?? e.timestamp_ns);
  const tech = Array.isArray(e.mitre_attack_technique) && e.mitre_attack_technique.length
    ? e.mitre_attack_technique[0] : null;

  const meta = [
    sev,
    tech ? `T${tech.replace(/^T/, '')}` : null,
    e.primary_artifact_key ? _trim(e.primary_artifact_key, 22) : null,
  ].filter(Boolean).join(' · ');

  li.innerHTML = `
    <div class="seq">#${row.seq}</div>
    <div class="body">
      <div class="agent">${_escape(agent)} <span style="opacity:0.5;">·</span> <span style="color:var(--text-dim);">${ts}</span></div>
      <div class="meta">${_escape(meta)}</div>
      <div class="hash" title="${_escape(hashFull)}">⎔ ${_escape(hashShort)}…</div>
    </div>
  `;
  return li;
}

function _formatTs(ns) {
  if (!ns) return '—';
  const ms = Number(ns) / 1e6;
  if (!Number.isFinite(ms)) return '—';
  const d = new Date(ms);
  // HH:MM:SS — operator-friendly, year is contextual
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function _trim(s, n) {
  s = String(s);
  return s.length <= n ? s : s.slice(0, n - 1) + '…';
}

function _escape(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
