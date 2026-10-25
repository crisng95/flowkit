# NARRATIVE EXPANSION LADDER PATCH V1 — FINAL DESIGN PATCH

**Project:** Enterprise AI-Native Film Studio  
**Patch scope:** IDEA → LOGLINE → MACRO BEAT SHEET → SEQUENCE PLAN → SCENE LIST → SCENE BREAKDOWN → MICRO BEATS → SCREENPLAY REALIZATION → SCRIPT LOCK → DIRECTING → CINEMATOGRAPHY → SHOT EXPANSION → SHOT LIST  
**Status:** DESIGN PATCH — READY TO MERGE INTO FINAL DESIGN CONSOLIDATION  
**Purpose:** Vá khoảng trống giữa Story Intelligence và Shot Production bằng một chuỗi mở rộng narrative có contract, budget, state transition, traceability và QA gate rõ ràng.  
**Important:** Đây là patch design độc lập, chưa phải bản master hợp nhất cuối. Sau khi các phần phân tích khác hoàn tất, patch này phải được merge vào authority cuối.

---

# 0. PATCH SUMMARY

Kiến trúc Story hiện tại đã có:

```text
Idea / Topic
Premise
Angle
Theme
Research
Character
Conflict / Stakes
StoryGraph
Structure
Emotion
Sequence
Scene
Beat
Dialogue
Critique
Repair
Script Lock
Directing
Cinematography
Shot
```

Nhưng còn thiếu một chuỗi canonical expansion được khóa thành first-class artifacts:

```text
IDEA
→ LOGLINE
→ MACRO BEAT SHEET
→ SEQUENCE PLAN
→ SCENE LIST
→ SCENE BREAKDOWN
→ MICRO BEATS
→ SCREENPLAY REALIZATION
→ SCRIPT LOCK
→ DIRECTING UNITS
→ SHOT EXPANSION
→ SHOT LIST
```

Patch này bổ sung chính xác khoảng trống đó.

---

# 1. CORE DESIGN PRINCIPLE

Không cho phép nhảy từ:

```text
IDEA → SCREENPLAY
```

hoặc:

```text
SEQUENCE → SHOT LIST
```

mà không có artifact trung gian đủ mạnh.

Canonical principle:

```text
EVERY EXPANSION STEP
MUST PRODUCE
AN EXPLICIT VERSIONED ARTIFACT
WITH:
- parent reference
- child references
- dramatic function
- state before
- state after
- duration budget
- QA status
- provenance
```

---

# 2. CANONICAL NARRATIVE EXPANSION LADDER

```text
IDEA
│
▼
IDEA CONTRACT
│
▼
LOGLINE
│
▼
LOGLINE GATE
│
▼
PREMISE / ANGLE / THEME
│
▼
STORY CORE LOCK
│
▼
MACRO BEAT SHEET
│
▼
MACRO STRUCTURE GATE
│
▼
SEQUENCE PLAN
│
▼
SEQUENCE CAUSALITY GATE
│
▼
SCENE LIST
│
▼
SCENE FUNCTION GATE
│
▼
SCENE BREAKDOWN
│
▼
MICRO BEATS
│
▼
BEAT MOVEMENT GATE
│
▼
SCREENPLAY REALIZATION
│
▼
SCRIPT DRAFT
│
▼
INDEPENDENT CRITIQUE
│
▼
TARGETED STORY REPAIR
│
▼
STORY QUALITY GATE
│
▼
SCRIPT LOCK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIRECTING / PRE-PRODUCTION BOUNDARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│
▼
DIRECTING PLAN
│
▼
CINEMATOGRAPHY PLAN
│
▼
SHOT EXPANSION
│
▼
SHOT LIST
│
▼
SHOT COVERAGE GATE
│
▼
8-LAYER SHOT SPEC
│
▼
STATIC KEYFRAME SPEC + MOTION DELTA SPEC
```

---

# 3. FIXED COUNTS ARE PROFILES, NOT UNIVERSAL RULES

Các con số như:

```text
15 macro beats
8 sequences
40–60 scenes
3–5 micro beats/scene
500–1500 shots
```

không được hard-code cho mọi project.

Chúng phải đi qua:

```text
STRUCTURE PROFILE
+
FORMAT PROFILE
+
DURATION PROFILE
+
NICHE PROFILE
+
PACING PROFILE
+
EDITING PROFILE
```

Ví dụ minh họa:

```text
90-minute feature
→ 15 macro beats / 8 sequences / 45–80 scenes / 700–1400 shots

10-minute cinematic short
→ 5–9 macro beats / 3–5 sequences / 10–22 scenes / 90–220 shots

12-minute documentary
→ question-driven macro units / 4–8 sequences / 12–28 scenes / 100–250 shots
```

Rule:

```text
COUNTS ARE BUDGET TARGETS,
NOT ARTIFICIAL STORY REQUIREMENTS.
```

---

# 4. ARTIFACT HIERARCHY

```text
Project
│
├── IdeaContract
├── LoglineContract
├── StoryCoreLock
├── MacroBeatSheet
│   └── MacroBeat[]
├── SequencePlan
│   └── SequenceContract[]
├── SceneListManifest
│   └── SceneListItem[]
├── SceneBreakdownManifest[]
│   └── MicroBeat[]
├── ScreenplayDraft[]
├── ScriptLockManifest
├── DirectingPlan
├── CinematographyPlan
├── ShotListManifest
│   └── ShotPlan[]
└── ShotSpecs[]
```

---

# 5. IDEA CONTRACT

