# SPIKE_PLAN_CREDENTIAL_BROKER.md
# Design Spike Plan — Main safeStorage ↔ Utility Process Credential Broker

**Status:** REQUIRED BEFORE L6

## Goal

Prove that:
- renderer cannot read plaintext secret;
- credential is encrypted at rest with Electron safeStorage;
- utility-process provider operation can obtain/use a scoped credential;
- secret is not logged/persisted into project DB;
- utility crash/restart does not corrupt vault state.

## Candidate protocol

```text
Renderer:
  submit generation with credential_id

Utility:
  requests credential lease for:
    credential_id
    provider
    operation
    correlation_id

Main:
  validates caller/operation
  decrypts secret
  returns short-lived scoped secret message
```

## Questions to resolve

- send plaintext over Electron MessagePort or proxy provider request through Main?
- memory zeroization practical limits in JS?
- expiry/lease semantics?
- Linux safeStorage degraded-mode UX?
- key rotation while jobs queued?

## Negative tests

- renderer requests decrypt;
- utility asks for unrelated provider credential;
- malformed credential ID;
- log interceptor scans for secret;
- project export scanned for secret.
