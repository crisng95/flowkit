# CROSS_DOCUMENT_CONTRADICTION_AUDIT_V0_10.md
# Cross-Document Contradiction Audit

**Date:** 2026-09-20  
**Status:** PATCHED CANDIDATE

## Audit scope

Reviewed current architecture/research/ADR/state documents for contradictions involving maturity, job states, provider identity, cost, quota, cancellation, credentials, continuity, QA, repair and persistence.

## Findings and patches

### C-001 — stale maturity headers
Several V0.1 baseline documents still said L4 after the current state reached L5.5.

**Patch:** `PROJECT_STATE.md` is the single maturity authority; baseline headers are updated and historical review statements remain untouched.

### C-002 — monolithic job state
Older draft text mixed scheduler ownership, provider submission, artifact readiness and creative approval.

**Patch:** four orthogonal axes:

```text
scheduler_state
provider_state
artifact_state
creative_state
```

### C-003 — Google provider conflation
`Flow`, `Veo`, Google Flow product and direct Veo API were sometimes discussed as one contract.

**Patch:** separate:

```text
GOOGLE/FLOW_PRODUCT
GOOGLE/FLOW_PRIVATE_TRANSPORT (experimental if used)
GOOGLE/GEMINI_API/VEO
GOOGLE/VERTEX_AI/VEO
```

### C-004 — Wan provider conflation
`WANAdapter` was too broad.

**Patch:** `WanLocalAdapter` and `AlibabaModelStudioWanAdapter` are separate runtime providers.

### C-005 — generic cost fields under-specified
`estimated_cost`/`actual_cost` did not identify units.

**Patch:** add billing unit kind, quantity, currency/credit unit, surface and evidence version.

### C-006 — placeholder quota examples could look authoritative
Old examples used illustrative provider caps.

**Patch:** runtime values come only from `ProviderProfile` + account/live evidence.

### C-007 — generic cancellation semantics
A generic `cancel()` could imply running remote work always stops.

**Patch:** track `cancel_queued`, `cancel_running`, `delete_terminal`; `CANCEL_REQUESTED` is only local intent until provider confirmation.

### C-008 — API-key vs browser-session credentials
Generic string leases do not model a full cookie/session jar safely.

**Patch:** browser sessions stay in provider-specific isolated session boundaries.

### C-009 — parent image vs semantic state authority
No contradiction after clarification:

```text
StateSnapshot = semantic authority
parent accepted image = conditioning artifact/evidence
```

Conflict blocks propagation.

### C-010 — weighted QA vs blocking severity
FlowKit-style weighted metrics remain useful sensors; final acceptance is severity/policy-driven. Blocking failures cannot be averaged away.

### C-011 — repair preserve semantics
`preserve` means a contractual invariant to re-check, not a guarantee the generator will obey it.

### C-012 — SQLite/PostgreSQL role
No contradiction:

```text
SQLite WAL = V1 local operational-store candidate
PostgreSQL = future shared-server/multi-writer reconsideration
```

### C-013 — event-log authority
Current-state tables remain authoritative; durable events are audit/observability/recovery evidence, not event sourcing.

### C-014 — 8-layer rigidity
Eight layers are canonical semantic structure, not mandatory repeated prompt prose.

### C-015 — current provider facts age
No quota/price/task-retention number is a timeless ADR constant.

**Patch:** versioned evidence profiles with `verified_at`.

## Result

After V0.10 patches:

```text
unresolved conceptual BLOCKER = 0
unresolved CRITICAL contradiction = 0
```

External/runtime evidence blockers remain open and prevent L6.
