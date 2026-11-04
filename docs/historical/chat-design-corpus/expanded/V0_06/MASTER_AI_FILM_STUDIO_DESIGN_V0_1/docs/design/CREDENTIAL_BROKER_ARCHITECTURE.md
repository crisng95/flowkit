# CREDENTIAL_BROKER_ARCHITECTURE.md
# Credential Broker Architecture V0.6

**Status:** REVIEWED CANDIDATE  
**Evidence:** `docs/research/spikes/CREDENTIAL_BROKER_PROOF_V0_6.md`

---

# 1. Trust Domains

```text
LOW-PRIVILEGE
Renderer
    │
    │ typed capability IPC
    ▼
PRIVILEGED
Electron Main / Security Broker
    │
    ├── safeStorage
    ├── credential metadata policy
    ├── utility identity/session registry
    └── lease authorization
    │
    │ one-use scoped credential lease
    ▼
TRUSTED APPLICATION BACKEND
Production Utility Process
    └── provider adapter
```

Third-party/untrusted plugins are **not** allowed in the same Utility trust domain in V1.

---

# 2. Credential Record

Project state stores only:

```text
credential_id
provider
label
status
credential_version
```

Encrypted vault stores:

```text
credential_id
encrypted_payload
provider
credential_version
encryption_backend_metadata
created_at
rotated_at?
```

Never store:
- plaintext key;
- bearer token;
- raw cookie/session bundle;
- decrypted secret in project JSON/SQLite;
- secret in task/job payload.

---

# 3. Utility Identity

Main creates each Utility instance with:

```text
utility_instance_id
utility_session_token
allowed_providers[]
allowed_operations[]
spawned_at
```

Session token is random and process-instance-scoped.

On Utility exit:
- session is invalidated;
- outstanding leases revoked;
- replacement process gets a new token.

---

# 4. Credential Lease

Request:

```text
utility_instance_id
utility_session_token
credential_id
provider
operation
correlation_id
```

Authorization:

```text
trusted utility?
valid instance token?
provider allowed?
operation allowed?
credential active?
credential provider matches?
secure storage available?
```

Lease metadata:

```text
lease_id
credential_id
credential_version
provider
operation
utility_instance_id
correlation_id
issued_at
expires_at
single_use=true
```

Secret bytes are not persisted as lease metadata.

---

# 5. Lease Semantics

Hard rules:

```text
single use
short TTL
provider scoped
operation scoped
utility-instance scoped
credential-version scoped
not renewable by renderer
not serializable into project state
```

A new generation attempt obtains a new lease.

---

# 6. Secret Handoff Decision

V1 candidate:

```text
Main decrypts just-in-time
→ sends secret to trusted Utility for one authorized provider operation
```

Why not Main network proxy:
- would move provider HTTP/session logic into Main;
- enlarges Main's operational failure surface;
- weakens separation of UI/security broker and production runtime.

Why not dedicated secret/provider process:
- stronger isolation but more IPC/process complexity;
- not justified until untrusted provider plugins exist.

Revisit if:
- third-party provider code becomes supported;
- provider session material is especially sensitive;
- enterprise security requires adapter sandboxing.

---

# 7. Electron safeStorage Policy

Use asynchronous API when available:

```text
safeStorage.isEncryptionAvailable()
safeStorage.encryptStringAsync(...)
safeStorage.decryptStringAsync(...)
```

Reason:
- Electron currently recommends async API;
- supports key rotation and temporary unavailability handling.

Linux:
- inspect selected backend;
- `basic_text` is not accepted as equivalent to secure OS-backed storage.

Windows:
- target live spike must verify DPAPI-backed behavior under packaged app context.

macOS:
- code signing consistency affects Keychain behavior and update prompts.

---

# 8. Renderer API Surface

Allowed:

```text
credentials.list()
credentials.add()
credentials.rename()
credentials.remove()
credentials.bindToProvider()
credentials.testConnection()
```

The add/update flow sends raw secret only through a dedicated privileged submission channel that immediately transfers it to Main for encryption; renderer state must not cache/rebroadcast it.

Forbidden:

```text
credentials.getSecret()
credentials.decrypt()
credentials.exportRaw()
credentials.dumpVault()
```

---

# 9. Preload/API Design

Do not expose generic:

```text
window.api.invoke(channel, payload)
```

Expose capability-specific API, e.g.:

```text
window.studio.credentials.add(...)
window.studio.credentials.list(...)
window.studio.generation.submit(...)
```

Preload never exposes `ipcRenderer` object itself.

---

# 10. Logging

Central redaction policy runs before sink.

Sensitive keys:

```text
authorization
cookie
set-cookie
api_key
apikey
access_token
refresh_token
session
secret
signed_url
```

Provider SDK errors are normalized before renderer/log output.

Debug mode must not disable redaction.

---

# 11. Export / Backup

Project export includes:

```text
credential binding:
  provider
  credential_id
```

It does not include the machine credential vault.

Import on another machine:
- project loads;
- credential binding is unresolved until user selects/adds matching local credential.

---

# 12. Rotation

```text
credential version N
↓ rotate
credential version N+1
```

Effects:
- new lease requests use N+1;
- old unconsumed leases are invalid;
- already submitted provider job lineage records credential ID/version metadata only;
- no secret content is retained for reproducibility.

---

# 13. Failure States

```text
CREDENTIAL_NOT_FOUND
CREDENTIAL_REVOKED
CREDENTIAL_PROVIDER_MISMATCH
CREDENTIAL_BACKEND_UNAVAILABLE
CREDENTIAL_INSECURE_BACKEND
UTILITY_AUTH_FAILED
PROVIDER_SCOPE_DENIED
OPERATION_SCOPE_DENIED
LEASE_EXPIRED
LEASE_REPLAY_DENIED
LEASE_STALE_AFTER_ROTATION
```

Credential failure is not generic provider retry.

---

# 14. Browser/Session Credentials

API-key lease semantics do not automatically apply to full browser sessions/cookie jars.

For `BROWSER_SESSION`:

```text
session remains inside provider-specific trusted session boundary
```

Prefer provider-specific Electron/Chromium `session` partition or isolated adapter-managed session rather than serializing cookie material into a generic lease.

This requires provider-specific design before a browser-session adapter is marked hardened.

---

# 15. Freeze Gates

Before L6/L7:
- Windows packaged Electron safeStorage round trip;
- renderer secret API absence/denial;
- real Main↔Utility message round trip;
- utility crash revokes old session/lease;
- rotation invalidates stale leases;
- logs/export canary scan clean;
- Linux degraded backend policy implemented/tested if Linux ships;
- browser-session credentials separately reviewed for providers that use them.
