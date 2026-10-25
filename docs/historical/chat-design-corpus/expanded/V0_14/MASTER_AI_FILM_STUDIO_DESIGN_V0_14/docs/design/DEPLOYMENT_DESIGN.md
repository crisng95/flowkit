# DEPLOYMENT_DESIGN.md
# Desktop Process / Deployment Topology — Deep Dive V0.3

**Status:** REVIEWED CANDIDATE  
**Assumption:** V1 is a local-first desktop application. Cross-platform remains desirable but not yet a hard requirement.

---

# 1. Options

## OPTION A — Renderer + Electron Main only

Main process owns:
- windows;
- SQLite;
- orchestrator;
- provider requests;
- ffmpeg;
- artifact I/O.

### Pros
- simplest packaging;
- no backend IPC beyond renderer↔main.

### Cons
- heavy/long-running production logic can affect Electron main responsiveness/stability;
- privileged UI/window logic and production backend share failure domain;
- harder to isolate third-party provider/decoder crashes.

**Reject as target.**

---

## OPTION B — Renderer + Preload + Main Security Broker + Electron Utility Process Backend

```text
Renderer (sandboxed)
↓ narrow preload bridge
Main Process / Security Broker
↓ MessagePort / utilityProcess IPC
Utility Process / Production Backend
↓
SQLite + Orchestrator + Provider adapters + Artifact services
```

Electron's `utilityProcess` launches a child process with Node.js and MessagePort support and is intended for child-process-like utility workloads.

### Pros
- renderer stays unprivileged;
- main process remains primarily security/window broker;
- production backend crash can be isolated/restarted;
- no localhost HTTP server required;
- easier separation of secrets/privileges;
- still packaged as one desktop app.

### Cons
- IPC/process lifecycle complexity;
- safeStorage is main-process API, so credential access needs broker contract;
- DB/file handles must live in backend and not be shared.

**Preferred candidate.**

---

## OPTION C — Electron UI + independent localhost backend service

### Pros
- backend language/stack independent;
- easier future headless/server mode;
- independently restartable.

### Cons
- local port/auth/CORS/origin/host security;
- service install/lifecycle/firewall issues;
- larger packaging/support burden;
- accidental LAN exposure risk if bound incorrectly.

**Defer.**

---

# 2. Candidate V1 Topology

```text
┌─────────────────────────────────────┐
│ Renderer                            │
│ React/UI                            │
│ sandboxed, no Node                  │
└─────────────────┬───────────────────┘
                  │ contextBridge
                  ▼
┌─────────────────────────────────────┐
│ Electron Main / Security Broker     │
│ window/nav policy                   │
│ IPC sender validation               │
│ safeStorage credential broker       │
│ file/folder picker                  │
│ update lifecycle                    │
└─────────────────┬───────────────────┘
                  │ typed IPC / ports
                  ▼
┌─────────────────────────────────────┐
│ Production Utility Process          │
│ Domain/application services         │
│ SQLite repository                   │
│ orchestrator                        │
│ compiler                            │
│ provider adapters                   │
│ QA/repair                           │
│ artifact store                      │
└─────────────────────────────────────┘
```

---

# 3. Failure Isolation

If renderer crashes:
- backend jobs may continue;
- renderer reconnects/reloads state.

If utility backend crashes:
- main remains alive;
- main restarts backend;
- backend executes recovery sequence from durable DB/provider state.

If main process exits/app closes:
- entire desktop app stops;
- remote submitted jobs remain remote;
- next launch reconciles.

Future background service mode may allow jobs to continue after UI exit, but this is not required by the current V1 candidate.

---

# 4. Secret Flow

```text
Renderer:
  selects credential_id only

Backend:
  requests scoped credential use

Main security broker:
  decrypts via safeStorage
  returns/forwards only to authorized provider operation
```

Never return decrypted secret to renderer.

Whether the decrypted value is sent to utility process or provider requests are proxied through a privileged provider broker is a security/performance implementation decision to spike. The simpler candidate is scoped secret transfer to the utility process over authenticated internal IPC, with strict memory/logging rules.

---

# 5. Filesystem Flow

Renderer requests:
```text
choose import
choose project
choose export
reveal artifact
```

Main uses native dialogs/policy.

Backend receives validated authorized root/path tokens, not arbitrary privileged file APIs from the renderer.

---

# 6. Update / Migration

Candidate:

```text
update available
↓
check active production state
↓
persist/checkpoint all local state
↓
do not start new jobs
↓
remote in-flight jobs recorded for reconciliation
↓
backup before destructive migration
↓
install update
↓
schema compatibility/migration
↓
backend recovery
↓
resume scheduler
```

No app update should silently discard active job identity.

---

# 7. Packaging

Candidate components:

```text
Electron renderer/main/preload
production utility-process bundle
SQLite native/runtime dependency
ffmpeg/ffprobe if required
provider adapter packages
migration files
contract schemas
```

Package signing/notarization requirements depend on target OS and distribution plan; not yet frozen.

---

# 8. Revisit Conditions

Choose external local service instead of utilityProcess if:
- backend moves to another language;
- UI-closed background processing becomes MUST;
- remote headless control becomes MUST;
- multi-client local access becomes MUST.

Choose server/PostgreSQL topology if:
- multiple machines/users edit the same project concurrently;
- organization/team collaboration becomes V1 core.

---

# 9. Official References

Electron utilityProcess:
https://www.electronjs.org/docs/latest/api/utility-process

Electron process model:
https://www.electronjs.org/docs/latest/tutorial/process-model

Electron security:
https://www.electronjs.org/docs/latest/tutorial/security


# Credential Handoff Patch

V1 selects scoped plaintext handoff from Main to a **trusted** Utility process rather than routing all provider networking through Main.

Constraint:
- Utility contains only first-party/trusted production code.
- Third-party plugins must use a separate future sandbox/process boundary.

On Utility exit:
```text
invalidate utility session
revoke outstanding leases
spawn replacement
run durable production recovery
```
