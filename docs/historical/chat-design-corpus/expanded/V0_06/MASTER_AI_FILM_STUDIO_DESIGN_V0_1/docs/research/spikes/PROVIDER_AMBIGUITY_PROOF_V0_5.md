# PROVIDER_AMBIGUITY_PROOF_V0.5.md
# Provider Ambiguity Proof — FlowKit / Veo Family

**Date:** 2026-09-20  
**Status:** PARTIAL PROOF — CODE/DOC EVIDENCE + LOCAL FAULT INJECTION  
**Not claimed:** live paid-provider crash test. No live provider credentials were available in this design environment.

---

# 1. Question

What happens when a generation submit may have been accepted remotely, but the client loses the response or crashes before persisting the remote operation identifier?

This is the financially dangerous ambiguity window:

```text
LOCAL PREPARED
↓
POST / generate
↓
REMOTE ACCEPTS + CHARGES / STARTS WORK
↓
NETWORK RESPONSE LOST OR PROCESS CRASHES
↓
LOCAL DOES NOT HAVE OPERATION ID
↓
RESTART
↓
???
```

Blind resubmit can create a second paid generation.

---

# 2. Existing FlowKit Evidence

Audited commit:

`crisng95/flowkit@d7977fd51b87d4da2a25a05b896f5cdac064e030`

Relevant paths:

- `agent/sdk/services/operations.py`
- `tests/unit/test_operations.py`
- `agent/db/schema.py`
- `agent/worker/processor.py`
- `agent/services/flow_batch.py`

## 2.1 What FlowKit already does correctly

`generate_scene_video(..., request_id=...)` reads a previously stored remote operation identifier. If one exists, it does **not** submit again; it constructs a pending operation and re-polls it.

The repository unit test `TestGenerateSceneVideoRetry` explicitly asserts:

```text
mock_client.generate_video.assert_not_called()
```

when a remote operation identifier is already persisted.

Therefore:

```text
REMOTE OP HANDLE ALREADY PERSISTED
→ retry = RE-POLL
→ no duplicate submit
```

This is a strong behavior and should be retained.

## 2.2 Ambiguity gap found

The submit flow is effectively:

```text
submit_result = generate_video(...)
↓
extract operations
↓
op_name = ...
↓
update_request(... remote op ...)
↓
poll
```

There is an unavoidable gap between:

```text
REMOTE ACCEPT
```

and:

```text
REMOTE OP HANDLE PERSISTED LOCALLY
```

If the process dies or the submit response is lost inside that gap, the next attempt has no saved `existing_op`, so the current FlowKit path can submit again.

The current request status schema exposes:

```text
PENDING
PROCESSING
COMPLETED
FAILED
```

but no explicit:

```text
SUBMITTING
UNKNOWN_REMOTE_STATE
RECONCILING
AMBIGUOUS_HOLD
```

No test was found that fault-injects a crash after remote acceptance but before local operation-handle persistence.

**Finding:** FlowKit's current anti-duplicate logic is strong **after** handle persistence, but does not fully close the submit→persist ambiguity window.

---

# 3. Official Veo / Google Gen AI Evidence

Current official Google documentation describes Veo generation as a long-running operation.

The API/SDK:
1. submits generation;
2. returns a server-assigned operation;
3. uses the operation object/name for later polling.

The documented REST response contains:

```json
{
  "name": ".../operations/<unique-operation-id>"
}
```

and polling requires that operation name.

Current documented `GenerateVideosParameters` includes model/source/config/image/video/prompt fields; the audited public interface does not document a client request-id/idempotency field.

The current public Veo request body documentation also does not show a request-id/idempotency token.

Therefore, based on current public documentation, **the operation handle is the documented recovery handle once it has been received, but a deterministic server-side idempotency key cannot be assumed for the response-loss window.**

This is a documentation-level conclusion, not a claim about undocumented backend behavior.

---

# 4. Local Fault-Injection Proof

A local provider simulator was executed for the exact ambiguity window.

## Explicit scenarios

