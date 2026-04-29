/**
 * Flow Kit — Chrome Extension Background Service Worker
 *
 * Connects to local Python agent via WebSocket (agent runs WS server).
 * Captures bearer token, solves reCAPTCHA, proxies API calls through browser.
 */

const AGENT_WS_URL = "ws://127.0.0.1:9222";
// NOTE: This is a browser-restricted public API key — safe to ship in extension bundles.
const API_KEY = "AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY";

let ws = null;
let flowKey = null;
let callbackSecret = null; // Auth secret for HTTP callback, received from server on WS connect
let state = "off"; // off | idle | running
let manualDisconnect = false;
let initialized = false;
let keepAlivePortCount = 0;
let lastFlowTabId = null;
let lastFlowTabUrl = "";
let lastFlowSeenAt = 0;
let activeProjectId = "";
const flowProjectTabMap = new Map();
let metrics = {
  tokenCapturedAt: null,
  tokenAuthState: "unknown", // unknown | valid | invalid
  tokenAuthCheckedAt: null,
  tokenAuthError: null,
  requestCount: 0, // captcha-consuming requests only (gen image/video/upscale)
  successCount: 0,
  failedCount: 0,
  lastError: null,
};
const MAX_MEDIA_CACHE_SIZE = 2500;
const MEDIA_CACHE_TTL_MS = 14 * 24 * 60 * 60 * 1000;
const MEDIA_URL_MIN_REMAINING_MS = 90 * 1000;
const MEDIA_CACHE_STORAGE_KEY = "mediaUrlCacheV1";
const MEDIA_CACHE_FLUSH_DELAY_MS = 450;
const TOKEN_CAPTURE_REBROADCAST_MS = 120000;
const mediaUrlCache = new Map();
const pendingMediaForwardMap = new Map();
let mediaCacheSaveTimer = null;
let mediaForwardTimer = null;
let lastTokenBroadcastValue = "";
let lastTokenBroadcastAt = 0;

// ─── URL → Log Type Classifier ─────────────────────────────

// Keep request log comprehensive, hide only noisy telemetry.
const _HIDDEN_LOG_TYPES = new Set(["TRACKING"]);

const FLOW_SIGNED_MEDIA_URL_RE =
  /https:\/\/(?:storage\.googleapis\.com\/ai-sandbox-videofx\/(?:image|video)\/[0-9a-f-]{36}|flow-content\.google\/(?:image|video)\/[0-9a-f-]{36})[^\s"'\\]*/gi;
const FLOW_MEDIA_PATH_RE = /\/(image|video)\/([0-9a-f-]{36})(?:\?|$)/i;
const FLOW_UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function normalizeProjectId(raw) {
  const candidate = String(raw || "").trim().toLowerCase();
  return FLOW_UUID_RE.test(candidate) ? candidate : "";
}

function setActiveProjectId(projectId, _source = "unknown") {
  const normalized = normalizeProjectId(projectId);
  if (!normalized) return;
  activeProjectId = normalized;
}

function inferActiveProjectId() {
  const direct = normalizeProjectId(activeProjectId);
  if (direct) return direct;

  const fromTab = normalizeProjectId(extractProjectIdFromFlowUrl(lastFlowTabUrl));
  if (fromTab) return fromTab;

  for (const entry of requestLog) {
    const fromLog = normalizeProjectId(
      entry?.projectId || entry?.project_id || "",
    );
    if (fromLog) return fromLog;
  }
  return "";
}

function shouldLogType(logType) {
  return !_HIDDEN_LOG_TYPES.has(logType);
}

function extractProjectIdFromFlowUrl(url) {
  if (typeof url !== "string" || !url.startsWith("http")) return "";
  try {
    const parsed = new URL(url);
    const qp = normalizeProjectId(
      parsed.searchParams.get("projectId")
        || parsed.searchParams.get("project_id")
        || parsed.searchParams.get("flowId"),
    );
    if (qp) return qp;
    const path = String(parsed.pathname || "");
    const pathMatch = path.match(
      /\/project(?:s)?\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:\/|$)/i,
    );
    if (pathMatch?.[1]) return normalizeProjectId(pathMatch[1]);
  } catch {
    return "";
  }
  return "";
}

function rememberProjectTab(projectId, tabId) {
  const pid = normalizeProjectId(projectId);
  if (!pid) return;
  if (!Number.isInteger(tabId) || tabId < 0) return;
  flowProjectTabMap.set(pid, tabId);
  setActiveProjectId(pid, "project_tab_map");
}

function findProjectIdForTab(tabId) {
  if (!Number.isInteger(tabId) || tabId < 0) return "";
  for (const [projectId, mappedTabId] of flowProjectTabMap.entries()) {
    if (mappedTabId === tabId) return projectId;
  }
  return "";
}

function extractProjectIdFromApiRequest(url, body) {
  const fromBody = normalizeProjectId(
    body?.clientContext?.projectId
      || body?.requests?.[0]?.clientContext?.projectId
      || body?.json?.projectId
      || body?.projectId,
  );
  if (fromBody) return fromBody;
  try {
    const parsed = new URL(String(url || ""));
    const fromQuery = normalizeProjectId(
      parsed.searchParams.get("clientContext.projectId")
        || parsed.searchParams.get("projectId")
        || parsed.searchParams.get("project_id"),
    );
    if (fromQuery) return fromQuery;
  } catch {
    return "";
  }
  return "";
}

function decodeEscapedFlowText(raw) {
  const input = String(raw || "").replace(/\\\//g, "/");
  return input.replace(/\\u([0-9a-fA-F]{4})/g, (_m, hex) =>
    String.fromCharCode(parseInt(hex, 16)),
  );
}

function extractSignedUrlExpiresAtMs(url) {
  if (typeof url !== "string" || !url.startsWith("http")) return null;
  try {
    const parsed = new URL(url);
    const rawExpires =
      parsed.searchParams.get("Expires")
      || parsed.searchParams.get("expires");
    if (rawExpires) {
      const ts = Number.parseInt(rawExpires, 10);
      if (Number.isFinite(ts) && ts > 0) return ts * 1000;
    }

    const xGoogExpires =
      parsed.searchParams.get("X-Goog-Expires")
      || parsed.searchParams.get("x-goog-expires");
    const xGoogDate =
      parsed.searchParams.get("X-Goog-Date")
      || parsed.searchParams.get("x-goog-date");
    if (!xGoogExpires || !xGoogDate) return null;

    const durationSec = Number.parseInt(xGoogExpires, 10);
    if (!Number.isFinite(durationSec) || durationSec <= 0) return null;
    const m = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/.exec(xGoogDate);
    if (!m) return null;
    const issuedAtMs = Date.UTC(
      Number(m[1]),
      Number(m[2]) - 1,
      Number(m[3]),
      Number(m[4]),
      Number(m[5]),
      Number(m[6]),
    );
    if (!Number.isFinite(issuedAtMs) || issuedAtMs <= 0) return null;
    return issuedAtMs + durationSec * 1000;
  } catch {
    return null;
  }
}

function isUsableSignedMediaUrl(url, now = Date.now()) {
  if (typeof url !== "string" || !url.startsWith("http")) return false;
  const expiresAt = extractSignedUrlExpiresAtMs(url);
  if (!expiresAt) return true;
  return expiresAt > (now + MEDIA_URL_MIN_REMAINING_MS);
}

function _classifyApiUrl(url) {
  if (url.includes("uploadImage")) return "UPLOAD";
  if (url.includes("batchGenerateImages")) return "GEN_IMG";
  if (url.includes("UpsampleVideo")) return "UPSCALE";
  if (url.includes("ReferenceImages")) return "GEN_VID_REF";
  if (url.includes("batchAsyncGenerateVideo")) return "GEN_VID";
  if (url.includes("batchCheckAsync")) return "POLL";
  if (url.includes("upsampleImage")) return "UPS_IMG";
  if (url.includes("/media/")) return "MEDIA";
  if (url.includes("/credits")) return "CREDITS";
  return "API";
}

function rememberFlowTab(tabId, url = "", source = "unknown") {
  if (!Number.isInteger(tabId) || tabId < 0) return;
  lastFlowTabId = tabId;
  lastFlowTabUrl = typeof url === "string" ? url : "";
  lastFlowSeenAt = Date.now();
  const projectId = extractProjectIdFromFlowUrl(lastFlowTabUrl);
  if (projectId) {
    rememberProjectTab(projectId, tabId);
  }
  try {
    console.debug(
      `[FlowAgent] rememberFlowTab id=${tabId} source=${source} url=${lastFlowTabUrl || "unknown"}`,
    );
  } catch (_) {
    // no-op
  }
}

function rememberMediaEntries(entries = []) {
  const now = Date.now();
  for (const row of entries) {
    if (!row || typeof row !== "object") continue;
    const mediaId = String(row.mediaId || "").toLowerCase().trim();
    const mediaType = String(row.mediaType || "").toLowerCase().trim();
    const url = String(row.url || "").trim();
    const projectId = normalizeProjectId(row.projectId);
    if (!/^[0-9a-f-]{36}$/.test(mediaId)) continue;
    if (mediaType !== "image" && mediaType !== "video") continue;
    if (!url.startsWith("http")) continue;
    if (!isUsableSignedMediaUrl(url, now)) continue;
    const expiresAt = extractSignedUrlExpiresAtMs(url);
    const prev = mediaUrlCache.get(mediaId);
    mediaUrlCache.set(mediaId, {
      mediaId,
      mediaType,
      url,
      seenAt: now,
      expiresAt: Number.isFinite(expiresAt) ? expiresAt : prev?.expiresAt || null,
      projectId: projectId || prev?.projectId || "",
    });
  }

  // prune stale/overflow rows
  for (const [mid, item] of mediaUrlCache.entries()) {
    if (!item?.seenAt || now - item.seenAt > MEDIA_CACHE_TTL_MS) {
      mediaUrlCache.delete(mid);
    }
  }
  if (mediaUrlCache.size > MAX_MEDIA_CACHE_SIZE) {
    const rows = Array.from(mediaUrlCache.values()).sort(
      (a, b) => (a.seenAt || 0) - (b.seenAt || 0),
    );
    const removeCount = mediaUrlCache.size - MAX_MEDIA_CACHE_SIZE;
    for (let i = 0; i < removeCount; i += 1) {
      const victim = rows[i];
      if (victim?.mediaId) mediaUrlCache.delete(victim.mediaId);
    }
  }
  schedulePersistMediaCache();
}

function getCachedMediaEntries(limit = 1200, projectId = "") {
  const now = Date.now();
  const requestedProjectId = normalizeProjectId(projectId);
  const rows = [];
  for (const [mid, item] of mediaUrlCache.entries()) {
    if (!item?.seenAt || now - item.seenAt > MEDIA_CACHE_TTL_MS) {
      mediaUrlCache.delete(mid);
      continue;
    }
    if (!isUsableSignedMediaUrl(item?.url, now)) {
      mediaUrlCache.delete(mid);
      continue;
    }
    if (
      requestedProjectId &&
      normalizeProjectId(item?.projectId) !== requestedProjectId
    ) {
      continue;
    }
    rows.push({
      mediaId: mid,
      mediaType: item.mediaType,
      url: item.url,
      projectId: normalizeProjectId(item.projectId),
      seenAt: item.seenAt || 0,
      expiresAt: item.expiresAt || null,
    });
  }
  rows.sort((a, b) => (Number(b.seenAt || 0) - Number(a.seenAt || 0)));
  return rows.slice(0, limit).map((row) => ({
    mediaId: row.mediaId,
    mediaType: row.mediaType,
    url: row.url,
    projectId: row.projectId,
  }));
}

function schedulePersistMediaCache() {
  if (mediaCacheSaveTimer) return;
  mediaCacheSaveTimer = setTimeout(() => {
    mediaCacheSaveTimer = null;
    const rows = getCachedMediaEntries(MAX_MEDIA_CACHE_SIZE);
    try {
      const maybePromise = chrome.storage.local.set({
        [MEDIA_CACHE_STORAGE_KEY]: rows,
      });
      if (maybePromise && typeof maybePromise.catch === "function") {
        maybePromise.catch(() => {});
      }
    } catch (_) {
      // ignore
    }
  }, 600);
}

async function loadPersistedMediaCache() {
  try {
    const data = await chrome.storage.local.get([MEDIA_CACHE_STORAGE_KEY]);
    const rows = Array.isArray(data?.[MEDIA_CACHE_STORAGE_KEY])
      ? data[MEDIA_CACHE_STORAGE_KEY]
      : [];
    if (!rows.length) return;
    rememberMediaEntries(rows);
  } catch (_) {
    // ignore cache restore errors
  }
}

function queueMediaEntriesForAgent(entries = []) {
  if (!Array.isArray(entries) || entries.length === 0) return;

  for (const row of entries) {
    if (!row || typeof row !== "object") continue;
    const mediaId = String(row.mediaId || "").toLowerCase().trim();
    const mediaType = String(row.mediaType || "").toLowerCase().trim();
    const url = String(row.url || "").trim();
    const projectId = normalizeProjectId(row.projectId);
    if (!/^[0-9a-f-]{36}$/.test(mediaId)) continue;
    if (mediaType !== "image" && mediaType !== "video") continue;
    if (!url.startsWith("http")) continue;
    pendingMediaForwardMap.set(mediaId, { mediaId, mediaType, url, projectId });
  }

  if (mediaForwardTimer) return;
  mediaForwardTimer = setTimeout(() => {
    mediaForwardTimer = null;
    const rows = Array.from(pendingMediaForwardMap.values());
    pendingMediaForwardMap.clear();
    if (!rows.length) return;
    rememberMediaEntries(rows);
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: "media_urls_refresh",
          urls: rows,
        }),
      );
    }
  }, MEDIA_CACHE_FLUSH_DELAY_MS);
}

