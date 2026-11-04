# SECURITY_MODEL.md
# Security Architecture — Deep Dive V0.3

**Status:** REVIEWED CANDIDATE  
**Scope:** local-first desktop studio with privileged filesystem, provider credentials, large media artifacts, and optional provider/plugins.  
**Feature coding:** NOT STARTED.

---

# 1. Security Principle

The renderer/UI is not trusted with operating-system privileges, raw provider secrets, arbitrary filesystem access, or unrestricted process execution.

Security boundaries:

```text
UNTRUSTED / LOW PRIVILEGE
Renderer UI
    │
    │ narrow validated IPC
    ▼
PRIVILEGED BROKER
Electron Main / Security Broker
    │
    ├── secret broker
    ├── filesystem permission broker
    ├── window/navigation policy
    └── process lifecycle
    │
    │ validated MessagePort / IPC
    ▼
PRODUCTION BACKEND
Utility Process / Local Backend
    ├── domain/application services
    ├── SQLite
    ├── orchestrator
    ├── provider adapters
    └── artifact manager
```

No renderer directly receives:
- API keys;
- browser/session secrets;
- raw OS keychain material;
- arbitrary shell capability;
- unrestricted filesystem APIs.

---

# 2. Electron Security Baseline

Candidate baseline follows Electron's official security guidance:

```text
nodeIntegration = false
contextIsolation = true
sandbox = true
webSecurity = true
allowRunningInsecureContent = false
no experimental Blink features
restrict navigation/new windows
validate IPC sender
restrict external URL opening
prefer custom app protocol over file://
current supported Electron release
```

Content Security Policy candidate:

```text
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';   # revisit if UI stack permits stricter
img-src 'self' data: blob:;
media-src 'self' blob:;
connect-src 'self' <explicit-provider-proxy-or-local-endpoints>;
object-src 'none';
base-uri 'none';
frame-ancestors 'none';
```

Exact CSP depends on renderer architecture and must be tightened during implementation.

---

# 3. Renderer ↔ Privileged IPC

Renderer never gets a generic bridge such as:

```text
window.api.invoke(channel, arbitraryPayload)
```

Instead expose capability-scoped methods:

```text
project.open(...)
project.save(...)
shot.update(...)
generation.submit(...)
generation.cancel(...)
artifact.reveal(...)
```

Every IPC handler:

1. validates sender/origin/frame;
2. validates request schema;
3. checks project/session authorization;
4. performs only one bounded capability;
5. returns a versioned response envelope;
6. redacts privileged error detail.

No raw `ipcRenderer`, `fs`, `child_process`, or secret accessor is exposed through `contextBridge`.

---

# 4. Secrets / Provider Credentials

Candidate implementation:

```text
Credential metadata
→ SQLite:
   credential_id
   provider
   label
   created_at
   status

Encrypted secret payload
→ separate local credential vault
→ encrypted/decrypted only by privileged main-process broker
→ Electron safeStorage async API
```

Electron `safeStorage` uses OS-backed cryptography. Current official docs describe macOS Keychain, Windows DPAPI, and Linux secret-service/portal-backed providers where available.

Rules:

- never store plaintext keys in project JSON/SQLite rows;
- never include secret values in logs;
- never expose secrets to renderer;
- never include secrets in generated prompt/ShotIR;
- use credential IDs in domain state;
- decrypt just-in-time;
- minimize lifetime in memory;
- support credential revoke/replace;
- surface `safeStorage.isEncryptionAvailable()` / temporary unavailability as explicit state;
- key rotation/re-encryption supported through the async safeStorage flow.

Linux fallback behavior requires an explicit warning/policy if secure storage is unavailable.

---

# 5. Provider Session / Browser Credentials

Some provider transports may use authenticated browser/session state rather than API keys.

Security rule:

```text
session material
≠
project asset
```

Session/cookie material must be held only inside its authorized provider adapter/session boundary.

Do not:
- export it with project backups;
- print it to logs;
- expose it to renderer;
- duplicate it across unrelated plugins.

Provider adapters must declare credential type:

```text
API_KEY
OAUTH_TOKEN
LOCAL_SESSION
BROWSER_SESSION
NONE
```

and corresponding storage/access policy.

---

# 6. Filesystem Boundary

The backend only operates inside:
- project workspace roots explicitly selected by the user;
- application data/cache roots;
- configured import/export destinations.

Path safety:

```text
normalize
→ resolve real path where appropriate
→ verify within authorized root
→ reject traversal / symlink escape according to operation
```

Do not trust:
- archive entry paths;
- imported project-relative paths;
- filenames returned by remote providers;
- user-supplied export templates.

Zip/archive extraction must block:
```text
../
absolute paths
drive-letter escape
symlink/hardlink escape
```

---

# 7. Imported Source Trust

Screenplays, prompt packs, JSON project files, metadata and archives are DATA.

They do not gain execution rights.

Importers must not:
- execute embedded shell commands;
- dynamically import arbitrary JavaScript;
- evaluate expressions from metadata;
- invoke external programs based solely on imported fields.

Provider/model configuration imports require validation against allowlisted schema and capability types.

---

# 8. Plugin Boundary

Plugin marketplace is NOT part of frozen V1 core.

If plugins are added later, require manifest:

```yaml
plugin_id:
version:
permissions:
  filesystem:
    read: []
    write: []
  network:
    domains: []
  providers: []
  secrets: []
  subprocess: false
```

