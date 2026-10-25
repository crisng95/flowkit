# REAL_GENERATION_TARGETED_REPAIR_BENCHMARK_PROTOCOL_V0_9.md
# Real-Generation Targeted Repair Benchmark Protocol

**Status:** READY FOR EXECUTION

---

# 1. Goal

Determine whether Targeted Repair actually improves accepted-shot outcomes versus naive full regeneration.

---

# 2. Benchmark Set

Minimum:

```text
90 failed shot artifacts
```

At least 10 each:

```text
IDENTITY_DRIFT
WARDROBE_MISMATCH
PROP_MISMATCH
ACTION_MISMATCH
LOCATION_MISMATCH
CAMERA_FAIL
LIGHTING_FAIL
CONTINUITY_FAIL
NARRATIVE_INTENT_FAIL
```

Use real failed generations where possible.

---

# 3. Arms

For each failed artifact, run:

## A — Targeted Repair

Planner chooses:

```text
PATCH_IN_PLACE
REGENERATE_FROM_ANCHOR
REPLAN_SHOT
```

with explicit preserve/invalidate/recheck.

## B — Full Regenerate Baseline

Regenerate from same upstream accepted inputs without targeted repair.

If provider randomness supports seeds, record them; do not assume deterministic equivalence.

---

# 4. Outcomes

Primary:

```text
accepted after first repair attempt
accepted within max repair attempts
```

Secondary:

```text
target defect fixed
new blocking regression
new high regression
identity preserved
state preserved
continuity preserved
provider calls
generation cost
QA cost
latency
```

---

# 5. Repair Success Definition

A repair is successful only when:

```text
target defect = fixed
AND
no new BLOCKING failure
AND
no unacceptable HIGH regression
AND
shot accepted by frozen QA policy
```

A visually improved but still rejected result is not success.

---

# 6. Comparative Metrics

Per failure class:

```text
targeted first-pass repair rate
full-regenerate first-pass acceptance rate
targeted total acceptance rate
full-regenerate total acceptance rate
regression rate
average provider calls
average cost per accepted shot
average time to accepted shot
```

---

# 7. Causal-Diagnosis Audit

For every failed targeted repair, classify:

```text
wrong responsible layer
correct layer / provider ignored constraint
reference weakness
state ambiguity
provider capability mismatch
QA false positive
new stochastic regression
```

This tests the Repair Planner, not only generation quality.

---

# 8. Sequence-Level Effects

For repairs changing accepted end state:

```text
revalidate dependent continuation shots
```

Measure:
```text
descendant invalidation count
descendant rework cost
```

A cheap current-shot fix that forces expensive downstream rework may not be globally optimal.

---

# 9. Fairness of Comparison

Same:
- story/beat facts;
- canonical refs;
- state authority;
- provider/model unless provider switch is the tested repair;
- budget/quality tier.

Record every intentional difference.

---

# 10. Gate

Targeted Repair is hardened only if evidence shows, at minimum:

```text
non-inferior acceptance rate
AND
lower regression and/or lower accepted-shot cost/latency
```

for meaningful defect classes.

Do not require Targeted Repair to beat full regeneration for every failure class; the routing policy may learn when full regeneration/replanning is the better action.
