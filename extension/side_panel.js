/**
 * Flow Kit — Side Panel
 * Displays live connection status, metrics, and request log.
 */

// ── Type label map ───────────────────────────────────────────

const TYPE_LABELS = {
  // Worker request types
  GENERATE_IMAGE:           'GEN IMAGE',
  REGENERATE_IMAGE:         'REGEN IMAGE',
  EDIT_IMAGE:               'EDIT IMAGE',
  GENERATE_CHARACTER_IMAGE: 'GEN REF',
  REGENERATE_CHARACTER_IMAGE: 'REGEN REF',
  EDIT_CHARACTER_IMAGE:     'EDIT REF',
  GENERATE_VIDEO:           'GEN VIDEO',
  GENERATE_VIDEO_REFS:      'GEN VIDEO FROM REFS',
  UPSCALE_VIDEO:            'UPSCALE VIDEO',
  // Captcha action types
  IMAGE_GENERATION:         'GEN IMAGE',
  VIDEO_GENERATION:         'GEN VIDEO',
  // Extension-classified API types
  GEN_IMG:                  'GEN IMAGE',
  GEN_VID:                  'GEN VIDEO',
  GEN_VID_REF:              'GEN VIDEO FROM REFS',
  UPSCALE:                  'UPSCALE VIDEO',
  UPS_IMG:                  'UPSCALE IMAGE',
  POLL:                     'CHECK GEN VIDEO',
  CREDITS:                  'CHECK CREDIT',
  CREATE_PROJECT:           'CREATE PROJECT',
  UPLOAD:                   'UPLOAD IMAGE',
  MEDIA:                    'READ MEDIA',
  TRACKING:                 'GOOGLE FLOW TRACK',
  URL_REFRESH:              'URL REFRESH',
  TRPC:                     'TRPC',
  API:                      'API',
};

let _activeProjectId = '';
let _projectPollTimer = null;
let _keepAlivePort = null;
let _keepAliveTimer = null;
let _lastReconnectKickAt = 0;
const PROJECT_ID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function normalizeProjectId(value) {
  const raw = String(value || '').trim().toLowerCase();
  return PROJECT_ID_RE.test(raw) ? raw : '';
}

function inferProjectIdFromEntries(entries) {
  if (!Array.isArray(entries)) return '';
  for (const entry of entries) {
    const pid = normalizeProjectId(
      entry?.projectId || entry?.project_id || entry?.project || '',
    );
    if (pid) return pid;
  }
  return '';
}

function formatType(type) {
  if (!type) return '—';
  return TYPE_LABELS[type] || type.slice(0, 5).toUpperCase();
}

// ── Time formatting ──────────────────────────────────────────

function formatTime(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    const ss = String(d.getSeconds()).padStart(2, '0');
    return `${hh}:${mm}:${ss}`;
  } catch {
    return '—';
  }
}

// ── Status update ────────────────────────────────────────────

