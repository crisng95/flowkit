# CREDENTIAL_BROKER_PROOF_V0.6.md
# Electron Credential Broker Proof — Architecture + Fault/Security Simulation

**Date:** 2026-09-20  
**Status:** PARTIAL PROOF  
**Not claimed:** target-Windows Electron `safeStorage` live proof.

---

# 1. Goal

Prove the architecture prevents the renderer from receiving plaintext provider secrets while allowing an authorized production utility process to perform a scoped provider operation.

Security path:

```text
Renderer
  └── credential_id only
        ↓
Main Security Broker
  ├── validates caller / provider / operation
  ├── decrypts machine-local secret
  └── grants short-lived one-use secret lease
        ↓
Trusted Production Utility Process
  └── provider adapter uses credential
```

The renderer never receives the secret.

---

# 2. Official Electron Constraints Verified

Current official Electron documentation states:

- `safeStorage` is a **Main-process** API.
- Electron recommends the async `encryptStringAsync` / `decryptStringAsync` APIs.
- on Windows, `safeStorage` uses DPAPI-backed protection;
- on macOS, Keychain;
- Linux security varies with the available secret-service backend, and `basic_text` can indicate an insecure fallback.
- Electron recommends `contextIsolation`, sandboxing, no Node integration for untrusted content, and validating the sender of IPC.
- `utilityProcess` is spawned from Main and communicates through MessagePort-style APIs.

Therefore the V1 security design is compatible with Electron's documented process model:

```text
Renderer = low privilege
Main = security / OS capability broker
Utility = trusted production backend
```

---

# 3. Architecture Choice Revisited

Three options were compared.

## Option A — Main sends short-lived scoped plaintext secret to trusted Utility

Advantages:
- provider logic remains in production backend;
- Main remains mostly security/window broker;
- no localhost service;
- simple adapter integration.

Risk:
- plaintext secret exists in Utility memory for the request.

## Option B — Main performs all credentialed provider networking

Advantages:
- Utility never sees secret.

Problems:
- provider transports and network logic migrate into Main;
- Main failure/security surface grows;
- violates the earlier process-separation goal.

## Option C — Dedicated provider-secret process

Advantages:
- stronger compartmentalization.

Problems:
- more process lifecycle/IPC complexity;
- premature before plugin/untrusted adapter requirement exists.

### Candidate decision

For V1:

```text
Option A
```

with hard conditions:

- Utility process is trusted application code only;
- third-party plugins are NOT loaded in the same Utility trust domain;
- lease is provider + operation + utility scoped;
- lease is short-lived and one-use;
- secret never returns to Renderer;
- secret never enters durable project state;
- logs centrally redact secret-bearing fields.

If untrusted third-party provider plugins become a requirement, revisit Option C.

---

# 4. Local Security Simulation

The design spike implemented:

```text
machine-local encrypted vault simulation
main-style broker
trusted utility registration
provider scope
operation scope
short TTL
single-use lease
rotation invalidation
utility-crash revocation
log/export leak scans
```

The harness intentionally used AES-GCM only as a **stand-in for encrypted-at-rest behavior**. It is not represented as Electron `safeStorage`.

Results:

```json
{
  "tests": {
    "renderer_denied": true,
    "authorized_utility_gets_secret": true,
    "lease_replay_denied": true,
    "provider_mismatch_denied": true,
    "operation_scope_denied": true,
    "utility_auth_denied": true,
    "expired_lease_denied": true,
    "rotation_invalidates_old_lease": true,
    "crash_revokes_unconsumed_lease": true,
    "vault_no_plaintext_secret": true,
    "export_no_plaintext_secret": true,
    "logs_no_plaintext_secret": true,
    "workdir_secret_scan_clean": true,
    "broker_serializable_metadata_has_no_secret": true
  },
  "all_pass": true,
  "leaks": [],
  "limitations": [
    "This is a local protocol/security simulation, not Electron runtime execution.",
    "AES-GCM in this harness stands in for safeStorage; it does not prove OS-backed DPAPI/Keychain behavior.",
    "The sandbox is Linux x64 and Electron executable is not installed.",
    "JS memory zeroization cannot be guaranteed by this simulation or by ordinary garbage-collected runtime semantics."
  ]
}
```

All executed assertions passed: **True**.

---

# 5. Properties Demonstrated by Simulation

## Renderer denial

```text
Renderer → request secret
= DENIED
```

## Utility identity

Wrong utility/session token:
```text
DENIED
```

## Provider scope

Credential registered for FLOW cannot be leased as VEO:
```text
DENIED
```

## Operation scope

Utility approved for generation cannot request arbitrary `DELETE_PROJECT`:
```text
DENIED
```

## Single-use

A consumed lease cannot be replayed.

