# EVIDENCE_LEDGER_V0_15.md

**Current evidence inventory after Windows Persistence Run 2.**

| Evidence ID | Gate | Class | Status | SHA-256 prefix |
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
| EV-PERSIST-WIN-RUN2-002 | PERSISTENCE_WINDOWS | TARGET_RUNTIME | PASS | `9fe10421394bb95e` |

## Gate status

```json
{
  "PERSISTENCE_WINDOWS": {
    "closed": true,
    "required_classes": [
      "TARGET_RUNTIME"
    ],
    "present_passing_classes": [
      "TARGET_RUNTIME"
    ],
    "missing_classes": [],
    "evidence_ids": [
      "EV-PERSIST-LOCAL-001",
      "EV-PERSIST-WIN-RUN1-001",
      "EV-PERSIST-WIN-RUN2-002"
    ]
  },
  "CREDENTIAL_BROKER_WINDOWS": {
    "closed": false,
    "required_classes": [
      "TARGET_RUNTIME"
    ],
    "present_passing_classes": [],
    "missing_classes": [
      "TARGET_RUNTIME"
    ],
    "evidence_ids": [
      "EV-CRED-LOCAL-001"
    ]
  },
  "PROVIDER_AMBIGUITY": {
    "closed": false,
    "required_classes": [
      "LIVE_PROVIDER"
    ],
    "present_passing_classes": [],
    "missing_classes": [
      "LIVE_PROVIDER"
    ],
    "evidence_ids": [
      "EV-PROVIDER-AMB-001"
    ]
  },
  "STATIC_QA_CALIBRATION": {
    "closed": false,
    "required_classes": [
      "VISUAL_CALIBRATION"
    ],
    "present_passing_classes": [],
    "missing_classes": [
      "VISUAL_CALIBRATION"
    ],
    "evidence_ids": [
      "EV-QA-POLICY-001"
    ]
  },
  "TARGETED_REPAIR_LIVE": {
    "closed": false,
    "required_classes": [
      "LIVE_GENERATION_BENCHMARK"
    ],
    "present_passing_classes": [],
    "missing_classes": [
      "LIVE_GENERATION_BENCHMARK"
    ],
    "evidence_ids": [
      "EV-REPAIR-PLAN-001"
    ]
  },
  "PERFORMANCE_TARGET": {
    "closed": false,
    "required_classes": [
      "TARGET_RUNTIME"
    ],
    "present_passing_classes": [],
    "missing_classes": [
      "TARGET_RUNTIME"
    ],
    "evidence_ids": [
      "EV-PERF-LOCAL-001"
    ]
  },
  "PROVIDER_PROFILE_LIVE": {
    "closed": false,
    "required_classes": [
      "LIVE_ACCOUNT_OBSERVATION"
    ],
    "present_passing_classes": [],
    "missing_classes": [
      "LIVE_ACCOUNT_OBSERVATION"
    ],
    "evidence_ids": []
  },
  "CONTRACT_TRACEABILITY": {
    "closed": true,
    "required_classes": [
      "STATIC_ANALYSIS"
    ],
    "present_passing_classes": [
      "STATIC_ANALYSIS"
    ],
    "missing_classes": [],
    "evidence_ids": [
      "EV-CONTRACT-001"
    ]
  }
}
```

**Evidence integrity:** `True`

**All L6 critical gates closed:** `False`