function updateStatus(data) {
  if (!data) return;

  // Connection dot
  const dot = document.getElementById('conn-dot');
  const connected = data.agentConnected;
  dot.className = connected ? 'on' : '';

  // Toggle state
  const toggle = document.getElementById('main-toggle');
  const toggleLabel = document.getElementById('toggle-label');
  const isOn = !data.manualDisconnect;
  toggle.checked = isOn;
  toggleLabel.textContent = isOn ? 'ON' : 'OFF';

  // State badge
  const stateBadge = document.getElementById('state-badge');
  const st = data.state || 'off';
  stateBadge.textContent = st;
  stateBadge.className = st; // idle | running | off

  // Token status
  const tokenEl = document.getElementById('token-status');
  const tokenAuthState = String(
    data.tokenAuthState
    || data.metrics?.tokenAuthState
    || 'unknown',
  );
  const tokenAuthError = String(
    data.tokenAuthError
    || data.metrics?.tokenAuthError
    || '',
  );
  if (data.flowKeyPresent) {
    const ageMs = data.tokenAge || 0;
    const ageMin = Math.round(ageMs / 60000);
    if (tokenAuthState === 'invalid') {
      tokenEl.textContent = tokenAuthError
        ? `token invalid (${tokenAuthError}) — open Flow to refresh`
        : 'token expired/invalid — open Flow to refresh';
      tokenEl.className = 'bad';
    } else if (tokenAuthState === 'valid') {
      tokenEl.textContent = `token valid · synced ${ageMin}m`;
      tokenEl.className = 'ok';
    } else if (ageMs > 3600000) {
      tokenEl.textContent = `token stale ${ageMin}m — open Flow to refresh`;
      tokenEl.className = 'warn';
    } else {
      tokenEl.textContent = `token synced ${ageMin}m (pending verify)`;
      tokenEl.className = 'warn';
    }
    // Auto-refresh when token age > 55 min and not yet verified valid.
    if (ageMs > 3300000 && data.agentConnected && tokenAuthState !== 'valid') {
      chrome.runtime.sendMessage({ type: 'REFRESH_TOKEN' });
    }
  } else {
    tokenEl.textContent = 'no token';
    tokenEl.className = 'bad';
  }

  // Metrics
  const m = data.metrics || {};
  document.getElementById('m-total').textContent   = m.requestCount || 0;
  document.getElementById('m-success').textContent = m.successCount || 0;
  document.getElementById('m-failed').textContent  = m.failedCount  || 0;

  const runtimeProjectId = normalizeProjectId(data.activeProjectId);
  if (runtimeProjectId) {
    setProjectId(runtimeProjectId);
  }

  // Auto-heal: if user did not manually disconnect but WS is down, trigger reconnect.
  if (!connected && !data.manualDisconnect) {
    const now = Date.now();
    if (now - _lastReconnectKickAt > 5000) {
      _lastReconnectKickAt = now;
      chrome.runtime.sendMessage({ type: 'RECONNECT' }).catch(() => {});
    }
  }
}

// ── Request log ──────────────────────────────────────────────

