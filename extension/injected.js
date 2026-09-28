/**
 * Injected into the page's MAIN world on flow.google.com — has access to
 * window.grecaptcha. A detectable Flow hijack blocks minting; this script
 * never alters page reCAPTCHA functions or retries a token request.
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

// ─── Site key resolution ────────────────────────────────────
// Prefer the site key the page is currently configured with; the constant is
// only a fallback for a page that has not configured one yet.

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

function assertNoDetectedHijack() {
  const execute = window.grecaptcha?.enterprise?.execute;
  if (window.__fk_hijack != null ||
      (typeof execute === 'function' &&
       Function.prototype.toString.call(execute).includes('extension_hijack_detected'))) {
    throw new Error('EXTENSION_HIJACK_DETECTED');
  }
}

async function mintCaptcha(pageAction) {
  const previous = captchaMintTail.catch(() => {});
  let release;
  captchaMintTail = new Promise((resolve) => { release = resolve; });
  await previous;
  try {
    await waitForGrecaptcha();
    await waitReady(2500);
    assertNoDetectedHijack();
    const token = await Promise.race([
      window.grecaptcha.enterprise.execute(resolveSitekey(), { action: pageAction }),
      new Promise((_, reject) => setTimeout(() => reject(new Error('execute_hang')), 8000)),
    ]);
    if (!token) throw new Error('empty_token');
    return String(token);
  } finally {
    release();
  }
}

window.addEventListener('GET_CAPTCHA', async ({ detail }) => {
  const { requestId, pageAction } = detail;
  try {
    const token = await mintCaptcha(pageAction);
    window.dispatchEvent(new CustomEvent('CAPTCHA_RESULT', {
      detail: {
        requestId,
        token,
        mintPath: 'public_execute',
      },
    }));
  } catch (e) {
    window.dispatchEvent(new CustomEvent('CAPTCHA_RESULT', {
      detail: {
        requestId,
        error: e.message,
        mintPath: e.message === 'EXTENSION_HIJACK_DETECTED' ? 'hijack_detected' : 'public_execute',
      },
    }));
  }
});

function waitForGrecaptcha(timeout = 22000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      try { assertNoDetectedHijack(); } catch (e) { return reject(e); }
      if (window.grecaptcha?.enterprise?.execute) return resolve();
      if (Date.now() - start > timeout) return reject(new Error('grecaptcha not available'));
      setTimeout(check, 200);
    };
    check();
  });
}