```yaml
IdeaContract:
  idea_id: string
  project_id: string
  version: string
  one_sentence: string
  subject:
    focal_subject: string | null
    secondary_subjects: []
  situation:
    current_state: string
    disruption_hint: string | null
  latent_pressure:
    possible_conflict: string | null
    possible_stakes: string | null
  context:
    language: string
    locale: string | null
    era: string | null
  source:
    origin: USER | IMPORTED | GENERATED
    source_refs: []
  status: DRAFT | ACCEPTED | SUPERSEDED
```

Gate tối thiểu:

```text
[ ] one sentence usable
[ ] subject or central phenomenon identifiable
[ ] no contradiction with explicit project locks
```

---

# 6. LOGLINE CONTRACT

Canonical formula:

```text
WHO
+
WANTS WHAT
+
WHY NOW
+
WHAT STANDS IN THE WAY
+
WHAT HAPPENS IF THEY FAIL
+
WHAT MAKES THIS STORY DISTINCT
```

```yaml
LoglineContract:
  logline_id: string
  idea_id: string
  version: string
  protagonist_or_focal_subject: string
  inciting_situation: string
  conscious_goal: string | null
  central_opposition: string
  stakes: string
  urgency_or_why_now: string | null
  contradiction_or_irony: string | null
  transformation_potential: string | null
  central_question: string | null
  final_logline: string
  provenance:
    generated_from: []
    brain_profile_version: string
  qa:
    status: PASS | WARN | FAIL
    findings: []
```

Blocking defects:

```text
LOGLINE_NO_FOCAL_SUBJECT
LOGLINE_NO_GOAL_OR_CENTRAL_QUESTION
LOGLINE_NO_OPPOSITION
LOGLINE_NO_STAKES
LOGLINE_GENERIC
LOGLINE_CONTRADICTS_TOPIC
```

Rule:

```text
DO NOT EXPAND TO MACRO STRUCTURE
IF THE LOGLINE DOES NOT CONTAIN
A VIABLE STORY ENGINE.
```

---

# 7. STORY CORE LOCK

Trước Macro Beat Sheet cần lightweight lock:

```text
LOGLINE
+
PREMISE
+
ANGLE
+
THEME HYPOTHESIS
+
CORE CHARACTER GOAL / QUESTION
+
CORE CONFLICT
+
CORE STAKES
```

```yaml
StoryCoreLock:
  story_core_id: string
  logline_version: string
  premise_version: string
  angle_version: string
  theme_version: string
  protagonist_goal: string | null
  central_conflict: string
  primary_stakes: string
  central_question: string
  status: FROZEN_FOR_STRUCTURE
```

---

# 8. STRUCTURE PROFILE

Không hard-code 15 beat / 8 sequence.

```yaml
StructureProfile:
  profile_id: string
  name: string
  macro_model:
    type: SCREENPLAY_15_BEAT | THREE_ACT | FIVE_ACT | EIGHT_SEQUENCE |
          INVESTIGATIVE | MYSTERY_REVEAL | ESSAY_DOCUMENTARY |
          QUESTION_ANSWER | CUSTOM
  macro_beat_target:
    min: number
    preferred: number
    max: number
  sequence_target:
    min: number
    preferred: number
    max: number
  scene_target:
    min: number
    preferred: number
    max: number
  micro_beats_per_scene:
    min: number
    preferred: number
    max: number
  narrative_constraints: []
  genre_constraints: []
```

---

# 9. MACRO BEAT SHEET

Macro Beat Sheet là bản đồ state transition lớn của toàn bộ story.

```yaml
MacroBeatSheet:
  beat_sheet_id: string
  story_core_id: string
  structure_profile_id: string
  version: string
  beats: []
  runtime_budget_seconds: number
  status: DRAFT | REVIEWED | APPROVED
```

```yaml
MacroBeat:
  macro_beat_id: string
  ordinal: number
  dramatic_function: string
  narrative_question: string | null
  protagonist_state_before: {}
  event: string
  decision_or_turn: string
  consequence: string
  information_change: []
  relationship_change: []
  power_change: []
  emotional_change: []
  stakes_change: []
  setup_ids: []
  payoff_ids: []
  state_after: {}
  estimated_start_pct: number | null
  estimated_end_pct: number | null
  duration_budget_seconds: number | null
  dependencies: []
```

Gate:

```text
MACRO_BEAT_NO_FUNCTION
MACRO_BEAT_NO_STATE_CHANGE
MACRO_BEAT_CAUSAL_GAP
MACRO_BEAT_NO_ESCALATION
MACRO_BEAT_BREAKS_CHARACTER_MOTIVATION
MACRO_BEAT_PAYOFF_WITHOUT_SETUP
```

---

# 10. EIGHT-SEQUENCE PROFILE

Eight Sequence là một selectable structure profile, không phải universal rule.

```yaml
EightSequenceProfile:
  sequence_count: 8
  mapping:
    - sequence: 1
      function: SETUP_AND_DISRUPTION
    - sequence: 2
      function: RESISTANCE_AND_COMMITMENT
    - sequence: 3
      function: EARLY_PROGRESS
    - sequence: 4
      function: COMPLICATION_TO_MIDPOINT
    - sequence: 5
      function: REORIENTATION
    - sequence: 6
      function: ESCALATION_AND_LOSS
    - sequence: 7
      function: CRISIS_AND_FINAL_CHOICE
    - sequence: 8
      function: CLIMAX_AND_CONSEQUENCE
```

---

# 11. SEQUENCE PLAN

