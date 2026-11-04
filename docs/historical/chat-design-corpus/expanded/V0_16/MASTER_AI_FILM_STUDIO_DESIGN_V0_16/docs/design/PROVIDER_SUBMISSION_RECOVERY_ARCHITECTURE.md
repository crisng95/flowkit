# PROVIDER_SUBMISSION_RECOVERY_ARCHITECTURE.md
# Provider Submission / Ambiguity Recovery Architecture V0.5

**Status:** REVIEWED CANDIDATE  
**Source:** Provider Ambiguity Proof V0.5

## 1. Invariant

`UNKNOWN_REMOTE_STATE` is a safety state, not a generic error.

No generic retry engine may resubmit an ambiguous side-effecting generation request.

## 2. States

```text
PREPARED
SUBMITTING
SUBMITTED
POLLING
UNKNOWN_REMOTE_STATE
RECONCILING
AMBIGUOUS_HOLD
COMPLETED
FAILED_FINAL
CANCEL_REQUESTED
CANCELED
STALE_RESULT
```

## 3. Submission Identity

Persist before network call:

```text
local_request_id
submission_attempt_id
input_fingerprint
provider_profile_version
local_submission_key
client_token? 
unique_output_prefix?
prepared_at
```

Persist after confirmed response:

```text
provider_request_id?
provider_operation_id
accepted_at
```

## 4. Submit Outcome

```text
ACCEPTED(handle)
PROVEN_NOT_SUBMITTED
AMBIGUOUS
FINAL_FAILURE
```

Transport exceptions are not automatically classified as `PROVEN_NOT_SUBMITTED`.

## 5. Reconciliation

Priority:

```text
1. provider server-idempotency lookup/replay
2. caller token lookup
3. provider operation listing/search
4. provider-specific project/job listing
5. unique output-prefix/artifact detection
6. ambiguity timeout / human decision
```

Each strategy must return evidence.

## 6. Resubmit Rule

Allowed only if:
- provider guarantees same-key idempotency; or
- reconciliation proves no remote job exists; or
- transport proves request never crossed side-effect boundary.

Otherwise:
`AMBIGUOUS_HOLD`.

## 7. Crash Recovery

Startup scans:
- SUBMITTING;
- UNKNOWN_REMOTE_STATE;
- RECONCILING;
- SUBMITTED/POLLING.

`SUBMITTING` without a persisted handle is promoted to `UNKNOWN_REMOTE_STATE`, not back to `QUEUED`.

## 8. Provider Profile Extension

Every provider profile includes:

```text
submission_recovery_profile_version
idempotency_mode
operation_handle_mode
reconcile_methods[]
ambiguous_resubmit_policy
ambiguity_retention
verified_at
evidence[]
```

## 9. FlowKit Adapter

Retain its useful re-poll behavior once operation ID is stored.

Do not reuse the current four-state request lifecycle as canonical runtime state.

The adapter maps Flow-specific operation/workflow/media IDs into separate canonical fields.

## 10. Veo Direct Adapter

Current documentation establishes server operation handle + poll.

Until live proof finds a stronger mechanism, classify direct Veo submit ambiguity as:

```text
HANDLE_ONLY
AMBIGUOUS_RESUBMIT_POLICY = NEVER_AUTO
```

A unique GCS output prefix can be added as completion evidence where supported, but not as a substitute for operation reconciliation.

## 11. Test Matrix

Required contract tests per adapter:

```text
T1 fail before transport
T2 response lost after remote accept
T3 crash after response before local handle commit
T4 restart with SUBMITTED
T5 polling timeout
T6 provider 429
T7 provider 5xx
T8 stale input during remote run
T9 cancel after submit
T10 operation expires/disappears
```