```json
{
  "legacy_flow_like_lost_response": 2,
  "legacy_flow_like_normal": 1,
  "safe_handle_only_lost_response": {
    "jobs": 1,
    "local": {
      "status": "AMBIGUOUS_HOLD",
      "remote_op": null,
      "submission_key": "sub-S1-abc",
      "client_token": "client-S1-abc"
    }
  },
  "safe_idempotent_lost_response": {
    "jobs": 1,
    "local": {
      "status": "SUBMITTED",
      "remote_op": "op-1",
      "submission_key": "sub-S1-abc",
      "client_token": "client-S1-abc"
    }
  },
  "safe_client_lookup_lost_response": {
    "jobs": 1,
    "local": {
      "status": "SUBMITTED",
      "remote_op": "op-1",
      "submission_key": "sub-S1-abc",
      "client_token": "client-S1-abc"
    }
  },
  "safe_before_transport": {
    "jobs": 1,
    "local": {
      "status": "SUBMITTED",
      "remote_op": "op-1",
      "submission_key": "sub-S1-abc",
      "client_token": "client-S1-abc"
    }
  }
}
```

Interpretation:

### Legacy Flow-like behavior

```text
remote accepts
→ crash before local handle save
→ restart sees no handle
→ resubmit
```

Result:

```text
remote job count = 2
```

This proves the control-flow hazard independent of any particular provider billing system.

### New safety-first HANDLE_ONLY behavior

```text
remote accepts
→ crash before handle save
→ restart sees persisted SUBMITTING
→ transition UNKNOWN_REMOTE_STATE
→ provider has no deterministic lookup key
→ AMBIGUOUS_HOLD
```

Result:

```text
remote job count = 1
```

It avoids duplicate work, but may require waiting/manual resolution.

### Server-idempotency behavior

With a simulated server idempotency key:

```text
same submission key
→ same remote job
```

Result:

```text
remote job count = 1
remote handle recovered
```

### Client-token lookup behavior

With a simulated searchable client token:

```text
reconcile(local client token)
→ recover existing remote job
```

Result:

```text
remote job count = 1
```

---

# 5. Property-Style Fault Runs

500 randomized recovery runs were executed for each recovery capability class.

```json
{
  "HANDLE_ONLY": {
    "runs": 500,
    "duplicates": 0,
    "ambiguous_holds": 173,
    "submitted_or_recovered": 327
  },
  "SERVER_IDEMPOTENCY": {
    "runs": 500,
    "duplicates": 0,
    "ambiguous_holds": 0,
    "submitted_or_recovered": 500
  },
  "CLIENT_TOKEN_LOOKUP": {
    "runs": 500,
    "duplicates": 0,
    "ambiguous_holds": 0,
    "submitted_or_recovered": 500
  }
}
```

Safety invariant in this simulator:

```text
NO AUTOMATIC DUPLICATE REMOTE SUBMIT AFTER AMBIGUOUS ACCEPTANCE
```

held in all executed safe-algorithm runs.

This proves the local state-machine policy under the simulator. It does **not** prove a real provider exposes the recovery primitives.

---

# 6. Provider Recovery Capability Classes

Every adapter must publish one immutable/versioned recovery profile.

```yaml
submission_recovery_profile:
  provider:
  model_family:
  idempotency:
    supported:
    mechanism:
  lookup_by_client_token:
    supported:
  list_recent_operations:
    supported:
  unique_output_prefix:
    supported:
  operation_handle:
    returned_on_submit:
    pollable:
  ambiguous_resubmit_policy:
    SAFE | RECONCILE_FIRST | NEVER_AUTO
  verified_at:
  evidence:
```

Classes:

```text
CLASS A — SERVER IDEMPOTENCY
best: same key is guaranteed not to create duplicate job

CLASS B — CLIENT TOKEN LOOKUP
remote job can be recovered from caller-owned token

CLASS C — LIST / SEARCH
remote jobs can be enumerated and deterministically matched

CLASS D — ARTIFACT PREFIX
completion can be recognized by unique output destination;
cannot necessarily identify in-progress remote job

CLASS E — HANDLE ONLY
safe after handle persisted;
response-loss ambiguity cannot be automatically resolved

CLASS F — NONE
synchronous/opaque side effect with no recoverable identity
```

---

# 7. New Submission State Machine

