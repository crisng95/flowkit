# JOB_STATE_MODEL_CHECK_V0_13.md

**Status:** LOCAL MODEL-CHECK EVIDENCE

```json
{
  "reachability": {
    "scheduler": {
      "states": [
        "CLAIMED",
        "QUEUED",
        "RUNNING",
        "TERMINAL",
        "WAITING_CAPACITY",
        "WAITING_DEPENDENCY",
        "WAITING_RECOVERY"
      ],
      "reachable": [
        "CLAIMED",
        "QUEUED",
        "RUNNING",
        "TERMINAL",
        "WAITING_CAPACITY",
        "WAITING_DEPENDENCY",
        "WAITING_RECOVERY"
      ],
      "unreachable": [],
      "dangling_targets": []
    },
    "provider": {
      "states": [
        "AMBIGUOUS_HOLD",
        "CANCEL_REQUESTED",
        "NOT_SUBMITTED",
        "POLLING",
        "RECONCILING",
        "REMOTE_CANCELED",
        "REMOTE_FAILED",
        "REMOTE_SUCCEEDED",
        "SUBMITTED",
        "SUBMITTING",
        "UNKNOWN_REMOTE_STATE"
      ],
      "reachable": [
        "AMBIGUOUS_HOLD",
        "CANCEL_REQUESTED",
        "NOT_SUBMITTED",
        "POLLING",
        "RECONCILING",
        "REMOTE_CANCELED",
        "REMOTE_FAILED",
        "REMOTE_SUCCEEDED",
        "SUBMITTED",
        "SUBMITTING",
        "UNKNOWN_REMOTE_STATE"
      ],
      "unreachable": [],
      "dangling_targets": []
    },
    "artifact": {
      "states": [
        "ARCHIVED",
        "CORRUPT",
        "MISSING",
        "NONE",
        "QUARANTINED",
        "READY",
        "STAGING",
        "STALE_RESULT"
      ],
      "reachable": [
        "ARCHIVED",
        "CORRUPT",
        "MISSING",
        "NONE",
        "QUARANTINED",
        "READY",
        "STAGING",
        "STALE_RESULT"
      ],
      "unreachable": [],
      "dangling_targets": []
    },
    "creative": {
      "states": [
        "APPROVED",
        "LOCKED",
        "NEEDS_HUMAN_REVIEW",
        "NOT_APPLICABLE",
        "PENDING_QA",
        "QA_ERROR",
        "QA_FAILED",
        "QA_RUNNING",
        "REJECTED",
        "REPAIR_PENDING"
      ],
      "reachable": [
        "APPROVED",
        "LOCKED",
        "NEEDS_HUMAN_REVIEW",
        "NOT_APPLICABLE",
        "PENDING_QA",
        "QA_ERROR",
        "QA_FAILED",
        "QA_RUNNING",
        "REJECTED",
        "REPAIR_PENDING"
      ],
      "unreachable": [],
      "dangling_targets": []
    }
  },
  "scenario_results": [
    {
      "name": "initial",
      "expected_valid": true,
      "actual_valid": true,
      "pass": true,
      "state": {
        "scheduler": "QUEUED",
        "provider": "NOT_SUBMITTED",
        "artifact": "NONE",
        "creative": "NOT_APPLICABLE"
      }
    },
    {
      "name": "ambiguous_hold",
      "expected_valid": true,
      "actual_valid": true,
      "pass": true,
      "state": {
        "scheduler": "WAITING_RECOVERY",
        "provider": "AMBIGUOUS_HOLD",
        "artifact": "NONE",
        "creative": "NOT_APPLICABLE"
      }
    },
    {
      "name": "qa_failed",
      "expected_valid": true,
      "actual_valid": true,
      "pass": true,
      "state": {
        "scheduler": "TERMINAL",
        "provider": "REMOTE_SUCCEEDED",
        "artifact": "READY",
        "creative": "QA_FAILED"
      }
    },
    {
      "name": "stale_result",
      "expected_valid": true,
      "actual_valid": true,
      "pass": true,
      "state": {
        "scheduler": "TERMINAL",
        "provider": "REMOTE_SUCCEEDED",
        "artifact": "STALE_RESULT",
        "creative": "REJECTED"
      }
    },
    {
      "name": "missing_but_historically_approved",
      "expected_valid": true,
      "actual_valid": true,
      "pass": true,
      "state": {
        "scheduler": "TERMINAL",
        "provider": "REMOTE_SUCCEEDED",
        "artifact": "MISSING",
        "creative": "APPROVED"
      }
    },
    {
      "name": "invalid_terminal_polling",
      "expected_valid": false,
      "actual_valid": false,
      "pass": true,
      "state": {
        "scheduler": "TERMINAL",
        "provider": "POLLING",
        "artifact": "NONE",
        "creative": "NOT_APPLICABLE"
      }
    },
    {
      "name": "invalid_not_submitted_artifact",
      "expected_valid": false,
      "actual_valid": false,
      "pass": true,
      "state": {
        "scheduler": "RUNNING",
        "provider": "NOT_SUBMITTED",
        "artifact": "READY",
        "creative": "PENDING_QA"
      }
    },
    {
      "name": "invalid_qa_without_artifact",
      "expected_valid": false,
      "actual_valid": false,
      "pass": true,
      "state": {
        "scheduler": "RUNNING",
        "provider": "REMOTE_SUCCEEDED",
        "artifact": "NONE",
        "creative": "QA_RUNNING"
      }
    }
  ],
  "all_states_reachable": true,
  "scenario_checks_pass": true,
  "design_findings": [
    "Artifact APPROVED/REJECTED duplicated creative acceptance semantics in V0.10; removed from artifact axis.",
    "WAITING_RECOVERY was missing from scheduler axis for AMBIGUOUS_HOLD; added.",
    "QA_ERROR was referenced by QA design but absent from creative state axis; added."
  ]
}
```

## Result

- all declared states are reachable from their axis initial state;
- no transition points to an undeclared state;
- canonical valid/invalid scenario checks pass;
- three cross-document defects were patched:
  1. duplicate creative APPROVED/REJECTED semantics removed from artifact state;
  2. `WAITING_RECOVERY` added to scheduler state;
  3. `QA_ERROR` added to creative state.

This is a state-model consistency proof, not runtime orchestrator proof.
