# JOB_STATE_MODEL_V0_13.md
# Orthogonal Job State Model — V0.13

**Status:** REVIEWED CANDIDATE / MODEL-CHECKED LOCALLY  
**Supersedes:** `JOB_STATE_MODEL_V0_10.md`

A generation job has four independent state dimensions. Keeping them orthogonal prevents provider completion, artifact materialization, and creative approval from being conflated.

---

# 1. Scheduler State

```text
QUEUED
WAITING_DEPENDENCY
WAITING_CAPACITY
CLAIMED
RUNNING
WAITING_RECOVERY
TERMINAL
```

`WAITING_RECOVERY` is explicit so an ambiguous remote job is not falsely marked TERMINAL merely because no worker is actively polling it.

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

Financial side-effect safety belongs to this axis.

---

# 3. Artifact Materialization State

```text
NONE
STAGING
READY
STALE_RESULT
QUARANTINED
MISSING
CORRUPT
ARCHIVED
```

V0.13 removes `APPROVED` and `REJECTED` from this axis because those are creative/acceptance semantics, not file/materialization semantics.

---

# 4. Creative Acceptance State

```text
NOT_APPLICABLE
PENDING_QA
QA_RUNNING
QA_ERROR
QA_FAILED
REPAIR_PENDING
NEEDS_HUMAN_REVIEW
APPROVED
LOCKED
REJECTED
```

`QA_ERROR` means the reviewer/evaluator itself failed; it is distinct from the artifact failing QA.

---

# 5. Examples

Remote generation succeeded, artifact downloaded, QA failed:

```text
scheduler = TERMINAL
provider  = REMOTE_SUCCEEDED
artifact  = READY
creative  = QA_FAILED
```

Remote acceptance is ambiguous and no reconciler is actively working:

```text
scheduler = WAITING_RECOVERY
provider  = AMBIGUOUS_HOLD
artifact  = NONE
creative  = NOT_APPLICABLE
```

User edited ShotSpec while remote job ran:

```text
scheduler = TERMINAL
provider  = REMOTE_SUCCEEDED
artifact  = STALE_RESULT
creative  = REJECTED
```

Artifact was previously approved but later disappears from disk:

```text
scheduler = TERMINAL
provider  = REMOTE_SUCCEEDED
artifact  = MISSING
creative  = APPROVED
```

This is valid: creative judgment history and current byte availability are separate facts.

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
MISSING_ARTIFACT
```

Derived UI status is not persistence authority.

---

# 7. Transition Ownership

Each subsystem may update only its own axis:

```text
Scheduler/Recovery Coordinator → scheduler_state
Provider Adapter/Orchestrator → provider_state
Artifact Store/Reconciler → artifact_state
QA/Repair/Human Approval → creative_state
```

Cross-axis transitions are coordinated by application services but no module may silently rewrite another axis.

---

# 8. Persistence

`GenerationJob` stores:

```text
scheduler_state
provider_state
artifact_state
creative_state
```

together with immutable input identity and provider operation fields.

The previous generic `status` field is deprecated as canonical authority.
