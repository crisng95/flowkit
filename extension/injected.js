/**
 * Injected into the page's MAIN world on flow.google.com (and an old pinned
 * labs.google tab) — has access to window.grecaptcha.
 *
 * The reCAPTCHA site key survived the September 2026 migration unchanged. The
 * TRPC fetch intercept below did not: it belongs to the labs.google frontend
 * and is inert on flow.google.com, where media urls come back inline on the
 * generate call and from the media rpc.
 */
const SITE_KEY = '6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV';

// ─── TRPC Response Monitor ─────────────────────────────────
// Monkey-patch fetch to intercept TRPC responses containing media URLs.
// Fresh signed GCS URLs are extracted and forwarded to the agent.

const _originalFetch = window.fetch;
window.fetch = async function (...args) {
  const response = await _originalFetch.apply(this, args);
  try {
    const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
    // Only intercept TRPC calls on labs.google that return project/flow data
    if (url.includes('/fx/api/trpc/') && response.ok) {
      const clone = response.clone();
      clone.text().then(text => {
        if (text.includes('storage.googleapis.com/ai-sandbox-videofx/')) {
          window.dispatchEvent(new CustomEvent('TRPC_MEDIA_URLS', {
            detail: { url, body: text },
          }));
        }
      }).catch(() => {});
    }
  } catch {}
  return response;
};


let captchaMintTail = Promise.resolve();

// ─── reCAPTCHA mint (ported from FlowBridge2 — live-verified on the 2026-09-22 build) ───
// Flow's current build rejects a token obtained by calling
// `grecaptcha.enterprise.execute(SITE_KEY, {action})` directly with
// PUBLIC_ERROR_UNUSUAL_ACTIVITY ("reCAPTCHA evaluation failed"), even though the
// site key and action match the UI byte for byte, while the same account's UI
// still generates. The working recipe is the one the page itself uses: ready() →
// render an invisible widget bound to the page's own site key → execute(widgetId).
// Prefer the site key the page is currently configured with; the constant is only
// a fallback for a page that has not configured one yet.
function resolveSitekey() {
  try {
    const cfg = window.___grecaptcha_cfg || {};
    const clients = cfg.clients || {};
    for (const k of Object.keys(clients)) {
      const c = clients[k];
      if (c && c.sitekey) return c.sitekey;
    }
  } catch (e) { /* fall through to the constant */ }
  return SITE_KEY;
}

function waitReady(timeout = 5000) {
  return new Promise((resolve) => {
    let done = false;
    const fin = () => { if (!done) { done = true; resolve(); } };
    try { window.grecaptcha?.enterprise?.ready?.(fin); } catch (e) { /* ignore */ }
    setTimeout(fin, timeout);
  });
}

let _widgetPromise = null;
function ensureWidget(sitekey) {
  if (_widgetPromise) return _widgetPromise;
  _widgetPromise = (async () => {
    await waitReady(5000);
    let host = document.getElementById('flowkit-recaptcha-host');
    if (!host) {
      host = document.createElement('div');
      host.id = 'flowkit-recaptcha-host';
      host.style.cssText = 'position:fixed;left:-9999px;top:0;width:1px;height:1px;';
      document.documentElement.appendChild(host);
    }
    return await new Promise((resolve, reject) => {
      try {
        const widgetId = window.grecaptcha.enterprise.render(host, {
          sitekey,
          size: 'invisible',
          callback: () => {},
          'error-callback': (m) => reject(new Error('render_error: ' + m)),
        });
        resolve(widgetId);
      } catch (e) {
        reject(new Error('render_threw: ' + (e && e.message || e)));
      }
    });
  })().catch((e) => { _widgetPromise = null; throw e; });
  return _widgetPromise;
}

async function executeWithRetry(sitekey, action, attempts = 2) {
  let lastErr = null;
  for (let i = 0; i < attempts; i++) {
    try {
      await waitReady(2500);
      const widgetId = await ensureWidget(sitekey);
      const token = await Promise.race([
        window.grecaptcha.enterprise.execute(widgetId, { action }),
        new Promise((_, rej) => setTimeout(() => rej(new Error('execute_hang')), 8000)),
      ]);
      if (token) return String(token);
      lastErr = new Error('empty_token');
    } catch (e) {
      lastErr = e;
    }
    await new Promise((r) => setTimeout(r, 600));
  }
  throw lastErr || new Error('execute_failed');
}

async function mintCaptcha(pageAction) {
  const previous = captchaMintTail.catch(() => {});
  let release;
  captchaMintTail = new Promise((resolve) => { release = resolve; });
  await previous;
  try {
    await waitForGrecaptcha();
    return await executeWithRetry(resolveSitekey(), pageAction);
  } finally {
    release();
  }
}

window.addEventListener('GET_CAPTCHA', async ({ detail }) => {
  const { requestId, pageAction } = detail;
  try {
    const token = await mintCaptcha(pageAction);
    window.dispatchEvent(new CustomEvent('CAPTCHA_RESULT', {
      detail: { requestId, token },
    }));
  } catch (e) {
    window.dispatchEvent(new CustomEvent('CAPTCHA_RESULT', {
      detail: { requestId, error: e.message },
    }));
  }
});

function waitForGrecaptcha(timeout = 22000) {   // it loads lazily; 10s was optimistic
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      if (window.grecaptcha?.enterprise?.execute) return resolve();
      if (Date.now() - start > timeout) return reject(new Error('grecaptcha not available'));
      setTimeout(check, 200);
    };
    check();
  });
}
