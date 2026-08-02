/**
 * Flow Kit — Chrome Extension Background Service Worker
 *
 * Connects to local Python agent via WebSocket (agent runs WS server).
 * Captures bearer token, solves reCAPTCHA, proxies API calls through browser.
 */

const AGENT_WS_URL = 'ws://127.0.0.1:9222';
// NOTE: This is a browser-restricted public API key — safe to ship in extension bundles.
const API_KEY = 'AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY';

let ws = null;
let flowKey = null;
let identity = null;   // { email, name, picture, sub } — Google account signed into Flow
let callbackSecret = null;  // Auth secret for HTTP callback, received from server on WS connect
let state = 'off'; // off | idle | running
let manualDisconnect = false;

// ─── Flow Music (flowmusic.app) state ───────────────────────
// Kiến trúc auth khác hẳn Flow video: bearer là JWT của Supabase (không phải ya29 của
// Google), route qua chính www.flowmusic.app/__api/* (Next.js API, session cookie +
// Authorization kèm thêm) — không có reCAPTCHA nào chặn các API đã khảo sát.
let musicKey = null;        // Supabase JWT access_token bắt được qua webRequest
let musicKeyCapturedAt = null;
let musicIdentity = null;   // { email, name, picture, sub } decode thẳng từ payload JWT
let metrics = {
  tokenCapturedAt: null,
  requestCount: 0,   // captcha-consuming requests only (gen image/video/upscale)
  successCount: 0,
  failedCount: 0,
  lastError: null,
};

// ─── URL → Log Type Classifier ─────────────────────────────

// Visible log types — only these appear in the request log
const _VISIBLE_TYPES = new Set(['GEN_IMG', 'GEN_VID', 'GEN_VID_REF', 'UPSCALE', 'UPS_IMG', 'TRACKING', 'URL_REFRESH']);

function _classifyApiUrl(url) {
  if (url.includes('uploadImage')) return 'UPLOAD';
  if (url.includes('batchGenerateImages')) return 'GEN_IMG';
  if (url.includes('UpsampleVideo')) return 'UPSCALE';
  if (url.includes('ReferenceImages')) return 'GEN_VID_REF';
  if (url.includes('batchAsyncGenerateVideo')) return 'GEN_VID';
  if (url.includes('batchCheckAsync')) return 'POLL';
  if (url.includes('upsampleImage')) return 'UPS_IMG';
  if (url.includes('/media/')) return 'MEDIA';
  if (url.includes('/credits')) return 'CREDITS';
  return 'API';
}

// ─── Request Log ────────────────────────────────────────────

let requestLog = [];

function addRequestLog(entry) {
  requestLog.unshift(entry);
  if (requestLog.length > 100) requestLog.pop();
  broadcastRequestLog();
}

function updateRequestLog(id, updates) {
  const entry = requestLog.find((e) => e.id === id);
  if (entry) Object.assign(entry, updates);
  broadcastRequestLog();
}

function broadcastRequestLog() {
  chrome.runtime.sendMessage({ type: 'REQUEST_LOG_UPDATE', log: requestLog }).catch(() => { });
}

// ─── Startup ────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(init);
chrome.runtime.onStartup.addListener(init);
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'reconnect') connectToAgent();
  if (alarm.name === 'keepAlive') keepAlive();
  if (alarm.name === 'token-refresh') {
    await captureTokenFromFlowTab();
    await fetchIdentity();
  }
  if (alarm.name === 'identity-refresh') await fetchIdentity();
  if (alarm.name === 'music-token-refresh') await ensureFlowMusicTab();
});

async function init() {
  const data = await chrome.storage.local.get([
    'flowKey', 'metrics', 'callbackSecret', 'identity',
    'musicKey', 'musicKeyCapturedAt', 'musicIdentity',
  ]);
  if (data.flowKey) flowKey = data.flowKey;
  if (data.identity) identity = data.identity;
  if (data.metrics) Object.assign(metrics, data.metrics);
  if (data.callbackSecret) callbackSecret = data.callbackSecret;
  if (data.musicKey) musicKey = data.musicKey;
  if (data.musicKeyCapturedAt) musicKeyCapturedAt = data.musicKeyCapturedAt;
  if (data.musicIdentity) musicIdentity = data.musicIdentity;
  connectToAgent();
  chrome.alarms.create('keepAlive', { periodInMinutes: 0.4 });
}

// ─── Token Capture ──────────────────────────────────────────

chrome.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    if (!details?.requestHeaders?.length) return;
    const authHeader = details.requestHeaders.find(
      (h) => h.name?.toLowerCase() === 'authorization',
    );
    const value = authHeader?.value || '';
    if (!value.startsWith('Bearer ya29.')) return;

    const token = value.replace(/^Bearer\s+/i, '').trim();
    if (!token) return;

    // Token ĐỔI = phiên mới: hết hạn tự gia hạn, hoặc người dùng vừa đổi tài khoản Google.
    // Trường hợp sau phải bắt ngay, nếu không agent còn tưởng là account cũ tới tận lần
    // alarm sau và sẽ cho thao tác lên nhầm tài khoản.
    const tokenChanged = token !== flowKey;

    // Always update — even if same token string, refresh the timestamp
    flowKey = token;
    metrics.tokenCapturedAt = Date.now();
    chrome.storage.local.set({ flowKey, metrics });
    console.log('[FlowAgent] Bearer token captured');

    // Notify agent
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'token_captured', flowKey }));
    }
    // Listener này chạy rất dày → chỉ dò lại khi CHƯA biết tài khoản, hoặc khi token vừa đổi.
    if (!identity || tokenChanged) fetchIdentity();
  },
  { urls: ['https://aisandbox-pa.googleapis.com/*', 'https://labs.google/*'] },
  ['requestHeaders', 'extraHeaders'],
);

