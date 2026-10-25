# FAILURE_RECOVERY_MODEL.md
# Failure & Recovery Model — Deep Dive V0.2

**Status:** CANDIDATE  
**Rule:** technical failure recovery must never silently rewrite creative truth.

---

# 1. Failure Domains

```text
A. local process
B. database
C. artifact filesystem
D. provider transport
E. provider remote job
F. compiler/schema
G. dependency graph
H. QA
I. user concurrent edits
J. update/migration
```

Each failure is assigned an owner and recovery action.

---

# 2. Status Separation

Technical execution:

```text
PREPARED
QUEUED
CLAIMED
SUBMITTING
SUBMITTED
POLLING
DOWNLOADING
ARTIFACT_READY
FAILED_RETRYABLE
FAILED_FINAL
UNKNOWN_REMOTE_STATE
RECONCILING
AMBIGUOUS_HOLD
CANCEL_REQUESTED
CANCELED
STALE_RESULT
```

Creative acceptance:

```text
PENDING_QA
QA_FAILED
REPAIR_PENDING
APPROVED
LOCKED
REJECTED
```

Never map `ARTIFACT_READY` directly to `APPROVED`.

---

# 3. Failure Matrix

| Failure | Detection | Immediate State | Recovery | Automatic? |
|---|---|---|---|---|
| app crash before provider submit | PREPARED/QUEUED survives | QUEUED/RECOVERY | resume | yes |
| crash during HTTP submit | missing confirmed remote state | UNKNOWN_REMOTE_STATE | reconcile provider before resubmit | yes if adapter supports |
| HTTP timeout after provider accepted | timeout + possible remote side effect | UNKNOWN_REMOTE_STATE | lookup by idempotency/request identity | no blind retry |
| provider 429 | typed rate-limit error | FAILED_RETRYABLE | backoff respecting provider policy | yes |
| provider 5xx | typed transient error | FAILED_RETRYABLE | bounded retry | yes |
| provider permanent 4xx | typed final error | FAILED_FINAL | user/config/repair action | no |
| provider job disappears | poll returns not-found | RECOVERY_REQUIRED | reconcile request history / mark orphan | bounded |
| DB busy | SQLite busy | no semantic change | bounded DB retry | yes |
| DB corruption/integrity failure | startup/integrity check | BLOCKED | restore/recover backup | no auto destructive fix |
| artifact download interrupted | partial file | DOWNLOADING/RECOVERY | resume/re-download if supported | yes |
| final file exists, DB row absent | startup reconciler | ORPHAN_FILE | verify lineage then register/quarantine | policy |
| DB READY, file missing | startup reconciler | ARTIFACT_MISSING | re-download/recover | policy |
| user edits ShotSpec while job runs | fingerprint mismatch | STALE_RESULT | retain candidate; do not activate | yes |
| parent regenerated | dependency version changes | descendants INVALIDATED | replan/recompile affected descendants | yes |
| child finishes after parent changed | fingerprint/dependency mismatch | STALE_RESULT | do not accept | yes |
| user cancel before submit | state check | CANCELED | no provider call | yes |
| user cancel after submit, provider cancel supported | cancel API | CANCEL_REQUESTED | remote cancel then CANCELED | yes |
| user cancel after submit, provider cannot cancel | local cancellation | CANCEL_REQUESTED | ignore/quarantine late result | yes |
| migration interrupted | migration version/checksum | MIGRATION_RECOVERY | rollback/restore/resume supported migration | controlled |
| update during active jobs | update gate | UPDATE_BLOCKED | checkpoint/drain before update | yes |
| QA tool fails | reviewer error | QA_ERROR | retry reviewer / alternate sensor | yes |
| QA disagrees across sensors | conflicting results | NEEDS_REVIEW | severity/rule resolution | not purely automatic |
| repair repeats without improvement | repair history threshold | REPAIR_ESCALATED | re-anchor/replan/manual review | no blind loop |

---

# 4. Remote Ambiguity Rule

This is a hard invariant:

> A provider timeout after a request may have left the remote side effect running.

Therefore:

```text
timeout
≠
safe-to-retry
```

The adapter must classify:

```text
SAFE_TO_RETRY
RECONCILE_FIRST
FINAL_FAILURE
```

For `RECONCILE_FIRST`, the orchestrator does not resubmit until it can determine whether a remote job exists or the configured policy explicitly permits a duplicate candidate.

---

# 5. Retry Taxonomy

Retry belongs to transport/execution, not creative repair.

```text
TRANSIENT_NETWORK
RATE_LIMIT
PROVIDER_5XX
POLL_TEMPORARY_FAILURE
DOWNLOAD_TEMPORARY_FAILURE
DB_BUSY
```