```yaml
SequencePlan:
  sequence_plan_id: string
  beat_sheet_id: string
  version: string
  sequences: []
  target_count: number
  runtime_budget_seconds: number
  status: DRAFT | REVIEWED | APPROVED
```

```yaml
SequenceContract:
  sequence_id: string
  ordinal: number
  macro_beat_refs: []
  purpose: string
  opening_state: {}
  objective: string
  opposition: string
  escalation_pattern: string
  major_turn: string
  closing_state: {}
  emotional_target: string
  information_delta: []
  relationship_delta: []
  stakes_delta: []
  setup_obligations: []
  payoff_obligations: []
  estimated_duration_seconds: number
  scene_budget:
    min: number
    preferred: number
    max: number
```

Sequence Causality Gate:

```text
[ ] opening state matches previous sequence end
[ ] sequence has purpose
[ ] escalation exists
[ ] major turn exists
[ ] closing state changes
[ ] next sequence is causally enabled
[ ] setup/payoff obligations preserved
```

---

# 12. DURATION BUDGET ENGINE

Input:

```text
target_runtime
format
genre
platform
pacing profile
dialogue density
action density
```

Output:

```yaml
DurationBudget:
  total_seconds: number
  macro_beats: {}
  sequences: {}
  scenes: {}
  micro_beats: {}
  shot_budget: {}
```

Invariant:

```text
SUM(child budgets)
≈
parent budget
within configured tolerance
```

---

# 13. SCENE BUDGET ENGINE

Estimate scene count from:

```text
runtime
sequence count
average scene duration
genre
format
pacing
dialogue density
```

```yaml
SceneBudget:
  total_scene_target:
    min: number
    preferred: number
    max: number
  per_sequence: {}
  average_scene_seconds:
    min: number
    preferred: number
    max: number
  rationale: string
```

---

# 14. SCENE LIST MANIFEST

```yaml
SceneListManifest:
  scene_list_id: string
  sequence_plan_id: string
  version: string
  scenes: []
  duration_budget_seconds: number
  status: DRAFT | REVIEWED | APPROVED
```

```yaml
SceneListItem:
  scene_id: string
  ordinal: number
  sequence_id: string
  slugline_hint:
    location: string
    interior_exterior: INT | EXT | MIXED
    time_of_day: string
  participants: []
  narrative_function: string
  focal_character: string | null
  scene_objective: string
  opposition: string
  conflict: string
  stakes: string
  expected_turn: string
  primary_state_change_dimension: string
  information_change: []
  relationship_change: []
  emotional_change: []
  power_change: []
  risk_change: []
  setup_refs: []
  payoff_refs: []
  estimated_duration_seconds: number
```

---

# 15. SCENE FUNCTION GATE

Blocking:

```text
SCENE_NO_FUNCTION
SCENE_NO_CONFLICT
SCENE_NO_TURN
SCENE_NO_STATE_CHANGE
SCENE_DUPLICATES_PREVIOUS_FUNCTION
SCENE_NOT_CAUSALLY_CONNECTED
SCENE_BREAKS_TIMELINE
SCENE_BREAKS_KNOWLEDGE_STATE
```

Exception:

```text
DELIBERATE_STATIC_SCENE
```

must include explicit artistic reason.

---

# 16. SCENE BREAKDOWN MANIFEST

```yaml
SceneBreakdownManifest:
  breakdown_id: string
  scene_id: string
  version: string
  opening_state: {}
  closing_state: {}
  micro_beats: []
  duration_budget_seconds: number
  status: DRAFT | REVIEWED | APPROVED
```

---

# 17. MICRO BEAT CONTRACT

Canonical pattern:

```text
INTENTION
→ ACTION / TACTIC
→ REACTION
→ RESISTANCE / NEW INFORMATION
→ MICRO-CHANGE
```

```yaml
MicroBeat:
  micro_beat_id: string
  scene_id: string
  ordinal: number
  acting_character_ids: []
  focal_character_id: string | null
  intention: string
  tactic: string
  action: string
  reaction: string
  resistance_or_new_information: string
  knowledge_delta: []
  emotional_delta: []
  relationship_delta: []
  power_delta: []
  micro_turn: string
  resulting_state: {}
  setup_refs: []
  payoff_refs: []
  estimated_duration_seconds: number
```

---

# 18. MICRO BEAT BUDGET

Typical target may be 3–5 micro beats/scene, nhưng profile có thể khác:

```text
quiet dialogue scene: 3–8
action scene: 5–20
montage: variable
one-beat visual scene: 1–3
```

Rule:

```text
MICRO BEAT COUNT FOLLOWS DRAMATIC MOVEMENT,
NOT AN ARBITRARY FIXED NUMBER.
```

---

# 19. BEAT MOVEMENT GATE

```text
MICRO_BEAT_NO_INTENTION
MICRO_BEAT_NO_ACTION
MICRO_BEAT_NO_REACTION
MICRO_BEAT_NO_CHANGE
MICRO_BEAT_REPEATS_PREVIOUS
MICRO_BEAT_CAUSAL_GAP
MICRO_BEAT_CHARACTER_LOGIC_BREAK
```

---

# 20. SCREENPLAY REALIZATION STAGE

Stage này phải trở thành explicit.

Input:

```text
SceneContract
+
SceneBreakdown
+
MicroBeats
+
Character Voice
+
Knowledge State
+
Dialogue Intent
+
Subtext Policy
+
Active Production Profile
```

Output:

```text
Screenplay Scene Draft
```

---

# 21. SCREENPLAY SCENE CONTRACT

