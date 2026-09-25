# JOB_STATE_MODEL_V0_10.md
# Orthogonal Job State Model

**Status:** REVIEWED CANDIDATE

A generation job has multiple state dimensions. Combining them into one giant enum hides ambiguity.

---

# 1. Scheduler State

```text
QUEUED
WAITING_DEPENDENCY
WAITING_CAPACITY
CLAIMED
RUNNING
TERMINAL
```

Meaning:
- local ownership/scheduling only;
- does not tell whether a provider has accepted a job.

---

# 2. Provider Submission State

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

This axis owns paid/remote side-effect safety.

---

# 3. Artifact State

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

This axis describes local artifact materialization/lineage state.

---

# 4. Creative Acceptance State

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

This axis describes creative/semantic acceptance.

---

# 5. Example

A job can legitimately be:

```text
scheduler_state = TERMINAL
provider_state  = REMOTE_SUCCEEDED
artifact_state  = READY
creative_state  = QA_FAILED
```

This is not contradictory.

Another:

```text
scheduler_state = WAITING_CAPACITY
provider_state  = NOT_SUBMITTED
artifact_state  = NONE
creative_state  = NOT_APPLICABLE
```

Another:

```text
scheduler_state = TERMINAL
provider_state  = REMOTE_SUCCEEDED
artifact_state  = STALE_RESULT
creative_state  = REJECTED
```

because the user changed ShotSpec while the remote job was running.

---

# 6. Derived UI Summary

UI may derive:

```text
WAITING
GENERATING
RECOVERING
AMBIGUOUS
DOWNLOADING
REVIEWING
REPAIRING
APPROVED
FAILED
```

but derived UI summary is not persisted as the only source of truth.

---

# 7. Persistence Patch

`GenerationJob` stores at minimum:

```text
scheduler_state
provider_state
artifact_state
creative_state
```

plus:
```text
provider_operation_id
input_fingerprint
lease/worker fields
error code
```

This replaces ambiguous single `status` semantics in the canonical data model.
