# ADR-0007 — Ambiguous Provider Submission Recovery

**Status:** PROPOSED / EVIDENCE-SUPPORTED

## Context

Media generation is side-effecting and often billable. A network failure can occur after the provider accepts the request but before the local process durably records the remote operation handle.

## Decision

Add first-class states:

```text
SUBMITTING
UNKNOWN_REMOTE_STATE
RECONCILING
AMBIGUOUS_HOLD
```

No automatic resubmission is allowed after ambiguous acceptance unless:
- server idempotency guarantees same-job behavior; or
- reconciliation proves absence; or
- transport proves the request never reached the side-effect boundary.

## Evidence

- FlowKit already re-polls when a remote operation ID is stored.
- Source audit shows an unprotected submit→local-save window.
- Local fault-injection simulation demonstrates the legacy pattern can create two jobs after that crash point.
- Safety-first state machine produced zero duplicate jobs in 1,500 randomized simulated recovery runs across three provider capability classes.

## Consequence

Some providers may leave jobs in `AMBIGUOUS_HOLD` rather than auto-retrying. This is intentional financial correctness.

## Revisit

After live provider-specific fault-injection proves stronger reconciliation/idempotency primitives.