// ─── Request Log ────────────────────────────────────────────

let requestLog = [];

function broadcastTokenCaptured(force = false) {
  if (!flowKey || ws?.readyState !== WebSocket.OPEN) return;
  const now = Date.now();
  const shouldSend =
    force
    || flowKey !== lastTokenBroadcastValue
    || (now - lastTokenBroadcastAt) >= TOKEN_CAPTURE_REBROADCAST_MS;
  if (!shouldSend) return;
  ws.send(JSON.stringify({ type: "token_captured", flowKey }));
  lastTokenBroadcastValue = flowKey;
  lastTokenBroadcastAt = now;
}

function saveFlowKey(token) {
  if (!token || typeof token !== "string") return;
  const normalized = token.replace(/^Bearer\s+/i, "").trim();
  if (!normalized.startsWith("ya29.")) return;
  const tokenChanged = normalized !== flowKey;
  flowKey = normalized;
  metrics.tokenCapturedAt = Date.now();
  metrics.tokenAuthState = "unknown";
  metrics.tokenAuthCheckedAt = Date.now();
  metrics.tokenAuthError = null;
  metrics.lastError = null;
  chrome.storage.local.set({ flowKey, metrics });
  // Avoid flooding token_captured when webRequest keeps seeing the same token.
  broadcastTokenCaptured(tokenChanged);
}

function setTokenAuthState(nextState, error = null) {
  const normalizedState =
    nextState === "valid" || nextState === "invalid" ? nextState : "unknown";
  const normalizedError = error ? String(error).slice(0, 240) : null;
  const changed =
    metrics.tokenAuthState !== normalizedState ||
    metrics.tokenAuthError !== normalizedError;
  metrics.tokenAuthState = normalizedState;
  metrics.tokenAuthCheckedAt = Date.now();
  metrics.tokenAuthError = normalizedError;
  if (changed) broadcastStatus();
}

function isAuthFailureResponse(status, responseText = "") {
  if (status === 401) return true;
  if (status !== 400) return false;
  const text = String(responseText || "").toLowerCase();
  if (!text) return false;
  return (
    text.includes("unauth") ||
    text.includes("token expired") ||
    text.includes("invalid token") ||
    text.includes("invalid authentication") ||
    text.includes("invalid credentials") ||
    text.includes("login required") ||
    text.includes("missing required authentication credential")
  );
}

function addRequestLog(entry) {
  const pid = normalizeProjectId(entry?.projectId || entry?.project_id || "");
  if (pid) {
    entry.projectId = pid;
    setActiveProjectId(pid, "request_log_add");
  }
  requestLog.unshift(entry);
  if (requestLog.length > 400) requestLog.pop();
  broadcastRequestLog();
}

function updateRequestLog(id, updates) {
  const entry = requestLog.find((e) => e.id === id);
  if (entry) {
    Object.assign(entry, updates);
    const pid = normalizeProjectId(
      updates?.projectId || updates?.project_id || entry?.projectId || "",
    );
    if (pid) {
      entry.projectId = pid;
      setActiveProjectId(pid, "request_log_update");
    }
  }
  broadcastRequestLog();
}

function broadcastRequestLog() {
  chrome.runtime
    .sendMessage({ type: "REQUEST_LOG_UPDATE", log: requestLog })
    .catch(() => {});
}

// ─── Startup ────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(init);
chrome.runtime.onStartup.addListener(init);
chrome.runtime.onConnect.addListener((port) => {
  if (port?.name !== "side-panel-keepalive") return;
  keepAlivePortCount += 1;
  connectToAgent();

  port.onMessage.addListener((msg) => {
    if (msg?.type === "PING") {
      if (ws?.readyState !== WebSocket.OPEN) connectToAgent();
      try {
        port.postMessage({ type: "PONG", t: Date.now() });
      } catch (_) {
        // ignore
      }
    }
  });

  port.onDisconnect.addListener(() => {
    keepAlivePortCount = Math.max(0, keepAlivePortCount - 1);
  });
});
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === "reconnect") connectToAgent();
  if (alarm.name === "keepAlive") keepAlive();
  if (alarm.name === "token-refresh") {
    await captureTokenFromFlowTab();
  }
});

async function init() {
  if (initialized) return;
  initialized = true;
  const data = await chrome.storage.local.get([
    "flowKey",
    "metrics",
    "callbackSecret",
  ]);
  if (data.flowKey) flowKey = data.flowKey;
  if (data.metrics) Object.assign(metrics, data.metrics);
  if (!["unknown", "valid", "invalid"].includes(metrics.tokenAuthState)) {
    metrics.tokenAuthState = "unknown";
  }
  if (!flowKey) {
    metrics.tokenAuthState = "unknown";
    metrics.tokenAuthCheckedAt = null;
    metrics.tokenAuthError = null;
  }
  if (data.callbackSecret) callbackSecret = data.callbackSecret;
  await loadPersistedMediaCache();
  connectToAgent();
  chrome.alarms.create("keepAlive", { periodInMinutes: 0.4 });
}

// Electron may not consistently fire onStartup/onInstalled for unpacked extension reloads.
// Initialize eagerly whenever the service worker spins up.
void init().catch((err) => {
  console.error("[FlowAgent] Init failed:", err);
});

// ─── Token Capture ──────────────────────────────────────────

chrome.webRequest.onBeforeSendHeaders.addListener(
  (details) => {
    if (!details?.requestHeaders?.length) return;
    const authHeader = details.requestHeaders.find(
      (h) => h.name?.toLowerCase() === "authorization",
    );
    const value = authHeader?.value || "";
    if (!value.startsWith("Bearer ya29.")) return;

    const token = value.replace(/^Bearer\s+/i, "").trim();
    if (!token) return;
    if (Number.isInteger(details.tabId) && details.tabId >= 0) {
      rememberFlowTab(details.tabId, details.url || "", "webRequest");
    } else {
      void getFlowTabs()
        .then((tabs) => {
          const best = selectBestFlowTab(tabs);
          if (best?.id) rememberFlowTab(best.id, best.url || "", "webRequest.fallback");
        })
        .catch(() => {});
    }

    // Always update — even if same token string, refresh the timestamp
    saveFlowKey(token);
    console.log("[FlowAgent] Bearer token captured");
  },
  {
    urls: [
      "https://aisandbox-pa.googleapis.com/*",
      "https://*.googleapis.com/*",
      "https://*.google.com/*",
      "https://*.google/*",
      "https://labs.google/*",
    ],
  },
  ["requestHeaders", "extraHeaders"],
);

// Capture signed media URLs directly from browser requests so old media can be
// recovered without depending solely on TRPC response parsing.
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    const url = String(details?.url || "");
    if (!url.startsWith("http")) return;
    let entries = extractSignedMediaEntriesFromText(url);
    if (!entries.length) return;
    const mappedProjectId = findProjectIdForTab(details?.tabId);
    if (mappedProjectId) {
      entries = entries.map((entry) => ({ ...entry, projectId: mappedProjectId }));
    }
    queueMediaEntriesForAgent(entries);
    if (Number.isInteger(details.tabId) && details.tabId >= 0) {
      rememberFlowTab(details.tabId, details.initiator || url, "mediaRequest");
    }
  },
  {
    urls: [
      "https://flow-content.google/*",
      "https://storage.googleapis.com/ai-sandbox-videofx/*",
    ],
  },
);

if (chrome.tabs?.onUpdated?.addListener) {
  chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    const url = changeInfo?.url || tab?.url || "";
    if (isFlowToolUrl(url)) {
      rememberFlowTab(tabId, url, "tabs.onUpdated");
    }
  });
}

if (chrome.tabs?.onActivated?.addListener) {
  chrome.tabs.onActivated.addListener(async (activeInfo) => {
    try {
      const tab = await getTabById(activeInfo?.tabId);
      if (tab?.id && isFlowToolUrl(tab.url)) {
        rememberFlowTab(tab.id, tab.url || "", "tabs.onActivated");
      }
    } catch (_) {
      // ignore
    }
  });
}

if (chrome.windows?.onFocusChanged?.addListener) {
  chrome.windows.onFocusChanged.addListener(async () => {
    try {
      const best = selectBestFlowTab(await getFlowTabs());
      if (best?.id) rememberFlowTab(best.id, best.url || "", "windows.focus");
    } catch (_) {
      // ignore
    }
  });
}