```yaml
ScreenplayScene:
  screenplay_scene_id: string
  scene_id: string
  version: string
  slugline: string
  action_blocks: []
  dialogue_blocks: []
  transitions: []
  micro_beat_bindings: []
  setup_payoff_bindings: []
  source_breakdown_version: string
  character_state_versions: {}
  active_profile_version: string
  qa_status: PASS | WARN | FAIL
```

---

# 22. DIALOGUE INTENT CONTRACT

```yaml
DialogueIntent:
  dialogue_intent_id: string
  scene_id: string
  speaker_id: string
  surface_goal: string
  hidden_intent: string
  desired_outcome: string
  avoidance: string | null
  tactic: string
  emotional_pressure: string
  relationship_pressure: string
  knowledge_constraints: []
  forbidden_disclosures: []
  voice_register: string
  subtext_target: string
  expected_listener_effect: string
```

---

# 23. SCREENPLAY REALIZATION RULES

May:

```text
choose wording
choose action-description phrasing
realize dialogue
add non-canonical texture
```

May not, without upstream repair:

```text
alter locked premise
alter character core motivation
invent contradictory knowledge
bypass setup/payoff
change scene outcome
```

---

# 24. SCREENPLAY ASSEMBLY

```text
Scene Drafts
↓
Sequence Assembly
↓
Full Draft Assembly
↓
Cross-Scene Continuity Pass
↓
Story Critique Council
↓
Targeted Repair
↓
Full Draft Re-assembly
```

---

# 25. FULL-DRAFT CRITIQUE

Critique Council phải kiểm tra:

```text
Premise
Angle
Theme
Research/Factuality
Character
Motivation
Conflict/Stakes
Causality
Structure
Emotional Arc
Emotional Rhythm
Scene Movement
Beat Movement
Dialogue/Subtext
Pacing
Setup/Payoff
Continuity
Audience Experience
```

---

# 26. TARGETED STORY REPAIR

```text
PATCH_DIALOGUE
PATCH_ACTION_LINE
REWRITE_MICRO_BEAT
REWRITE_SCENE
REPLAN_SEQUENCE
REPLAN_STRUCTURE
REWORK_CHARACTER
RESEARCH_MORE
REOPEN_PREMISE
```

Invariant:

```text
REPAIR THE EARLIEST RESPONSIBLE LAYER.
```

---

# 27. SCRIPT LOCK

```yaml
ScriptLockManifest:
  script_lock_id: string
  project_id: string
  version: string
  screenplay_hash: string
  story_core_version: string
  macro_beat_sheet_version: string
  sequence_plan_version: string
  scene_list_version: string
  scene_breakdown_versions: []
  character_state_versions: []
  setup_payoff_snapshot_version: string
  timeline_snapshot_version: string
  active_profile_version: string
  unresolved_blocking_findings: 0
  locked_at: string
  approver: string
```

---

# 28. HARD BOUNDARY: STORY VS PRE-PRODUCTION

```text
STORY DEPARTMENT
IDEA → SCRIPT LOCK

PRE-PRODUCTION
SCRIPT LOCK → DIRECTING → CINEMATOGRAPHY → SHOT LIST
```

Không generate final Shot List trước Script Lock, trừ exploratory mode được đánh dấu rõ.

---

# 29. DIRECTING PLAN

```yaml
DirectingPlan:
  plan_id: string
  script_lock_id: string
  version: string
  scene_directing_units: []
```

---

# 30. DIRECTING UNIT

```yaml
DirectingUnit:
  directing_unit_id: string
  scene_id: string
  micro_beat_refs: []
  narrative_function: string
  audience_experience_target: string
  information_strategy: string
  performance_intent: string
  blocking_intent: string
  dramatic_emphasis: string
  reveal_withhold_strategy: string
  rhythm_intent: string
  transition_intent: string
```

---

# 31. CINEMATOGRAPHY PLAN

```yaml
CinematographyPlan:
  plan_id: string
  directing_plan_id: string
  version: string
  scene_camera_strategies: []
```

---

# 32. SCENE CAMERA STRATEGY

```yaml
SceneCameraStrategy:
  scene_id: string
  visual_objective: string
  point_of_view_strategy: string
  coverage_strategy: string
  framing_strategy: string
  lens_strategy: string
  movement_strategy: string
  focus_strategy: string
  composition_strategy: string
  lighting_strategy: string
  color_strategy: string
  continuity_requirements: []
```

---

# 33. SHOT EXPANSION ENGINE

Input:

```text
Script Lock
+
Micro Beats
+
Directing Units
+
Cinematography Strategy
+
Coverage Profile
+
Runtime Budget
```

Output:

```text
Shot List Manifest
```

Rule:

```text
MICRO BEAT
→ ONE OR MORE SHOTS
```

not:

```text
SCENE
→ RANDOM NUMBER OF SHOTS
```

---

# 34. SHOT BUDGET ENGINE

Inputs:

```text
runtime_seconds
average_shot_length_target
genre
editing rhythm
scene density
action density
coverage strategy
platform
```

Baseline estimator:

```text
estimated_shots
≈
runtime_seconds
/
average_shot_length_seconds
```

Then adjust by:

```text
coverage multiplier
action multiplier
dialogue multiplier
montage multiplier
platform multiplier
```

---

# 35. SHOT BUDGET CONTRACT

```yaml
ShotBudget:
  total_target:
    min: number
    preferred: number
    max: number
  average_shot_length_seconds:
    min: number
    preferred: number
    max: number
  per_sequence: {}
  per_scene: {}
  coverage_profile: string
  rationale: string
```

