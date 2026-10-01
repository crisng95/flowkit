# ADR-0004 — Secret Storage Boundary

**Status:** PROPOSED

## Decision

Use a privileged main-process credential broker:
- encrypted local credential vault;
- Electron async `safeStorage`;
- SQLite stores credential metadata/IDs only;
- renderer never receives plaintext secrets.

## Why

Electron safeStorage is OS-backed (e.g. DPAPI on Windows, Keychain on macOS) and belongs to main process.

## Open implementation choice

Whether provider calls in utility process receive short-lived decrypted secrets over internal IPC or route credentialed network requests through a privileged provider broker requires a spike.

## Revisit

If non-Electron/server mode becomes core.