let _openingFlowTab = false;
const FLOW_TAB_QUERY = [
  "https://labs.google/*",
  "https://flow.google.com/*",
  "https://*.flow.google.com/*",
];
const FLOW_ENTRY_URL = "https://labs.google/fx/tools/flow";
const FLOW_PROJECT_NEW_URL = "https://labs.google/fx/tools/flow/project/new";
const FLOW_LOCALE_SEGMENT = "[a-z]{2,3}(?:-[a-z0-9]{2,8})*";
const FLOW_TOOLS_PATH_RE = new RegExp(
  `^/fx/(?:${FLOW_LOCALE_SEGMENT}/)?tools/flow(?:/|$)`,
  "i",
);
const FLOW_LEGACY_PROJECT_PATH_RE =
  /^\/fx\/projects\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?:\/|$)/i;

function detectFlowLocale() {
  const url = String(lastFlowTabUrl || "");
  if (!url.startsWith("http")) return "";
  try {
    const parsed = new URL(url);
    const m = String(parsed.pathname || "").match(/^\/fx\/([^/]+)\//i);
    const locale = String(m?.[1] || "").trim().toLowerCase();
    if (
      !locale
      || locale === "tools"
      || locale === "projects"
      || locale === "api"
    ) return "";
    return locale;
  } catch {
    return "";
  }
}

function buildFlowEntryUrls(projectId = "") {
  const pid = normalizeProjectId(projectId);
  const locale = detectFlowLocale();
  const localeFlowBase = locale ? `https://labs.google/fx/${locale}/tools/flow` : "";
  const localeProjectRoute = pid && localeFlowBase
    ? `${localeFlowBase}/project/${pid}`
    : "";
  const projectRoute = pid ? `${FLOW_ENTRY_URL}/project/${pid}` : "";
  const projectRouteQuery = pid ? `${FLOW_ENTRY_URL}?projectId=${pid}` : "";
  const localeProjectRouteQuery = pid && localeFlowBase
    ? `${localeFlowBase}?projectId=${pid}`
    : "";
  const legacyProjectRoute = pid ? `https://labs.google/fx/projects/${pid}` : "";
  const localeProjectNewRoute = localeFlowBase
    ? `${localeFlowBase}/project/new`
    : "";
  const urls = [
    pid && localeProjectRoute ? localeProjectRoute : null,
    projectRoute || null,
    projectRouteQuery || null,
    localeProjectRouteQuery || null,
    localeFlowBase || null,
    FLOW_ENTRY_URL,
    localeProjectNewRoute || null,
    FLOW_PROJECT_NEW_URL,
    "https://flow.google.com/",
    pid ? `https://flow.google.com/?projectId=${pid}` : null,
    legacyProjectRoute || null,
  ].filter(Boolean);
  return Array.from(new Set(urls));
}

function isFlowToolUrl(url) {
  if (typeof url !== "string" || !url.startsWith("http")) return false;
  let parsed = null;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }
  const host = String(parsed.host || "").toLowerCase();
  const path = String(parsed.pathname || "").toLowerCase();

  if (host === "flow.google.com" || host.endsWith(".flow.google.com"))
    return true;

  if (host === "labs.google" || host.endsWith(".labs.google")) {
    if (FLOW_TOOLS_PATH_RE.test(path)) return true;
    if (FLOW_LEGACY_PROJECT_PATH_RE.test(path)) return true;
  }

  return false;
}

function isFlowDomainUrl(url) {
  if (typeof url !== "string" || !url.startsWith("http")) return false;
  try {
    const host = String(new URL(url).host || "").toLowerCase();
    return (
      host === "labs.google" ||
      host.endsWith(".labs.google") ||
      host === "flow.google.com" ||
      host.endsWith(".flow.google.com")
    );
  } catch {
    return false;
  }
}

async function getFlowTabsFromWindows() {
  if (typeof chrome.windows?.getAll !== "function") return [];
  try {
    const windows = await chrome.windows.getAll({ populate: true });
    if (!windows?.length) return [];
    const allTabs = windows.flatMap((w) => (Array.isArray(w.tabs) ? w.tabs : []));
    return allTabs.filter((t) => isFlowToolUrl(t?.url) || isFlowDomainUrl(t?.url));
  } catch (_) {
    return [];
  }
}

async function getTabById(tabId) {
  if (!Number.isInteger(tabId) || tabId < 0) return null;
  if (typeof chrome.tabs?.get === "function") {
    try {
      return await chrome.tabs.get(tabId);
    } catch (_) {
      for (const [pid, mappedTabId] of flowProjectTabMap.entries()) {
        if (mappedTabId === tabId) flowProjectTabMap.delete(pid);
      }
      // fall through to windows fallback
    }
  }
  const winTabs = await getFlowTabsFromWindows();
  return winTabs.find((t) => t?.id === tabId) || null;
}

async function getFlowTabs() {
  try {
    if (typeof chrome.tabs?.query === "function") {
      const tabs = await chrome.tabs.query({ url: FLOW_TAB_QUERY });
      const matches = (tabs || []).filter(
        (t) => isFlowToolUrl(t?.url) || isFlowDomainUrl(t?.url),
      );
      if (matches.length) return matches;
    }
  } catch (_) {
    // fall through
  }

  // Fallback for Electron extension runtime where URL-filtered query can be flaky.
  try {
    if (typeof chrome.tabs?.query === "function") {
      const tabs = await chrome.tabs.query({});
      if (tabs?.length) {
        const matches = tabs.filter(
          (t) => isFlowToolUrl(t?.url) || isFlowDomainUrl(t?.url),
        );
        if (matches.length) return matches;
      }
    }
  } catch (_) {
    // fall through
  }

  return await getFlowTabsFromWindows();
}

function selectBestFlowTab(tabs) {
  if (!tabs?.length) return null;
  const readyFlow = tabs.find((t) => isFlowToolUrl(t.url) && t.status === "complete");
  if (readyFlow) return readyFlow;
  const anyFlow = tabs.find((t) => isFlowToolUrl(t.url));
  if (anyFlow) return anyFlow;
  const readyFlowDomain = tabs.find(
    (t) => isFlowDomainUrl(t.url) && t.status === "complete",
  );
  if (readyFlowDomain) return readyFlowDomain;
  const anyFlowDomain = tabs.find((t) => isFlowDomainUrl(t.url));
  if (anyFlowDomain) return anyFlowDomain;
  return null;
}

function selectBestFlowTabForProject(tabs, projectId = "") {
  const pid = normalizeProjectId(projectId);
  if (!tabs?.length || !pid) return selectBestFlowTab(tabs);
  const matches = tabs.filter((t) =>
    String(t?.url || "").toLowerCase().includes(pid),
  );
  if (matches.length) {
    return selectBestFlowTab(matches) || matches[0];
  }
  return selectBestFlowTab(tabs);
}

function flowTabHasProject(tabUrl, projectId = "") {
  const pid = normalizeProjectId(projectId);
  if (!pid) return false;
  return String(tabUrl || "").toLowerCase().includes(pid);
}

async function waitForFlowTabReady(tabId, timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const tab = await getTabById(tabId);
      const status = String(tab?.status || "").toLowerCase();
      const readyStatus = !status || status === "complete";
      if (tab && readyStatus && isFlowToolUrl(tab.url))
        return tab;
    } catch (_) {
      // ignore transient tab errors and keep polling
    }
    await sleep(350);
  }
  return null;
}

async function forceNavigateTabToFlow(tabId, projectId = "") {
  if (!Number.isInteger(tabId) || tabId < 0) return null;
  const targetUrl = buildFlowEntryUrls(projectId)[0] || FLOW_ENTRY_URL;
  try {
    if (typeof chrome.tabs?.update === "function") {
      await chrome.tabs.update(tabId, { url: targetUrl, active: true });
    }
  } catch (_) {
    return null;
  }
  return await waitForFlowTabReady(tabId, 25000);
}

async function ensureFlowTabVisible(projectId = "") {
  const targetUrls = buildFlowEntryUrls(projectId);
  const tabs = await getFlowTabs();
  const best = selectBestFlowTabForProject(tabs, projectId);
  if (best?.id) {
    try {
      if (typeof chrome.tabs?.update === "function") {
        const shouldRetargetProject =
          !!normalizeProjectId(projectId) && !flowTabHasProject(best.url, projectId);
        const shouldRetargetRoute = !isFlowToolUrl(best.url);
        await chrome.tabs.update(best.id, {
          active: true,
          ...(
            shouldRetargetProject || shouldRetargetRoute
              ? { url: targetUrls[0] || FLOW_ENTRY_URL }
              : {}
          ),
        });
      }
    } catch (_) {
      /* no-op */
    }
    return best;
  }

  const canCreateTab = typeof chrome.tabs?.create === "function";
  const canCreateWindow = typeof chrome.windows?.create === "function";
  if (!canCreateTab) {
    // Electron extension runtime may expose query/get/sendMessage but not tabs.create().
    // Try window creation first; otherwise wait for a Flow surface opened by the host app.
    if (canCreateWindow) {
      try {
        const createdWindow = await chrome.windows.create({
          url: targetUrls[0] || FLOW_ENTRY_URL,
          focused: true,
          type: "normal",
        });
        const createdTabs = Array.isArray(createdWindow?.tabs)
          ? createdWindow.tabs
          : [];
        const createdBest = selectBestFlowTab(createdTabs);
        if (createdBest?.id) {
          rememberFlowTab(
              createdBest.id,
              createdBest.url || (targetUrls[0] || FLOW_ENTRY_URL),
              "windows.create",
            );
          const ready = await waitForFlowTabReady(createdBest.id, 20000);
          return ready || createdBest;
        }
      } catch (_) {
        // no-op
      }
    }

    for (let i = 0; i < 12; i += 1) {
      const retryBest = selectBestFlowTab(await getFlowTabs());
      if (retryBest?.id) return retryBest;
      await sleep(350);
    }
    return null;
  }

  const created = await chrome.tabs.create({
    url: targetUrls[0] || FLOW_ENTRY_URL,
    active: true,
  });
  if (created?.id) {
    rememberFlowTab(created.id, created.url || (targetUrls[0] || FLOW_ENTRY_URL), "create");
    const ready = await waitForFlowTabReady(created.id, 20000);
    return ready || created;
  }
  return null;
}

