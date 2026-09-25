# ADR-0016 — Credential Authority

## STATUS

**ACCEPTED FOR PRE-MASTER CONSOLIDATION**

This is a design/authority decision only. It does not claim packaged Electron, safeStorage, Utility IPC, or provider credential implementation evidence.

## CONTEXT

Historical V0.16 sources already converge on a privileged Electron security boundary:

- ADR-0004 places long-lived secrets behind a main-process credential broker.
- ADR-0008 adds scoped, short-lived credential leases to trusted Production Utility.
- SECURITY_MODEL forbids plaintext secrets in Renderer, project state, prompts and logs.
- CREDENTIAL_BROKER_ARCHITECTURE defines safeStorage-backed vault semantics and Utility-instance-scoped leases.
- V0.16 PROJECT_STATE simultaneously lists the credential broker as an accepted direction while also retaining a stale pending item for "secret storage".

Current FlowKit authentication/session mechanisms are useful compatibility execution paths, but they are not the canonical target security architecture.

## PROBLEM

Without one explicit credential owner, the future Master could accidentally preserve multiple authorities:

- Electron Main/security broker;
- Production Utility/provider adapter;
- Renderer-side state;
- legacy FlowKit session/cookie behavior.

That would violate the one-authority rule and blur long-lived secret ownership.

## CANONICAL DECISION

The **HOST SECURITY BROKER abstraction** is the canonical credential authority.

For the target Electron topology:

```text
Electron Main + safeStorage
= long-lived secret owner

Production Utility
= short-lived scoped credential lease consumer

Renderer
= no long-lived secret read/ownership

Legacy FlowKit credential/session mechanism
= compatibility adapter only
```

The Host Security Broker owns long-lived secret lifecycle, storage, encryption/decryption authorization, rotation, revocation and lease issuance.

The Production Utility receives only short-lived, operation/provider/credential-version scoped use authorization/lease material required for a trusted provider operation.

Renderer must not expose, retain, return, inspect or become authoritative for decrypted long-lived secrets.

Provider-specific browser/session credentials may remain inside their authorized isolated provider/session boundary; they do not become project/domain truth.

## OWNERSHIP

- **Host Security Broker:** canonical long-lived credential authority.
- **Electron Main + safeStorage implementation target:** privileged secret storage/decryption boundary.
- **Production Utility:** temporary lease consumer; never long-lived owner.
- **Renderer:** credential metadata/binding UI only; no secret authority.
- **Provider adapter:** consumes authorized lease/session material for one allowed operation.
- **Current FlowKit mechanism:** compatibility/legacy adapter, never canonical owner.

## AUTHORITY PRECEDENCE

1. Host Security Broker security invariants.
2. credential status/version/revocation policy.
3. scoped lease authorization policy.
4. provider/session-specific access boundary.
5. Utility operation request.
6. Renderer request/metadata intent.
7. legacy FlowKit compatibility behavior.

A lower layer cannot expand secret scope granted by a higher layer.

## INVARIANTS

1. Renderer never receives a long-lived decrypted secret.
2. Project/domain persistence stores credential identity/binding, not plaintext secret.
3. Long-lived secret encryption/decryption is authorized by Host Security Broker.
4. Utility lease is short-lived, scoped, non-authoritative and revocable.
5. Lease scope includes at least credential version, provider and operation; Utility identity/session scope is required in the Electron topology.
6. Rotation invalidates stale lease authorization.
7. Logs/export/backup never serialize long-lived secret material.
8. Browser/session material is not silently converted into a generic API-key lease.
9. Legacy FlowKit credentials cannot override Host Security Broker policy.

## DATA IDENTITY

Canonical persistent identities may include:

```text
credential_id
credential_version
provider_binding
credential_status
```

Ephemeral authorization identity may include:

```text
lease_id
utility_instance_id
provider
operation
correlation_id
issued_at
expires_at
single_use
```

Secret bytes are not canonical project data.

## VERSIONING

- credential rotation creates a new credential version.
- lease authorization pins the credential version.
- provider/job lineage records credential identity/version metadata only where needed for audit.
- Host Security Broker contract is versioned independently from provider adapters.

## INVALIDATION

Credential revoke/rotate/security-policy change invalidates:

- unconsumed stale leases;
- cached authorization derived from obsolete credential version;
- provider connection state that explicitly depends on the obsolete credential where required.

It does not invalidate narrative/story/shot truth.

## LEGACY FLOWKIT IMPACT

Current FlowKit browser/session/cookie or extension-authenticated execution remains a compatibility adapter path.

It may:
- execute authorized provider calls;
- hold session material inside its provider-specific compatibility boundary.

It may not:
- define canonical credential architecture;
- make Renderer/session cookies project truth;
- bypass Host Security Broker policy in the target architecture.

## MIGRATION IMPLICATION

Future implementation must introduce a host-level security port/interface so provider execution requests credential use by ID/scope rather than owning raw long-lived secrets.

FlowKit compatibility adapters must sit behind that port.

## REJECTED ALTERNATIVES

- Renderer owns or can retrieve decrypted secrets — rejected.
- Production Utility is long-lived credential vault owner — rejected.
- project SQLite/JSON stores plaintext provider secrets — rejected.
- legacy FlowKit session behavior becomes target credential authority — rejected.
- Main performs all provider networking solely to avoid lease semantics — not required as canonical V1 ownership model.

## CONSEQUENCES

Positive:
- one credential authority;
- clear trust boundary;
- provider adapters remain replaceable;
- FlowKit compatibility is retained without architecture capture.

Cost:
- requires host broker/lease contract during implementation;
- provider browser-session adapters need dedicated session isolation.

## TRACEABILITY SOURCES

- historical V0.16 ADR-0004-SECRET-STORAGE-BOUNDARY.md
- historical V0.16 ADR-0008-CREDENTIAL-BROKER.md
- historical V0.16 docs/design/SECURITY_MODEL.md
- historical V0.16 docs/design/CREDENTIAL_BROKER_ARCHITECTURE.md
- historical V0.16 PROJECT_STATE.md
- PRE_MASTER_CONTRADICTION_REGISTER_V1.md PM-005