## Expiry

Expired lease cannot be consumed.

## Rotation

Secret rotation invalidates leases issued against the prior credential version.

## Crash

Unconsumed leases assigned to a crashed utility are revoked.

## Durable storage scan

The simulated vault persisted only ciphertext/metadata.

## Project export scan

Project export contained only:

```text
credential_id
provider
```

and no plaintext secret.

## Logging scan

Injected Authorization/API-key log messages were redacted before sink.

---

# 6. Critical Design Patch

A "credential ID" alone is not enough. The broker must authorize a **use**, not just a lookup.

Canonical lease request:

```yaml
credential_lease_request:
  utility_instance_id:
  utility_session_token:
  credential_id:
  provider:
  operation:
  correlation_id:
```

Broker verifies:

```text
caller == trusted utility
utility session valid
credential provider matches requested provider
operation allowed for utility
credential active
safeStorage available
```

Then issues a lease:

```yaml
credential_lease:
  lease_id:
  credential_id:
  credential_version:
  provider:
  operation:
  utility_instance_id:
  correlation_id:
  expires_at:
  single_use: true
```

The plaintext secret itself is not persisted as part of the lease.

---

# 7. Renderer API

Renderer may call only:

```text
credentials.listMetadata()
credentials.addViaPrivilegedDialog(...)
credentials.remove(...)
credentials.selectForProvider(...)
```

Renderer must NOT expose:

```text
credentials.decrypt()
credentials.getSecret()
credentials.exportRaw()
```

The provider-generation command contains:

```text
credential_id
```

not a key/token string.

---

# 8. SafeStorage Availability Policy

Before writing/using credentials:

```text
safeStorage availability check
↓
platform backend check
```

On Linux, insecure `basic_text` must not be silently presented as secure storage.

Candidate policy:

```text
SECURE_BACKEND
→ allow persistent vault

TEMPORARILY_UNAVAILABLE
→ block secret operation and surface recovery message

INSECURE_BASIC_TEXT
→ default block persistent secret storage
   unless explicit future policy says otherwise
```

For Windows target, live spike must confirm DPAPI-backed behavior through Electron.

---

# 9. Secret Lifecycle

```text
user enters secret in privileged flow
↓
Main encrypts with safeStorage
↓
persist encrypted blob + metadata
↓
renderer keeps credential_id only
↓
Utility requests scoped lease
↓
Main decrypts just-in-time
↓
secret used for provider request
↓
lease consumed/revoked
```

No project backup contains the encrypted vault by default.

Credential vault is user/machine application data, not project data.

---

# 10. Logging Contract

Fields always classified SECRET:

```text
Authorization
Cookie
Set-Cookie
API key
OAuth token
browser session token
raw credential payload
signed access URL when bearer-like
```

Redaction occurs before any log sink, not after file creation.

Exception objects from provider SDKs must be sanitized because they may echo request headers/options.

---

# 11. Utility Crash / Restart

Utility crash:

```text
Main observes exit
↓
revoke outstanding leases for utility instance
↓
start new utility instance
↓
new session token
↓
production backend runs durable recovery
```

Old utility session/lease IDs cannot be reused.

---

# 12. Credential Rotation

Credential record has:

```text
credential_id
credential_version
provider
status
```

Rotation:
```text
version N → N+1
```

Old unconsumed leases become invalid.

Queued generation jobs do not embed secret bytes; they resolve `credential_id` at execution time under project policy.

If reproducibility requires exact credential identity, lineage stores credential ID/version metadata but never secret content.

---

# 13. Remaining Live Proof

The current sandbox does not have an Electron executable and is not the target Windows runtime.

Therefore the following are still required:

1. Windows Electron app spike;
2. verify `safeStorage.isEncryptionAvailable()`;
3. verify selected backend/DPAPI behavior;
4. async encrypt/decrypt round trip;
5. renderer attempt to invoke secret method is impossible/denied;
6. Main↔`utilityProcess` scoped lease round trip;
7. crash Utility and prove lease/session invalidation;
8. rotate credential and prove stale lease rejection;
9. scan real app logs/project exports for canary secret;
10. package/restart/update and verify vault still decrypts for same Windows user.

Until then:

```text
CREDENTIAL BROKER
= ARCHITECTURE + LOCAL SECURITY SIMULATION PASS
= PARTIAL_PROOF
≠ WINDOWS LIVE-PROVEN
```

---

# 14. Decision

Keep:

```text
Renderer
→ narrow typed IPC
→ Main Security Broker / safeStorage
→ trusted Utility Process
```

Use **short-lived, single-use, provider/operation-scoped credential leases**.

Do not move provider networking into Main in V1 unless the live spike shows secret handoff creates an unacceptable security/operational problem.