async function ensureFlowToolTabReady(projectId = "") {
  const normalizedProjectId = normalizeProjectId(projectId);
  const projectTargetUrl = buildFlowEntryUrls(normalizedProjectId)[0] || FLOW_ENTRY_URL;
  if (normalizedProjectId) {
    const mappedTabId = flowProjectTabMap.get(normalizedProjectId);
    if (Number.isInteger(mappedTabId) && mappedTabId >= 0) {
      try {
        let tab = await getTabById(mappedTabId);
        if (
          tab?.id &&
          !flowTabHasProject(tab.url, normalizedProjectId) &&
          typeof chrome.tabs?.update === "function"
        ) {
          tab = await chrome.tabs.update(tab.id, {
            url: projectTargetUrl,
            active: true,
          });
        }
        if (tab?.id) {
          const ready = await waitForFlowTabReady(tab.id, 12000);
          if (ready?.id) {
            rememberFlowTab(
              ready.id,
              ready.url || "",
              "projectMap",
            );
            rememberProjectTab(normalizedProjectId, ready.id);
            return ready;
          }
        }
      } catch (_) {
        // Continue with regular discovery.
      }
    }
  }

  // Prefer last known Flow tab captured from content/webRequest signal.
  if (Number.isInteger(lastFlowTabId) && lastFlowTabId >= 0) {
    try {
      let tab = await getTabById(lastFlowTabId);
      if (tab?.id) {
        if (
          normalizedProjectId &&
          !flowTabHasProject(tab.url, normalizedProjectId) &&
          typeof chrome.tabs?.update === "function"
        ) {
          tab = await chrome.tabs.update(tab.id, {
            url: projectTargetUrl,
            active: true,
          });
        }
        if (!isFlowToolUrl(tab.url)) {
          try {
            if (typeof chrome.tabs?.update === "function") {
              await chrome.tabs.update(tab.id, {
                url: normalizedProjectId ? projectTargetUrl : FLOW_ENTRY_URL,
                active: true,
              });
            }
          } catch (_) {
            // no-op
          }
        }
        const ready = await waitForFlowTabReady(tab.id, 25000);
        if (ready?.id) {
          rememberFlowTab(ready.id, ready.url || "", "lastKnown");
          if (normalizedProjectId) rememberProjectTab(normalizedProjectId, ready.id);
          return ready;
        }
      }
    } catch (_) {
      // stale tab id, continue normal flow
    }
  }

  // Retry discovery/open to tolerate transient login/interstitial states.
  for (let attempt = 0; attempt < 3; attempt += 1) {
    let tab = selectBestFlowTabForProject(await getFlowTabs(), normalizedProjectId);
    if (!tab?.id) {
      tab = await ensureFlowTabVisible(normalizedProjectId);
    }

    if (tab?.id) {
      if (
        normalizedProjectId &&
        !flowTabHasProject(tab.url, normalizedProjectId) &&
        typeof chrome.tabs?.update === "function"
      ) {
        try {
          tab = await chrome.tabs.update(tab.id, {
            url: projectTargetUrl,
            active: true,
          });
        } catch (_) {
          // ignore and continue
        }
      }
      if (!isFlowToolUrl(tab.url)) {
        try {
          await chrome.tabs.update(tab.id, {
            url: normalizedProjectId ? projectTargetUrl : FLOW_ENTRY_URL,
            active: true,
          });
        } catch (_) {
          // no-op
        }
      }

      const ready = await waitForFlowTabReady(tab.id, 25000);
      if (ready?.id) {
        rememberFlowTab(ready.id, ready.url || "", "ensureFlowToolTabReady");
        if (normalizedProjectId) rememberProjectTab(normalizedProjectId, ready.id);
        return ready;
      }
    }

    // Fallback: explicitly try known Flow entry URLs when a create API exists.
    const canCreateTab = typeof chrome.tabs?.create === "function";
    const canCreateWindow = typeof chrome.windows?.create === "function";
    const fallbackUrls = buildFlowEntryUrls(normalizedProjectId);
    if (canCreateTab || canCreateWindow) {
      for (const url of fallbackUrls) {
        try {
          let created = null;
          if (canCreateTab) {
            created = await chrome.tabs.create({ url, active: true });
          } else if (canCreateWindow) {
            const createdWindow = await chrome.windows.create({
              url,
              focused: true,
              type: "normal",
            });
            const tabs = Array.isArray(createdWindow?.tabs)
              ? createdWindow.tabs
              : [];
            created = selectBestFlowTab(tabs);
          }
          if (!created?.id) continue;
          rememberFlowTab(created.id, created.url || url, "fallbackCreate");
          const ready = await waitForFlowTabReady(created.id, 25000);
          if (ready?.id) {
            rememberFlowTab(ready.id, ready.url || "", "fallbackCreate");
            if (normalizedProjectId)
              rememberProjectTab(normalizedProjectId, ready.id);
            return ready;
          }
        } catch (_) {
          // no-op
        }
      }
    }

    await sleep(400);
  }

  return null;
}

async function captureTokenFromFlowTab(projectId = "") {
  if (_openingFlowTab) {
    console.log("[FlowAgent] Flow tab already opening, skipping");
    return;
  }
  _openingFlowTab = true;
  try {
    const bestTab = await ensureFlowToolTabReady(projectId);
    if (!bestTab?.id) {
      console.log("[FlowAgent] Flow tab not ready for token capture");
      return;
    }
    await chrome.scripting.executeScript({
      target: { tabId: bestTab.id },
      files: ["content.js"],
    });
    console.log("[FlowAgent] Token refresh triggered on Flow tab");
  } catch (e) {
    console.error("[FlowAgent] Token refresh failed:", e);
  } finally {
    _openingFlowTab = false;
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
    console.error("[FlowAgent] WS connect error:", e);
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    console.log("[FlowAgent] Connected to agent");
    chrome.alarms.clear("reconnect");
    setState("idle");

    // Token refresh alarm — 45 min gives buffer before ~60 min expiry
    chrome.alarms.create("token-refresh", { periodInMinutes: 45 });

    // Send current state + resend token if we have one
    ws.send(
      JSON.stringify({
        type: "extension_ready",
        flowKeyPresent: !!flowKey,
        tokenAge:
          flowKey && metrics.tokenCapturedAt
            ? Date.now() - metrics.tokenCapturedAt
            : null,
        tokenAuthState: metrics.tokenAuthState || "unknown",
        tokenAuthCheckedAt: metrics.tokenAuthCheckedAt || null,
        tokenAuthError: metrics.tokenAuthError || null,
      }),
    );
    if (flowKey) {
      broadcastTokenCaptured(true);
    }
  };

  ws.onmessage = async ({ data }) => {
    try {
      const msg = JSON.parse(data);

      if (msg.method === "api_request") {
        await handleApiRequest(msg);
      } else if (msg.method === "trpc_request") {
        await handleTrpcRequest(msg);
      } else if (msg.method === "pull_project_urls") {
        await handlePullProjectUrls(msg);
      } else if (msg.method === "solve_captcha") {
        await handleSolveCaptcha(msg);
      } else if (msg.method === "refresh_token") {
        try {
          await captureTokenFromFlowTab();
          await sleep(1200);
          sendToAgent({
            id: msg.id,
            result: {
              ok: true,
              flowKeyPresent: !!flowKey,
              tokenAge: metrics.tokenCapturedAt
                ? Date.now() - metrics.tokenCapturedAt
                : null,
              tokenAuthState: metrics.tokenAuthState || "unknown",
              tokenAuthCheckedAt: metrics.tokenAuthCheckedAt || null,
              tokenAuthError: metrics.tokenAuthError || null,
            },
          });
        } catch (e) {
          sendToAgent({
            id: msg.id,
            result: {
              ok: false,
              error: e?.message || "REFRESH_TOKEN_FAILED",
              flowKeyPresent: !!flowKey,
              tokenAge: metrics.tokenCapturedAt
                ? Date.now() - metrics.tokenCapturedAt
                : null,
              tokenAuthState: metrics.tokenAuthState || "unknown",
              tokenAuthCheckedAt: metrics.tokenAuthCheckedAt || null,
              tokenAuthError: metrics.tokenAuthError || null,
            },
          });
        }
      } else if (msg.method === "get_status") {
        let flowTabsPreview = [];
        if (
          !Number.isInteger(lastFlowTabId) ||
          lastFlowTabId < 0 ||
          !lastFlowSeenAt ||
          Date.now() - lastFlowSeenAt > 45000
        ) {
          try {
            const tabs = await getFlowTabs();
            flowTabsPreview = (tabs || []).slice(0, 6).map((t) => ({
              id: t?.id ?? null,
              status: t?.status || null,
              url: String(t?.url || "").slice(0, 180),
            }));
            const best = selectBestFlowTab(tabs);
            if (best?.id) {
              rememberFlowTab(best.id, best.url || "", "get_status");
            }
          } catch (_) {
            // ignore status best-effort tab probing
          }
        }
        sendToAgent({
          id: msg.id,
          result: {
            connected: ws?.readyState === WebSocket.OPEN,
            agentConnected: ws?.readyState === WebSocket.OPEN,
            state,
            activeProjectId: inferActiveProjectId(),
            flowKeyPresent: !!flowKey,
            manualDisconnect,
            flowTabId: lastFlowTabId,
            flowTabUrl: lastFlowTabUrl || null,
            flowTabSeenAt: lastFlowSeenAt || null,
            tokenAge: metrics.tokenCapturedAt
              ? Date.now() - metrics.tokenCapturedAt
              : null,
            tokenAuthState: metrics.tokenAuthState || "unknown",
            tokenAuthCheckedAt: metrics.tokenAuthCheckedAt || null,
            tokenAuthError: metrics.tokenAuthError || null,
            metrics,
            mediaCacheSize: mediaUrlCache.size,
            projectTabBindings: flowProjectTabMap.size,
            debugFlowTabs: flowTabsPreview,
          },
        });
      } else if (msg.type === "callback_secret") {
        callbackSecret = msg.secret;
        chrome.storage.local.set({ callbackSecret: msg.secret });
        console.log("[FlowAgent] Received callback secret");
      } else if (msg.type === "pong") {
        // keepalive response
      }
    } catch (e) {
      console.error("[FlowAgent] Message error:", e);
    }
  };

  ws.onclose = () => {
    setState("off");
    chrome.alarms.clear("token-refresh");
    if (!manualDisconnect) scheduleReconnect();
  };

  ws.onerror = (e) => {
    console.error("[FlowAgent] WS error:", e);
    metrics.lastError = "WS_ERROR";
    chrome.storage.local.set({ metrics });
  };
}

function scheduleReconnect() {
  // Use both immediate timer + alarm fallback. Alarm alone can be delayed
  // in MV3 service workers (especially inside Electron).
  setTimeout(() => connectToAgent(), 3000);
  chrome.alarms.create("reconnect", { delayInMinutes: 0.1 });
}

function keepAlive() {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "ping" }));
  } else {
    connectToAgent();
  }
}

