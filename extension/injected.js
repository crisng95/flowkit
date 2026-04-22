(() => {
  // Chrome can inject this file more than once into the same page.
  if (window.__flowKitInjected) return;
  window.__flowKitInjected = true;

  /**
   * Injected into the MAIN world on labs.google.
   * Has access to window.grecaptcha and monitors Flow TRPC responses.
   */
  const SITE_KEY = '6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV';
  const originalFetch = window.fetch;

  if (typeof originalFetch === 'function') {
    window.fetch = async function (...args) {
      const response = await originalFetch.apply(this, args);
      try {
        const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
        if (url.includes('/fx/api/trpc/') && response.ok) {
          const clone = response.clone();
          clone.text().then((text) => {
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
  }

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
        if (Date.now() - start > timeout) {
          return reject(new Error('grecaptcha not available'));
        }
        setTimeout(check, 200);
      };
      check();
    });
  }
})();