```text
PREPARED
↓ commit
SUBMITTING
↓ network submit
├── provably no bytes/side-effect
│      → PREPARED / SAFE_RETRY
│
├── operation handle received
│      → persist handle
│      → SUBMITTED
│      → POLLING
│
└── acceptance uncertain
       → UNKNOWN_REMOTE_STATE
       → RECONCILING
          ├── existing job recovered
          │      → SUBMITTED/POLLING
          │
          ├── provider proves no job
          │      → PREPARED / SAFE_RETRY
          │
          └── cannot prove either
                 → AMBIGUOUS_HOLD
```

`UNKNOWN_REMOTE_STATE` is **not** a retryable transport error.

---

# 8. Mandatory Invariant

```text
NO_RETRY_WITHOUT_PROOF
```

If remote acceptance is possible and no deterministic reconciliation primitive exists:

```text
DO NOT AUTO RESUBMIT
```

The system prefers a temporarily stuck job over silently paying for duplicate generation.

---

# 9. Adapter Contract Patch

Provider adapter must implement:

```text
submit(prepared_request)
→ SubmitOutcome

reconcile(submission_identity)
→ ReconcileOutcome

poll(remote_operation)
→ PollOutcome
```

`SubmitOutcome`:

```text
ACCEPTED(handle)
PROVEN_NOT_SUBMITTED
AMBIGUOUS
FINAL_FAILURE
```

`ReconcileOutcome`:

```text
RECOVERED(handle)
PROVEN_ABSENT
STILL_AMBIGUOUS
EXPIRED_UNKNOWN
```

Generic orchestrator may resubmit only on:

```text
PROVEN_NOT_SUBMITTED
PROVEN_ABSENT
or server-idempotent SAME-KEY policy
```

---

# 10. Veo Candidate Policy

Based on currently documented public interfaces:

```text
operation handle:
  YES after response

poll:
  YES

documented client idempotency key:
  NOT ESTABLISHED

documented lookup by local client token:
  NOT ESTABLISHED
```

Therefore conservative V1 policy for direct Veo adapter:

```text
before handle persisted:
  RECONCILE_FIRST / NEVER_AUTO if acceptance uncertain

after handle persisted:
  POLL EXISTING OPERATION
```

If using `outputGcsUri`, a unique per-local-job output prefix may provide an **artifact-level fallback** to identify completed output, but it is not equivalent to a documented in-progress job lookup and must not be promoted to exactly-once semantics without a live spike.

---

# 11. FlowKit Adapter Migration Rule

Keep:

```text
existing remote operation
→ re-poll, never resubmit
```

Replace:

```text
PROCESSING + missing op
→ generic retry
```

with:

```text
SUBMITTING + missing op
→ UNKNOWN_REMOTE_STATE
→ provider reconciliation policy
```

Also rename overloaded storage field:

```text
request.request_id
```

when it actually contains remote operation ID.

Canonical model should use:

```text
local_request_id
provider_request_id?
provider_operation_id?
idempotency_key?
```

---

# 12. Acceptance Status

## Proven now

- existing FlowKit retry-after-handle path intentionally re-polls rather than re-submits;
- current code has a submit→persist ambiguity window;
- current status model lacks an explicit unknown-remote-state;
- the new local state machine prevents automatic duplicates in fault-injection simulations;
- optimistic safety policy is implementable independently of provider.

## Not yet proven

- live Veo behavior when TCP/HTTP response is intentionally severed after server acceptance;
- undocumented server-side request deduplication;
- whether direct Veo can recover an operation by a caller-generated token;
- Flow web/private batch behavior for a completely lost submit response;
- live cost/billing behavior under ambiguity.

---

# 13. Decision

**Architecture patch accepted:**

```text
SUBMITTING
UNKNOWN_REMOTE_STATE
RECONCILING
AMBIGUOUS_HOLD
```

become first-class orchestration states.

No provider adapter can claim `SAFE_RETRY_AFTER_AMBIGUITY` without provider-specific evidence.

---

# 14. Remaining Live Proof

To close this gate for a real V1 provider:

1. use a test project/account;
2. submit one low-cost video job;
3. fault-inject connection termination after request send;
4. preserve local `SUBMITTING` state;
5. attempt provider-specific reconciliation;
6. verify whether the original remote job exists;
7. verify no second paid job is created;
8. record exact request/operation IDs and billing side effect;
9. repeat for at least:
   - response loss;
   - crash after handle received but before local persistence;
   - restart during polling.

Until then this gate is:

```text
PARTIAL_PROOF
NOT LIVE-PROVEN
```
