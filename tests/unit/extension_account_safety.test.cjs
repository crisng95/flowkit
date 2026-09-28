const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const extension = path.join(__dirname, '..', '..', 'extension');
const read = (name) => fs.readFileSync(path.join(extension, name), 'utf8');

test('manifest only auto-injects the media monitor and isolated relay', () => {
  const manifest = JSON.parse(read('manifest.json'));
  assert.deepEqual(manifest.content_scripts.map((script) => script.js), [
    ['injected.js'], ['content.js'],
  ]);
});

function makeBackground(captchaResponse = { token: 'test-token', mintPath: 'public_execute' }) {
  const calls = { tabs: 0, captcha: 0, scripts: 0, callbacks: [], rpc: 0 };
  const chrome = {
    action: { setBadgeBackgroundColor() {}, setBadgeText() {} },
    alarms: { clear() {}, create() {}, onAlarm: { addListener() {} } },
    runtime: {
      getManifest: () => ({ version: 'test', host_permissions: ['https://flow.google.com/*'] }),
      onInstalled: { addListener() {} }, onStartup: { addListener() {} },
      onMessage: { addListener() {} }, sendMessage: async () => {},
    },
    scripting: {
      async executeScript() {
        calls.scripts++;
        return [{ result: { status: 200, text: 'local-rpc-result' } }];
      },
    },
    storage: { local: { get: async () => ({}), set: async () => {} } },
    tabs: {
      async query() { calls.tabs++; return [{ id: 7, discarded: false }]; },
      async sendMessage() { calls.captcha++; return captchaResponse; },
      async create() { throw new Error('unexpected tab creation'); },
    },
    webRequest: { onBeforeSendHeaders: { addListener() {} } },
  };
  class FakeWebSocket { static CONNECTING = 0; static OPEN = 1; constructor() { this.readyState = 0; } }
  const context = vm.createContext({
    chrome, WebSocket: FakeWebSocket, URL,
    navigator: { userAgent: 'FlowkitAccountSafetyTest/1.0' },
    fetch: async (_url, options) => {
      calls.callbacks.push(JSON.parse(options.body));
      return { ok: true };
    },
    console: { log() {}, error() {} },
    setTimeout() { return 1; }, setInterval() { return 1; },
  });
  vm.runInContext(read('background.js'), context, { filename: 'background.js' });
  return { context, calls };
}

test('CAPTCHA batch and standalone paths require a literal true opt-in before tab access', async () => {
  const { context, calls } = makeBackground();
  await vm.runInContext("handleBatchRpc({id:'a',params:{rpcid:'x',freq:'__CAPTCHA__',captchaAction:'IMAGE_GENERATION'}})", context);
  await vm.runInContext("handleBatchRpc({id:'b',params:{rpcid:'x',freq:'__CAPTCHA__',captchaAction:'IMAGE_GENERATION',accountSafetyOptIn:1}})", context);
  await vm.runInContext("handleSolveCaptcha({id:'c',params:{captchaAction:'IMAGE_GENERATION'}})", context);
  await vm.runInContext("handleApiRequest({id:'d',params:{url:'https://aisandbox-pa.googleapis.com/test',captchaAction:'IMAGE_GENERATION'}})", context);
  await vm.runInContext("handleBatchRpc({id:'e',params:{rpcid:'ogiZ0b',freq:'already-filled'}})", context);
  assert.equal(calls.tabs, 0);
  assert.equal(calls.captcha, 0);
  assert.equal(calls.scripts, 0);
  assert.equal(calls.callbacks.length, 5);
  assert.ok(calls.callbacks.every((r) => r.status === 403));
  assert.ok(calls.callbacks.every((r) => (r.error || r.result?.error) === 'ACCOUNT_SAFETY_OPT_IN_REQUIRED'));
});

test('non-CAPTCHA RPC works while a placeholder without an action fails closed', async () => {
  const { context, calls } = makeBackground();
  await vm.runInContext("handleBatchRpc({id:'a',params:{rpcid:'x',freq:'plain'}})", context);
  assert.equal(calls.tabs, 1);
  assert.equal(calls.scripts, 1);
  assert.equal(calls.captcha, 0);
  assert.equal(calls.callbacks[0].status, 200);
  await vm.runInContext("handleBatchRpc({id:'b',params:{rpcid:'x',freq:'__CAPTCHA__'}})", context);
  assert.equal(calls.tabs, 1);
  assert.equal(calls.callbacks[1].error, 'CAPTCHA_ACTION_REQUIRED');
  await vm.runInContext("handleBatchRpc({id:'c',params:{rpcid:'maseQ',freq:'already-filled',accountSafetyOptIn:true}})", context);
  assert.equal(calls.tabs, 1);
  assert.equal(calls.callbacks[2].error, 'CAPTCHA_ACTION_REQUIRED');
});