---

# 36. SHOT LIST MANIFEST

```yaml
ShotListManifest:
  shot_list_id: string
  script_lock_id: string
  directing_plan_id: string
  cinematography_plan_id: string
  version: string
  shots: []
  target_shot_count: number
  estimated_runtime_seconds: number
  status: DRAFT | REVIEWED | APPROVED
```

---

# 37. SHOT PLAN CONTRACT

```yaml
ShotPlan:
  shot_id: string
  ordinal: number
  sequence_id: string
  scene_id: string
  micro_beat_refs: []
  directing_unit_id: string
  shot_function: string
  subject_ids: []
  action_summary: string
  performance_intent: string
  framing: string
  camera_position: string
  lens_intent: string
  camera_movement: string
  focus_intent: string
  lighting_intent: string
  composition_intent: string
  estimated_duration_seconds: number
  continuity_constraints: []
  must_preserve: []
  must_change: []
```

---

# 38. SHOT COVERAGE GATE

```text
SHOT_NO_NARRATIVE_FUNCTION
SHOT_NOT_BOUND_TO_BEAT
SHOT_DUPLICATE_WITHOUT_PURPOSE
SHOT_MISSING_REQUIRED_COVERAGE
SHOT_BREAKS_SCREEN_DIRECTION
SHOT_BREAKS_STATE
SHOT_BREAKS_CHARACTER_POSITION
SHOT_DURATION_BUDGET_INVALID
SHOT_COUNT_OUTSIDE_PROFILE_WITHOUT_REASON
```

---

# 39. 8-LAYER SHOT SPEC HANDOFF

Only after ShotPlan passes coverage gate:

```text
ShotPlan
↓
8-Layer ShotSpec
```

Mapping:

```text
L1 Subject
L2 State / Wardrobe
L3 Action / Performance
L4 Environment
L5 Time / Atmosphere
L6 Camera
L7 Lighting / Style
L8 Continuity
```

---

# 40. STATIC + MOTION SPLIT

```text
1 SHOT
=
1 STATIC KEYFRAME SPEC
+
1 MOTION DELTA SPEC
```

Static captures observable keyframe state. Motion captures temporal delta from approved start/static state.

---

# 41. NARRATIVE TRACEABILITY

Every child artifact must trace upward.

```text
SHOT 0875
↓
MICRO BEAT MB-0204
↓
SCENE SC-047
↓
SEQUENCE SQ-06
↓
MACRO BEAT B-11
↓
STORY CORE
↓
LOGLINE
↓
IDEA
```

---

# 42. TRACE CONTRACT

```yaml
NarrativeTrace:
  artifact_id: string
  artifact_type: string
  parent_ids: []
  root_idea_id: string
  dramatic_purpose: string
  inherited_constraints: []
  local_changes: []
  source_versions: {}
```

---

# 43. BIDIRECTIONAL TRACE

Must support:

```text
TOP-DOWN:
Idea → Shots

BOTTOM-UP:
Shot → Why does this shot exist?
```

Every Shot should answer:

```text
Which micro beat?
Which scene function?
Which sequence objective?
Which macro beat?
Which logline promise?
```

---

# 44. INVALIDATION MODEL

If Logline changes:

```text
invalidate:
StoryCore
MacroBeats
Sequences
Scenes
MicroBeats
Screenplay
ScriptLock
Directing
Shots
```

If Dialogue wording changes only:

```text
invalidate:
affected screenplay scene
dialogue QA
possibly performance notes

do not automatically invalidate:
macro beats
sequence plan
scene list
```

---

# 45. INVALIDATION SCOPE CONTRACT

```yaml
InvalidationRecord:
  source_artifact_id: string
  source_version_old: string
  source_version_new: string
  reason: string
  directly_invalidated: []
  transitively_invalidated: []
  preserved: []
  approved_by: string
```

---

# 46. VERSIONING RULE

Every first-class artifact is immutable after approval.

Change creates:

```text
v1 → v2
```

Never silently mutate an approved artifact.

---

# 47. STATUS MODEL

```text
DRAFT
REVIEWED
APPROVED
LOCKED
SUPERSEDED
INVALIDATED
```

---

# 48. EXPANSION QUALITY PRINCIPLE

Every expansion should add:

```text
specificity
causality
state detail
dramatic movement
production detail
```

without changing upstream truth.

---

# 49. EXPANSION INVARIANT

```text
CHILDREN
MUST FULLY REALIZE
PARENT FUNCTION
WITHOUT CONTRADICTING
PARENT AUTHORITY.
```

---

# 50. COLLAPSE TEST

Validation by reverse compression:

```text
Micro Beats → summarize ≈ Scene Contract
Scenes → summarize ≈ Sequence Contract
Sequences → summarize ≈ Macro Beat Sheet
```

If not:

```text
EXPANSION DRIFT
```

---

# 51. EXPANSION DRIFT DEFECTS

```text
EXPANSION_LOGLINE_DRIFT
EXPANSION_MACRO_BEAT_DRIFT
EXPANSION_SEQUENCE_DRIFT
EXPANSION_SCENE_DRIFT
EXPANSION_MICRO_BEAT_DRIFT
EXPANSION_SCREENPLAY_DRIFT
EXPANSION_SHOT_DRIFT

BUDGET_RUNTIME_OVERFLOW
BUDGET_SCENE_OVERFLOW
BUDGET_SHOT_OVERFLOW

TRACE_ORPHAN_ARTIFACT
TRACE_MISSING_PARENT
TRACE_CYCLE
```

---