// Flow Music: bearer là Supabase JWT (tiền tố "eyJ", không phải "ya29." của Google) —
// gửi kèm cả trên các call same-origin tới www.flowmusic.app lẫn tới sb.flowmusic.app.
chrome.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    if (!details?.requestHeaders?.length) return;
    const authHeader = details.requestHeaders.find(
      (h) => h.name?.toLowerCase() === 'authorization',
    );
    const value = authHeader?.value || '';
    if (!value.startsWith('Bearer eyJ')) return;

    const token = value.replace(/^Bearer\s+/i, '').trim();
    if (!token || token === musicKey) {
      if (token) musicKeyCapturedAt = Date.now();
      return;
    }

    musicKey = token;
    musicKeyCapturedAt = Date.now();
    chrome.storage.local.set({ musicKey, musicKeyCapturedAt });
    console.log('[FlowAgent] Flow Music bearer token captured');

    const payload = _decodeJwtPayload(token);
    if (payload?.email || payload?.sub) {
      musicIdentity = {
        email: payload.email ? String(payload.email).trim().toLowerCase() : null,
        name: payload.user_metadata?.full_name || payload.user_metadata?.name || null,
        picture: payload.user_metadata?.picture || payload.user_metadata?.avatar_url || null,
        sub: payload.sub || null,
      };
      chrome.storage.local.set({ musicIdentity });
    }

    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'music_token_captured', musicKey }));
      if (musicIdentity) ws.send(JSON.stringify({ type: 'music_identity', identity: musicIdentity }));
    }
  },
  { urls: ['https://www.flowmusic.app/*', 'https://sb.flowmusic.app/*'] },
  ['requestHeaders', 'extraHeaders'],
);

/** Decode a JWT payload without verifying signature — chỉ để đọc email/sub cho hiển thị,
 *  không dùng cho mục đích xác thực (server tự verify khi request thật). */
function _decodeJwtPayload(token) {
  try {
    const part = token.split('.')[1];
    const b64 = part.replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(
      atob(b64).split('').map((c) => '%' + c.charCodeAt(0).toString(16).padStart(2, '0')).join(''),
    );
    return JSON.parse(json);
  } catch {
    return null;
  }
}

async function ensureFlowMusicTab() {
  const tabs = await chrome.tabs.query({ url: ['https://www.flowmusic.app/*'] });
  if (tabs.length) return tabs[0];
  console.log('[FlowAgent] No Flow Music tab found — opening one in background');
  return await chrome.tabs.create({ url: 'https://www.flowmusic.app/', active: false });
}

let _openingFlowTab = false;

async function captureTokenFromFlowTab() {
  const tabs = await chrome.tabs.query({
    url: ['https://labs.google/fx/tools/flow*', 'https://labs.google/fx/*/tools/flow*'],
  });
  if (!tabs.length) {
    if (_openingFlowTab) {
      console.log('[FlowAgent] Flow tab already opening, skipping');
      return;
    }
    _openingFlowTab = true;
    try {
      console.log('[FlowAgent] No Flow tab found — opening one in background');
      await chrome.tabs.create({ url: 'https://labs.google/fx/tools/flow', active: false });
      await sleep(3000);
      const retryTabs = await chrome.tabs.query({
        url: ['https://labs.google/fx/tools/flow*', 'https://labs.google/fx/*/tools/flow*'],
      });
      if (!retryTabs.length) {
        console.log('[FlowAgent] Flow tab not ready yet after open');
        return;
      }
      await chrome.scripting.executeScript({
        target: { tabId: retryTabs[0].id },
        files: ['content.js'],
      });
      console.log('[FlowAgent] Token refresh triggered on newly opened Flow tab');
    } catch (e) {
      console.error('[FlowAgent] Token refresh failed after opening tab:', e);
    } finally {
      _openingFlowTab = false;
    }
    return;
  }
  try {
    await chrome.scripting.executeScript({
      target: { tabId: tabs[0].id },
      files: ['content.js'],
    });
    console.log('[FlowAgent] Token refresh triggered on Flow tab');
  } catch (e) {
    console.error('[FlowAgent] Token refresh failed:', e);
  }
}

// ─── Account identity ───────────────────────────────────────
// Mọi thứ trên Flow — project, media, credit — thuộc về TÀI KHOẢN Google đang đăng nhập
// trong Chrome. Agent cần biết tài khoản đó để không trộn dự án của account này sang
// account khác (media_id của account A không resolve được bằng token của account B).
//
// Nguồn chính: `/fx/api/auth/session` — Flow là một app NextAuth, endpoint này trả
// `{ user: { email, name, image }, access_token }` theo cookie phiên. Gọi thẳng từ service
// worker (đã có host permission labs.google/*) nên không phải cào DOM.
// Dự phòng: tokeninfo của chính bearer ya29 → cho `sub` (id Google bền vững) và thường cả
// email; dùng khi endpoint session đổi shape.

async function _identityFromSession() {
  const res = await fetch('https://labs.google/fx/api/auth/session', {
    credentials: 'include',
    headers: { accept: 'application/json' },
  });
  if (!res.ok) return null;
  const u = (await res.json())?.user || {};
  if (!u.email) return null;
  return {
    email: String(u.email).trim().toLowerCase(),
    name: u.name || null,
    picture: u.image || null,
    sub: u.id || null,
    source: 'session',
  };
}

