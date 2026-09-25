# JOB_STATE_MODEL_V0_10.md
# Orthogonal Job State Model

**Status:** REVIEWED CANDIDATE

A generation job has several independent state dimensions. A single giant enum hides financially important ambiguity.

## Scheduler state

```text
QUEUED
WAITING_DEPENDENCY
WAITING_CAPACITY
CLAIMED
RUNNING
TERMINAL
```

## Provider-submission state

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

## Artifact state

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

## Creative acceptance state

```text
NOT_APPLICABLE
PENDING_QA
QA_RUNNING
QA_FAILED
REPAIR_PENDING
NEEDS_HUMAN_REVIEW
APPROVED
LOCKED
REJECTED
```

Examples:

```text
scheduler = TERMINAL
provider  = REMOTE_SUCCEEDED
artifact  = READY
creative  = QA_FAILED
```

and:

```text
scheduler = TERMINAL
provider  = REMOTE_SUCCEEDED
artifact  = STALE_RESULT
creative  = REJECTED
```

UI may derive a compact summary such as WAITING / GENERATING / RECOVERING / REVIEWING / APPROVED / FAILED, but the derived summary is not the persistence authority.
