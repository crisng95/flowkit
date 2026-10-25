# HARNESS_VALIDATION_V0_12.md
# Hardening Harness Validation

**Status:** HARNESS-LEVEL EVIDENCE ONLY

The following harnesses/analyzers were created and locally validated where execution was possible:

## Electron Credential Broker Harness

JavaScript syntax checks:

```json
{
  "main.js": {
    "returncode": 0,
    "stderr": ""
  },
  "preload.js": {
    "returncode": 0,
    "stderr": ""
  },
  "utility.js": {
    "returncode": 0,
    "stderr": ""
  }
}
```

This proves syntax validity in the current Node runtime only.

It does **not** prove:
- Electron `safeStorage` on Windows;
- `utilityProcess` runtime behavior;
- packaged-app security boundary.

Those remain target execution gates.

## Static QA Calibration Analyzer

A deliberately imperfect sample was analyzed.

```json
{
  "returncode": 0,
  "report": {
    "fixtures": 4,
    "classes": {
      "CAMERA_ANGLE_FAIL": {
        "tp": 1,
        "fp": 0,
        "tn": 0,
        "fn": 0,
        "precision": 1.0,
        "recall": 1.0,
        "specificity": null,
        "f1": 1.0,
        "false_negative_rate": 0.0
      },
      "IDENTITY_DRIFT": {
        "tp": 1,
        "fp": 0,
        "tn": 0,
        "fn": 0,
        "precision": 1.0,
        "recall": 1.0,
        "specificity": null,
        "f1": 1.0,
        "false_negative_rate": 0.0
      },
      "PROP_MISSING_CRITICAL": {
        "tp": 0,
        "fp": 0,
        "tn": 0,
        "fn": 1,
        "precision": null,
        "recall": 0.0,
        "specificity": null,
        "f1": null,
        "false_negative_rate": 1.0
      },
      "STYLE_DRIFT": {
        "tp": 0,
        "fp": 1,
        "tn": 0,
        "fn": 0,
        "precision": 0.0,
        "recall": null,
        "specificity": 0.0,
        "f1": null,
        "false_negative_rate": null
      }
    },
    "blocking_classes": [
      "IDENTITY_DRIFT",
      "PROP_MISSING_CRITICAL"
    ],
    "blocking_false_negative_rate": 0.5,
    "dataset_versions": [
      "demo"
    ],
    "reviewer_versions": [
      "demo-r1"
    ]
  }
}
```

The analyzer correctly exposes a blocking false negative in the sample rather than hiding it.

This validates metric plumbing, not AI vision quality.

## Targeted Repair Benchmark Analyzer

A paired sample was analyzed.

```json
{
  "returncode": 0,
  "report": {
    "overall": {
      "targeted": {
        "n": 2,
        "acceptance_rate": 0.5,
        "blocking_regression_rate": 0.5,
        "high_regression_rate": 0.0,
        "avg_provider_calls": 1.5,
        "avg_cost": 1.5,
        "avg_latency_s": 55,
        "avg_cost_per_accepted": 3.0
      },
      "full_regen": {
        "n": 2,
        "acceptance_rate": 1.0,
        "blocking_regression_rate": 0.0,
        "high_regression_rate": 0.0,
        "avg_provider_calls": 1,
        "avg_cost": 1.5,
        "avg_latency_s": 47.5,
        "avg_cost_per_accepted": 1.5
      }
    },
    "by_failure_code": {
      "CAMERA_FAIL": {
        "targeted": {
          "n": 1,
          "acceptance_rate": 1.0,
          "blocking_regression_rate": 0.0,
          "high_regression_rate": 0.0,
          "avg_provider_calls": 1,
          "avg_cost": 1.0,
          "avg_latency_s": 30,
          "avg_cost_per_accepted": 1.0
        },
        "full_regen": {
          "n": 1,
          "acceptance_rate": 1.0,
          "blocking_regression_rate": 0.0,
          "high_regression_rate": 0.0,
          "avg_provider_calls": 1,
          "avg_cost": 1.5,
          "avg_latency_s": 45,
          "avg_cost_per_accepted": 1.5
        }
      },
      "IDENTITY_DRIFT": {
        "targeted": {
          "n": 1,
          "acceptance_rate": 0.0,
          "blocking_regression_rate": 1.0,
          "high_regression_rate": 0.0,
          "avg_provider_calls": 2,
          "avg_cost": 2.0,
          "avg_latency_s": 80,
          "avg_cost_per_accepted": null
        },
        "full_regen": {
          "n": 1,
          "acceptance_rate": 1.0,
          "blocking_regression_rate": 0.0,
          "high_regression_rate": 0.0,
          "avg_provider_calls": 1,
          "avg_cost": 1.5,
          "avg_latency_s": 50,
          "avg_cost_per_accepted": 1.5
        }
      }
    }
  }
}
```

The sample intentionally shows that Targeted Repair can lose to full regeneration for some failure classes. The analyzer reports that outcome rather than assuming Targeted Repair must win.

This validates benchmark neutrality, not real repair efficacy.
