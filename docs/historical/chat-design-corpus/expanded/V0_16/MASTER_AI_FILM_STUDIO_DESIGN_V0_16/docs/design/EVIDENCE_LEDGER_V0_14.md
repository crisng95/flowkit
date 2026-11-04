# EVIDENCE_LEDGER_V0_14.md

**Purpose:** evidence inventory after first real Windows persistence run.

| Evidence | Gate | Class | Status | SHA-256 prefix |
|---|---|---|---|---|
| EV-PERSIST-LOCAL-001 | PERSISTENCE_WINDOWS | LOCAL_SIMULATION | PARTIAL | `3c944b4cec510398` |
| EV-PROVIDER-AMB-001 | PROVIDER_AMBIGUITY | LOCAL_SIMULATION | PARTIAL | `a0256cc5aa06f86a` |
| EV-CRED-LOCAL-001 | CREDENTIAL_BROKER_WINDOWS | LOCAL_SIMULATION | PARTIAL | `9a25b4001cf60001` |
| EV-QA-POLICY-001 | STATIC_QA_CALIBRATION | LOCAL_SIMULATION | PARTIAL | `5fce03380457e3a7` |
| EV-REPAIR-PLAN-001 | TARGETED_REPAIR_LIVE | LOCAL_SIMULATION | PARTIAL | `25e227db1f8cfb19` |
| EV-PERF-LOCAL-001 | PERFORMANCE_TARGET | LOCAL_SIMULATION | PARTIAL | `85d48c0916d2d2c0` |
| EV-CONTRACT-001 | CONTRACT_TRACEABILITY | STATIC_ANALYSIS | PASS | `25cd5e56e8242df6` |
| EV-HARNESS-001 | HARNESS_SET | HARNESS_VALIDATION | PASS | `52f80263bd08af57` |
| EV-PERSIST-WIN-RUN1-001 | PERSISTENCE_WINDOWS | TARGET_RUNTIME | FAIL | `27209750c447f6e1` |

## Persistence gate

```json
{
  "closed": false,
  "required_classes": [
    "TARGET_RUNTIME"
  ],
  "present_passing_classes": [],
  "missing_classes": [
    "TARGET_RUNTIME"
  ],
  "evidence_ids": [
    "EV-PERSIST-LOCAL-001",
    "EV-PERSIST-WIN-RUN1-001"
  ]
}
```

Run 1 FAIL remains in lineage. A future V2 PASS may close the gate but must not erase Run 1.