/** Cùng endpoint, nhưng fetch TỪ TRONG tab Flow: request cùng origin nên cookie phiên chắc
 *  chắn được gửi kèm — dùng khi fetch từ service worker về rỗng (cookie SameSite). */
async function _identityFromFlowTab() {
  const tabs = await chrome.tabs.query({
    url: ['https://labs.google/fx/tools/flow*', 'https://labs.google/fx/*/tools/flow*'],
  });
  if (!tabs.length) return null;
  const [res] = await chrome.scripting.executeScript({
    target: { tabId: tabs[0].id },
    func: async () => {
      try {
        const r = await fetch('/fx/api/auth/session', { headers: { accept: 'application/json' } });
        return r.ok ? await r.json() : null;
      } catch { return null; }
    },
  });
  const u = res?.result?.user;
  if (!u?.email) return null;
  return {
    email: String(u.email).trim().toLowerCase(),
    name: u.name || null,
    picture: u.image || null,
    sub: u.id || null,
    source: 'flow-tab',
  };
}

async function _identityFromTokenInfo() {
  if (!flowKey) return null;
  const res = await fetch(
    'https://oauth2.googleapis.com/tokeninfo?access_token=' + encodeURIComponent(flowKey),
  );
  if (!res.ok) return null;
  const d = await res.json();
  if (!d?.email && !d?.sub) return null;
  return {
    email: d.email ? String(d.email).trim().toLowerCase() : null,
    name: null,
    picture: null,
    sub: d.sub || null,
    source: 'tokeninfo',
  };
}

/** Lấy tài khoản đang đăng nhập; báo agent khi đổi account. Trả về identity hoặc null. */
async function fetchIdentity({ notify = true } = {}) {
  let next = null;
  for (const probe of [_identityFromSession, _identityFromFlowTab, _identityFromTokenInfo]) {
    try {
      next = await probe();
      if (next) break;
    } catch (e) {
      console.warn('[FlowAgent] identity probe failed:', probe.name, e?.message || e);
    }
  }
  if (!next) {
    console.warn('[FlowAgent] Không xác định được tài khoản Flow (chưa đăng nhập?)');
    return identity;   // giữ giá trị cũ, đừng xoá — mạng lỗi không có nghĩa là đã đăng xuất
  }
  const changed = next.email !== identity?.email || next.sub !== identity?.sub;
  identity = { ...next, fetchedAt: Date.now() };
  chrome.storage.local.set({ identity });
  if (changed) console.log('[FlowAgent] Tài khoản Flow:', identity.email || identity.sub);
  if (notify) sendIdentityToAgent();
  return identity;
}

function sendIdentityToAgent() {
  if (identity && ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'identity', identity }));
  }
}

// ─── WebSocket to Agent ─────────────────────────────────────

function connectToAgent() {
  if (manualDisconnect) return;
  if (ws?.readyState === WebSocket.CONNECTING) return;
  if (ws?.readyState === WebSocket.OPEN) return;

  try {
    ws = new WebSocket(AGENT_WS_URL);
  } catch (e) {
    console.error('[FlowAgent] WS connect error:', e);
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    console.log('[FlowAgent] Connected to agent');
    chrome.alarms.clear('reconnect');
    setState('idle');

    // Token refresh alarm — 45 min gives buffer before ~60 min expiry
    chrome.alarms.create('token-refresh', { periodInMinutes: 45 });
    // Lưới an toàn cho việc đổi tài khoản: bình thường token đổi là bắt được ngay, nhưng nếu
    // người dùng đổi account ở tab khác mà chưa gọi API nào thì 2 phút sau vẫn nhận ra.
    chrome.alarms.create('identity-refresh', { periodInMinutes: 2 });
    // Flow Music: JWT Supabase cũng sống ~60 phút — giữ 1 tab mở để trang tự refresh token
    // (webRequest bắt lại passively), không cần tự dựng lại refresh_token flow.
    chrome.alarms.create('music-token-refresh', { periodInMinutes: 45 });

    // Send current state + resend token if we have one
    ws.send(JSON.stringify({
      type: 'extension_ready',
      flowKeyPresent: !!flowKey,
      tokenAge: flowKey && metrics.tokenCapturedAt ? Date.now() - metrics.tokenCapturedAt : null,
    }));
    // Agent không giữ state qua lần khởi động — gửi lại tài khoản đã biết ngay, rồi dò lại
    // nền phòng khi người dùng đã đổi account trong lúc agent tắt.
    sendIdentityToAgent();
    fetchIdentity();
    if (flowKey) {
      ws.send(JSON.stringify({ type: 'token_captured', flowKey }));
    }
    if (musicKey) {
      ws.send(JSON.stringify({ type: 'music_token_captured', musicKey }));
    }
    if (musicIdentity) {
      ws.send(JSON.stringify({ type: 'music_identity', identity: musicIdentity }));
    }
  };

  ws.onmessage = async ({ data }) => {
    try {
      const msg = JSON.parse(data);

      if (msg.method === 'api_request') {
        await handleApiRequest(msg);
      } else if (msg.method === 'trpc_request') {
        await handleTrpcRequest(msg);
      } else if (msg.method === 'music_api_request') {
        await handleMusicApiRequest(msg);
      } else if (msg.method === 'music_stream_request') {
        await handleMusicStreamRequest(msg);
      } else if (msg.method === 'solve_captcha') {
        await handleSolveCaptcha(msg);
      } else if (msg.method === 'get_status') {
        sendToAgent({
          id: msg.id,
          result: {
            state,
            flowKeyPresent: !!flowKey,
            manualDisconnect,
            tokenAge: metrics.tokenCapturedAt ? Date.now() - metrics.tokenCapturedAt : null,
            metrics,
          },
        });
      } else if (msg.method === 'get_identity') {
        const id = msg.params?.refresh === false ? identity : await fetchIdentity({ notify: false });
        sendToAgent({ id: msg.id, result: id || null });
      } else if (msg.type === 'callback_secret') {
        callbackSecret = msg.secret;
        chrome.storage.local.set({ callbackSecret: msg.secret });
        console.log('[FlowAgent] Received callback secret');
      } else if (msg.type === 'pong') {
        // keepalive response
      }
    } catch (e) {
      console.error('[FlowAgent] Message error:', e);
    }
  };

  ws.onclose = () => {
    setState('off');
    chrome.alarms.clear('token-refresh');
    chrome.alarms.clear('identity-refresh');
    if (!manualDisconnect) scheduleReconnect();
  };

  ws.onerror = (e) => {
    console.error('[FlowAgent] WS error:', e);
    metrics.lastError = 'WS_ERROR';
    chrome.storage.local.set({ metrics });
  };
}