test('opted-in batch mints once and returns a non-sensitive mint path', async () => {
  const { context, calls } = makeBackground();
  await vm.runInContext("handleBatchRpc({id:'a',params:{rpcid:'x',freq:'__CAPTCHA__',captchaAction:'IMAGE_GENERATION',accountSafetyOptIn:true}})", context);
  assert.equal(calls.captcha, 1);
  assert.equal(calls.scripts, 1);
  assert.equal(calls.callbacks[0].mintPath, 'public_execute');
  assert.equal(calls.callbacks[0].data, 'local-rpc-result');
});

test('detected hijack is terminal across Flow tabs', async () => {
  const { context, calls } = makeBackground({ error: 'EXTENSION_HIJACK_DETECTED', mintPath: 'hijack_detected' });
  await vm.runInContext("handleBatchRpc({id:'a',params:{rpcid:'x',freq:'__CAPTCHA__',captchaAction:'IMAGE_GENERATION',accountSafetyOptIn:true}})", context);
  assert.equal(calls.captcha, 1);
  assert.equal(calls.scripts, 0);
  assert.equal(calls.callbacks[0].mintPath, 'hijack_detected');
  assert.match(calls.callbacks[0].error, /EXTENSION_HIJACK_DETECTED/);
});

test('a token from an old Flow tab without a verified mint path is rejected', async () => {
  const { context, calls } = makeBackground({ token: 'legacy-bypass-token' });
  await vm.runInContext("handleBatchRpc({id:'a',params:{rpcid:'ogiZ0b',freq:'__CAPTCHA__',captchaAction:'IMAGE_GENERATION',accountSafetyOptIn:true}})", context);
  assert.equal(calls.captcha, 1);
  assert.equal(calls.scripts, 0);
  assert.equal(calls.callbacks[0].mintPath, 'unknown');
  assert.match(calls.callbacks[0].error, /EXTENSION_HIJACK_DETECTED/);
});

test('a failed mint does not open a recovery tab or mint twice', async () => {
  const { context, calls } = makeBackground({ error: 'NO_TOKEN' });
  await vm.runInContext("handleBatchRpc({id:'a',params:{rpcid:'ogiZ0b',freq:'__CAPTCHA__',captchaAction:'IMAGE_GENERATION',accountSafetyOptIn:true}})", context);
  assert.equal(calls.captcha, 1);
  assert.equal(calls.scripts, 0);
  assert.match(calls.callbacks[0].error, /NO_TOKEN/);
});

function makeInjected(execute) {
  const listeners = new Map();
  const results = [];
  const window = {
    fetch: async () => ({ ok: true }),
    grecaptcha: { enterprise: { ready: (callback) => callback(), execute } },
    addEventListener(name, handler) { listeners.set(name, handler); },
    dispatchEvent(event) { results.push(event); },
  };
  const context = vm.createContext({
    window, CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
    setTimeout() { return 1; },
  });
  vm.runInContext(read('injected.js'), context, { filename: 'injected.js' });
  return { window, listeners, results };
}

test('injected mint uses public execute once without changing Object.assign', async () => {
  let count = 0;
  const assign = Object.assign;
  const { listeners, results } = makeInjected(async () => { count++; return 'test-token'; });
  await listeners.get('GET_CAPTCHA')({ detail: { requestId: 'a', pageAction: 'IMAGE_GENERATION' } });
  assert.equal(count, 1);
  assert.equal(Object.assign, assign);
  assert.equal(results[0].detail.token, 'test-token');
  assert.equal(results[0].detail.mintPath, 'public_execute');
});

test('injected mint rejects a detectable Flow hijack before execute', async () => {
  let count = 0;
  const { listeners, results } = makeInjected(async function () {
    const marker = 'extension_hijack_detected';
    count++;
    return marker;
  });
  await listeners.get('GET_CAPTCHA')({ detail: { requestId: 'a', pageAction: 'IMAGE_GENERATION' } });
  assert.equal(count, 0);
  assert.equal(results[0].detail.error, 'EXTENSION_HIJACK_DETECTED');
  assert.equal(results[0].detail.mintPath, 'hijack_detected');
});

test('a Flow tab retaining the old bypass object cannot mint', async () => {
  let count = 0;
  const { window, listeners, results } = makeInjected(async () => { count++; return 'test-token'; });
  window.__fk_hijack = { trapped: false, pristine: () => 'legacy-token' };
  await listeners.get('GET_CAPTCHA')({ detail: { requestId: 'a', pageAction: 'IMAGE_GENERATION' } });
  assert.equal(count, 0);
  assert.equal(results[0].detail.error, 'EXTENSION_HIJACK_DETECTED');
});