# 52. FORMAT PROFILE EXAMPLE — 90-MINUTE FEATURE

Illustrative only:

```yaml
Feature90Profile:
  runtime_minutes: 90
  macro_beats:
    preferred: 15
  sequences:
    preferred: 8
  scenes:
    min: 45
    preferred: 60
    max: 80
  micro_beats_per_scene:
    preferred: 4
  average_shot_length_seconds:
    preferred: 5
  shots:
    min: 700
    preferred: 1050
    max: 1400
```

---

# 53. FORMAT PROFILE EXAMPLE — 10-MINUTE CINEMATIC SHORT

```yaml
Short10Profile:
  runtime_minutes: 10
  macro_beats:
    min: 5
    preferred: 7
    max: 9
  sequences:
    min: 3
    preferred: 4
    max: 5
  scenes:
    min: 10
    preferred: 15
    max: 22
  micro_beats_per_scene:
    preferred: 4
  average_shot_length_seconds:
    preferred: 4
  shots:
    min: 90
    preferred: 150
    max: 220
```

---

# 54. FORMAT PROFILE EXAMPLE — 12-MINUTE DOCUMENTARY

```yaml
Documentary12Profile:
  runtime_minutes: 12
  structure_profile: QUESTION_DRIVEN
  macro_units:
    min: 6
    preferred: 8
    max: 12
  sequences:
    min: 4
    preferred: 6
    max: 8
  scenes:
    min: 12
    preferred: 18
    max: 28
  average_shot_length_seconds:
    preferred: 4.5
```

---

# 55. ACTIVE PRODUCTION PROFILE INTEGRATION

Narrative Expansion Ladder consumes one pinned:

```text
ActiveProductionProfile
```

It controls:

```text
structure profile
beat density
scene density
pacing
dialogue style
research depth
shot density
editing rhythm
QA policy
```

---

# 56. NICHE-SPECIFIC EXPANSION

Family Drama:

```text
fewer but deeper scenes
higher subtext density
longer emotional beats
lower cut density
```

Horror:

```text
information withholding
tension beats
reveal timing
negative-space coverage
sound-driven shot planning
```

True Crime:

```text
evidence units
chronology units
source attribution
uncertainty markers
```

Science Documentary:

```text
concept units
cause/effect steps
visual explanation beats
scale demonstrations
```

---

# 57. STORY CORE TO STRUCTURE DATA FLOW

```text
StoryCoreLock
↓
StructureProfileResolver
↓
MacroBeatPlanner
↓
MacroBeat QA
↓
SequencePlanner
↓
Sequence QA
↓
SceneExpansionPlanner
↓
Scene QA
↓
MicroBeatPlanner
↓
Beat QA
↓
ScreenplayRealizer
```

---

# 58. NO MAGIC EXPAND

Forbidden production behavior:

```text
LLM:
“Turn this one sentence into a 90-minute screenplay.”
```

Canonical:

```text
EXPAND
→ VALIDATE
→ LOCK
→ NEXT LEVEL
```

---

# 59. REPLAN VS REWRITE

```text
REPLAN:
changes structure or state transitions

REWRITE:
changes realization while preserving plan
```

Example:

```text
Scene ending wrong → REPLAN
Dialogue stiff → REWRITE
```

---

# 60. HUMAN REVIEW POINTS

Optional but supported:

```text
after Logline
after Macro Beat Sheet
after Sequence Plan
after Script Draft
before Script Lock
before final Shot List
```

Automation can run without human approval unless project policy requires it.

---

# 61. AUTONOMOUS MODE

```text
Idea
→ auto logline
→ auto gate
→ auto macro beats
→ auto gate
→ auto sequence
→ auto gate
→ auto scenes
→ auto gate
→ auto micro beats
→ auto screenplay
→ auto critique
→ auto repair
→ auto script lock candidate
→ auto directing
→ auto shots
```

Every gate still writes evidence.

---

# 62. EVIDENCE MODEL

```yaml
ExpansionGateEvidence:
  gate_id: string
  artifact_id: string
  artifact_version: string
  status: PASS | WARN | FAIL
  findings: []
  metrics: {}
  reviewer_ids: []
  created_at: string
```

---

# 63. NO FALSE PASS

A successful LLM response is not PASS.

PASS means:

```text
artifact exists
+
schema valid
+
semantic gate passes
+
no blocking findings
```

---

# 64. STORAGE MODEL

Recommended logical tables:

```text
ideas
loglines
story_core_locks
structure_profiles
macro_beat_sheets
macro_beats
sequence_plans
sequences
scene_lists
scenes
scene_breakdowns
micro_beats
screenplay_scenes
script_locks
directing_plans
cinematography_plans
shot_lists
shots
narrative_traces
invalidation_records
gate_evidence
```

---

# 65. RELATIONAL KEYS

```text
logline.idea_id
macro_beat_sheet.story_core_id
sequence_plan.beat_sheet_id
scene.sequence_id
micro_beat.scene_id
screenplay_scene.scene_id
shot.micro_beat_refs[]
```

---

# 66. IMMUTABILITY

Approved versions are immutable.

Modification:

```text
clone
→ modify
→ new version
→ re-run affected gates
```

---

# 67. EDITORIAL LINEAGE

If editorial drops a shot:

```text
ShotPlan remains in lineage
status = OMITTED_IN_EDIT
```

Do not delete provenance.

---

# 68. CROSS-LAYER QA

Need global checks:

```text
Logline promise fulfilled?
Macro beats support premise?
Sequences causally connected?
Scenes realize sequence purpose?
Micro beats move scenes?
Screenplay realizes micro beats?
Shots realize micro beats?
```