function scheduleReconnect() {
  chrome.alarms.create('reconnect', { delayInMinutes: 0.083 }); // ~5s
}

function keepAlive() {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }));
  } else {
    connectToAgent();
  }
}

function sendToAgent(msg) {
  // API responses (with msg.id) go via HTTP — immune to WS disconnect
  if (msg.id) {
    fetch('http://127.0.0.1:8100/api/ext/callback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(msg),
    }).catch(() => {
      // HTTP failed — fallback to WS
      if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
    });
    return;
  }
  // Non-response messages (ping, status) or no secret yet — use WS
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg));
  }
}

// ─── reCAPTCHA Solving ──────────────────────────────────────

async function requestCaptchaFromTab(tabId, requestId, pageAction) {
  try {
    return await chrome.tabs.sendMessage(tabId, {
      type: 'GET_CAPTCHA',
      requestId,
      pageAction,
    });
  } catch (error) {
    const msg = error?.message || '';
    const shouldInject =
      msg.includes('Receiving end does not exist') ||
      msg.includes('Could not establish connection');
    if (!shouldInject) throw error;

    // Inject content script and retry
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ['content.js'],
    });
    await sleep(200);
    return await chrome.tabs.sendMessage(tabId, {
      type: 'GET_CAPTCHA',
      requestId,
      pageAction,
    });
  }
}

async function solveCaptcha(requestId, captchaAction) {
  const tabs = await chrome.tabs.query({
    url: ['https://labs.google/fx/tools/flow*', 'https://labs.google/fx/*/tools/flow*'],
  });

  if (!tabs.length) {
    // Auto-open Flow tab and wait briefly before returning error
    try {
      await chrome.tabs.create({ url: 'https://labs.google/fx/tools/flow', active: false });
      await sleep(3000);
      // Retry tab query after opening
      const retryTabs = await chrome.tabs.query({
        url: ['https://labs.google/fx/tools/flow*', 'https://labs.google/fx/*/tools/flow*'],
      });
      if (!retryTabs.length) return { error: 'NO_FLOW_TAB' };
      const resp = await Promise.race([
        requestCaptchaFromTab(retryTabs[0].id, requestId, captchaAction),
        new Promise((_, rej) => setTimeout(() => rej(new Error('CAPTCHA_TIMEOUT')), 30000)),
      ]);
      return resp;
    } catch (e) {
      return { error: e.message || 'NO_FLOW_TAB' };
    }
  }

  try {
    const resp = await Promise.race([
      requestCaptchaFromTab(tabs[0].id, requestId, captchaAction),
      new Promise((_, rej) => setTimeout(() => rej(new Error('CAPTCHA_TIMEOUT')), 30000)),
    ]);
    return resp;
  } catch (e) {
    return { error: e.message };
  }
}

async function handleSolveCaptcha(msg) {
  const { id, params } = msg;
  const result = await solveCaptcha(id, params?.captchaAction || 'VIDEO_GENERATION');

  // Standalone captcha solve counts as captcha-consuming
  metrics.requestCount++;
  if (result?.token) {
    metrics.successCount++;
  } else {
    metrics.failedCount++;
    metrics.lastError = result?.error || 'NO_TOKEN';
  }
  chrome.storage.local.set({ metrics });

  sendToAgent({ id, result });
}

// ─── API Request Proxy ──────────────────────────────────────

async function getMediaUrl(
  mediaId
) {

  const [tab] =
    await chrome.tabs.query({

      url: [

        'https://labs.google/fx/tools/flow*',

        'https://labs.google/fx/*/tools/flow*'

      ]

    });

  if (!tab) {

    throw new Error(
      'NO_FLOW_TAB'
    );

  }

  return await chrome.tabs.sendMessage(

    tab.id,

    {

      type:
        'GET_MEDIA_URL',

      requestId:
        crypto.randomUUID(),

      mediaId

    }

  );

}

