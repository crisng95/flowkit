# ADR-0009 — Hierarchical Admission, Backpressure and Fairness

**Status:** PROPOSED / LOCAL-EVIDENCE SUPPORTED

## Decision

Scheduler admission uses all applicable gates:

```text
global
+ provider
+ model
+ operation type
+ local resource
+ dependency readiness
+ budget
```

Ordering among ready jobs uses:

```text
priority class
+ project fairness
+ oldest-ready
```

## Evidence

In a 300-job synthetic workload:
- a global-only limit violated configured provider caps;
- hierarchical provider/model limits produced zero configured cap violations;
- project fairness kept mean start times within a bounded spread in the simulation.

## Limitation

Provider/model caps and job durations were synthetic. Actual values require provider-specific live evidence.