function sendToAgent(msg) {
  // API responses (with msg.id) go via HTTP — immune to WS disconnect
  if (msg.id) {
    fetch("http://127.0.0.1:8100/api/ext/callback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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

async function requestCaptchaFromTab(
  tabId,
  requestId,
  pageAction,
  projectId = "",
) {
  const sendCaptchaMessage = async (tid) =>
    await chrome.tabs.sendMessage(tid, {
      type: "GET_CAPTCHA",
      requestId,
      pageAction,
    });

  try {
    return await sendCaptchaMessage(tabId);
  } catch (error) {
    const msg = error?.message || "";
    const shouldInject =
      msg.includes("Receiving end does not exist") ||
      msg.includes("Could not establish connection");
    const hostPermissionDenied =
      msg.includes("Cannot access contents of the page") ||
      msg.includes("must request permission to access the respective host");

    if (!shouldInject && !hostPermissionDenied) throw error;

    let tabUrl = "";
    try {
      const t = await chrome.tabs.get(tabId);
      tabUrl = t?.url || "";
    } catch (_) {
      // ignore
    }

    // If current tab isn't Flow-ready, switch to a ready Flow tab.
    if (!isFlowToolUrl(tabUrl)) {
      let reopened = await ensureFlowToolTabReady(projectId);
      if (!reopened?.id) {
        reopened = await forceNavigateTabToFlow(tabId, projectId);
      }
      if (!reopened?.id) {
        throw new Error(
          `NO_FLOW_TAB [original_error=${msg}] [tab_url=${tabUrl || "unknown"}]`,
        );
      }
      tabId = reopened.id;
      tabUrl = reopened.url || "";
    }

    if (!isFlowToolUrl(tabUrl)) {
      throw new Error(`FLOW_TAB_NOT_READY [tab_url=${tabUrl || "unknown"}]`);
    }

    // Try (re)inject + send up to 2 rounds.
    let lastErr = msg;
    for (let i = 0; i < 2; i += 1) {
      try {
        await chrome.scripting.executeScript({
          target: { tabId },
          files: ["content.js"],
        });
      } catch (injectErr) {
        lastErr = injectErr?.message || lastErr;
      }

      await sleep(220);

      try {
        return await sendCaptchaMessage(tabId);
      } catch (sendErr) {
        lastErr = sendErr?.message || lastErr;
        const denied =
          lastErr.includes("Cannot access contents of the page") ||
          lastErr.includes(
            "must request permission to access the respective host",
          );
        if (denied) {
          const reopened =
            (await ensureFlowToolTabReady(projectId))
            || (await forceNavigateTabToFlow(tabId, projectId));
          if (reopened?.id) {
            tabId = reopened.id;
            tabUrl = reopened.url || "";
          } else if (Number.isInteger(tabId) && tabId >= 0) {
            const forced = await forceNavigateTabToFlow(tabId, projectId);
            if (forced?.id) {
              tabId = forced.id;
              tabUrl = forced.url || "";
            }
          }
        }
      }
    }

    throw new Error(`${lastErr} [tab_url=${tabUrl || "unknown"}]`);
  }
}

async function solveCaptcha(requestId, captchaAction, projectId = "") {
  let lastError = "NO_FLOW_TAB";

  // Multiple attempts significantly reduce transient NO_FLOW_TAB / host-access failures.
  for (let attempt = 0; attempt < 3; attempt += 1) {
    let targetTab = null;
    try {
      targetTab = await ensureFlowToolTabReady(projectId);
    } catch (e) {
      lastError = e?.message || "NO_FLOW_TAB";
    }

    if (!targetTab?.id) {
      lastError = "NO_FLOW_TAB";
      await sleep(450);
      continue;
    }
    if (projectId) rememberProjectTab(projectId, targetTab.id);

    try {
      await chrome.scripting
        .executeScript({
          target: { tabId: targetTab.id },
          files: ["content.js"],
        })
        .catch(() => {});

      const resp = await Promise.race([
        requestCaptchaFromTab(targetTab.id, requestId, captchaAction, projectId),
        new Promise((_, rej) =>
          setTimeout(() => rej(new Error("CAPTCHA_TIMEOUT")), 35000),
        ),
      ]);

      if (resp?.token) return resp;

      lastError = resp?.error || "CAPTCHA_FAILED";
      const retryable =
        String(lastError).includes("NO_FLOW_TAB") ||
        String(lastError).includes("FLOW_TAB_NOT_READY") ||
        String(lastError).includes("Cannot access contents of the page") ||
        String(lastError).includes(
          "must request permission to access the respective host",
        );
      if (!retryable) return resp;
    } catch (e) {
      lastError = e?.message || "CAPTCHA_FAILED";
      const retryable =
        String(lastError).includes("NO_FLOW_TAB") ||
        String(lastError).includes("FLOW_TAB_NOT_READY") ||
        String(lastError).includes("Cannot access contents of the page") ||
        String(lastError).includes(
          "must request permission to access the respective host",
        ) ||
        String(lastError).includes("CAPTCHA_TIMEOUT");
      if (!retryable) return { error: lastError };
    }

    await sleep(500 + attempt * 250);
  }

  return { error: lastError || "CAPTCHA_FAILED" };
}

async function handleSolveCaptcha(msg) {
  const { id, params } = msg;
  const result = await solveCaptcha(
    id,
    params?.captchaAction || "VIDEO_GENERATION",
    normalizeProjectId(params?.projectId),
  );

  // Standalone captcha solve counts as captcha-consuming
  metrics.requestCount++;
  if (result?.token) {
    metrics.successCount++;
  } else {
    metrics.failedCount++;
    metrics.lastError = result?.error || "NO_TOKEN";
  }
  chrome.storage.local.set({ metrics });

  sendToAgent({ id, result });
}

function extractSignedMediaEntriesFromText(rawText) {
  const text = decodeEscapedFlowText(rawText);
  const matches = text.match(FLOW_SIGNED_MEDIA_URL_RE) || [];
  const dedup = new Map();
  for (const raw of matches) {
    const clean = String(raw).replace(/\\/g, "");
    const m = clean.match(FLOW_MEDIA_PATH_RE);
    if (!m) continue;
    const mediaType = String(m[1] || "").toLowerCase();
    const mediaId = String(m[2] || "").toLowerCase();
    if (!/^[0-9a-f-]{36}$/.test(mediaId)) continue;
    if (mediaType !== "image" && mediaType !== "video") continue;
    dedup.set(mediaId, { mediaId, mediaType, url: clean });
  }
  return Array.from(dedup.values());
}

async function handlePullProjectUrls(msg) {
  const { id, params } = msg;
  const projectId = String(params?.projectId || "").trim();
  const forceFresh = Boolean(params?.forceFresh);
  const normalizedProjectId = normalizeProjectId(projectId);
  if (normalizedProjectId) {
    setActiveProjectId(normalizedProjectId, "pull_project_urls");
  }
  addRequestLog({
    id,
    type: "URL_REFRESH",
    time: new Date().toISOString(),
    status: "processing",
    error: null,
    outputUrl: null,
    url: "pull_project_urls",
    projectId: normalizedProjectId || "",
    payloadSummary: projectId ? `project_id=${projectId}` : "project_id=missing",
  });
  const mediaHints = Array.isArray(params?.mediaHints)
    ? params.mediaHints
        .map((row) => ({
          mediaId: String(row?.mediaId || "").toLowerCase().trim(),
          mediaType: String(row?.mediaType || "").toLowerCase().trim(),
        }))
        .filter((row) => /^[0-9a-f-]{36}$/.test(row.mediaId))
    : [];
  if (!projectId) {
    updateRequestLog(id, { status: "failed", error: "MISSING_PROJECT_ID" });
    sendToAgent({ id, status: 400, error: "MISSING_PROJECT_ID" });
    return;
  }

  const cachedEntriesByProject = getCachedMediaEntries(1800, projectId);
  const hintIds = new Set(mediaHints.map((row) => row.mediaId));
  const cachedEntriesByHints = !cachedEntriesByProject.length && hintIds.size
    ? getCachedMediaEntries(2600).filter((row) => hintIds.has(String(row?.mediaId || "").toLowerCase()))
    : [];
  const cachedEntries = cachedEntriesByProject.length
    ? cachedEntriesByProject
    : cachedEntriesByHints;
  const cacheSource = cachedEntriesByProject.length
    ? "cache_project"
    : (cachedEntriesByHints.length ? "cache_media_hints" : "cache_empty");
  const cacheAgeMs = lastFlowSeenAt
    ? Date.now() - lastFlowSeenAt
    : Number.MAX_SAFE_INTEGER;
  if (!forceFresh && cachedEntries.length >= 20 && cacheAgeMs < 12 * 60 * 1000) {
    updateRequestLog(id, {
      status: "success",
      httpStatus: 200,
      responseSummary: `cache_hot entries=${cachedEntries.length}`,
    });
    sendToAgent({
      id,
      status: 200,
      data: {
        projectId,
        entries: cachedEntries,
        attempts: [{ source: `${cacheSource}_hot`, status: 200, len: cachedEntries.length }],
      },
    });
    return;
  }

  let tab = null;
  try {
    const maxWaitMs = cachedEntries.length ? 5000 : 9000;
    tab = await Promise.race([
      ensureFlowToolTabReady(projectId),
      sleep(maxWaitMs).then(() => null),
    ]);
  } catch (e) {
    if (!forceFresh && cachedEntries.length) {
      updateRequestLog(id, {
        status: "success",
        httpStatus: 200,
        responseSummary: `cache entries=${cachedEntries.length}`,
      });
      sendToAgent({
        id,
        status: 200,
        data: {
          projectId,
          entries: cachedEntries,
          attempts: [{ source: cacheSource, status: 200, len: cachedEntries.length }],
        },
      });
      return;
    }
    updateRequestLog(id, {
      status: "failed",
      httpStatus: 503,
      error: e?.message || "NO_FLOW_TAB",
    });
    sendToAgent({ id, status: 503, error: e?.message || "NO_FLOW_TAB" });
    return;
  }
  if (!tab?.id) {
    if (!forceFresh && cachedEntries.length) {
      updateRequestLog(id, {
        status: "success",
        httpStatus: 200,
        responseSummary: `cache entries=${cachedEntries.length}`,
      });
      sendToAgent({
        id,
        status: 200,
        data: {
          projectId,
          entries: cachedEntries,
          attempts: [{ source: cacheSource, status: 200, len: cachedEntries.length }],
        },
      });
      return;
    }
    updateRequestLog(id, {
      status: "failed",
      httpStatus: 503,
      error: "NO_FLOW_TAB",
    });
    sendToAgent({ id, status: 503, error: "NO_FLOW_TAB" });
    return;
  }

  try {
    await chrome.scripting
      .executeScript({ target: { tabId: tab.id }, files: ["content.js"] })
      .catch(() => {});

    const execResults = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      world: "MAIN",
      args: [projectId, mediaHints],
      func: async (pid, hintRows) => {
        const mkInput = (payload) => encodeURIComponent(JSON.stringify(payload));
        const normalizedHints = Array.isArray(hintRows)
          ? hintRows
              .map((row) => ({
                mediaId: String(row?.mediaId || "").toLowerCase().trim(),
                mediaType: String(row?.mediaType || "").toLowerCase().trim(),
              }))
              .filter((row) => /^[0-9a-f-]{36}$/.test(row.mediaId))
          : [];
        const hintMap = new Map(
          normalizedHints.map((row) => [row.mediaId, row.mediaType]),
        );
        const buildCandidates = () => {
          const pathname = String(window.location.pathname || "");
          const localeMatch = pathname.match(/^\/fx\/([^/]+)\//i);
          const locale = localeMatch?.[1] ? String(localeMatch[1]).trim() : "";
          const roots = [
            locale ? `${window.location.origin}/fx/${locale}/api/trpc` : null,
            `${window.location.origin}/fx/api/trpc`,
            `${window.location.origin}/api/trpc`,
            locale ? `https://flow.google.com/fx/${locale}/api/trpc` : null,
            `https://flow.google.com/api/trpc`,
            `https://flow.google.com/fx/api/trpc`,
            locale ? `https://labs.google/fx/${locale}/api/trpc` : null,
            `https://labs.google/fx/api/trpc`,
            `https://labs.google/api/trpc`,
          ].filter(Boolean);
          const payloads = [
            ["flow.getFlow", { json: { projectId: pid } }],
            ["flow.getFlow", { projectId: pid }],
            ["flow.getProject", { json: { projectId: pid } }],
            ["flow.getProject", { projectId: pid }],
            ["flow.getProjectFlow", { json: { projectId: pid } }],
            ["flow.getProjectFlow", { projectId: pid }],
            ["project.getProject", { json: { projectId: pid } }],
            ["project.getProject", { projectId: pid }],
            ["project.getProject", { id: pid }],
            ["project.getFlow", { json: { projectId: pid } }],
            ["project.getFlow", { projectId: pid }],
          ];
          const out = [];
          const seen = new Set();
          for (const root of roots) {
            for (const [procedure, payload] of payloads) {
              const candidates = [
                [`${root}/${procedure}?input=${mkInput(payload)}`, "GET", null],
                [
                  `${root}/${procedure}?batch=1&input=${mkInput({ 0: payload })}`,
                  "GET",
                  null,
                ],
                [`${root}/${procedure}`, "POST", payload],
                [`${root}/${procedure}?batch=1`, "POST", { 0: payload }],
              ];
              for (const candidate of candidates) {
                const key = `${candidate[1]}:${candidate[0]}:${JSON.stringify(candidate[2] || null)}`;
                if (seen.has(key)) continue;
                seen.add(key);
                out.push(candidate);
                if (out.length >= 40) return out;
              }
            }
          }
          return out;
        };
        const endpointCandidates = buildCandidates();
        const signedUrlRe =
          /https:\/\/(?:storage\.googleapis\.com\/ai-sandbox-videofx\/(?:image|video)\/[0-9a-f-]{36}|flow-content\.google\/(?:image|video)\/[0-9a-f-]{36})[^\s"'\\]*/gi;
        const mediaPathRe = /\/(image|video)\/([0-9a-f-]{36})(?:\?|$)/i;
        const decodeEscaped = (raw) =>
          String(raw || "")
            .replace(/\\\//g, "/")
            .replace(/\\u([0-9a-fA-F]{4})/g, (_m, hex) =>
              String.fromCharCode(parseInt(hex, 16)),
            );
        const dedup = new Map();
        const attempts = [];
        const isDirectMediaUrl = (value) =>
          typeof value === "string"
          && /https:\/\/(?:storage\.googleapis\.com\/ai-sandbox-videofx\/(?:image|video)\/[0-9a-f-]{36}|flow-content\.google\/(?:image|video)\/[0-9a-f-]{36})/i.test(value);
        const upsertFromText = (raw) => {
          if (!raw) return;
          const normalized = decodeEscaped(raw);
          const matches = normalized.match(signedUrlRe) || [];
          for (const item of matches) {
            const clean = String(item || "").replace(/\\/g, "");
            const m = clean.match(mediaPathRe);
            if (!m) continue;
            let mediaType = String(m[1] || "").toLowerCase();
            const mediaId = String(m[2] || "").toLowerCase();
            if (!/^[0-9a-f-]{36}$/.test(mediaId)) continue;
            if (!mediaType) {
              mediaType = String(hintMap.get(mediaId) || "").toLowerCase();
            }
            if (mediaType !== "image" && mediaType !== "video") continue;
            dedup.set(mediaId, { mediaId, mediaType, url: clean });
          }
        };

        const probeRedirectCandidates = async () => {
          if (!normalizedHints.length) return;
          const roots = Array.from(
            new Set(
              [
                `${window.location.origin}/fx/api/trpc`,
                `https://labs.google/fx/api/trpc`,
                `https://flow.google.com/fx/api/trpc`,
              ].filter(Boolean),
            ),
          );
          // Keep redirect probing lightweight to avoid pull_project_urls timeout.
          const mediaRows = normalizedHints.slice(0, 24);
          const tasks = [];
          for (const row of mediaRows) {
            for (const root of roots) {
              const q = new URLSearchParams({
                name: row.mediaId,
                mediaUrlType: "MEDIA_URL_TYPE_ORIGINAL",
              });
              tasks.push({
                mediaId: row.mediaId,
                mediaType: row.mediaType,
                url: `${root}/media.getMediaUrlRedirect?${q.toString()}`,
              });
            }
          }
          const maxProbes = 72;
          if (tasks.length > maxProbes) tasks.length = maxProbes;
          let index = 0;
          let stop = false;
          const targetFound = Math.max(8, Math.min(mediaRows.length, 18));
          const workers = new Array(Math.min(6, tasks.length)).fill(0).map(async () => {
            while (index < tasks.length && !stop) {
              const current = tasks[index++];
              const controller = new AbortController();
              const timeoutHandle = setTimeout(() => controller.abort(), 1200);
              try {
                const resp = await fetch(current.url, {
                  method: "GET",
                  credentials: "include",
                  redirect: "follow",
                  signal: controller.signal,
                });
                const finalUrl = String(resp.url || "");
                if (finalUrl.startsWith("http")) {
                  upsertFromText(finalUrl);
                  let text = "";
                  try { text = await resp.text(); } catch (_) { text = ""; }
                  if (text) upsertFromText(text);
                  if (!dedup.has(current.mediaId) && isDirectMediaUrl(finalUrl)) {
                    dedup.set(current.mediaId, {
                      mediaId: current.mediaId,
                      mediaType: current.mediaType || "image",
                      url: finalUrl,
                    });
                  }
                  if (dedup.size >= targetFound) {
                    stop = true;
                  }
                }
              } catch (_) {
                // ignore
              } finally {
                clearTimeout(timeoutHandle);
              }
            }
          });
          await Promise.all(workers);
          attempts.push({
            source: "media_redirect_probe",
            status: 200,
            len: dedup.size,
            probes: tasks.length,
          });
        };

        // Fast path: read already loaded sources first.
        let trpcPerfUrls = [];
        try {
          const resources = (performance.getEntriesByType("resource") || [])
            .map((entry) => entry?.name)
            .filter((name) => typeof name === "string");
          for (const item of resources) upsertFromText(item);
          trpcPerfUrls = Array.from(
            new Set(
              resources.filter((item) =>
                item.includes("/api/trpc/"),
              ),
            ),
          ).slice(0, 24);
          const sample = resources
            .filter((item) =>
              item.includes("flow-content.google")
              || item.includes("storage.googleapis.com")
              || item.includes("googleusercontent.com")
              || item.includes("/image/")
              || item.includes("/video/")
              || item.includes("/api/trpc/"),
            )
            .slice(0, 8)
            .map((item) => String(item).slice(0, 220));
          attempts.push({
            source: "performance",
            status: 200,
            len: resources.length,
            trpc: trpcPerfUrls.length,
            sample,
          });
        } catch (_) {
          // ignore
        }
        try {
          const html = String(document.documentElement?.outerHTML || "");
          if (html) upsertFromText(html);
          attempts.push({ source: "html", status: 200, len: html.length });
        } catch (_) {
          // ignore
        }
        try {
          const nodes = Array.from(document.querySelectorAll("img,video,source"));
          let domCount = 0;
          const domSample = [];
          for (const el of nodes) {
            const src = el?.currentSrc || el?.src || "";
            const srcset = el?.srcset || "";
            if (src) {
              upsertFromText(src);
              domCount += 1;
              if (domSample.length < 6) domSample.push(String(src).slice(0, 220));
            }
            if (srcset) {
              upsertFromText(srcset);
              domCount += 1;
              if (domSample.length < 6) domSample.push(String(srcset).slice(0, 220));
            }
          }
          attempts.push({ source: "dom", status: 200, len: domCount, sample: domSample });
        } catch (_) {
          // ignore
        }

        const fetchOne = async ([url, method, body]) => {
          let timeoutHandle = null;
          try {
            const controller = new AbortController();
            timeoutHandle = setTimeout(() => controller.abort(), 4500);
            const resp = await fetch(url, {
              method,
              headers: {
                "content-type": "application/json",
                accept: "*/*",
              },
              credentials: "include",
              signal: controller.signal,
              body: body ? JSON.stringify(body) : undefined,
            });
            const text = await resp.text();
            return {
              url,
              status: resp.status,
              text,
            };
          } catch (error) {
            return {
              url,
              status: 0,
              error: error?.message || "FETCH_FAILED",
              text: "",
            };
          } finally {
            if (timeoutHandle) clearTimeout(timeoutHandle);
          }
        };

        if (dedup.size < 10 && trpcPerfUrls.length) {
          const perfSettled = await Promise.all(
            trpcPerfUrls.map((url) => fetchOne([url, "GET", null])),
          );
          for (const row of perfSettled) {
            attempts.push({
              source: "perf_trpc",
              url: row.url,
              status: row.status,
              len: row.text?.length || 0,
              ...(row.error ? { error: row.error } : {}),
            });
            if (!row.text) continue;
            upsertFromText(row.text);
          }
        }

        const settled = await Promise.all(
          endpointCandidates.map((candidate) => fetchOne(candidate)),
        );
        for (const row of settled) {
          attempts.push({
            url: row.url,
            status: row.status,
            len: row.text?.length || 0,
            ...(row.error ? { error: row.error } : {}),
          });
          if (!row.text) continue;
          upsertFromText(row.text);
        }
        if (dedup.size < 10) {
          await probeRedirectCandidates();
        }

        return {
          projectId: pid,
          entries: Array.from(dedup.values()),
          attempts,
        };
      },
    });

    const result = execResults?.[0]?.result || {};
    const entriesRaw = Array.isArray(result.entries) ? result.entries : [];
    const entries = entriesRaw.map((row) => ({
      ...(row || {}),
      projectId: normalizeProjectId(row?.projectId || projectId),
    }));
    if (entries.length) queueMediaEntriesForAgent(entries);
    const mergedEntries = entries.length
      ? entries
      : cachedEntries;
    updateRequestLog(id, {
      status: "success",
      httpStatus: 200,
      responseSummary: `entries=${mergedEntries.length}`,
    });
    sendToAgent({
      id,
      status: 200,
      data: {
        projectId,
        entries: mergedEntries,
        attempts: Array.isArray(result.attempts) ? result.attempts : [],
      },
    });
  } catch (e) {
    if (!forceFresh && cachedEntries.length) {
      updateRequestLog(id, {
        status: "success",
        httpStatus: 200,
        responseSummary: `cache_fallback entries=${cachedEntries.length}`,
      });
      sendToAgent({
        id,
        status: 200,
        data: {
          projectId,
          entries: cachedEntries,
          attempts: [
            { source: `${cacheSource}_fallback`, status: 200, len: cachedEntries.length },
          ],
        },
      });
      return;
    }
    updateRequestLog(id, {
      status: "failed",
      httpStatus: 500,
      error: e?.message || "PULL_PROJECT_URLS_FAILED",
    });
    sendToAgent({
      id,
      status: 500,
      error: e?.message || "PULL_PROJECT_URLS_FAILED",
    });
  }
}

// ─── API Request Proxy ──────────────────────────────────────

async function handleTrpcRequest(msg) {
  const { id, params } = msg;
  const { url, method = "POST", headers = {}, body } = params;
  const trpcProjectId =
    extractProjectIdFromApiRequest(url, body)
    || extractProjectIdFromFlowUrl(url);
  if (trpcProjectId) {
    setActiveProjectId(trpcProjectId, "trpc_request");
  }

  let trpcUrl = null;
  try {
    trpcUrl = new URL(url);
  } catch {
    trpcUrl = null;
  }
  const host = trpcUrl?.host || "";
  const isAllowedHost =
    host === "labs.google" ||
    host.endsWith(".labs.google") ||
    host === "flow.google.com" ||
    host.endsWith(".flow.google.com");
  const isAllowedPath = trpcUrl?.pathname?.includes("/api/trpc/") ?? false;
  if (!trpcUrl || trpcUrl.protocol !== "https:" || !isAllowedHost || !isAllowedPath) {
    sendToAgent({ id, error: "INVALID_TRPC_URL" });
    return;
  }

  setState("running");
  // TRPC calls don't consume captcha — don't count in metrics

  const logId = id;
  const logType = url.includes("createProject") ? "CREATE_PROJECT" : "TRPC";
  if (shouldLogType(logType)) {
    const payloadSummary = body ? JSON.stringify(body).slice(0, 260) : null;
    addRequestLog({
      id: logId,
      type: logType,
      time: new Date().toISOString(),
      status: "processing",
      error: null,
      outputUrl: null,
      url,
      projectId: normalizeProjectId(trpcProjectId || inferActiveProjectId()),
      payloadSummary,
    });
  }

  const fetchHeaders = { "Content-Type": "application/json", ...headers };
  if (flowKey) {
    fetchHeaders["authorization"] = `Bearer ${flowKey}`;
  }

  try {
    const resp = await fetch(url, {
      method,
      headers: fetchHeaders,
      body: body ? JSON.stringify(body) : undefined,
      credentials: "include",
    });
    const text = await resp.text();
    let data = text;
    try {
      data = JSON.parse(text);
    } catch (_) {
      // Keep raw response text for non-JSON responses.
    }
    chrome.storage.local.set({ metrics });
    updateRequestLog(logId, {
      status: resp.ok ? "success" : "failed",
      httpStatus: resp.status,
      responseSummary: String(text || "").slice(0, 300),
      ...(resp.ok ? {} : { error: `HTTP_${resp.status}` }),
    });
    sendToAgent({ id, status: resp.status, data });
  } catch (e) {
    console.error("[FlowAgent] tRPC request failed:", e);
    chrome.storage.local.set({ metrics });
    updateRequestLog(logId, {
      status: "failed",
      error: e.message || "TRPC_FETCH_FAILED",
    });
    sendToAgent({ id, error: e.message || "TRPC_FETCH_FAILED" });
  } finally {
    setState("idle");
  }
}

async function performFlowTabFetch(
  url,
  methodUpper,
  headers,
  finalBody,
  projectId = "",
) {
  const tab = await ensureFlowToolTabReady(projectId);
  if (!tab?.id) throw new Error("NO_FLOW_TAB");

  const execResults = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    world: "MAIN",
    args: [url, methodUpper, headers || {}, finalBody || null],
    func: async (targetUrl, method, fetchHeaders, payload) => {
      try {
        const response = await fetch(targetUrl, {
          method,
          headers: fetchHeaders || {},
          credentials: "include",
          body: method === "GET" ? undefined : JSON.stringify(payload || {}),
        });
        const text = await response.text();
        return { ok: true, status: response.status, text };
      } catch (error) {
        return {
          ok: false,
          error: error?.message || "FLOW_TAB_FETCH_FAILED",
        };
      }
    },
  });

  const result = execResults?.[0]?.result;
  if (!result?.ok) {
    throw new Error(result?.error || "FLOW_TAB_FETCH_FAILED");
  }
  return {
    status: Number(result.status) || 500,
    text: String(result.text || ""),
  };
}

async function handleApiRequest(msg) {
  const { id, params } = msg;
  const { url, method, headers, body, captchaAction } = params;
  const requestProjectId = extractProjectIdFromApiRequest(url, body);
  if (requestProjectId) {
    setActiveProjectId(requestProjectId, "api_request");
  }

  if (!url) {
    sendToAgent({ id, error: "MISSING_URL" });
    return;
  }

  if (!url.startsWith("https://aisandbox-pa.googleapis.com/")) {
    sendToAgent({ id, error: "INVALID_URL" });
    return;
  }

  setState("running");
  const hasCaptcha = !!captchaAction;
  if (hasCaptcha) metrics.requestCount++;

  const logId = id;
  const logType = _classifyApiUrl(url);
  if (shouldLogType(logType)) {
    const payloadSummary = body ? JSON.stringify(body).slice(0, 200) : null;
    addRequestLog({
      id: logId,
      type: logType,
      time: new Date().toISOString(),
      status: "processing",
      error: null,
      outputUrl: null,
      url,
      projectId: normalizeProjectId(requestProjectId || inferActiveProjectId()),
      payloadSummary,
    });
  }

  try {
    // Step 1: Solve captcha if needed
    let captchaToken = null;
    if (captchaAction) {
      const captchaResult = await solveCaptcha(id, captchaAction, requestProjectId);
      captchaToken = captchaResult?.token || null;
      if (!captchaToken) {
        // Cannot proceed without captcha — API will 403
        const err = captchaResult?.error || "CAPTCHA_FAILED";
        console.error(
          `[FlowAgent] Captcha failed for ${captchaAction}: ${err}`,
        );
        sendToAgent({ id, status: 403, error: `CAPTCHA_FAILED: ${err}` });
        if (hasCaptcha) {
          metrics.failedCount++;
          metrics.lastError = `CAPTCHA_FAILED: ${err}`;
        }
        chrome.storage.local.set({ metrics });
        updateRequestLog(logId, {
          status: "failed",
          error: `CAPTCHA_FAILED: ${err}`,
        });
        setState("idle");
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

    // Step 3: Use flowKey for auth (with one bootstrap attempt if missing)
    let activeFlowKey = flowKey;
    if (!activeFlowKey) {
      try {
        await captureTokenFromFlowTab(requestProjectId);
      } catch (_) {
        // ignore bootstrap errors and continue
      }
      await sleep(700);
      activeFlowKey = flowKey;
    }

    const methodUpper = String(method || "POST").toUpperCase();
    const isReadGet = methodUpper === "GET";
    const isMediaRead = /\/v1\/media\//.test(url);
    const isCreditsRead = /\/v1\/credits(?:\?|$)/.test(url);

    const buildFetchUrl = ({
      dropProjectContext = false,
    } = {}) => {
      if (!dropProjectContext) return url;
      try {
        const parsed = new URL(url);
        parsed.searchParams.delete("clientContext.projectId");
        return parsed.toString();
      } catch {
        return url;
      }
    };

    const buildFetchHeaders = (
      token,
      { minimal = false } = {},
    ) => {
      const base = { ...(headers || {}) };
      const mustMinimize = minimal || (isReadGet && (isMediaRead || isCreditsRead));
      if (mustMinimize) {
        const clean = {};
        const accept = base.accept || base.Accept;
        const lang = base["accept-language"] || base["Accept-Language"];
        if (accept) clean.accept = accept;
        if (lang) clean["accept-language"] = lang;
        if (token) clean.authorization = `Bearer ${token}`;
        return clean;
      }
      if (token) {
        base.authorization = `Bearer ${token}`;
      } else {
        delete base.authorization;
      }
      return base;
    };

    const performApiFetch = async (
      token,
      { minimal = false, dropProjectContext = false, omitCredentials = false } = {},
    ) => {
      const targetUrl = buildFetchUrl({ dropProjectContext });
      const fetchHeaders = buildFetchHeaders(token, { minimal });
      return fetch(targetUrl, {
        method: methodUpper,
        headers: fetchHeaders,
        credentials: omitCredentials ? "omit" : "include",
        body: methodUpper === "GET" ? undefined : JSON.stringify(finalBody),
      });
    };

    // Step 4: Make the API call from browser context
    let response = null;
    let responseText = "";
    const applyTabResponse = (tabResult) => {
      response = {
        status: Number(tabResult?.status) || 500,
        ok: Number(tabResult?.status) >= 200 && Number(tabResult?.status) < 300,
      };
      responseText = String(tabResult?.text || "");
    };

    try {
      response = await performApiFetch(activeFlowKey);
      responseText = await response.text();
    } catch (primaryFetchErr) {
      if (!(isMediaRead || isCreditsRead)) throw primaryFetchErr;

      // Fallback path for /v1/media where strict endpoint header handling can fail.
      try {
        response = await performApiFetch(activeFlowKey, { minimal: true });
        responseText = await response.text();
      } catch (retryErr) {
        try {
          response = await performApiFetch(activeFlowKey, {
            minimal: true,
            dropProjectContext: true,
            omitCredentials: true,
          });
          responseText = await response.text();
        } catch (_) {
          const viaTab = await performFlowTabFetch(
            buildFetchUrl({ dropProjectContext: true }),
            methodUpper,
            buildFetchHeaders(activeFlowKey, { minimal: true }),
            finalBody,
            requestProjectId,
          );
          applyTabResponse(viaTab);
        }
      }
    }

    // Token/context may be stale (401 and sometimes 400 on credits endpoint).
    // Try one token-refresh + one retry.
    const shouldRetryAuth =
      response
      && (
        response.status === 401
        || (isCreditsRead && response.status === 400)
      );
    if (shouldRetryAuth) {
      try {
        await captureTokenFromFlowTab(requestProjectId);
      } catch (_) {
        // ignore refresh errors and keep original response
      }
      await sleep(900);
      const refreshedFlowKey = flowKey;
      if (refreshedFlowKey && refreshedFlowKey !== activeFlowKey) {
        activeFlowKey = refreshedFlowKey;
        try {
          response = await performApiFetch(activeFlowKey, {
            minimal: isReadGet && (isMediaRead || isCreditsRead),
            dropProjectContext: false,
          });
          responseText = await response.text();
        } catch (retry401Err) {
          if (!(isReadGet && (isMediaRead || isCreditsRead))) throw retry401Err;
          const viaTab = await performFlowTabFetch(
            buildFetchUrl({ dropProjectContext: false }),
            methodUpper,
            buildFetchHeaders(activeFlowKey, { minimal: true }),
            finalBody,
            requestProjectId,
          );
          applyTabResponse(viaTab);
        }
      }
    }

    // Google can intermittently return 500 for project-scoped /v1/media calls.
    // Retry once globally with minimal headers before surfacing the failure.
    if (response && isMediaRead && response.status >= 500) {
      try {
        const retryResp = await performApiFetch(activeFlowKey, {
          minimal: true,
          dropProjectContext: true,
          omitCredentials: true,
        });
        const retryText = await retryResp.text();
        if (retryResp.ok || retryResp.status < response.status) {
          response = retryResp;
          responseText = retryText;
        }
      } catch (_) {
        // Keep original failed response
      }
    }

    let responseData;
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
    if (isAuthFailureResponse(response.status, responseText)) {
      setTokenAuthState("invalid", `HTTP_${response.status}`);
    } else if (response.ok && activeFlowKey) {
      setTokenAuthState("valid", null);
    }
    if (response.ok) {
      if (hasCaptcha) {
        metrics.successCount++;
        metrics.lastError = null;
      }
      updateRequestLog(logId, {
        status: "success",
        httpStatus: response.status,
        responseSummary,
      });
    } else {
      if (hasCaptcha) {
        metrics.failedCount++;
        metrics.lastError = `API_${response.status}`;
      }
      updateRequestLog(logId, {
        status: "failed",
        error: `API_${response.status}`,
        httpStatus: response.status,
        responseSummary,
      });
    }
  } catch (e) {
    sendToAgent({
      id,
      status: 500,
      error: e.message || "API_REQUEST_FAILED",
    });
    if (hasCaptcha) {
      metrics.failedCount++;
      metrics.lastError = e.message;
    }
    updateRequestLog(logId, {
      status: "failed",
      error: e.message || "API_REQUEST_FAILED",
    });
  }

  chrome.storage.local.set({ metrics });
  setState("idle");
}

// ─── State & Popup ──────────────────────────────────────────

function setState(newState) {
  state = newState;
  const badges = { idle: "●", running: "▶", off: "○" };
  const colors = { idle: "#22c55e", running: "#f59e0b", off: "#6b7280" };
  chrome.action.setBadgeText({ text: badges[state] || "" });
  chrome.action.setBadgeBackgroundColor({ color: colors[state] || "#000" });
  broadcastStatus();
}

function broadcastStatus() {
  chrome.runtime.sendMessage({ type: "STATUS_PUSH" }).catch(() => {});
}

chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  const senderTabId = sender?.tab?.id;
  const senderTabUrl = sender?.tab?.url || sender?.url || "";
  if (
    Number.isInteger(senderTabId) &&
    senderTabId >= 0 &&
    isFlowToolUrl(senderTabUrl)
  ) {
    rememberFlowTab(senderTabId, senderTabUrl, "runtimeSender");
  }

  if (msg.type === "FLOW_AUTH_TOKEN") {
    saveFlowKey(msg.token || "");
    reply({ ok: true });
    return true;
  }

  if (msg.type === "FLOW_TAB_HEARTBEAT") {
    if (Number.isInteger(senderTabId) && senderTabId >= 0) {
      rememberFlowTab(senderTabId, msg.url || senderTabUrl, "heartbeat");
    }
    reply({
      ok: true,
      flowTabId: lastFlowTabId,
      flowTabUrl: lastFlowTabUrl,
      flowTabSeenAt: lastFlowSeenAt,
    });
    return true;
  }

  if (msg.type === "STATUS") {
    reply({
      connected: ws?.readyState === WebSocket.OPEN,
      agentConnected: ws?.readyState === WebSocket.OPEN,
      flowKeyPresent: !!flowKey,
      manualDisconnect,
      activeProjectId: inferActiveProjectId(),
      flowTabId: lastFlowTabId,
      flowTabSeenAt: lastFlowSeenAt,
      tokenAge: metrics.tokenCapturedAt
        ? Date.now() - metrics.tokenCapturedAt
        : null,
      tokenAuthState: metrics.tokenAuthState || "unknown",
      tokenAuthCheckedAt: metrics.tokenAuthCheckedAt || null,
      tokenAuthError: metrics.tokenAuthError || null,
      metrics: {
        requestCount: metrics.requestCount,
        successCount: metrics.successCount,
        failedCount: metrics.failedCount,
        lastError: metrics.lastError,
        tokenAuthState: metrics.tokenAuthState || "unknown",
        tokenAuthCheckedAt: metrics.tokenAuthCheckedAt || null,
        tokenAuthError: metrics.tokenAuthError || null,
      },
      state,
    });
  }

  if (msg.type === "DISCONNECT") {
    manualDisconnect = true;
    if (ws) ws.close();
    reply({ ok: true });
    return true;
  }

  if (msg.type === "RECONNECT") {
    manualDisconnect = false;
    connectToAgent();
    reply({ ok: true });
    return true;
  }

  if (msg.type === "REQUEST_LOG") {
    reply({ log: requestLog });
    return true;
  }

  if (msg.type === "OPEN_FLOW_TAB") {
    ensureFlowTabVisible()
      .then((tab) => {
        if (tab?.id) reply({ ok: true, tabId: tab.id });
        else reply({ error: "NO_FLOW_TAB" });
      })
      .catch((e) => reply({ error: e.message }));
    return true;
  }

  if (msg.type === "REFRESH_TOKEN") {
    captureTokenFromFlowTab()
      .then(() => reply({ ok: true }))
      .catch((e) => reply({ error: e.message }));
    return true;
  }

  if (msg.type === "TEST_CAPTCHA") {
    solveCaptcha(`test-${Date.now()}`, msg.pageAction || "IMAGE_GENERATION")
      .then((r) => reply(r))
      .catch((e) => reply({ error: e.message }));
    return true;
  }

  if (msg.type === "TRPC_MEDIA_URLS") {
    handleTrpcMediaUrls(msg.trpcUrl, msg.body);
    reply({ ok: true });
    return true;
  }

  return true;
});

// ─── TRPC Media URL Extractor ──────────────────────────────

function handleTrpcMediaUrls(trpcUrl, bodyText) {
  try {
    const projectIdFromUrl = extractProjectIdFromFlowUrl(trpcUrl);
    if (projectIdFromUrl) {
      setActiveProjectId(projectIdFromUrl, "trpc_media_urls");
    }
    const normalizedBody = decodeEscapedFlowText(bodyText);
    // Extract all fresh GCS signed URLs
    const urlRegex =
      /https:\/\/(?:storage\.googleapis\.com\/ai-sandbox-videofx\/(?:image|video)\/[0-9a-f-]{36}|flow-content\.google\/(?:image|video)\/[0-9a-f-]{36})\?[^"'\s]+/g;
    const matches = normalizedBody.match(urlRegex) || [];
    if (!matches.length) return;

    // Deduplicate and parse
    const urlMap = {};
    for (const rawUrl of matches) {
      // Unescape JSON-escaped URLs
      const url = decodeEscapedFlowText(rawUrl).replace(/\\/g, "");
      const mediaMatch = url.match(/\/(image|video)\/([0-9a-f-]{36})\?/);
      if (mediaMatch) {
        const [, mediaType, mediaId] = mediaMatch;
        // Keep last occurrence (freshest)
        urlMap[mediaId] = { mediaType, url, mediaId };
      }
    }

    const entries = Object.values(urlMap).map((entry) => ({
      ...entry,
      projectId: projectIdFromUrl || "",
    }));
    if (!entries.length) return;
    queueMediaEntriesForAgent(entries);

    console.log(
      `[FlowAgent] Captured ${entries.length} fresh media URLs from TRPC`,
    );
    // URL refresh is silent — don't show in request log
  } catch (e) {
    console.error("[FlowAgent] Failed to extract TRPC media URLs:", e);
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

function _rand(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function _buildBatchLogPayload() {
  const events = [];
  const types = ["FLOW_IMAGE_LATENCY", "FLOW_VIDEO_LATENCY"];
  const count = _rand(1, 3);
  for (let i = 0; i < count; i++) {
    events.push({
      event: types[_rand(0, types.length - 1)],
      eventProperties: [
        { key: "CURRENT_TIME_MS", doubleValue: Date.now() },
        { key: "DURATION_MS", doubleValue: _rand(150, 800) },
        { key: "USER_AGENT", stringValue: _UA },
        { key: "IS_DESKTOP", booleanValue: true },
      ],
      eventMetadata: { sessionId: _telemetrySessionId },
      eventTime: new Date().toISOString(),
    });
  }
  return { appEvents: events };
}

function _buildFrontendEventsPayload() {
  const eventTypes = [
    "FLOW_IMAGE_LATENCY",
    "FLOW_VIDEO_LATENCY",
    "GRID_SCROLL_DEPTH",
    "FLOW_PROJECT_OPEN",
    "FLOW_SCENE_VIEW",
  ];
  const count = _rand(1, 4);
  const events = [];
  for (let i = 0; i < count; i++) {
    const et = eventTypes[_rand(0, eventTypes.length - 1)];
    const params = {
      USER_AGENT: {
        "@type": "type.googleapis.com/google.protobuf.StringValue",
        value: _UA,
      },
      IS_DESKTOP: {
        "@type": "type.googleapis.com/google.protobuf.StringValue",
        value: "true",
      },
    };
    if (et.includes("LATENCY")) {
      params.CURRENT_TIME_MS = {
        "@type": "type.googleapis.com/google.protobuf.StringValue",
        value: String(Date.now()),
      };
      params.DURATION_MS = {
        "@type": "type.googleapis.com/google.protobuf.StringValue",
        value: String(_rand(100, 600)),
      };
    }
    if (et === "GRID_SCROLL_DEPTH") {
      params.MEDIA_GENERATION_PAYGATE_TIER = {
        "@type": "type.googleapis.com/google.protobuf.StringValue",
        value: "PAYGATE_TIER_TWO",
      };
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
  if (!flowKey || state === "off") return;

  const headers = {
    "Content-Type": "text/plain;charset=UTF-8",
    authorization: `Bearer ${flowKey}`,
  };

  // Telemetry is silent — don't show in request log
  try {
    if (Math.random() < 0.5) {
      await fetch(`https://aisandbox-pa.googleapis.com/v1:batchLog`, {
        method: "POST",
        headers,
        credentials: "include",
        body: JSON.stringify(_buildBatchLogPayload()),
      });
    } else {
      await fetch(
        `https://aisandbox-pa.googleapis.com/v1/flow:batchLogFrontendEvents`,
        {
          method: "POST",
          headers,
          credentials: "include",
          body: JSON.stringify(_buildFrontendEventsPayload()),
        },
      );
    }
  } catch {}
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
setInterval(
  () => {
    _telemetrySessionId = `;${Date.now()}`;
  },
  _rand(25, 35) * 60 * 1000,
);

scheduleTelemetry();

console.log("[FlowAgent] Extension loaded");
