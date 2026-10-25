# STATIC_QA_POLICY_SPIKE_EVIDENCE_V0.7.md
# Static QA Acceptance-Policy Spike

**Status:** PARTIAL PROOF — POLICY LOGIC ONLY  
**Not claimed:** vision-model calibration.

## Goal

Test whether a weighted aggregate score can incorrectly pass a shot with one story-critical blocking failure.

Synthetic fixtures:
- 60 adversarial cases with one BLOCKING dimension intentionally failed while all other dimensions are high;
- 60 valid cases.

Policy A:
```text
weighted average >= 0.75 → PASS
```

Policy B:
```text
any BLOCKING dimension below acceptance threshold → FAIL
```

Results:

```json
{
  "fixtures": 120,
  "blocking_fail_cases": 60,
  "valid_cases": 60,
  "weighted_policy": {
    "threshold": 0.75,
    "blocking_false_negatives": 60,
    "false_positives": 0
  },
  "severity_policy": {
    "blocking_false_negatives": 0,
    "false_positives": 0
  },
  "note": "Synthetic policy test. It proves acceptance-policy behavior, not computer-vision detection quality."
}
```

## Finding

In this synthetic adversarial set, weighted averaging produced **60 blocking false negatives**.

The severity policy produced **0 blocking false negatives** in the same policy-level fixtures.

This validates the architecture rule:

```text
BLOCKING failures cannot be averaged away.
```

It does **not** prove a vision model can correctly detect identity/state/prop/continuity/intent defects. That remains a separate calibration requirement with real images and labeled near-misses.
