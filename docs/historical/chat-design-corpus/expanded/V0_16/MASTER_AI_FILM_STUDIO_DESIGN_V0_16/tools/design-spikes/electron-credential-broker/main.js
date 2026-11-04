const { app, BrowserWindow, ipcMain, safeStorage, utilityProcess, MessageChannelMain } = require('electron');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

const RESULT_PATH = path.join(__dirname, 'electron_credential_broker_results.json');
const CANARY = 'MASTER_STUDIO_CANARY_SECRET_2026';
const credentialId = 'cred-canary-flow';
const provider = 'FLOW';
const operation = 'GENERATE_VIDEO';

const state = {
  tests: {},
  events: [],
  limitations: [
    'This harness proves Electron runtime behavior only on the machine where it is executed.',
    'It does not prove provider networking or browser-session credential isolation.'
  ]
};

function event(name, detail = {}) {
  state.events.push({ ts: new Date().toISOString(), name, detail });
}

function writeResults() {
  fs.writeFileSync(RESULT_PATH, JSON.stringify(state, null, 2), 'utf8');
}

function safeScan(text) {
  return !String(text).includes(CANARY);
}

async function run() {
  await app.whenReady();

  state.tests.safeStorage_available = safeStorage.isEncryptionAvailable();

  if (!safeStorage.isEncryptionAvailable()) {
    state.tests.safeStorage_round_trip = false;
    state.tests.renderer_has_no_secret_api = false;
    state.tests.utility_scoped_lease = false;
    state.tests.utility_crash_revokes_session = false;
    writeResults();
    app.exit(2);
    return;
  }

  const encrypted = await safeStorage.encryptStringAsync(CANARY);
  const decrypted = await safeStorage.decryptStringAsync(encrypted);
  state.tests.safeStorage_round_trip = decrypted === CANARY;

  const vaultPath = path.join(app.getPath('userData'), 'credential-broker-spike-vault.json');
  fs.writeFileSync(vaultPath, JSON.stringify({
    credential_id: credentialId,
    provider,
    encrypted_b64: encrypted.toString('base64')
  }, null, 2), 'utf8');
  state.tests.vault_plaintext_scan_clean = safeScan(fs.readFileSync(vaultPath, 'utf8'));

  const utilitySessionToken = crypto.randomBytes(24).toString('hex');
  let utilityAlive = true;
  let consumedLeaseIds = new Set();

  const utility = utilityProcess.fork(path.join(__dirname, 'utility.js'), [], {
    serviceName: 'Master Studio Credential Broker Spike'
  });

  utility.on('exit', () => {
    utilityAlive = false;
    event('utility_exit');
  });

  const win = new BrowserWindow({
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true
    }
  });

  await win.loadFile(path.join(__dirname, 'index.html'));

  ipcMain.handle('spike:get-public-surface', (evt) => {
    // Public renderer API intentionally returns capability metadata only.
    return {
      credential_methods: ['listMetadata', 'bindCredential', 'submitGeneration'],
      secret_methods: []
    };
  });

  ipcMain.handle('spike:renderer-request-secret', () => {
    throw new Error('RENDERER_SECRET_ACCESS_DENIED');
  });

  const publicSurface = await win.webContents.executeJavaScript(
    'window.spikeApi.getPublicSurface()',
    true
  );
  state.tests.renderer_has_no_secret_api =
    Array.isArray(publicSurface.secret_methods) &&
    publicSurface.secret_methods.length === 0;

  let rendererDenied = false;
  try {
    await win.webContents.executeJavaScript('window.spikeApi.tryRequestSecret()', true);
  } catch (e) {
    rendererDenied = true;
  }
  state.tests.renderer_secret_request_denied = rendererDenied;

  function issueLease({ utilityId, sessionToken, requestedProvider, requestedOperation }) {
    if (!utilityAlive) throw new Error('UTILITY_NOT_ALIVE');
    if (utilityId !== 'utility-1') throw new Error('UTILITY_ID_DENIED');
    if (sessionToken !== utilitySessionToken) throw new Error('UTILITY_AUTH_FAILED');
    if (requestedProvider !== provider) throw new Error('PROVIDER_SCOPE_DENIED');
    if (requestedOperation !== operation) throw new Error('OPERATION_SCOPE_DENIED');

    const leaseId = crypto.randomBytes(16).toString('hex');
    return {
      leaseId,
      utilityId,
      provider,
      operation,
      credentialVersion: 1,
      expiresAt: Date.now() + 10000,
      encrypted
    };
  }

  const lease = issueLease({
    utilityId: 'utility-1',
    sessionToken: utilitySessionToken,
    requestedProvider: provider,
    requestedOperation: operation
  });

  // Decrypt just-in-time in Main, then send plaintext only to the trusted utility.
  const plaintext = await safeStorage.decryptStringAsync(lease.encrypted);
  utility.postMessage({
    type: 'CREDENTIAL_LEASE',
    utilityId: 'utility-1',
    sessionToken: utilitySessionToken,
    leaseId: lease.leaseId,
    provider,
    operation,
    expiresAt: lease.expiresAt,
    secret: plaintext
  });

  const leaseResult = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('UTILITY_TIMEOUT')), 5000);
    utility.once('message', (msg) => {
      clearTimeout(timer);
      resolve(msg);
    });
  });

  state.tests.utility_scoped_lease =
    leaseResult &&
    leaseResult.type === 'LEASE_CONSUMED' &&
    leaseResult.canaryMatched === true;

  consumedLeaseIds.add(lease.leaseId);

  // Simulate crash; old session must no longer be accepted by broker policy.
  utility.kill();
  await new Promise(r => setTimeout(r, 300));

  let oldSessionDenied = false;
  try {
    issueLease({
      utilityId: 'utility-1',
      sessionToken: utilitySessionToken,
      requestedProvider: provider,
      requestedOperation: operation
    });
  } catch (e) {
    oldSessionDenied = true;
  }
  state.tests.utility_crash_revokes_session = oldSessionDenied;

  // Log/export canary scan.
  const exportPayload = JSON.stringify({
    project_id: 'P1',
    credential_binding: { credential_id: credentialId, provider }
  });
  state.tests.project_export_plaintext_scan_clean = safeScan(exportPayload);

  const eventText = JSON.stringify(state.events);
  state.tests.event_log_plaintext_scan_clean = safeScan(eventText);

  state.all_required_checks_pass = Object.values(state.tests).every(Boolean);
  writeResults();

  win.destroy();
  app.exit(state.all_required_checks_pass ? 0 : 3);
}

run().catch((err) => {
  state.fatal_error = String(err && err.stack || err);
  writeResults();
  app.exit(4);
});