may be retryable.

```text
INVALID_REQUEST
UNSUPPORTED_CAPABILITY
AUTHORIZATION
MISSING_REFERENCE
SCHEMA_VALIDATION
CONTENT_POLICY
```

are not generic-retry conditions.

---

# 6. Backoff

Provider-specific policy:

```text
base_delay
max_delay
attempt_limit
jitter
retry_after support
```

The provider adapter returns normalized guidance.

No infinite automatic retry.

---

# 7. Crash Recovery Startup Sequence

```text
1. open DB read-only enough to inspect schema
2. verify supported schema version
3. integrity/health checks
4. recover migration if necessary
5. scan jobs in non-terminal states
6. scan expired worker leases
7. reconcile UNKNOWN_REMOTE_STATE / SUBMITTED / POLLING jobs
8. reconcile artifact staging/final paths
9. recompute dependency readiness
10. resume scheduler
```

The scheduler starts only after recovery pass completes.

---

# 8. Stale Completion Rule

When a remote job finishes:

```text
if job.input_fingerprint != current_expected_fingerprint:
    artifact.status = STALE_RESULT
    do not set active artifact
    do not propagate end state
```

This protects against late provider results overwriting newer creative decisions.

---

# 9. Parent/Child Invalidation

Regenerating a parent does not blindly delete descendants.

Instead:

```text
parent artifact/version changed
↓
calculate descendants whose inputs depend on that parent
↓
mark:
  STALE_INPUT
or
  NEEDS_REVALIDATION
↓
preserve bytes/history
↓
recompile only affected descendants
```

If a descendant does not visually inherit the parent (e.g. independent ROOT branch), it is not invalidated.

---

# 10. Repair Escalation

Creative failures route:

```text
PATCH_IN_PLACE
→ regenerate affected artifact

REGENERATE_FROM_ANCHOR
→ reset conditioning to canonical reference / approved earlier state

REPLAN_SHOT
→ modify cinematography/action plan while preserving beat/story

ESCALATE_STORY
→ only if failure proves upstream story/action is unexecutable
```

Automatic loops must have attempt limits.

---

# 11. Database Corruption Policy

Never “fix” corruption by silently deleting rows.

On suspected corruption:

```text
BLOCK WRITES
→ preserve original files
→ run integrity diagnostics
→ locate newest verified backup/snapshot
→ offer/perform staged restore
→ verify artifact manifest
→ record recovery event
```

---

# 12. Backup / Restore Failure

Backup is valid only if:

```text
DB snapshot readable
+
manifest readable
+
all required artifact hashes verified
```

Partial copy ≠ successful backup.

---

# 13. Update / Migration Safety

Before application update:

```text
active remote jobs?
├── yes → either drain/checkpoint or preserve compatible reconciler
└── no  → proceed

backup required for destructive schema change
↓
apply migration
↓
verify schema/data
↓
start new scheduler
```

A new app version must not start generation if it cannot interpret in-flight job schema.

---

# 14. Recovery Events

Persist recovery log:

```text
recovery_event_id
timestamp
project_id
job_id?
artifact_id?
failure_code
detected_state
action_taken
result
operator_required
```

This is operational evidence, not just console logging.

---

# 15. Acceptance Gates for Reliability

Before architecture freeze:

- no blind remote retry after ambiguous timeout;
- restart resumes known remote jobs;
- stale provider result cannot overwrite newer shot state;
- parent invalidation is selective;
- artifact crash stages reconcile deterministically;
- schema migration interruption has recovery path;
- backup/restore is testable;
- duplicate job submission is prevented where provider supports idempotency and surfaced where it does not.


# Provider Submission Ambiguity Patch

`SUBMITTING` with no durable remote operation after crash/restart MUST NOT fall back to normal retry.

Recovery:

```text
SUBMITTING + missing remote handle
→ UNKNOWN_REMOTE_STATE
→ RECONCILING
   ├── RECOVERED(handle) → SUBMITTED/POLLING
   ├── PROVEN_ABSENT → PREPARED/SAFE_RETRY
   └── STILL_AMBIGUOUS → AMBIGUOUS_HOLD
```

Only provider-specific verified recovery evidence can permit automatic resubmit after ambiguity.


# V0.10 Provider Cancellation Patch

Canonical provider adapters must expose cancellation capabilities:

```text
cancel_queued: yes/no/unknown
cancel_running: yes/no/unknown
delete_terminal: yes/no/unknown
```

`CANCEL_REQUESTED` means local intent only.

It does not imply the remote provider stopped work or billing.

Provider-specific evidence determines transition to `REMOTE_CANCELED`.
