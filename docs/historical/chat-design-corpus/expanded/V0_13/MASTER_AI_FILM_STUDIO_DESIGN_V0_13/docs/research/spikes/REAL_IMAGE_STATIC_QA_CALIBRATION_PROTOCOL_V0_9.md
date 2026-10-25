# REAL_IMAGE_STATIC_QA_CALIBRATION_PROTOCOL_V0_9.md
# Real-Image Static QA Calibration Protocol

**Status:** READY FOR EXECUTION  
**Purpose:** measure actual reviewer/sensor quality on visual defects, not just policy logic.

---

# 1. Dataset Design

Minimum initial calibration set:

```text
240 images
```

Balanced:

```text
120 ACCEPTABLE
120 DEFECT
```

Defect classes:

```text
IDENTITY_WRONG_CHARACTER
IDENTITY_DRIFT
STATE_WARDROBE_MISMATCH
STATE_PHYSICAL_MISMATCH
PROP_MISSING_CRITICAL
PROP_WRONG_IDENTITY
LOCATION_MISMATCH
SPATIAL_CONTINUITY_FAIL
SCREEN_DIRECTION_FAIL
CAMERA_SHOT_SIZE_FAIL
CAMERA_ANGLE_FAIL
LIGHTING_CONTINUITY_FAIL
STYLE_DRIFT
PARENT_CONDITIONING_DRIFT
NARRATIVE_INTENT_FAIL
```

Each class needs:
- obvious failures;
- near-miss failures;
- hard negatives that look superficially correct.

---

# 2. Source Strategy

Use a mixture:

```text
A. real provider generations
B. deliberately regenerated variants with one changed constraint
C. accepted outputs from production tests
D. curated failure examples
```

Do not rely only on synthetic Photoshop-like edits if the target failure emerges from generative-model behavior.

---

# 3. Ground Truth

Every image is independently labeled by at least two reviewers.

Fields:

```text
fixture_id
shot_spec_version
reference_ids
state_snapshot
artifact_id
defect_codes[]
severity
confidence
evidence_regions[]
notes
reviewer_id
```

Disagreement:
```text
reviewer A
≠
reviewer B
→ adjudication
```

Store both original labels and adjudicated result.

---

# 4. Blind Evaluation

Automated reviewer does not receive:
- human label;
- expected pass/fail;
- prior reviewer conclusion;
- repair result.

It receives only:
- artifact;
- canonical references;
- ShotSpec/ShotIR expectations;
- state;
- parent/adjacent context needed by the dimension.

---

# 5. Dimension-Isolated Passes

Run separately:

```text
Identity Reviewer
State/Prop Reviewer
Camera/Composition Reviewer
Continuity Reviewer
Narrative Intent Reviewer
```

Then run the fused acceptance policy.

This allows measurement of:
- sensor quality;
- fusion/policy quality.

---

# 6. Metrics

Per defect class:

```text
TP
FP
TN
FN
precision
recall
specificity
F1
blocking false-negative rate
```

Overall:
```text
macro F1
weighted F1
human disagreement
review latency
review cost
```

Primary safety metric:

```text
BLOCKING FALSE-NEGATIVE RATE
```

---

# 7. Candidate Acceptance Targets

These are **design targets**, not achieved results.

For BLOCKING defect classes:

```text
recall >= 0.95
blocking false-negative rate <= 0.05
```

For HIGH defect classes:

```text
recall >= 0.90
```

False positives should be tracked because excessive rejection increases generation cost, but they do not justify lowering blocking recall blindly.

---

# 8. Calibration Split

```text
60% calibration/development
20% validation
20% locked holdout
```

Do not repeatedly tune against the holdout.

Version:
```text
dataset_version
reviewer_model/version
prompt_contract_version
policy_version
```

---

# 9. Provider / Style Stratification

Dataset must include:
- multiple providers/models;
- multiple visual styles;
- multiple skin tones/wardrobes/location types;
- single/multi-character shots;
- close/medium/wide;
- day/night/interior/exterior.

Do not infer universal QA quality from one genre/style.

---

# 10. Continuity Pairs

At least 25% of fixtures should be pair/sequence-based:

```text
parent accepted frame
+
candidate child frame
```

because continuity defects cannot be calibrated from isolated images alone.

---

# 11. Narrative Intent Fixtures

Use beat/shot pairs where:
- visually attractive frame is narratively wrong;
- reveal timing is wrong;
- reaction appears too early;
- audience attention lands on irrelevant object;
- relationship/power blocking contradicts intent.

This prevents QA from collapsing into aesthetic scoring.

---

# 12. Evidence Output

Each run produces:

```text
qa_calibration_report.json
confusion_matrix_by_defect.json
false_negative_gallery/
false_positive_gallery/
review_cost_latency.json
```

Every false negative is reviewed and assigned:
- sensor miss;
- contract ambiguity;
- ground-truth ambiguity;
- fusion/policy error.

---

# 13. Gate

Static QA cannot be marked hardened until:
- labeled dataset exists;
- holdout metrics are computed;
- blocking FN target is met or risk explicitly accepted;
- result is repeated after significant reviewer/model change.