async function handleTrpcRequest(msg) {
  const { id, params } = msg;
  const { url, method = 'POST', headers = {}, body } = params;

  if (!url || !url.startsWith('https://labs.google/')) {
    sendToAgent({ id, error: 'INVALID_TRPC_URL' });
    return;
  }

  setState('running');
  // TRPC calls don't consume captcha — don't count in metrics

  const logId = id;
  const logType = url.includes('createProject') ? 'CREATE_PROJECT' : 'TRPC';
  const imgType = url.includes('media.getMediaUrlRedirect') ? 'IMAGE' : 'TRPC';
  // TRPC calls are silent — don't show in request log

  if (imgType == 'IMAGE') {

    try {

      const mediaId =

        new URL(url)

          .searchParams

          .get('name');

      const media =

        await getMediaUrl(

          mediaId

        );

      sendToAgent({

        id,

        status:
          media.status,

        data: {

          url:
            media.url,

          redirected:

            media.redirected

        }

      });

    }

    catch (e) {

      sendToAgent({

        id,

        error:

          e.message

      });

    }

    return;

  }

  const fetchHeaders = { 'Content-Type': 'application/json', ...headers };
  if (flowKey) {
    fetchHeaders['authorization'] = `Bearer ${flowKey}`;
  }

  try {
    const resp = await fetch(url, {
      method,
      headers: fetchHeaders,
      body: body ? JSON.stringify(body) : undefined,
      credentials: 'include',
    });
    const data = await resp.json();
    chrome.storage.local.set({ metrics });
    updateRequestLog(logId, { status: 'success' });
    sendToAgent({ id, status: resp.status, data });
  } catch (e) {
    console.error('[FlowAgent] tRPC request failed:', e);
    chrome.storage.local.set({ metrics });
    updateRequestLog(logId, { status: 'failed', error: e.message || 'TRPC_FETCH_FAILED' });
    sendToAgent({ id, error: e.message || 'TRPC_FETCH_FAILED' });
  } finally {
    setState('idle');
  }
}

// ─── Flow Music: API relay + chat/SSE streaming ─────────────
// Khác Flow video: không có reCAPTCHA trên các endpoint đã khảo sát, auth chỉ cần
// Authorization Bearer (Supabase JWT, bắt qua webRequest ở trên) + cookie session (Chrome
// tự đính kèm nhờ credentials:'include' + host permission, không cần tự dựng cookie).

const MUSIC_WEB_ORIGIN = 'https://www.flowmusic.app';

async function handleMusicApiRequest(msg) {
  const { id, params } = msg;
  const { url, method = 'GET', headers = {}, body } = params || {};

  if (!url || !(url.startsWith('https://www.flowmusic.app/') || url.startsWith('https://sb.flowmusic.app/'))) {
    sendToAgent({ id, error: 'INVALID_MUSIC_URL' });
    return;
  }
  if (!musicKey) {
    sendToAgent({ id, status: 503, error: 'NO_MUSIC_KEY' });
    return;
  }

  const fetchHeaders = { 'content-type': 'application/json', ...headers, authorization: `Bearer ${musicKey}` };

  try {
    const resp = await fetch(url, {
      method,
      headers: fetchHeaders,
      credentials: 'include',
      body: (method === 'GET' || method === 'HEAD' || body === undefined) ? undefined : JSON.stringify(body),
    });
    const text = await resp.text();
    let data;
    try { data = text ? JSON.parse(text) : null; } catch { data = text; }
    sendToAgent({ id, status: resp.status, data });
  } catch (e) {
    sendToAgent({ id, status: 500, error: e.message || 'MUSIC_API_REQUEST_FAILED' });
  }
}

/** Gửi 1 tin nhắn vào conversation (mới hoặc có sẵn), rồi đọc trọn vẹn SSE phản hồi tới khi
 *  agent phía Google xong lượt (event "final"), gộp lại thành 1 kết quả trả về 1 lần — khớp
 *  với mô hình request/response sẵn có (agent Python chờ 1 future), không cần thêm cơ chế
 *  push tăng dần qua WS cho ca dùng hiện tại (tạo nhạc, ~30-70s/lượt). */
async function handleMusicStreamRequest(msg) {
  const { id, params } = msg;
  const {
    content, conversation_id = null,
    client_context = {}, model_name = 'producer:standard', mode = 'standard',
    timeout_s = 180,
  } = params || {};

  if (!content) {
    sendToAgent({ id, error: 'MISSING_CONTENT' });
    return;
  }
  if (!musicKey) {
    sendToAgent({ id, status: 503, error: 'NO_MUSIC_KEY' });
    return;
  }

  const fetchHeaders = { 'content-type': 'application/json', authorization: `Bearer ${musicKey}` };

  try {
    const postBody = {
      conversation_id: conversation_id || null,
      parts: [{ content, part_kind: 'user-prompt' }],
      client_context: {
        current_song_id: null, song_queue: [], selected_model: null,
        lyrics_id_map: {}, ghostwriter_version: 'standard',
        ...client_context,
      },
      model_name,
      mode,
    };

    const submitResp = await fetch(`${MUSIC_WEB_ORIGIN}/__api/conversation`, {
      method: 'POST',
      headers: fetchHeaders,
      credentials: 'include',
      body: JSON.stringify(postBody),
    });
    const submitText = await submitResp.text();
    let submitData;
    try { submitData = submitText ? JSON.parse(submitText) : null; } catch { submitData = submitText; }

    if (!submitResp.ok || !submitData?.job_id) {
      sendToAgent({ id, status: submitResp.status || 502, error: 'MUSIC_SUBMIT_FAILED', data: submitData });
      return;
    }

    const jobId = submitData.job_id;
    const result = await _consumeMusicStream(jobId, fetchHeaders, timeout_s);
    sendToAgent({ id, status: 200, data: { job_id: jobId, ...result } });
  } catch (e) {
    sendToAgent({ id, status: 500, error: e.message || 'MUSIC_STREAM_FAILED' });
  }
}