function updateRequestLog(entries) {
  const tbody = document.getElementById('log-body');
  const countEl = document.getElementById('log-count');

  if (!entries || entries.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="log-empty">No requests yet</td></tr>';
    countEl.textContent = '0';
    return;
  }

  countEl.textContent = entries.length;
  _logEntries = entries;
  const latestPid = inferProjectIdFromEntries(entries);
  if (latestPid) setProjectId(latestPid);

  // Render newest first (entries already sorted DESC by background.js)
  const rows = entries.map((entry) => {
    const shortId = entry.id ? String(entry.id).slice(0, 8) : '—';
    const type   = formatType(entry.type || entry.method);
    const projectId = normalizeProjectId(entry.projectId || entry.project_id || '');
    const shortProject = projectId ? `${projectId.slice(0, 8)}…` : '—';
    const time   = formatTime(entry.time || entry.timestamp || entry.createdAt);
    const status = entry.status || entry.state || 'pending';
    const error  = entry.error || '';

    let badgeHtml;
    if (status === 'COMPLETED' || status === 'success') {
      badgeHtml = '<span class="badge badge-ok">&#10003; done</span>';
    } else if (status === 'FAILED' || status === 'failed' || (typeof status === 'number' && status >= 400)) {
      badgeHtml = '<span class="badge badge-fail">&#10007; fail</span>';
    } else if (status === 'PROCESSING') {
      badgeHtml = '<span class="badge badge-proc">&#9203; gen...</span>';
    } else if (status === 200 || status === 'processing') {
      badgeHtml = '<span class="badge badge-proc">&#9203; sent</span>';
    } else {
      badgeHtml = '<span class="badge badge-proc">&#9203; sent</span>';
    }

    const errorDisplay = error
      ? `<td class="td-error" title="${escHtml(error)}">${escHtml(truncate(error, 28))}</td>`
      : `<td class="td-error empty">—</td>`;

    return `<tr>
      <td class="td-id" data-request-id="${escHtml(entry.id || '')}">${escHtml(shortId)}</td>
      <td class="td-type">${escHtml(type)}</td>
      <td class="td-project" title="${escHtml(projectId || '—')}" ${projectId ? `data-project-id="${escHtml(projectId)}"` : ''}>${escHtml(shortProject)}</td>
      <td class="td-time">${escHtml(time)}</td>
      <td>${badgeHtml}</td>
      ${errorDisplay}
    </tr>`;
  });

  tbody.innerHTML = rows.join('');

  // Attach click handlers to ID cells
  tbody.querySelectorAll('.td-id[data-request-id]').forEach(td => {
    td.addEventListener('click', () => {
      const reqId = td.getAttribute('data-request-id');
      if (reqId) showRequestDetail(reqId);
    });
  });
  tbody.querySelectorAll('.td-project[data-project-id]').forEach(td => {
    td.addEventListener('click', async () => {
      const pid = td.getAttribute('data-project-id');
      if (!pid) return;
      try {
        await navigator.clipboard.writeText(pid);
        setProjectId(pid);
      } catch {
        // ignore clipboard errors
      }
    });
  });
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function truncate(str, len) {
  if (!str || str.length <= len) return str;
  return str.slice(0, len) + '…';
}

function setProjectId(projectId) {
  _activeProjectId = normalizeProjectId(projectId);
  const idEl = document.getElementById('project-id');
  const copyBtn = document.getElementById('btn-copy-project');
  if (!idEl || !copyBtn) return;
  if (_activeProjectId) {
    idEl.textContent = _activeProjectId;
    idEl.title = _activeProjectId;
    copyBtn.disabled = false;
  } else {
    idEl.textContent = '—';
    idEl.title = 'No active project';
    copyBtn.disabled = true;
  }
}

async function fetchProjectId() {
  try {
    const res = await fetch(`http://127.0.0.1:8100/api/active-project?_=${Date.now()}`, {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache, no-store, max-age=0',
        Pragma: 'no-cache',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const apiProjectId = normalizeProjectId(data?.project_id);
    if (apiProjectId) {
      setProjectId(apiProjectId);
      return;
    }
    if (_activeProjectId) return;
  } catch {
    // keep current value, fall back to log/status derived project id
  }

  if (_activeProjectId) return;
  const fromLog = inferProjectIdFromEntries(_logEntries);
  if (fromLog) setProjectId(fromLog);
}

async function copyProjectId() {
  if (!_activeProjectId) return;
  const btn = document.getElementById('btn-copy-project');
  const oldText = btn.textContent;
  try {
    await navigator.clipboard.writeText(_activeProjectId);
    btn.textContent = 'Copied';
  } catch {
    const ta = document.createElement('textarea');
    ta.value = _activeProjectId;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { document.execCommand('copy'); btn.textContent = 'Copied'; } catch { btn.textContent = 'Failed'; }
    document.body.removeChild(ta);
  }
  setTimeout(() => { btn.textContent = oldText || 'Copy'; }, 1000);
}

// ── Request detail modal ────────────────────────────────────

let _logEntries = [];

function showRequestDetail(reqId) {
  const entry = _logEntries.find(e => e.id === reqId);
  if (!entry) return;

  const overlay = document.getElementById('detail-overlay');
  const title = document.getElementById('detail-title');
  const body = document.getElementById('detail-body');

  title.textContent = `Request ${String(reqId).slice(0, 12)}`;

  const fields = [
    ['ID', entry.id],
    ['Type', formatType(entry.type || entry.method)],
    ['Project ID', normalizeProjectId(entry.projectId || entry.project_id || '') || '—'],
    ['Time', formatTime(entry.time || entry.timestamp || entry.createdAt)],
    ['Status', entry.status || entry.state || 'pending'],
    ['HTTP', entry.httpStatus || '—'],
    ['URL', entry.url || '—'],
    ['Payload', entry.payloadSummary || '—'],
    ['Response', entry.responseSummary || '—'],
    ['Error', entry.error || '—'],
  ];

  body.innerHTML = fields.map(([label, value]) => {
    let cls = 'detail-value';
    if (label === 'Error' && value && value !== '—') cls += ' error';
    if (label === 'Status' && (value === 'COMPLETED' || value === 'success')) cls += ' ok';
    return `<div class="detail-row">
      <div class="detail-label">${escHtml(label)}</div>
      <div class="${cls}">${escHtml(String(value || '—'))}</div>
    </div>`;
  }).join('');

  overlay.classList.add('open');
}

document.getElementById('detail-close').addEventListener('click', () => {
  document.getElementById('detail-overlay').classList.remove('open');
});

document.getElementById('detail-overlay').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) {
    e.currentTarget.classList.remove('open');
  }
});

