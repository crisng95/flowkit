# ADR-0008 — Credential Broker and Scoped Secret Lease

**Status:** PROPOSED / PARTIAL-PROOF SUPPORTED  
**Date:** 2026-09-20

## Decision

Use Electron Main as privileged credential broker.

Store provider secrets in a machine/user-scoped encrypted vault protected with Electron `safeStorage`; project data stores credential IDs only.

Trusted Production Utility obtains short-lived, single-use leases scoped to:
- utility instance;
- provider;
- operation;
- credential version;
- correlation ID.

Renderer never receives plaintext secrets.

## Alternatives considered

### Main performs provider networking
Rejected for V1 because it expands Main's provider/network failure and maintenance surface.

### Dedicated provider-secret process
Deferred until third-party/untrusted provider plugins justify stronger isolation.

## Evidence

A local security simulation passed checks for:
- renderer denial;
- utility authentication;
- provider/operation scope;
- one-use and expiry;
- rotation invalidation;
- utility-crash revocation;
- vault/export/log secret scans.

This simulation does not prove real Electron/Windows safeStorage behavior.

## Revisit

After Windows Electron credential-broker spike or if untrusted plugins become core.