/** Đọc SSE của /__api/messages/{jobId}/stream tới khi kết nối đóng (server tự đóng ngay
 *  sau event "final") hoặc hết timeout. Dùng resp.text() (đợi trọn response) thay vì
 *  ReadableStream.getReader() thủ công — đơn giản hơn, tránh incompat khi đọc stream trong
 *  service worker của extension. */
async function _consumeMusicStream(jobId, fetchHeaders, timeoutS) {
  const url = `${MUSIC_WEB_ORIGIN}/__api/messages/${jobId}/stream?last_id=0`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutS * 1000);
  let text = '';
  let timedOut = false;
  try {
    const resp = await fetch(url, {
      method: 'GET',
      headers: { ...fetchHeaders, accept: 'text/event-stream' },
      credentials: 'include',
      signal: controller.signal,
    });
    if (!resp.ok) throw new Error(`MUSIC_STREAM_HTTP_${resp.status}`);
    text = await resp.text();
  } catch (e) {
    if (controller.signal.aborted) timedOut = true;
    else throw e;
  } finally {
    clearTimeout(timer);
  }

  // Chuẩn hoá CRLF→LF trước khi tách frame theo dòng trống — server có thể dùng "\r\n\r\n".
  const frames = text.replace(/\r\n/g, '\n').split('\n\n');
  let conversationId = null;
  const partsByIndex = new Map(); // index -> part mới nhất (ưu tiên bản "final")
  let finished = false;

  for (const frame of frames) {
    const parsed = _parseSseFrame(frame);
    if (!parsed) continue; // dòng comment/ping thuần (": ping ...") hoặc frame rỗng

    if (parsed.event === 'conversation_id') {
      try { conversationId = JSON.parse(parsed.data)?.id || conversationId; } catch { /* ignore */ }
    } else if (parsed.event === 'part') {
      try {
        const evt = JSON.parse(parsed.data);
        if (evt && typeof evt.index === 'number') partsByIndex.set(evt.index, evt.part);
      } catch { /* ignore */ }
    } else if (parsed.event === 'final') {
      finished = true;
    }
    // "begin"/"complete"/"suggestion" — bỏ qua, đủ dữ liệu từ "part" + "final"
  }

  const parts = [...partsByIndex.entries()].sort((a, b) => a[0] - b[0]).map(([, p]) => p);
  const toolReturns = parts.filter((p) => p.part_kind === 'tool-return');
  const texts = parts.filter((p) => p.part_kind === 'text').map((p) => p.content);

  return {
    conversation_id: conversationId,
    parts,
    tool_returns: toolReturns,
    text: texts.join('\n\n'),
    done: finished,
    timed_out: timedOut && !finished,
  };
}

function _parseSseFrame(frame) {
  const lines = frame.split('\n');
  let event = null;
  const dataLines = [];
  for (const line of lines) {
    if (!line || line.startsWith(':')) continue; // comment/ping
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
  }
  if (!event && !dataLines.length) return null;
  return { event: event || 'message', data: dataLines.join('\n') };
}

async function handleApiRequest(msg) {
  const { id, params } = msg;
  const { url, method, headers, body, captchaAction } = params;

  if (!url) {
    sendToAgent({ id, error: 'MISSING_URL' });
    return;
  }

  if (!url.startsWith('https://aisandbox-pa.googleapis.com/')) {
    sendToAgent({ id, error: 'INVALID_URL' });
    return;
  }

  setState('running');
  const hasCaptcha = !!captchaAction;
  if (hasCaptcha) metrics.requestCount++;

  const logId = id;
  const logType = _classifyApiUrl(url);
  if (_VISIBLE_TYPES.has(logType)) {
    const payloadSummary = body ? JSON.stringify(body).slice(0, 200) : null;
    addRequestLog({ id: logId, type: logType, time: new Date().toISOString(), status: 'processing', error: null, outputUrl: null, url, payloadSummary });
  }

  try {
    // Step 1: Solve captcha if needed
    let captchaToken = null;
    if (captchaAction) {
      const captchaResult = await solveCaptcha(id, captchaAction);
      captchaToken = captchaResult?.token || null;
      if (!captchaToken) {
        // Cannot proceed without captcha — API will 403
        const err = captchaResult?.error || 'CAPTCHA_FAILED';
        console.error(`[FlowAgent] Captcha failed for ${captchaAction}: ${err}`);
        sendToAgent({ id, status: 403, error: `CAPTCHA_FAILED: ${err}` });
        if (hasCaptcha) { metrics.failedCount++; metrics.lastError = `CAPTCHA_FAILED: ${err}`; }
        chrome.storage.local.set({ metrics });
        updateRequestLog(logId, { status: 'failed', error: `CAPTCHA_FAILED: ${err}` });
        setState('idle');
        return;
      }
    }

    // Step 2: Inject captcha token into body
    let finalBody = body;
    if (captchaToken && finalBody) {
      finalBody = JSON.parse(JSON.stringify(finalBody)); // deep clone
      if (finalBody.clientContext?.recaptchaContext) {
        finalBody.clientContext.recaptchaContext.token = captchaToken;
      }
      if (finalBody.requests && Array.isArray(finalBody.requests)) {
        for (const req of finalBody.requests) {
          if (req.clientContext?.recaptchaContext) {
            req.clientContext.recaptchaContext.token = captchaToken;
          }
        }
      }
    }

    // Step 3: Use flowKey for auth
    const activeFlowKey = flowKey;
    if (!activeFlowKey) {
      sendToAgent({ id, status: 503, error: 'NO_FLOW_KEY' });
      if (hasCaptcha) { metrics.failedCount++; metrics.lastError = 'NO_FLOW_KEY'; }
      chrome.storage.local.set({ metrics });
      updateRequestLog(logId, { status: 'failed', error: 'NO_FLOW_KEY' });
      setState('idle');
      return;
    }

    const fetchHeaders = { ...(headers || {}) };
    fetchHeaders['authorization'] = `Bearer ${activeFlowKey}`;

    // Step 4: Make the API call from browser context
    const response = await fetch(url, {
      method: method || 'POST',
      headers: fetchHeaders,
      credentials: 'include',
      body: method === 'GET' ? undefined : JSON.stringify(finalBody),
    });

    let responseData;
    const responseText = await response.text();
    try {
      responseData = JSON.parse(responseText);
    } catch {
      responseData = responseText;
    }

    sendToAgent({
      id,
      status: response.status,
      data: responseData,
    });

    const responseSummary = responseText ? responseText.slice(0, 300) : null;
    if (response.ok) {
      if (hasCaptcha) { metrics.successCount++; metrics.lastError = null; }
      updateRequestLog(logId, { status: 'success', httpStatus: response.status, responseSummary });
    } else {
      if (hasCaptcha) { metrics.failedCount++; metrics.lastError = `API_${response.status}`; }
      updateRequestLog(logId, { status: 'failed', error: `API_${response.status}`, httpStatus: response.status, responseSummary });
    }
  } catch (e) {
    sendToAgent({
      id,
      status: 500,
      error: e.message || 'API_REQUEST_FAILED',
    });
    if (hasCaptcha) { metrics.failedCount++; metrics.lastError = e.message; }
    updateRequestLog(logId, { status: 'failed', error: e.message || 'API_REQUEST_FAILED' });
  }

  chrome.storage.local.set({ metrics });
  setState('idle');
}

