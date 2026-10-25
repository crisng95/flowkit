# TARGETED_REPAIR_ARCHITECTURE.md
# Targeted Repair Architecture — Deep Dive V0.4

**Status:** REVIEWED CANDIDATE

---

# 1. Purpose

Repair the earliest responsible decision while preserving accepted decisions that remain valid.

The system must not respond to every creative defect with:

```text
rewrite prompt
→ regenerate everything
```

---

# 2. Repair Inputs

```text
failed_artifact
QAResult[]
active ShotSpec version
ShotIR version
state snapshot
reference versions
parent artifact
repair history
provider capability profile
```

---

# 3. Responsibility Map

| Failure | Earliest owner |
|---|---|
| WRONG_CHARACTER | Entity/Reference/L1 |
| IDENTITY_DRIFT | Reference Resolver / L1 |
| WRONG_WARDROBE | State Engine / L2 |
| WRONG_PROP | State + L2 |
| ACTION_MISMATCH | L3 / Directing / Motion compiler |
| PERFORMANCE_MISMATCH | L3 / Directing |
| LOCATION_MISMATCH | L4 / Reference Resolver |
| SPATIAL_CONTINUITY | L4 + L8 |
| SCREEN_DIRECTION | L6 + L8 |
| SHOT_SIZE/ANGLE | L6 |
| CAMERA_MOVE | L6 / Motion compiler |
| LIGHTING | L7 |
| STYLE_DRIFT | L7 / Visual DNA |
| PARENT_DRIFT | L8 / conditioning strategy |
| REFERENCE_LIMIT | Provider Router |
| UNSUPPORTED_MODE | Provider Capability |
| NARRATIVE_INTENT | Directing/Cinematography |
| BEAT_UNEXECUTABLE | Beat/Story escalation |

---

# 4. Repair Modes

## PATCH_IN_PLACE

Use when:
- upstream story/state is correct;
- failure is isolated;
- provider supports re-generation/edit without losing required anchors.

Example:
camera framing incorrect.

## REGENERATE_FROM_ANCHOR

Use when:
- parent visual is contaminated;
- chain drift accumulated;
- stronger canonical reference re-anchor is required.

Input:
```text
canonical refs
+ approved semantic state
+ earlier trusted anchor
+ current shot delta
```

## REPLAN_SHOT

Use when:
- chosen shot grammar is not executable;
- action/camera plan consistently fails;
- provider capability makes original visual plan impractical.

Preserve:
```text
Beat purpose
story facts
character objective
state
```

Recompute:
```text
cinematography decision
ShotSpec L6 and dependent fields
```

## ESCALATE_UPSTREAM

Use only when defect reveals the upstream plan itself is invalid.

Examples:
- impossible action timing;
- contradictory story state;
- beat cannot fit duration;
- required interaction cannot be represented with current asset/state plan.

---

# 5. Preserve Set

RepairPlan must explicitly name what cannot change.

Example:

```json
{
  "preserve": [
    "L1_SUBJECT",
    "L2_STATE",
    "L3_ACTION",
    "L4_ENVIRONMENT",
    "L5_TIME",
    "L7_STYLE",
    "L8_CONTINUITY_FACTS"
  ]
}
```

Compiler verifies repaired output remains bound to preserved versions.

---

# 6. Patch Representation

Patch at semantic field level:

```json
{
  "field": "L6_camera.shot_size",
  "old": "MEDIUM",
  "new": "CLOSE_UP",
  "reason": "reaction must become readable after recognition beat"
}
```

Do not make the repair engine's canonical output a raw appended prompt suffix.

---

# 7. Invalidation

Repair planner computes:

```text
changed semantic fields
↓
derived compiled requests
↓
candidate artifacts
↓
dependent child shots if conditioning/state changed
```

Examples:

### Camera-only patch
May invalidate:
- current static;
- current video.

Usually does not invalidate:
- entity refs;
- prior shots;
- unrelated branches.

### Accepted end-state change
May invalidate:
- dependent continuation shots;
- derived state snapshots;
- downstream motion/static artifacts.

---

# 8. Recheck Scope

Repair does not automatically re-run every expensive reviewer.

But any changed output must still pass all **safety-critical dependent dimensions**.

Example L6 camera patch:

```text
required:
CAMERA
COMPOSITION
CONTINUITY
NARRATIVE_INTENT

also lightweight regression:
IDENTITY
STATE
PROP
```

Because generative models can alter supposedly preserved fields.

---

# 9. Repair Attempts

Track:

```text
repair_attempt
same_failure_count
new_failure_count
repair_mode
provider/model
cost
```

Escalation candidate:

```text
same BLOCKING defect twice
→ stronger re-anchor or replan

3 unsuccessful creative repairs
→ NEEDS_REVIEW / alternative provider
```

Exact limits are policy-configurable.

No infinite loop.

---

# 10. Regression Detection

A repair can fix one dimension and break another.

Compare:

```text
QA_before
vs
QA_after
```

Classify:

```text
FIXED
UNCHANGED
REGRESSED
NEW_FAILURE
```

Repair success means:
- target failure fixed;
- no new blocking/high regression;
- required state/continuity remains valid.

---

# 11. Provider Switch

Provider switch is not the first repair step unless:
- capability mismatch;
- repeated provider-specific failure;
- project policy allows provider change;
- visual continuity impact is acceptable.

Switch must preserve ShotIR semantics and record new provider profile/version.

---

# 12. Cost-Aware Repair

Repair planner may compare:

```text
edit/retry cost
regenerate-from-anchor cost
alternate provider cost
human review cost
```

But cost does not override blocking correctness.

---

# 13. Repair Learning

Store aggregate repair outcomes:

```text
failure code
provider/model
repair mode
fields patched
success/failure
cost
latency
```

This may inform future policy.

Do not silently train/alter canonical behavior without versioned policy changes.

---

# 14. Repair Benchmark

Create adversarial set:

```text
identity drift
wardrobe drift
wrong prop
wrong location
wrong camera
wrong screen direction
wrong lighting
parent drift
action mismatch
narrative intent mismatch
```

Measure:

```text
target defect resolution rate
regression rate
average attempts
cost saved vs full regeneration
time saved
```

Targeted repair is not declared successful until it beats naive full-regenerate baseline on accepted-shot cost and/or preserves more correct dimensions.


# V0.7 Planner Spike Result

A deterministic planner spike executed 180 cases across nine failure categories and found zero preserve/owner invariants violated.

The synthetic invalidation model reduced average logical work scope by approximately 48% relative to rebuilding shot + descendants every time.

Important:

```text
planner correctness
≠
root-cause correctness
≠
generation repair success
```

In production:
- defect classification is evidence;
- responsible owner is a diagnosis;
- preserve fields are verification obligations;
- model output must be regression-checked.
