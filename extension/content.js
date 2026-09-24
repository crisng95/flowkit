/**
 * Content script — bridge between background.js and injected.js
 * Injects injected.js into MAIN world to access window.grecaptcha
 *
 * reCAPTCHA preload (ported from FlowBridge2): flow.google.com enforces
 * `require-trusted-types-for 'script'` with a policy that rejects google.com
 * URLs, and it no longer ships grecaptcha in the MAIN world at page load — a
 * plain <script src="https://www.google.com/recaptcha/enterprise.js"> tag is
 * blocked and the lazy wait then times out with `grecaptcha not available`.
 * Scripts fetched from the extension's own chrome-extension:// URL bypass the
 * page CSP entirely, so we ship enterprise.js + its real client locally and
 * feed them in right after the anchor evaluates.
 */
(function () {
  function addExtScript(name) {
    const s = document.createElement('script');
    // Cache-buster: Chrome may serve a stale injected.js out of its
    // chrome-extension:// resource cache after an extension reload.
    s.src = chrome.runtime.getURL(name) + '?v=' + chrome.runtime.getManifest().version;
    s.onload = () => s.remove();
    s.setAttribute('data-flowkit', name);
    (document.head || document.documentElement).appendChild(s);
  }

  addExtScript('injected.js');
  // The anchor sets ___grecaptcha_cfg stubs; its own gstatic append is
  // CSP-blocked, so the real client (bundled locally) follows.
  addExtScript('recaptcha_enterprise.js');
  setTimeout(() => addExtScript('recaptcha__en.js'), 50);
})();

chrome.runtime.onMessage.addListener((msg, _, reply) => {
  if (msg.type !== 'GET_CAPTCHA') return;

  const { requestId, pageAction } = msg;

  const handler = (e) => {
    if (e.detail?.requestId === requestId) {
      window.removeEventListener('CAPTCHA_RESULT', handler);
      clearTimeout(timer);
      reply({ token: e.detail.token, error: e.detail.error });
    }
  };

  const timer = setTimeout(() => {
    window.removeEventListener('CAPTCHA_RESULT', handler);
    reply({ error: 'CONTENT_TIMEOUT' });
  }, 25000);

  window.addEventListener('CAPTCHA_RESULT', handler);

  window.dispatchEvent(new CustomEvent('GET_CAPTCHA', {
    detail: { requestId, pageAction },
  }));

  return true; // keep channel open for async reply
});

// ─── TRPC Media URL Monitor ─────────────────────────────────
// Forward intercepted TRPC responses with media URLs to background.js
window.addEventListener('TRPC_MEDIA_URLS', (e) => {
  const { url, body } = e.detail || {};
  if (!body) return;
  chrome.runtime.sendMessage({
    type: 'TRPC_MEDIA_URLS',
    trpcUrl: url,
    body,
  }).catch(() => {});
});