// ─── State & Popup ──────────────────────────────────────────

function setState(newState) {
  state = newState;
  const badges = { idle: '●', running: '▶', off: '○' };
  const colors = { idle: '#22c55e', running: '#f59e0b', off: '#6b7280' };
  chrome.action.setBadgeText({ text: badges[state] || '' });
  chrome.action.setBadgeBackgroundColor({ color: colors[state] || '#000' });
  broadcastStatus();
}

function broadcastStatus() {
  chrome.runtime.sendMessage({ type: 'STATUS_PUSH' }).catch(() => { });
}

chrome.runtime.onMessage.addListener((msg, _, reply) => {
  if (msg.type === 'STATUS') {
    reply({
      connected: ws?.readyState === WebSocket.OPEN,
      agentConnected: ws?.readyState === WebSocket.OPEN,
      flowKeyPresent: !!flowKey,
      manualDisconnect,
      account: identity?.email || identity?.sub || null,
      tokenAge: metrics.tokenCapturedAt ? Date.now() - metrics.tokenCapturedAt : null,
      musicKeyPresent: !!musicKey,
      musicAccount: musicIdentity?.email || musicIdentity?.sub || null,
      musicTokenAge: musicKeyCapturedAt ? Date.now() - musicKeyCapturedAt : null,
      metrics: {
        requestCount: metrics.requestCount,
        successCount: metrics.successCount,
        failedCount: metrics.failedCount,
        lastError: metrics.lastError,
      },
      state,
    });
  }

  if (msg.type === 'MEDIA_REDIRECT') {

    console.log('MEDIA REDIRECT');

    console.log(msg.data);

    sendToAgent({

      type: 'MEDIA_REDIRECT',

      data: msg.data

    });

    reply({ ok: true });

    return true;

  }

  if (msg.type === 'DISCONNECT') {
    manualDisconnect = true;
    if (ws) ws.close();
    reply({ ok: true });
    return true;
  }

  if (msg.type === 'RECONNECT') {
    manualDisconnect = false;
    connectToAgent();
    reply({ ok: true });
    return true;
  }

  if (msg.type === 'REQUEST_LOG') {
    reply({ log: requestLog });
    return true;
  }

  if (msg.type === 'OPEN_FLOW_TAB') {
    chrome.tabs.query({
      url: ['https://labs.google/fx/tools/flow*', 'https://labs.google/fx/*/tools/flow*'],
    }).then((tabs) => {
      if (tabs.length) {
        chrome.tabs.update(tabs[0].id, { active: true });
        reply({ ok: true, tabId: tabs[0].id });
      } else {
        chrome.tabs.create({ url: 'https://labs.google/fx/tools/flow' })
          .then((tab) => reply({ ok: true, tabId: tab.id }))
          .catch((e) => reply({ error: e.message }));
      }
    }).catch((e) => reply({ error: e.message }));
    return true;
  }

  if (msg.type === 'REFRESH_TOKEN') {
    captureTokenFromFlowTab()
      .then(() => reply({ ok: true }))
      .catch((e) => reply({ error: e.message }));
    return true;
  }

  if (msg.type === 'TEST_CAPTCHA') {
    solveCaptcha(`test-${Date.now()}`, msg.pageAction || 'IMAGE_GENERATION')
      .then((r) => reply(r))
      .catch((e) => reply({ error: e.message }));
    return true;
  }

  if (msg.type === 'TRPC_MEDIA_URLS') {
    handleTrpcMediaUrls(msg.trpcUrl, msg.body);
    reply({ ok: true });
    return true;
  }

  return true;
});

