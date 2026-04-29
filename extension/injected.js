/**
 * Injected into MAIN world on labs.google — has access to window.grecaptcha
 * Also intercepts TRPC fetch responses to capture fresh signed media URLs.
 */
const SITE_KEY = '6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV';

// ─── TRPC Response Monitor ─────────────────────────────────
// Monkey-patch fetch to intercept TRPC responses containing media URLs.
// Fresh signed GCS URLs are extracted and forwarded to the agent.

const _originalFetch = window.fetch;
const _SIGNED_HINTS = [
  'storage.googleapis.com/ai-sandbox-videofx/',
  'flow-content.google/image/',
  'flow-content.google/video/',
  'ai-sandbox-videofx/image/',
  'ai-sandbox-videofx/video/',
];

function _extractAuthTokenFromHeaders(headersLike) {
  if (!headersLike) return null;
  try {
    const headers = new Headers(headersLike);
    const auth = headers.get('authorization') || headers.get('Authorization');
    if (!auth || !/^Bearer\s+ya29\./i.test(auth)) return null;
    return auth.replace(/^Bearer\s+/i, '').trim();
  } catch {
    return null;
  }
}

function _emitFlowAuthToken(token) {
  if (!token) return;
  window.dispatchEvent(new CustomEvent('FLOW_AUTH_TOKEN', {
    detail: { token },
  }));
}

function _isTrpcUrl(url) {
  return typeof url === 'string' && url.includes('/api/trpc/');
}

function _emitTrpcMediaIfNeeded(url, text) {
  if (!_isTrpcUrl(url) || !text) return;
  const hasSignedMediaUrl = _SIGNED_HINTS.some((hint) => text.includes(hint));
  if (!hasSignedMediaUrl) return;
  window.dispatchEvent(new CustomEvent('TRPC_MEDIA_URLS', {
    detail: { url, body: text },
  }));
}

window.fetch = async function (...args) {
  try {
    const req = args[0];
    const init = args[1];
    const tokenFromInit = _extractAuthTokenFromHeaders(init?.headers);
    if (tokenFromInit) _emitFlowAuthToken(tokenFromInit);

    if (req instanceof Request) {
      const tokenFromReq = _extractAuthTokenFromHeaders(req.headers);
      if (tokenFromReq) _emitFlowAuthToken(tokenFromReq);
    }
  } catch {}

  const response = await _originalFetch.apply(this, args);
  try {
    const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
    if (_isTrpcUrl(url) && response.ok) {
      const clone = response.clone();
      clone.text().then(text => {
        _emitTrpcMediaIfNeeded(url, text);
      }).catch(() => {});
    }
  } catch {}
  return response;
};

// Some Flow builds still use XHR for TRPC calls. Mirror fetch interception here.
const _xhrOpen = XMLHttpRequest.prototype.open;
const _xhrSend = XMLHttpRequest.prototype.send;

XMLHttpRequest.prototype.open = function (method, url, ...rest) {
  try {
    this.__flowkit_url = typeof url === 'string' ? url : String(url || '');
  } catch {
    this.__flowkit_url = '';
  }
  return _xhrOpen.call(this, method, url, ...rest);
};

XMLHttpRequest.prototype.send = function (...args) {
  try {
    this.addEventListener('load', function () {
      try {
        const url = this.__flowkit_url || this.responseURL || '';
        if (!_isTrpcUrl(url)) return;
        if (!(this.status >= 200 && this.status < 400)) return;
        const text = typeof this.responseText === 'string' ? this.responseText : '';
        _emitTrpcMediaIfNeeded(url, text);
      } catch {}
    });
  } catch {}
  return _xhrSend.apply(this, args);
};


window.addEventListener('GET_CAPTCHA', async ({ detail }) => {
  const { requestId, pageAction } = detail;
  try {
    await waitForGrecaptcha();
    const token = await window.grecaptcha.enterprise.execute(SITE_KEY, {
      action: pageAction,
    });
    window.dispatchEvent(new CustomEvent('CAPTCHA_RESULT', {
      detail: { requestId, token },
    }));
  } catch (e) {
    window.dispatchEvent(new CustomEvent('CAPTCHA_RESULT', {
      detail: { requestId, error: e.message },
    }));
  }
});

function waitForGrecaptcha(timeout = 10000) {
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