// ── Initial data fetch ───────────────────────────────────────

function fetchStatus() {
  chrome.runtime.sendMessage({ type: 'STATUS' }, (data) => {
    if (chrome.runtime.lastError) return;
    updateStatus(data);
  });
}

function fetchLog() {
  chrome.runtime.sendMessage({ type: 'REQUEST_LOG' }, (data) => {
    if (chrome.runtime.lastError) return;
    if (data && data.log) updateRequestLog(data.log);
  });
}

// ── Message listener (push updates) ─────────────────────────

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'STATUS_PUSH') {
    fetchStatus();
  }
  if (msg.type === 'REQUEST_LOG_UPDATE') {
    if (msg.log) updateRequestLog(msg.log);
  }
});

// ── Toggle (connect / disconnect) ───────────────────────────

document.getElementById('main-toggle').addEventListener('change', (e) => {
  const msgType = e.target.checked ? 'RECONNECT' : 'DISCONNECT';
  chrome.runtime.sendMessage({ type: msgType }, () => {
    if (chrome.runtime.lastError) return;
    setTimeout(fetchStatus, 400);
  });
});

// ── Action buttons ───────────────────────────────────────────

document.getElementById('btn-flow').addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'OPEN_FLOW_TAB' }, () => {
    if (chrome.runtime.lastError) return;
  });
});

document.getElementById('btn-token').addEventListener('click', () => {
  const btn = document.getElementById('btn-token');
  btn.textContent = 'Opening...';
  btn.disabled = true;
  chrome.runtime.sendMessage({ type: 'REFRESH_TOKEN' }, () => {
    if (chrome.runtime.lastError) { /* ignore */ }
    btn.textContent = 'Refresh Token';
    btn.disabled = false;
  });
});

document.getElementById('btn-copy-project').addEventListener('click', () => {
  copyProjectId();
});

function connectKeepAlivePort() {
  if (_keepAlivePort) return;
  try {
    _keepAlivePort = chrome.runtime.connect({ name: 'side-panel-keepalive' });
  } catch {
    _keepAlivePort = null;
    return;
  }

  _keepAlivePort.onDisconnect.addListener(() => {
    _keepAlivePort = null;
    if (_keepAliveTimer) {
      clearInterval(_keepAliveTimer);
      _keepAliveTimer = null;
    }
    setTimeout(connectKeepAlivePort, 1000);
  });

  if (_keepAliveTimer) clearInterval(_keepAliveTimer);
  _keepAliveTimer = setInterval(() => {
    try {
      _keepAlivePort?.postMessage({ type: 'PING', t: Date.now() });
    } catch {
      // ignore; onDisconnect will reconnect
    }
  }, 10000);
}

// ── Init ─────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  connectKeepAlivePort();
  fetchStatus();
  fetchLog();
  fetchProjectId();
  if (_projectPollTimer) clearInterval(_projectPollTimer);
  _projectPollTimer = setInterval(fetchProjectId, 3000);
});