// ─── TRPC Media URL Extractor ──────────────────────────────

function handleTrpcMediaUrls(trpcUrl, bodyText) {
  try {
    // Extract all fresh GCS signed URLs
    const urlRegex = /https:\/\/storage\.googleapis\.com\/ai-sandbox-videofx\/(?:image|video)\/[0-9a-f-]{36}\?[^"'\s]+/g;
    const matches = bodyText.match(urlRegex) || [];
    if (!matches.length) return;

    // Deduplicate and parse
    const urlMap = {};
    for (const rawUrl of matches) {
      // Unescape JSON-escaped URLs
      const url = rawUrl.replace(/\\u0026/g, '&').replace(/\\/g, '');
      const mediaMatch = url.match(/\/(image|video)\/([0-9a-f-]{36})\?/);
      if (mediaMatch) {
        const [, mediaType, mediaId] = mediaMatch;
        // Keep last occurrence (freshest)
        urlMap[mediaId] = { mediaType, url, mediaId };
      }
    }

    const entries = Object.values(urlMap);
    if (!entries.length) return;

    console.log(`[FlowAgent] Captured ${entries.length} fresh media URLs from TRPC`);
    // URL refresh is silent — don't show in request log

    // Forward to agent for DB update
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'media_urls_refresh',
        urls: entries,
      }));
    }
  } catch (e) {
    console.error('[FlowAgent] Failed to extract TRPC media URLs:', e);
  }
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// ─── Human-like Telemetry ──────────────────────────────────
// Periodically send tracking events to Google's analytics endpoints
// to mimic normal browser behavior.

const _UA = navigator.userAgent;
let _telemetrySessionId = `;${Date.now()}`;

function _rand(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }

function _buildBatchLogPayload() {
  const events = [];
  const types = ['FLOW_IMAGE_LATENCY', 'FLOW_VIDEO_LATENCY'];
  const count = _rand(1, 3);
  for (let i = 0; i < count; i++) {
    events.push({
      event: types[_rand(0, types.length - 1)],
      eventProperties: [
        { key: 'CURRENT_TIME_MS', doubleValue: Date.now() },
        { key: 'DURATION_MS', doubleValue: _rand(150, 800) },
        { key: 'USER_AGENT', stringValue: _UA },
        { key: 'IS_DESKTOP', booleanValue: true },
      ],
      eventMetadata: { sessionId: _telemetrySessionId },
      eventTime: new Date().toISOString(),
    });
  }
  return { appEvents: events };
}

function _buildFrontendEventsPayload() {
  const eventTypes = [
    'FLOW_IMAGE_LATENCY', 'FLOW_VIDEO_LATENCY', 'GRID_SCROLL_DEPTH',
    'FLOW_PROJECT_OPEN', 'FLOW_SCENE_VIEW',
  ];
  const count = _rand(1, 4);
  const events = [];
  for (let i = 0; i < count; i++) {
    const et = eventTypes[_rand(0, eventTypes.length - 1)];
    const params = {
      USER_AGENT: { '@type': 'type.googleapis.com/google.protobuf.StringValue', value: _UA },
      IS_DESKTOP: { '@type': 'type.googleapis.com/google.protobuf.StringValue', value: 'true' },
    };
    if (et.includes('LATENCY')) {
      params.CURRENT_TIME_MS = { '@type': 'type.googleapis.com/google.protobuf.StringValue', value: String(Date.now()) };
      params.DURATION_MS = { '@type': 'type.googleapis.com/google.protobuf.StringValue', value: String(_rand(100, 600)) };
    }
    if (et === 'GRID_SCROLL_DEPTH') {
      params.MEDIA_GENERATION_PAYGATE_TIER = { '@type': 'type.googleapis.com/google.protobuf.StringValue', value: 'PAYGATE_TIER_TWO' };
    }
    events.push({
      eventType: et,
      metadata: {
        sessionId: _telemetrySessionId,
        createTime: new Date().toISOString(),
        additionalParams: params,
      },
    });
  }
  return { events };
}

async function sendTelemetry() {
  if (!flowKey || state === 'off') return;

  const headers = {
    'Content-Type': 'text/plain;charset=UTF-8',
    'authorization': `Bearer ${flowKey}`,
  };

  // Telemetry is silent — don't show in request log
  try {
    if (Math.random() < 0.5) {
      await fetch(`https://aisandbox-pa.googleapis.com/v1:batchLog`, {
        method: 'POST', headers, credentials: 'include',
        body: JSON.stringify(_buildBatchLogPayload()),
      });
    } else {
      await fetch(`https://aisandbox-pa.googleapis.com/v1/flow:batchLogFrontendEvents`, {
        method: 'POST', headers, credentials: 'include',
        body: JSON.stringify(_buildFrontendEventsPayload()),
      });
    }
  } catch { }
}

// Send telemetry at random intervals (45-120s) to look organic
function scheduleTelemetry() {
  const delay = _rand(45, 120) * 1000;
  setTimeout(async () => {
    await sendTelemetry();
    scheduleTelemetry(); // reschedule with new random interval
  }, delay);
}

// Refresh session ID every ~30min like a real user
setInterval(() => { _telemetrySessionId = `;${Date.now()}`; }, _rand(25, 35) * 60 * 1000);

scheduleTelemetry();

console.log('[FlowAgent] Extension loaded');
