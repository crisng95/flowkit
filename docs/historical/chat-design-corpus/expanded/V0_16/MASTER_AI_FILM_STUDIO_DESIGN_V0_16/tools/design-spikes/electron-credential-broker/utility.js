const EXPECTED_CANARY = 'MASTER_STUDIO_CANARY_SECRET_2026';

process.parentPort.on('message', (event) => {
  const msg = event.data;
  if (!msg || msg.type !== 'CREDENTIAL_LEASE') return;

  const now = Date.now();
  const scoped =
    msg.utilityId === 'utility-1' &&
    msg.provider === 'FLOW' &&
    msg.operation === 'GENERATE_VIDEO' &&
    now <= msg.expiresAt;

  const canaryMatched = scoped && msg.secret === EXPECTED_CANARY;

  process.parentPort.postMessage({
    type: 'LEASE_CONSUMED',
    leaseId: msg.leaseId,
    scoped,
    canaryMatched
  });

  // Drop local reference immediately after use; no zeroization guarantee is claimed.
  msg.secret = null;
});
