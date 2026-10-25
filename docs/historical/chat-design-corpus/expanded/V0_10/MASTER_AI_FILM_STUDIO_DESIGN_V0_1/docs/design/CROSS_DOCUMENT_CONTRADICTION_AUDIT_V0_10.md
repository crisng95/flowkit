# CROSS_DOCUMENT_CONTRADICTION_AUDIT_V0_10.md
# Cross-Document Contradiction Audit

**Date:** 2026-09-20  
**Scope:** all current design/research/ADR/state markdown through V0.9  
**Status:** PATCHED CANDIDATE

---

# 1. Audit Method

Checked for contradictions across:

```text
maturity
job states
source-of-truth rules
provider identity
provider quota/cost
secret boundaries
continuity authority
QA acceptance
repair semantics
deployment topology
persistence
```

The audit distinguishes:
- true contradiction;
- historical/stale wording;
- intentional different state axes;
- provider-specific variation.

---

# 2. Findings

## C-001 — Stale maturity headers

Some baseline documents still said:

```text
L4 — Researched Design
```

while current authority files say:

```text
L5.5 — Reviewed + Partial Hardening Evidence
```

Affected:
- README
- PROJECT_VISION
- REQUIREMENTS
- DESIGN_DRAFT

### Decision

`PROJECT_STATE.md` is the single current maturity authority.

Baseline documents are updated to identify their historical origin while displaying current maturity linkage.

---

## C-002 — Old job lifecycle in DESIGN_DRAFT

Older draft used:

```text
QUEUED
→ RUNNING
→ PROVIDER_SUBMITTED
→ SUCCEEDED
→ ARTIFACT_READY
```

Newer failure/recovery design uses:

```text
PREPARED
QUEUED
CLAIMED
SUBMITTING
SUBMITTED
POLLING
UNKNOWN_REMOTE_STATE
RECONCILING
AMBIGUOUS_HOLD
...
```

### Root problem

One enum was being asked to represent:
- scheduler ownership;
- provider submission/reconciliation;
- artifact readiness;
- creative acceptance.

### Decision

Split state axes.

---

# 3. Canonical State Axes

## Scheduler State

```text
QUEUED
CLAIMED
RUNNING
WAITING_DEPENDENCY
WAITING_CAPACITY
TERMINAL
```

## Provider Submission State

```text
NOT_SUBMITTED
SUBMITTING
SUBMITTED
POLLING
UNKNOWN_REMOTE_STATE
RECONCILING
AMBIGUOUS_HOLD
REMOTE_SUCCEEDED
REMOTE_FAILED
CANCEL_REQUESTED
REMOTE_CANCELED
```

## Artifact State

```text
NONE
STAGING
READY
STALE_RESULT
QUARANTINED
MISSING
REJECTED
APPROVED
```

## Creative Acceptance State

```text
PENDING_QA
QA_RUNNING
QA_FAILED
REPAIR_PENDING
NEEDS_HUMAN_REVIEW
APPROVED
LOCKED
REJECTED
```

A single UI summary status may be derived, but canonical persistence keeps the axes distinct.

---

# 4. C-003 — Provider identity conflation

Prior prose sometimes used:
- Flow;
- Veo;
- Google Flow;
- direct Veo API

as if they were one provider contract.

### Decision

Separate:

```text
GOOGLE/FLOW_PRODUCT
GOOGLE/FLOW_PRIVATE_TRANSPORT (experimental if used)
GOOGLE/GEMINI_API/VEO
GOOGLE/VERTEX_AI/VEO
```

No recovery/quota/billing fact automatically crosses surfaces.

---

# 5. C-004 — Wan identity conflation

Prior architecture listed a generic `WANAdapter`.

But:

```text
Wan local
≠
Alibaba Cloud Wan API
```

### Decision

Use:

```text
WanLocalAdapter
AlibabaModelStudioWanAdapter
```

They may share ShotIR compilation concepts but not:
- credentials;
- quotas;
- billing;
- retries;
- task handles.

---

# 6. C-005 — Cost model too generic

Earlier `estimated_cost` / `actual_cost` fields were correct but under-specified.

Providers bill in incompatible units.

### Decision

Cost record requires:

```text
billing_unit_kind
unit_price_snapshot
estimated_quantity
actual_quantity
currency_or_credit_unit
billing_surface
price_evidence_version
```

Do not compare "cost" numerically across USD and Flow credits without explicit conversion policy.

---

# 7. C-006 — Quota values vs architecture

Earlier performance examples used placeholder caps like:

```text
Flow 4
Seedance 4
WAN remote 4
```

Current provider research shows model/surface/account-specific values differ.

### Decision

Examples are explicitly illustrative only.

Runtime admission values come from versioned `ProviderProfile`.

---

# 8. C-007 — Cancellation semantics

Generic cancellation language could imply a running remote job can always stop.

Current provider evidence shows this is false for at least some task APIs.

### Decision

Canonical adapter exposes capability:

```text
cancel_queued
cancel_running
delete_terminal
```

and returns a typed cancellation result.

No generic promise that `cancel()` stops billing/work.

---

# 9. C-008 — Secret storage vs browser sessions

API-key credential lease architecture is strong for string-like secrets.

Browser sessions/cookie jars are a different security object.

### Decision

Keep:
```text
API_KEY/OAUTH_TOKEN
→ Credential Broker lease
```

But:
```text
BROWSER_SESSION
→ provider-specific isolated session boundary
```

Do not serialize browser sessions as generic secret strings.

---

# 10. C-009 — Continuity authority

Potential conflict:
- parent image used for conditioning;
- semantic StateSnapshot is authority.

### Decision

No contradiction after clarification:

```text
StateSnapshot
= semantic authority

Parent accepted image
= conditioning artifact / visual evidence
```

If they disagree, propagation blocks for review/repair.

---

# 11. C-010 — QA score vs severity

Early FlowKit-derived video review uses weighted dimensions.

New Static QA rejects weighted score as sole acceptance authority.

### Decision

Metrics/weighted scores remain **sensors/diagnostics**.

Final acceptance is severity/policy driven.

This applies to both static and video QA.

---

# 12. C-011 — Repair preserve semantics

"Preserve" could be misread as a generative guarantee.

### Decision

Preserve means:

```text
contractual invariant to re-check
```

not:
```text
model is guaranteed not to change it
```

---

# 13. C-012 — SQLite current role

No contradiction found after review:

```text
SQLite WAL
= V1 local operational store candidate

PostgreSQL
= future multi-machine/team reconsideration
```

This remains consistent with local-first modular-monolith topology.

---

# 14. C-013 — Event log authority

Durable operational events could be mistaken for Event Sourcing.

### Decision

Explicit:

```text
current-state tables = authority
events = audit/observability/recovery evidence
```

---

# 15. C-014 — 8 Layer rigidity

Eight layers are semantic structure, not a requirement to emit all fields into every provider prompt.

### Decision

Compiler emits only relevant provider-supported semantics while ShotSpec retains canonical structure.

---

# 16. C-015 — Historical research facts vs current provider evidence

Provider capabilities/prices change frequently.

### Decision

No provider numeric fact is copied into a permanent ADR as timeless truth.

Use:

```text
ProviderProfile version
+ verified_at
+ evidence
```

---

# 17. Contradiction Status

After V0.10 patches:

```text
unresolved conceptual BLOCKER = 0
unresolved CRITICAL contradiction = 0
```

Still-open evidence blockers remain external/runtime proofs and are **not** treated as contradictions.

The architecture is still not L6 because evidence is incomplete.
