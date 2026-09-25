# ADR-0012 — Orthogonal Job State Correction V0.13

**Status:** PROPOSED / MODEL-CHECKED

## Problem

V0.10 artifact state contained `APPROVED` / `REJECTED`, duplicating the Creative Acceptance axis.

It also lacked:
- Scheduler `WAITING_RECOVERY` for ambiguous remote holds;
- Creative `QA_ERROR` although QA design already referenced evaluator failure.

## Decision

Use:

```text
Scheduler:
  ... WAITING_RECOVERY ...

Provider:
  ... UNKNOWN_REMOTE_STATE / RECONCILING / AMBIGUOUS_HOLD ...

Artifact Materialization:
  NONE / STAGING / READY / STALE_RESULT /
  QUARANTINED / MISSING / CORRUPT / ARCHIVED

Creative Acceptance:
  NOT_APPLICABLE / PENDING_QA / QA_RUNNING /
  QA_ERROR / QA_FAILED / REPAIR_PENDING /
  NEEDS_HUMAN_REVIEW / APPROVED / LOCKED / REJECTED
```

## Evidence

Local transition/reachability model check confirms:
- all declared states reachable;
- no dangling transition targets;
- canonical valid/invalid scenario checks pass.

## Consequence

UI summary remains derived; no approval semantics live in artifact materialization state.