---

# 69. STORY COMPRESSION TEST

```text
Full Script
→ compress to 1 paragraph
→ compress to Logline
```

Compare to original Logline.

Major divergence:

```text
STORY_DRIFT
```

---

# 70. SHOT COMPRESSION TEST

```text
Shot List
→ summarize by micro beat
→ summarize by scene
```

Should reconstruct scene function.

---

# 71. COVERAGE MODEL

```text
MASTER
TWO_SHOT
MEDIUM
CLOSE_UP
EXTREME_CLOSE_UP
POV
OTS
INSERT
CUTAWAY
REACTION
ESTABLISHING
TRACKING
HANDHELD
STATIC
SPECIALIZED
```

Do not force all scenes to use all coverage types.

---

# 72. COVERAGE STRATEGY PROFILE

```yaml
CoverageProfile:
  profile_id: string
  style: CLASSICAL | MINIMALIST | DOCUMENTARY | HIGH_COVERAGE | ACTION | CUSTOM
  required_coverage: []
  optional_coverage: []
  discouraged_coverage: []
  continuity_rules: []
```

---

# 73. SHOT DENSITY BY NICHE

Illustrative:

```text
intimate drama:
longer ASL
lower shot density

action:
shorter ASL
higher shot density

documentary:
mixed

horror:
variable; rhythm-sensitive
```

No global hard-coded shot count.

---

# 74. TRANSITION TO 8-LAYER SYSTEM

Narrative Expansion Ladder ends responsibility at:

```text
Approved ShotPlan
```

Then:

```text
ShotPlan
→ State/Reference Resolution
→ 8-Layer ShotSpec
→ Shot IR
```

---

# 75. OWNERSHIP BOUNDARIES

```text
Story Intelligence
owns:
Idea → Script Lock

Directing
owns:
dramatic realization intent

Cinematography
owns:
visual capture strategy

Shot Expansion
owns:
shot decomposition

8-Layer ShotSpec
owns:
generation-ready canonical shot state

Provider Compiler
owns:
provider-specific request
```

---

# 76. FAILURE ESCALATION

If Shot QA detects:

```text
shot cannot realize micro beat
```

repair may escalate:

```text
Shot
→ Cinematography
→ Directing
→ MicroBeat
→ Scene
```

Only if root cause requires it.

---

# 77. REPAIR SCOPE PRINCIPLE

```text
FIX EARLIEST RESPONSIBLE LAYER
WITH MINIMUM NECESSARY INVALIDATION.
```

---

# 78. EXAMPLE END-TO-END TRACE

```text
IDEA:
“Người đàn ông trở về quê bán nhà sau khi mẹ mất.”

↓ Logline

LOGLINE:
He wants to sell the family home, but a cassette left by his mother forces him to confront memories he avoided.

↓ Macro Beat

B11:
He finally plays the cassette.

↓ Sequence

SQ6:
Avoidance collapses; he is forced into emotional confrontation.

↓ Scene

SC47:
At night, alone in mother's room, he presses PLAY.

↓ Micro Beat

MB204:
He reaches for STOP, hears his mother's unfinished sentence, freezes.

↓ Shot

SH875:
Extreme close-up of thumb hovering above STOP button while mother's voice continues off-screen.
```

---

# 79. ACCEPTANCE CRITERIA FOR PATCH

```text
[ ] Logline is first-class artifact
[ ] Structure Profile exists
[ ] Macro Beat Sheet is first-class artifact
[ ] Sequence Plan is first-class artifact
[ ] Duration Budget exists
[ ] Scene Budget exists
[ ] Scene List Manifest exists
[ ] Scene Breakdown Manifest exists
[ ] MicroBeat ownership is explicit
[ ] Screenplay Realization stage exists
[ ] Script Lock boundary is explicit
[ ] Directing Unit exists
[ ] Cinematography Plan exists
[ ] Shot Budget exists
[ ] Shot Expansion is explicit
[ ] Shot List Manifest exists
[ ] NarrativeTrace supports top-down and bottom-up traceability
[ ] Expansion drift defects are registered
[ ] Invalidation is dependency-based
[ ] Counts come from profiles, not hard-coded global constants
```

---

# 80. REQUIRED NEW DEFECT CODES

```text
LOGLINE_NO_FOCAL_SUBJECT
LOGLINE_NO_GOAL_OR_CENTRAL_QUESTION
LOGLINE_NO_OPPOSITION
LOGLINE_NO_STAKES
LOGLINE_GENERIC

MACRO_BEAT_NO_FUNCTION
MACRO_BEAT_NO_STATE_CHANGE
MACRO_BEAT_CAUSAL_GAP

SEQUENCE_NO_TURN
SEQUENCE_NO_ESCALATION
SEQUENCE_CAUSAL_GAP

SCENE_NO_FUNCTION
SCENE_NO_CONFLICT
SCENE_NO_TURN
SCENE_NO_STATE_CHANGE

MICRO_BEAT_NO_INTENTION
MICRO_BEAT_NO_ACTION
MICRO_BEAT_NO_REACTION
MICRO_BEAT_NO_CHANGE

SCREENPLAY_REALIZATION_DRIFT

SHOT_NO_NARRATIVE_FUNCTION
SHOT_NOT_BOUND_TO_BEAT
SHOT_MISSING_REQUIRED_COVERAGE

BUDGET_RUNTIME_OVERFLOW
BUDGET_SCENE_OVERFLOW
BUDGET_SHOT_OVERFLOW

EXPANSION_LOGLINE_DRIFT
EXPANSION_MACRO_BEAT_DRIFT
EXPANSION_SEQUENCE_DRIFT
EXPANSION_SCENE_DRIFT
EXPANSION_MICRO_BEAT_DRIFT
EXPANSION_SCREENPLAY_DRIFT
EXPANSION_SHOT_DRIFT

TRACE_ORPHAN_ARTIFACT
TRACE_MISSING_PARENT
TRACE_CYCLE
```

