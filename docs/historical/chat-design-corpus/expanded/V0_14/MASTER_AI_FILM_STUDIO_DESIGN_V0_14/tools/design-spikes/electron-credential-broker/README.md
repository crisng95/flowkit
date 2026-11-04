# Electron Credential Broker — Live Proof Harness

**Classification:** DESIGN SPIKE ONLY.

## Run on target Windows

```powershell
cd tools\design-spikes\electron-credential-broker
npm install
npm start
type electron_credential_broker_results.json
```

Use a disposable test directory.

## Pass conditions

- `safeStorage_available = true`
- `safeStorage_round_trip = true`
- renderer has no secret-returning public method
- explicit renderer secret request is denied
- trusted Utility receives the canary through a scoped lease
- Utility crash invalidates the old Utility session
- encrypted vault file contains no plaintext canary
- project export and event log contain no plaintext canary

## Important limits

This harness does **not**:
- test a real provider;
- prove JavaScript memory zeroization;
- prove browser-session credential handling;
- replace platform signing/update tests.

The architecture remains PARTIAL_PROOF until this is executed on the target packaged Windows/Electron environment.