Default deny.

A plugin does not receive:
- entire credential vault;
- arbitrary filesystem;
- raw DB handle;
- unrestricted shell.

Plugins call stable host APIs.

---

# 9. Network Boundary

Provider communication:
- HTTPS/WSS only where remote;
- TLS verification enabled;
- no global certificate bypass;
- per-provider domain allowlist where feasible;
- explicit timeout;
- bounded redirects;
- no arbitrary user-controlled URL fetch in privileged backend without SSRF controls.

If a local HTTP service is ever introduced:
- bind to loopback only by default;
- use random authenticated session token or IPC alternative;
- reject non-loopback Host/origin;
- do not expose privileged endpoints unauthenticated.

Candidate topology V1 avoids local HTTP when Electron MessagePort/IPC is sufficient.

---

# 10. SSRF

Potential SSRF sources:
- import remote image/reference URL;
- provider webhook/callback;
- URL-based asset fetch;
- plugin network call.

Controls:
- URL parser;
- protocol allowlist;
- block localhost/private/link-local/metadata endpoints unless explicitly required;
- DNS resolution/rebinding protections for privileged fetchers;
- size/time limits;
- content-type verification.

---

# 11. Logging / Redaction

Structured logs must treat these as SECRET:

```text
Authorization
Cookie
Set-Cookie
API key
OAuth token
browser session token
signed URLs when they grant access
raw credential vault payload
```

Treat screenplay/prompt/user assets as PRIVATE CONTENT, not normal telemetry.

Default production logs should prefer:
- IDs;
- hashes;
- status codes;
- provider/model names;
- durations;
- byte counts;
- normalized error codes.

Full prompt/content logging is opt-in diagnostic data with clear retention controls.

---

# 12. Database Security

Local DB protection is OS/user-account level by default.

Do not claim SQLite itself encrypts the database.

If at-rest project encryption becomes a requirement, evaluate:
- OS disk encryption;
- encrypted project container;
- SQLCipher or equivalent;
- encrypted artifact store.

This is currently an OPEN PRODUCT REQUIREMENT, not silently assumed.

---

# 13. Artifact Safety

Artifacts are untrusted media until processed.

Image/video metadata parsing:
- use maintained libraries/tools;
- avoid executing embedded content;
- sandbox external decoders where practical;
- set resource limits for ffmpeg/image processing;
- validate generated file size and type.

An HTML/SVG artifact must not be rendered with privileged Electron context.

---

# 14. Command / Process Execution

Core product should not expose generic shell execution to project content.

If ffmpeg/ffprobe or other binaries are needed:
- fixed executable path owned by app;
- argv array, not shell concatenation;
- no `shell=true`;
- validate input/output paths;
- timeout/process kill;
- capture bounded output.

---

# 15. Supply Chain

Before release:
- lock dependencies;
- dependency vulnerability scanning;
- verify downloaded model/tools where bundled;
- signed release/update path where platform supports it;
- maintain third-party notices/licenses;
- no automatic arbitrary binary download-and-execute.

Reference repo license review remains required before code reuse.

---

# 16. Threat → Control Matrix

| Threat | Control |
|---|---|
| XSS gets OS access | sandbox + context isolation + no Node integration + narrow bridge |
| malicious iframe sends privileged IPC | validate sender/frame/origin + schema + authorization |
| renderer steals API key | secrets remain main/security broker only |
| path traversal overwrites files | authorized-root real-path validation |
| provider token leaks in logs | centralized structured redaction |
| imported project executes code | data-only parsers; no eval/dynamic execution |
| SSRF to local metadata/admin service | URL/network allowlist + private-range blocking |
| duplicate paid job after timeout | durable idempotency + UNKNOWN_REMOTE_STATE reconciliation |
| plugin steals files/secrets | default-deny permission manifest + host API |
| ffmpeg argument injection | argv arrays + no shell |
| malicious update | signed/trusted update channel + staged migration |
| stale background result overwrites work | input fingerprint/version gate |

---

# 17. Security Freeze Gates

Before L7:
- threat model reviewed against final topology;
- IPC contract allowlist complete;
- secret storage design spike on target OS;
- logging redaction tests defined;
- filesystem traversal tests defined;
- plugin scope explicitly excluded or permission architecture frozen;
- update trust model defined;
- at-rest encryption requirement explicitly accepted/rejected/deferred.

---

# 18. Official References

Electron security:
https://www.electronjs.org/docs/latest/tutorial/security

Electron context isolation:
https://www.electronjs.org/docs/latest/tutorial/context-isolation

Electron safeStorage:
https://www.electronjs.org/docs/latest/api/safe-storage


# Credential Broker V0.6 Patch

Credential access is a **use authorization**, not a secret lookup.

```text
Renderer → credential_id
Main Broker → validates Utility/provider/operation
Main safeStorage → decrypt just-in-time
Main → one-use scoped lease → trusted Utility
Utility → provider request
```

Rules:
- no generic secret IPC;
- one-use/TTL/provider/operation/utility/version scope;
- utility crash revokes outstanding leases;
- rotation invalidates previous-version leases;
- project export excludes credential vault;
- log redaction cannot be disabled by debug mode;
- third-party plugins are excluded from the trusted Utility process in V1.

Browser-session credentials require a separate provider-specific trust boundary and must not be treated as generic API-key strings.
