# STATIC_QA_ARCHITECTURE.md
# Static Image QA Architecture — Deep Dive V0.4

**Status:** REVIEWED CANDIDATE  
**Purpose:** determine whether a generated keyframe is safe to become an accepted visual anchor and continuity input.

---

# 1. Core Rule

A provider returning an image successfully means only:

```text
TECHNICAL GENERATION COMPLETED
```

It does **not** mean:

```text
SHOT ACCEPTED
```

Static QA protects downstream continuity from accepting a beautiful but semantically wrong frame.

---

# 2. QA Inputs

Static QA receives immutable IDs:

```text
artifact_id
shot_spec_version_id
shot_ir_version_id
start_state_snapshot_id
reference_bindings[]
parent_artifact_id?
provider_profile_version
```

The reviewer must inspect the actual generated image, not infer pass from prompt/provider status.

---

# 3. QA Sensors

Use multiple sensors with different responsibilities.

```text
A. Deterministic / Technical
B. Reference Similarity / CV Metrics
C. Semantic Vision Reviewer
D. Continuity Comparator
E. Narrative Intent Reviewer
```

No one sensor is trusted for all dimensions.

---

# 4. Dimensions

## Q1 — File / Technical Integrity

Checks:
- decodable file;
- correct media type;
- expected dimensions/aspect ratio;
- gross corruption;
- blank/near-empty image;
- extreme blur/noise;
- watermark/text when forbidden.

Owner: deterministic/technical.

## Q2 — Identity

Checks:
- correct character;
- face/body identity;
- number of subjects;
- no identity swap/merge;
- required distinguishing features.

Evidence:
- canonical identity refs;
- multi-view refs;
- semantic vision;
- optional embedding/reference similarity.

Severity:
`BLOCKING` when identity is story-critical.

## Q3 — State / Wardrobe

Checks:
- clothing variant;
- hair/makeup;
- injury/dirt/wetness;
- carried objects;
- scene-specific physical state.

Source of truth:
approved `StateSnapshot`.

## Q4 — Props / Production Assets

Checks:
- required prop present;
- owner/hand/contact correct;
- prop identity/version correct;
- no extra story-critical prop.

## Q5 — Environment / Location

Checks:
- correct location;
- persistent landmarks;
- geography/readability;
- required foreground/background;
- no contradictory environment state.

## Q6 — Action / Performance State

For a static keyframe:
- pose represents the intended instant;
- facial expression/performance readable;
- no impossible intermediate multi-action state;
- interaction/contact credible.

## Q7 — Camera / Composition

Checks:
- shot size;
- camera angle/height;
- viewpoint;
- framing;
- composition;
- screen direction when applicable;
- focal emphasis/information hierarchy.

## Q8 — Lighting / Style

Checks:
- motivated light logic;
- color/palette;
- visual DNA;
- material response;
- realism/style consistency;
- no waxy/plastic drift where prohibited.

## Q9 — Continuity

Compare against:
- canonical refs;
- approved parent frame;
- approved start state;
- spatial baseline;
- adjacent accepted shots where relevant.

Check:
- identity;
- wardrobe;
- props;
- location;
- screen direction;
- light source logic;
- story time/weather;
- damage/wear.

## Q10 — Narrative Intent

Question:
> Does this frame visually perform the job the shot exists to do?

Examples:
- intended reveal is readable;
- viewer attention lands on correct information;
- reaction is not prematurely exposed;
- power/relationship staging matches directing decision.

Narrative intent is not reduced to aesthetic preference.

---

# 5. Verdict Model

Every dimension returns:

```text
PASS
WARN
FAIL
NOT_APPLICABLE
NOT_EVALUATED
```

with:

```text
severity
confidence
evidence
reason_code
```

Severity:

```text
BLOCKING
HIGH
MEDIUM
LOW
COSMETIC
```

---

# 6. Overall Acceptance Policy

Hard rule:

```text
any BLOCKING FAIL
→ overall FAIL
```

No weighted average can hide a blocking failure.

Candidate policy:

```text
BLOCKING fail                 → FAIL
2+ HIGH fails                 → FAIL
1 HIGH fail                   → FAIL or REVIEW based on dimension policy
MEDIUM-only failures          → REVIEW / conditional repair
LOW/COSMETIC only             → PASS_WITH_WARNINGS possible
```

Threshold policy is versioned and project/profile dependent.

---

# 7. Metric Layer

Possible machine metrics:

```text
prompt/text-image alignment
reference/subject similarity
object presence/count
sharpness
noise/artifact indicators
composition signals
```

Metrics are sensors, not final truth.

Do not claim:

```text
higher aesthetic score = better cinematic shot
```

A semantically wrong but attractive image must fail.

---

# 8. Reviewer Independence

For high-risk dimensions, avoid one monolithic reviewer prompt that sees all previous conclusions.

Preferred:

```text
Identity/State Reviewer
Camera/Composition Reviewer
Continuity Reviewer
Narrative Intent Reviewer
```

or one model invoked with isolated dimension-specific contracts.

This reduces cross-dimension anchoring.

---

# 9. Evidence Binding

Each finding stores observable evidence:

```text
region/bbox when available
reference asset IDs
parent artifact ID
state fields compared
short explanation
metric values
reviewer version
```

Do not store opaque “looks wrong” alone.

---

# 10. QA Expectations from ShotIR

ShotIR compiles explicit expectations:

```json
{
  "must_have": [],
  "must_not_have": [],
  "identity_targets": [],
  "state_targets": {},
  "camera_targets": {},
  "continuity_targets": {},
  "narrative_intent": {}
}
```

QA should evaluate those expectations rather than reconstructing the whole shot from free-form prompt text.

---

# 11. Static QA State Machine

```text
ARTIFACT_READY
↓
PENDING_QA
↓
QA_RUNNING
├── QA_ERROR → reviewer retry/fallback
├── QA_FAILED → REPAIR_PENDING
├── NEEDS_HUMAN_REVIEW
└── QA_PASSED
      ↓
   APPROVED
      ↓
   eligible continuity anchor
```

Only `APPROVED`/`LOCKED` artifacts can become default parent conditioning.

---

# 12. Human Review

Human review is required/available when:
- reviewer confidence low;
- semantic sensors disagree;
- policy marks creative decision subjective;
- repair cost is high;
- the shot is a designated hero/canon shot.

Human override is logged with reason and reviewer identity.

---

# 13. Calibration Dataset

Before production claim, build labeled static QA fixtures containing:

```text
same identity / wrong identity
correct / wrong wardrobe
correct / wrong prop
correct / wrong location
screen direction pass/fail
camera size pass/fail
lighting continuity pass/fail
narrative reveal pass/fail
subtle vs severe defects
```

Need positives and adversarial near-misses.

---

# 14. QA Benchmark Metrics

Measure QA itself:

```text
precision/recall per defect class
blocking false-negative rate
false-positive rate
human disagreement rate
review latency
review cost
```

The most dangerous metric is `BLOCKING false-negative rate`.

---

# 15. Static QA Freeze Gates

Before L7:
- dimension contracts frozen;
- severity policy versioned;
- QAResult schema frozen;
- labeled calibration set defined;
- at least one semantic reviewer spike completed;
- blocking defects cannot be averaged away;
- accepted artifact propagation tested.