---

# 81. IMPLEMENTATION MODULES

```text
story-expansion/
├── idea/
├── logline/
├── structure-profile/
├── macro-beats/
├── sequences/
├── duration-budget/
├── scene-budget/
├── scene-list/
├── scene-breakdown/
├── micro-beats/
├── screenplay-realization/
├── script-lock/
├── narrative-trace/
└── invalidation/

preproduction/
├── directing/
├── cinematography/
├── coverage/
├── shot-budget/
├── shot-expansion/
└── shot-list/
```

---

# 82. IMPLEMENTATION ORDER

```text
P0 Contracts
P1 NarrativeTrace + Versioning
P2 Idea + Logline
P3 Structure Profile
P4 Macro Beat Sheet
P5 Sequence Plan
P6 Duration Budget
P7 Scene Budget + Scene List
P8 Scene Breakdown + MicroBeats
P9 Screenplay Realization
P10 Story Critique/Repair Integration
P11 Script Lock
P12 Directing Plan
P13 Cinematography Plan
P14 Coverage + Shot Budget
P15 Shot Expansion + Shot List
P16 ShotSpec handoff
P17 Cross-layer compression/drift tests
```

---

# 83. TEST MATRIX

Unit:

```text
schema
versioning
inheritance
budget math
trace links
cycle detection
invalidation
```

Integration:

```text
Idea→Logline
Logline→MacroBeats
MacroBeats→Sequences
Sequences→Scenes
Scenes→MicroBeats
MicroBeats→Screenplay
ScriptLock→Directing
Directing→Shots
Shots→ShotSpec
```

Semantic benchmark:

```text
story drift
causal drift
scene redundancy
beat stasis
dialogue realization drift
coverage redundancy
shot over-expansion
```

---

# 84. DEVIL'S ADVOCATE RISKS

## Risk 1 — Over-structuring creativity

Mitigation:

```text
profiles are selectable
exceptions allowed with explicit rationale
```

## Risk 2 — Mechanical 15-beat writing

Mitigation:

```text
15-beat is one profile, not universal authority
```

## Risk 3 — Too many artifacts

Mitigation:

```text
artifacts are machine-managed
UI can collapse them
```

## Risk 4 — False precision in shot counts

Mitigation:

```text
counts are budgets/ranges
not mandatory exact numbers
```

## Risk 5 — Expansion becomes repetitive

Mitigation:

```text
state-change and duplicate-function gates
```

---

# 85. MERGE INSTRUCTIONS FOR FINAL CONSOLIDATION

This patch should merge into:

```text
Story Intelligence Architecture
+
Canonical Contracts
+
Brain Pack Architecture
+
Directing Architecture
+
Cinematography Architecture
+
Shot Architecture
```

Authority updates required:

```text
1. Add Narrative Expansion Ladder to master architecture.
2. Add contracts to canonical contract authority.
3. Add defect codes to defect registry.
4. Add requirements for Logline/MacroBeat/SceneList/SceneBreakdown/ShotBudget/Trace.
5. Add dependency graph nodes.
6. Add task queue items.
7. Mark old implicit expansion wording as superseded.
```

---

# 86. NEW REQUIREMENTS RECOMMENDED

Exact IDs should be allocated during final consolidation to preserve numbering continuity:

```text
FR — Logline first-class artifact
FR — Structure Profile
FR — Macro Beat Sheet
FR — Sequence Plan
FR — Duration Budget
FR — Scene Budget
FR — Scene List Manifest
FR — Scene Breakdown Manifest
FR — Screenplay Realization
FR — Narrative Expansion Trace
FR — Shot Budget
FR — Shot Expansion
FR — Shot List Manifest

NFR — deterministic traceability
NFR — immutable approved versions
NFR — dependency-based invalidation
```

---

# 87. FINAL CANONICAL FORM

```text
IDEA
↓
LOGLINE
↓
PREMISE / ANGLE / THEME
↓
STORY CORE LOCK
↓
MACRO BEAT SHEET
↓
SEQUENCE PLAN
↓
SCENE LIST
↓
SCENE BREAKDOWN
↓
MICRO BEATS
↓
SCREENPLAY REALIZATION
↓
FULL SCRIPT
↓
INDEPENDENT CRITIQUE
↓
TARGETED STORY REPAIR
↓
SCRIPT LOCK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIRECTING
↓
CINEMATOGRAPHY
↓
SHOT EXPANSION
↓
SHOT LIST
↓
8-LAYER SHOT SPEC
↓
SHOT IR
↓
STATIC + MOTION
```

---

# 88. FINAL DECISION

The missing gap is now formally patched.

The Studio must not treat:

```text
Idea
→ Script
→ Shots
```

as a single opaque generation step.

It must operate through a traceable narrative expansion ladder where each level:

```text
inherits parent truth
adds controlled detail
changes state meaningfully
has a duration/size budget
has its own QA gate
has version/provenance
can be repaired independently
```

This patch is ready to be merged into the future **FINAL IMPLEMENTATION BASELINE**.

**End of design patch.**
