# BEAT → SCENE → DIRECTING → CINEMATOGRAPHY → SHOT
# CANONICAL AUTHORITY & TRACEABILITY ARCHITECTURE V1 — FINAL DESIGN

**Project:** Enterprise AI-Native Film Studio  
**Scope:** Chuẩn hóa đường đi từ Story Intent → Scene Dramatic Beat → Audience Experience → Directing / Blocking → Cinematography → Shot List → Full Shot Spec  
**Status:** FINAL DESIGN PATCH — READY TO MERGE INTO MASTER IMPLEMENTATION BASELINE  
**Primary goal:** Ngăn AI tự bịa camera / shot size / góc máy / lens / movement / lighting chỉ vì “cinematic”; mọi quyết định hình ảnh phải có **authority**, **constraint**, **justification** và **traceability** ngược về Scene Dramatic Beat và Scene.  
**Key distinction:** `MACRO STORY BEAT` ≠ `SCENE DRAMATIC BEAT`.

---

# 0. EXECUTIVE SUMMARY

Kiến trúc canonical cần khóa:

```text
STORY CORE
↓
MACRO STORY BEAT
↓
SEQUENCE
↓
SCENE
↓
SCENE DRAMATIC BEAT
↓
AUDIENCE EXPERIENCE TARGET
↓
DIRECTING INTENT
↓
BLOCKING / SPATIAL PLAN
↓
CINEMATOGRAPHY OBJECTIVE
↓
COVERAGE STRATEGY
↓
SHOT LIST
↓
SHOT ELIGIBILITY GATE
↓
FULL SHOT SPEC
↓
8-LAYER / L1-L12 TECHNICAL REALIZATION
```

Mọi quyết định camera phải có thể trace ngược:

```text
SHOT DECISION
→ Which Scene Dramatic Beat?
→ Which Audience Experience Target?
→ Which Scene spatial/state constraint?
→ Which Directing/Blocking intent?
→ Which Cinematography objective?
```

Nếu không trả lời được:

```text
NO JUSTIFICATION
→ INVALID SHOT DECISION
```

---

# 1. CANONICAL TERMINOLOGY

## 1.1 MACRO STORY BEAT

**Definition**

```text
Story thay đổi lớn ở đâu?
```

Macro Story Beat là thay đổi cấu trúc lớn của toàn câu chuyện.

Ví dụ:

```text
- Inciting disruption
- Commitment
- Midpoint reorientation
- Major loss
- Crisis
- Final choice
- Climax
- Consequence
```

Không dùng Macro Story Beat để trực tiếp chọn:

```text
85mm
close-up
Dutch angle
push-in
lighting ratio
```

Macro Story Beat quá cao cấp để quyết định camera cụ thể.

## 1.2 SEQUENCE

**Definition**

```text
Một chặng dramatic progression.
```

Sequence gom nhiều scene để hoàn thành một nhiệm vụ cấu trúc lớn.

Canonical concerns:

```text
opening state
sequence objective
opposition
escalation
major turn
closing state
emotion trajectory
information trajectory
setup/payoff obligations
```

## 1.3 SCENE

**Definition**

```text
Một đơn vị không gian/thời gian có state change.
```

Scene trả lời:

```text
Ở đâu?
Khi nào?
Ai có mặt?
Ai muốn gì?
Đối kháng là gì?
Không gian vận hành thế nào?
Scene bắt đầu state nào?
Scene kết thúc state nào?
```

Scene không chỉ là slugline.

## 1.4 SCENE DRAMATIC BEAT

**Definition**

```text
Một khoảnh khắc dramatic nhỏ bên trong scene:
nhân vật muốn gì,
làm gì,
phản ứng gì,
gặp resistance/new information gì,
và điều gì thay đổi?
```

Đây là **Beat trực tiếp cấp authority cho Shot**.

Canonical form:

```text
INTENTION
→ TACTIC
→ ACTION
→ REACTION
→ RESISTANCE / NEW INFORMATION
→ MICRO-TURN
→ STATE DELTA
```

## 1.5 AUDIENCE EXPERIENCE TARGET

**Definition**

```text
Người xem phải cảm / hiểu / lo / chờ / nghi ngờ điều gì
ở Scene Dramatic Beat này?
```

Ví dụ:

```text
loneliness = 70%
uncertainty = 60%
heartbreak = 90%
relief = 50%
curiosity = 80%
dread = 75%
```

Các con số là **target tương đối**, không phải phép đo cảm xúc tuyệt đối.

## 1.6 DIRECTING INTENT

**Definition**

```text
Actor / performance / reveal / timing phải được dàn dựng thế nào
để hiện thực hóa Beat và Audience Target?
```

Directing không chọn lens cụ thể trước Cinematography.

## 1.7 BLOCKING / SPATIAL PLAN

**Definition**

```text
Ai đứng đâu?
Di chuyển ra sao?
Khoảng cách giữa các nhân vật?
Eye-line?
Foreground / midground / background?
Ai chiếm ưu thế trong không gian?
Object nào là dramatic carrier?
```

Blocking là cầu nối bắt buộc giữa Beat và Camera.

## 1.8 CINEMATOGRAPHY OBJECTIVE

**Definition**

```text
Chuyển dramatic intent + spatial truth
thành visual language.
```

Cinematography quyết định:

```text
framing strategy
shot-size strategy
camera position
camera height
angle family
lens family
movement strategy
focus strategy
composition strategy
lighting strategy
color/contrast strategy
coverage strategy
```

Nhưng không được thay đổi dramatic intent upstream.

## 1.9 SHOT LIST

**Definition**

```text
Shot nào cần tồn tại và vì sao?
```

Shot List chưa phải Full Shot Spec.

Shot List xác định:

```text
shot identity
beat binding
shot function
coverage role
duration target
continuity obligations
```

## 1.10 FULL SHOT SPEC

**Definition**

```text
Chính xác camera / shot size / angle / lens / movement /
lighting / composition / focus / performance micro-detail...
```

Đây là tầng technical realization cuối.

---

# 2. TWO DIFFERENT HIERARCHIES — DO NOT CONFUSE

## 2.1 Narrative hierarchy

```text
STORY
↓
MACRO STORY BEAT
↓
SEQUENCE
↓
SCENE
↓
SCENE DRAMATIC BEAT
↓
SHOT
```

## 2.2 Creative decision hierarchy

```text
SCENE DRAMATIC BEAT
↓
AUDIENCE EXPERIENCE TARGET
↓
DIRECTING INTENT
↓
BLOCKING / SPATIAL PLAN
↓
CINEMATOGRAPHY OBJECTIVE
↓
SHOT PLAN
↓
FULL SHOT SPEC
```

Hai hierarchy này là **một hệ thống duy nhất** nhìn ở hai góc khác nhau.

---

# 3. GOLDEN RULES

```text
RULE 1
MACRO STORY BEAT không được dùng như Scene Dramatic Beat.

RULE 2
Scene Dramatic Beat là parent trực tiếp về narrative intent của Shot.

RULE 3
Scene là parent trực tiếp về space/time/state của Shot.

RULE 4
Audience Experience Target phải tồn tại trước quyết định cinematography quan trọng.

RULE 5
Directing / Blocking phải tồn tại trước final shot design.

RULE 6
Shot không được tồn tại chỉ vì “đẹp”.

RULE 7
Mọi camera decision phải trace được ngược về Beat/Scene/Directing.

RULE 8
Cinematography được sáng tạo nhưng chỉ trong phạm vi constraints hợp lệ.

RULE 9
Generated artifact không thể ngược lại sửa story intent.

RULE 10
Một Shot không có beat binding là ORPHAN SHOT và phải FAIL.
```

---

# 4. WHY THIS ARCHITECTURE EXISTS

AI rất dễ sinh:

```text
wide shot
medium shot
close-up
insert
POV
85mm
dramatic lighting
slow push-in
```

mà không biết tại sao.

Kết quả:

```text
beautiful shots
+
cinematic vocabulary
+
weak dramatic causality
=
cảnh đẹp rời rạc
```

Architecture này bắt buộc:

```text
WHY
→ WHAT
→ WHERE / WHEN
→ HOW ACTORS MOVE
→ HOW CAMERA SEES
```

---

# 5. AUTHORITY HIERARCHY

Canonical authority:

```text
1. Locked Story Facts
2. Macro Story Beat
3. Sequence Contract
4. Scene Contract
5. Scene Dramatic Beat
6. Audience Experience Target
7. Directing Intent
8. Blocking / Spatial Plan
9. Cinematography Objective
10. Shot List Item
11. Full Shot Spec
12. Provider Prompt / Compiled Request
13. Generated Artifact
```

Lower level không được phá higher level.

---

# 6. INHERITANCE MODEL

Mỗi field trong downstream spec phải có:

```text
FIXED
INHERITED
VARIABLE
```

## FIXED

Không được đổi.

Ví dụ:

```text
character identity
scene location
scene time
dramatic beat outcome
must-show prop
camera axis lock
```

## INHERITED

Kế thừa từ upstream.

Ví dụ:

```text
audience emotion target
blocking
scene color mood
continuity constraint
```

## VARIABLE

Được Cinematography chọn trong phạm vi cho phép.

Ví dụ:

```text
lens ∈ [50, 65]mm
push-in ∈ [0, 4]%
camera height ∈ [eye-level ± small offset]
```

---

# 7. MACRO STORY BEAT CONTRACT

```yaml
MacroStoryBeat:
  macro_beat_id: string
  sequence_ids: []

  dramatic_function: string
  story_state_before: {}
  event_or_decision: string
  consequence: string
  story_state_after: {}

  information_delta: []
  relationship_delta: []
  stakes_delta: []
  emotional_delta: []

  setup_refs: []
  payoff_refs: []

  status: DRAFT | APPROVED | LOCKED
```

Macro Beat không chứa camera fields.

---

# 8. SEQUENCE CONTRACT

```yaml
SequenceContract:
  sequence_id: string
  macro_beat_refs: []
  purpose: string
  opening_state: {}
  sequence_objective: string
  opposition: string
  escalation_pattern: string
  major_turn: string
  closing_state: {}
  audience_trajectory: []
  information_trajectory: []
  emotion_trajectory: []
  scene_ids: []
```

---

# 9. SCENE CONTRACT

```yaml
SceneContract:
  scene_id: string
  sequence_id: string
  location_id: string
  time_context: string
  participants: []
  focal_character_id: string | null
  narrative_function: string
  opening_state: {}
  scene_objective: string
  opposition: string
  conflict: string
  stakes: string
  scene_turn: string
  closing_state: {}
  information_delta: []
  relationship_delta: []
  emotional_delta: []
  power_delta: []
  risk_delta: []
  scene_beat_ids: []
  duration_budget_seconds: number
```

---

# 10. SCENE SPATIAL DRAMATIC CONTRACT

Đây là authority không gian trước Shot.

```yaml
SceneSpatialDramaticContract:
  scene_id: string
  space:
    location_id: string
    topology: string
    zones: []
    entrances: []
    exits: []
    anchor_objects: []
  participant_positions:
    - entity_id: string
      initial_zone: string
      spatial_role: string
  relationship_geometry:
    distance_rules: []
    dominance_rules: []
    separation_rules: []
  dramatic_objects:
    - object_id: string
      function: string
      must_preserve: boolean
  environmental_pressure:
    weather: string | null
    noise: string | null
    crowd: string | null
    visibility: string | null
  screen_direction:
    axis_policy: string
    eyeline_constraints: []
```

---

# 11. SCENE DRAMATIC BEAT CONTRACT

```yaml
SceneDramaticBeat:
  scene_beat_id: string
  scene_id: string
  ordinal: number
  dramatic_function: string
  acting_character_ids: []
  focal_character_id: string | null
  intention: string
  tactic: string
  action: string
  reaction: string
  resistance_or_new_information: string
  micro_turn: string
  state_before: {}
  state_after: {}
  knowledge_delta: []
  relationship_delta: []
  emotional_delta: []
  power_delta: []
  setup_refs: []
  payoff_refs: []
  audience_target_id: string
  status: DRAFT | APPROVED | LOCKED
```

---

# 12. AUDIENCE EXPERIENCE TARGET CONTRACT

```yaml
AudienceExperienceTarget:
  audience_target_id: string
  scene_beat_id: string
  primary_emotion:
    name: string
    target_intensity: number
  secondary_emotions:
    - name: string
      target_intensity: number
  tension:
    before: number
    after: number
  curiosity:
    before: number
    after: number
  understanding:
    must_understand: []
    must_not_yet_understand: []
  anticipation:
    expected_question: string | null
    expected_wait: string | null
  uncertainty:
    desired_level: number | null
  release:
    desired_level: number | null
  audience_attention_target:
    primary: string
    secondary: []
  forbidden_experience: []
```

---

# 13. DIRECTING INTENT CONTRACT

```yaml
DirectingIntent:
  directing_intent_id: string
  scene_beat_id: string
  performance_objective: string
  actor_direction:
    posture: string
    gaze: string
    breathing: string
    gesture: string
    tempo: string
    restraint_level: string
  reveal_strategy:
    reveal: []
    withhold: []
  attention_strategy:
    primary_focus: string
    secondary_focus: string | null
  rhythm:
    hold_before_action: number | null
    hold_after_action: number | null
  transition_intent:
    incoming: string | null
    outgoing: string | null
```

---

# 14. BLOCKING PLAN CONTRACT

```yaml
BlockingPlan:
  blocking_id: string
  scene_beat_id: string
  positions:
    - entity_id: string
      start_position: string
      end_position: string
      facing: string
  movements:
    - entity_id: string
      path: string
      motivation: string
  eyelines: []
  distance_changes: []
  foreground_elements: []
  midground_elements: []
  background_elements: []
  dramatic_object_interactions: []
  must_preserve: []
  forbidden_moves: []
```

---

# 15. CINEMATOGRAPHY OBJECTIVE CONTRACT

```yaml
CinematographyObjective:
  cine_objective_id: string
  scene_beat_id: string
  visual_goal: string
  emotional_goal: string
  framing_strategy: string
  spatial_strategy: string
  perspective_strategy: string
  shot_size_strategy:
    allowed: []
    discouraged: []
    forbidden: []
  lens_strategy:
    allowed_range_mm: []
    preferred_character: string
  camera_height_strategy: string
  angle_strategy: string
  movement_strategy: string
  focus_strategy: string
  lighting_strategy: string
  contrast_strategy: string
  color_strategy: string
  composition_strategy: string
  negative_space_policy: string | null
  coverage_strategy: string
  continuity_constraints: []
  justification: string
```

---

# 16. CAMERA DECISION RULE

Canonical:

```text
CAMERA_DECISION
=
f(
  SceneDramaticBeat,
  AudienceExperienceTarget,
  SceneSpatialDramaticContract,
  DirectingIntent,
  BlockingPlan,
  ContinuityState,
  ActiveProductionProfile
)
```

Không phải:

```text
CAMERA_DECISION
=
"make it cinematic"
```

---

# 17. SHOT LIST ITEM CONTRACT

```yaml
ShotListItem:
  shot_id: string
  scene_id: string
  scene_beat_id: string
  macro_beat_id: string
  sequence_id: string
  shot_function: string
  coverage_role: string
  subject_ids: []
  dramatic_object_ids: []
  audience_target_id: string
  directing_intent_id: string
  blocking_id: string
  cine_objective_id: string
  estimated_duration_seconds: number
  required_visual_information: []
  must_preserve: []
  must_change: []
  forbidden_changes: []
  status: PLANNED | ELIGIBLE | REJECTED
```

---

# 18. SHOT ELIGIBILITY GATE

Full Shot Spec không được tạo nếu thiếu bất kỳ mục bắt buộc nào:

```text
✓ macro_beat_id
✓ sequence_id
✓ scene_id
✓ scene_beat_id
✓ audience_target_id
✓ directing_intent_id
✓ blocking_id
✓ cine_objective_id
✓ shot_function
✓ coverage_role
✓ continuity state
```

Hard rule:

```text
NO ELIGIBILITY PASS
→ NO FULL SHOT SPEC
```

---

# 19. FULL SHOT SPEC CONTRACT

```yaml
FullShotSpec:
  shot_id: string
  version: string
  lineage:
    macro_beat_id: string
    sequence_id: string
    scene_id: string
    scene_beat_id: string
  narrative:
    shot_function: string
    audience_target: string
  subject:
    subject_ids: []
    state_refs: []
  performance:
    body_posture: string
    gaze: string
    facial_micro_expression: string
    gesture: string
    breath: string
    micro_detail: []
  environment:
    location_id: string
    spatial_anchor_refs: []
    weather: string | null
    atmosphere: string | null
  camera:
    shot_size: string
    framing: string
    camera_height: string
    angle: string
    camera_position: string
  lens:
    focal_length_mm: number
    lens_family: string
    aperture: string
  movement:
    type: string
    amount: string
    speed: string
    motivation: string
  focus:
    focus_target: string
    depth_strategy: string
    rack_focus: string | null
  lighting:
    key_strategy: string
    fill_strategy: string
    practicals: []
    contrast: string
    color_temperature: string | null
  composition:
    subject_placement: string
    negative_space: string | null
    foreground: string | null
    background: string | null
  continuity:
    must_preserve: []
    must_change: []
    forbidden_changes: []
  justification:
    shot_size_reason: string
    angle_reason: string
    lens_reason: string
    movement_reason: string
    lighting_reason: string
    composition_reason: string
```

---

# 20. SHOT DECISION TRACE CONTRACT

```yaml
ShotDecisionTrace:
  shot_id: string
  decisions:
    shot_size:
      value: string
      source: string
      reason: string
    angle:
      value: string
      source: string
      reason: string
    lens:
      value: string
      source: string
      reason: string
    movement:
      value: string
      source: string
      reason: string
    lighting:
      value: string
      source: string
      reason: string
    composition:
      value: string
      source: string
      reason: string
  valid: boolean
  failures: []
```

---

# 21. REQUIRED JUSTIFICATION QUESTIONS

Mỗi Shot phải trả lời:

```text
Why this shot exists?
Which Scene Dramatic Beat does it serve?
What must the audience feel/understand?
Why this shot size?
Why this angle?
Why this camera height?
Why this lens?
Why this movement?
Why this composition?
Why this lighting?
What must be preserved?
What must change?
```

---

# 22. CAMERA SIZE DECISION MATRIX

## Wide / Extreme Wide

Potential purposes:

```text
spatial orientation
isolation
scale
relationship geography
vulnerability in environment
establish blocking
```

## Medium

Potential purposes:

```text
performance + environment balance
interaction
body language
social distance
```

## Medium Close-Up

Potential purposes:

```text
intimacy with context
reaction
subtle performance
```

## Close-Up

Potential purposes:

```text
micro-expression
subjective pressure
emotional isolation
critical realization
```

## Extreme Close-Up

Potential purposes:

```text
specific physical detail
micro action
symbolic information
intense subjective emphasis
```

No size is inherently “better”.

---

# 23. ANGLE DECISION MATRIX

## Eye Level

```text
neutral intimacy
shared perspective
human parity
observational honesty
```

## High Angle

Possible functions:

```text
spatial vulnerability
reduced agency
exposure
```

Not automatically “weak”.

## Low Angle

Possible functions:

```text
presence
dominance
threat
monumentality
```

Not automatically “power”.

## Dutch / Canted

Must require explicit justification:

```text
destabilized perception
world-axis disruption
psychological imbalance
```

Forbidden as generic “cinematic style”.

---

# 24. LENS DECISION MATRIX

Lens choice must follow:

```text
spatial relationship
perspective compression
subject isolation
environmental inclusion
camera distance
performance intimacy
continuity
```

Example tendencies:

```text
24mm  → environmental inclusion / perspective emphasis
35mm  → immersive spatial proximity
50mm  → balanced natural perspective
85mm  → compression / isolation / close performance
135mm+ → strong compression / distant observation
```

These are tendencies, not automatic emotional labels.

---

# 25. MOVEMENT DECISION MATRIX

Movement must be motivated.

## Static

```text
containment
observation
emotional freeze
tension through stillness
```

## Push-In

```text
attention narrowing
realization
pressure increase
emotional compression
```

## Pull-Out

```text
isolation
loss
recontextualization
emotional release
```

## Pan / Tilt

```text
information reveal
relationship transfer
spatial discovery
```

## Tracking

```text
follow agency
maintain relationship through movement
immersive progression
```

No movement without function.

---

# 26. LIGHTING DECISION MODEL

Lighting follows:

```text
scene physical truth
time of day
practical sources
dramatic objective
style profile
continuity
```

It must not simply map:

```text
sad = blue
happy = warm
evil = red
```

---

# 27. COMPOSITION DECISION MODEL

Composition can encode:

```text
power
distance
absence
pressure
separation
connection
information hierarchy
attention
```

Example:

```text
empty chair + negative space
```

can function as visual carrier of absence only if Scene contract establishes that meaning.

---

# 28. PERFORMANCE MICRO-DETAIL

Full Shot Spec may include:

```text
lip tremor
eye hesitation
breath interruption
finger tension
weight shift
jaw release
blink suppression
```

But micro-detail must trace to:

```text
character state
beat emotion
directing intent
```

No random “acting texture”.

---

# 29. EXAMPLE — HANOI CAFÉ

## Macro Story Beat

```text
Character's denial begins to collapse.
```

## Sequence

```text
Memory confrontation.
```

## Scene

```text
Hanoi café
6PM
heavy rain
Lan alone
empty chair opposite
```

## Scene Dramatic Beat

```text
Lan tries not to look at the empty chair.
A song associated with the absent person begins.
She loses control for one second.
```

## Audience Target

```text
loneliness: 70 → 85
heartbreak: 40 → 90
release: 10
```

## Directing

```text
Lan keeps body closed.
No crying.
Eyes avoid chair.
Breath stops briefly.
Hand tightens around cup.
```

## Blocking

```text
Lan left side of table.
Empty chair remains opposite.
Window/rain behind chair.
No major movement.
```

## Cinematography

```text
Visual objective:
make absence occupy physical frame space.

Coverage:
start wider with negative space,
then compress toward performance.
```

## Shot 1

```text
Function: establish emotional separation
Medium-wide
50mm
eye-level
static
Lan left third
empty chair dominant negative space
rain soft background
```

## Shot 2

```text
Function: capture recognition
Medium close-up
85mm
eye-level
minimal push-in
shallow depth
```

## Shot 3

```text
Function: show suppressed reaction
Close-up
85mm
push-in 3%
lip tremor
breath interruption
```

Everything is traceable.

---

# 30. BAD EXAMPLE

```text
Scene is sad.
Use:
Dutch angle
14mm
fast orbit
blue lighting
dramatic zoom
```

Why invalid?

```text
no beat binding
no spatial reason
no directing reason
no audience target
no continuity reason
no shot function
```

Result:

```text
CINEMATIC_DECORATION
→ FAIL
```

---

# 31. SHOT ORPHAN DETECTION

Shot is orphan if:

```text
scene_beat_id missing
shot_function missing
audience_target missing
directing linkage missing
cinematography objective missing
```

Hard defect:

```text
SHOT_ORPHAN
```

---

# 32. CAMERA DECISION DEFECT CODES

Recommended:

```text
SHOT_ORPHAN
SHOT_NO_BEAT_BINDING
SHOT_NO_SCENE_BINDING
SHOT_NO_AUDIENCE_TARGET
SHOT_NO_NARRATIVE_FUNCTION
SHOT_NO_DIRECTING_INTENT
SHOT_NO_BLOCKING_CONTEXT
SHOT_NO_CINEMATOGRAPHY_OBJECTIVE

CAMERA_SHOT_SIZE_UNJUSTIFIED
CAMERA_ANGLE_UNJUSTIFIED
CAMERA_HEIGHT_UNJUSTIFIED
CAMERA_LENS_UNJUSTIFIED
CAMERA_MOVEMENT_UNJUSTIFIED
CAMERA_LIGHTING_UNJUSTIFIED
CAMERA_COMPOSITION_UNJUSTIFIED

CAMERA_DECORATIVE_ONLY
CAMERA_STYLE_OVER_STORY
CAMERA_BREAKS_BLOCKING
CAMERA_BREAKS_SCREEN_DIRECTION
CAMERA_BREAKS_CONTINUITY
CAMERA_BREAKS_SCENE_SPACE

PERFORMANCE_MICRODETAIL_UNJUSTIFIED
```

---

# 33. HARD GATES

## Scene Gate

```text
Scene Contract exists
Scene state change exists
Spatial contract exists
Scene beat list exists
```

## Beat Gate

```text
intention exists
action exists
reaction exists
micro-turn exists
audience target exists
```

## Directing Gate

```text
performance intent exists
blocking exists
reveal strategy exists
```

## Cinematography Gate

```text
visual objective exists
coverage strategy exists
camera constraints exist
```

## Shot Gate

```text
shot function exists
beat binding exists
decision trace exists
```

---

# 34. BOUNDED CREATIVITY

Cinematography is allowed to propose multiple valid options:

```text
Option A
50mm medium-wide static

Option B
65mm medium shot with slow compression

Option C
85mm close-up after spatial setup
```

But each option must pass:

```text
dramatic fit
spatial fit
blocking fit
continuity fit
style fit
audience-target fit
```

---

# 35. CAMERA OPTION SCORING

Advisory only:

```text
Narrative Fit
Emotional Fit
Spatial Fit
Performance Fit
Continuity Fit
Coverage Utility
Style Fit
Technical Feasibility
```

Blocking violation cannot be averaged away.

---

# 36. NO AUTOMATIC “EMOTION → LENS” LOOKUP

Forbidden:

```text
sadness → 85mm
fear → wide angle
power → low angle
```

Correct:

```text
emotion
+
space
+
blocking
+
dramatic function
+
subjective/objective POV
+
continuity
→ camera decision
```

---

# 37. ACTIVE PRODUCTION PROFILE INTEGRATION

Cinematography also receives:

```text
genre brain
niche brain
format brain
platform brain
production style brain
```

Examples:

```text
family drama:
restrained camera
performance-first
lower cut density

horror:
withholding
negative space
reveal control

documentary:
evidence clarity
observational integrity

action:
spatial legibility
movement continuity
coverage sufficiency
```

---

# 38. DURATION AWARENESS

Shot count and shot duration depend on:

```text
runtime
scene duration
beat duration
editing rhythm
genre
format
coverage style
```

No hard-coded global shot count.

---

# 39. SCENE BEAT → SHOT RELATIONSHIP

One Scene Beat may map to one shot or multiple shots depending on:

```text
information density
performance complexity
blocking complexity
coverage need
editorial rhythm
```

---

# 40. SHOT → BEAT COMPRESSION TEST

Validation:

```text
Shots for Beat X
→ summarize
```

Summary should reconstruct Beat X's dramatic function.

If not:

```text
SHOT_DRIFT
```

---

# 41. SCENE COMPRESSION TEST

```text
Scene Beats
→ summarize
≈ Scene Contract
```

If not:

```text
SCENE_BEAT_DRIFT
```

---

# 42. MACRO TRACE

```text
Shot
↓
Scene Dramatic Beat
↓
Scene
↓
Sequence
↓
Macro Story Beat
↓
Story Core
↓
Logline
↓
Idea
```

---

# 43. BOTTOM-UP WHY TRACE

Every shot should answer:

```text
Why does this shot exist?
Why this composition?
Why this lens?
Why this movement?
Why this light?
Why now?
Why at this duration?
```

---

# 44. TOP-DOWN AUTHORITY TRACE

```text
Story says WHAT matters.
Macro Beat says WHERE major change happens.
Sequence says WHICH dramatic phase.
Scene says WHERE/WHEN and WHAT state changes.
Scene Beat says WHAT moment changes.
Audience Target says WHAT viewer must experience.
Directing says HOW actors perform.
Blocking says HOW space is used.
Cinematography says HOW visual language encodes it.
Shot says WHICH concrete image unit realizes it.
```

---

# 45. IMMUTABILITY

Once approved:

```text
SceneBeat v1
```

must not be silently modified by Shot generation.

Change requires:

```text
SceneBeat v2
→ invalidate dependent Shots
→ regenerate/review affected scope
```

---

# 46. INVALIDATION RULES

If Scene Beat changes:

```text
invalidate:
Audience Target
Directing
Blocking
Cinematography
Shot List
Full Shot Specs
```

If only lens changes:

```text
invalidate:
Full Shot Spec
possibly downstream generation artifact

preserve:
Scene Beat
Scene
Sequence
Macro Beat
```

---

# 47. REPAIR ESCALATION

If generated shot fails:

```text
visual defect
→ repair shot

camera mismatch
→ repair cinematography

blocking mismatch
→ repair blocking/directing

beat mismatch
→ escalate to Scene Beat

scene mismatch
→ escalate to Scene
```

Rule:

```text
FIX EARLIEST RESPONSIBLE LAYER.
```

---

# 48. PROVIDER BOUNDARY

Provider prompt is downstream:

```text
Full Shot Spec
↓
Shot IR
↓
Provider Compiler
↓
Provider Request
```

Provider must never invent upstream story intent.

---

# 49. STORYBOARD BOUNDARY

Storyboard can be generated after Shot List / Shot Plan.

Recommended:

```text
Shot List
↓
Storyboard / Previz
↓
Review
↓
Full Shot Spec Refinement
```

Storyboard cannot replace Scene Beat authority.

---

# 50. FULL SHOT SPEC VS SHOT LIST

## Shot List

```text
Why this shot exists.
```

## Full Shot Spec

```text
Exactly how this shot is executed.
```

This distinction is mandatory.

---

# 51. DIRECTING VS CINEMATOGRAPHY

## Directing owns

```text
performance
blocking
dramatic emphasis
timing
reveal/withhold
actor relationship
```

## Cinematography owns

```text
framing
camera
lens
movement
focus
lighting
composition
coverage
```

Cinematography cannot rewrite acting intent.

---

# 52. SCENE VS BEAT

## Scene owns

```text
space
time
participants
scene objective
scene conflict
scene turn
state change
beat ordering
```

## Scene Beat owns

```text
moment-to-moment intention
action
reaction
resistance
micro-turn
audience target
```

---

# 53. MACRO BEAT VS SCENE BEAT

Never use generic `Beat` alone in persistent schemas.

Use exact namespace:

```text
MacroStoryBeat
SceneDramaticBeat
```

UI may shorten label visually, but storage/contracts must stay explicit.

---

# 54. RECOMMENDED DATABASE ENTITIES

```text
macro_story_beats
sequences
scenes
scene_spatial_contracts
scene_dramatic_beats
audience_experience_targets
directing_intents
blocking_plans
cinematography_objectives
shot_lists
shot_list_items
full_shot_specs
shot_decision_traces
shot_gate_evidence
```

---

# 55. MODULE BOUNDARIES

```text
story/
├── macro-beats/
├── sequences/
├── scenes/
└── scene-beats/

audience/
└── experience-target/

directing/
├── intent/
└── blocking/

cinematography/
├── objective/
├── coverage/
└── camera-decision/

shots/
├── shot-list/
├── eligibility/
├── full-shot-spec/
└── decision-trace/
```

---

# 56. IMPLEMENTATION ORDER

```text
P0  Contract schemas
P1  MacroStoryBeat namespace
P2  SceneDramaticBeat namespace
P3  SceneSpatialDramaticContract
P4  AudienceExperienceTarget
P5  DirectingIntent
P6  BlockingPlan
P7  CinematographyObjective
P8  ShotListItem
P9  ShotEligibilityGate
P10 FullShotSpec
P11 ShotDecisionTrace
P12 Defect registry
P13 Invalidation graph
P14 QA / compression tests
P15 UI explainability
```

---

# 57. UNIT TESTS

```text
MacroStoryBeat cannot contain camera fields.
SceneDramaticBeat requires scene_id.
Audience target requires scene_beat_id.
Shot requires scene_beat_id.
Shot eligibility rejects missing lineage.
Shot decision trace requires camera justification.
Inheritance precedence works.
Fixed fields cannot be overridden.
Variable fields stay within allowed ranges.
```

---

# 58. INTEGRATION TESTS

```text
MacroBeat→Sequence→Scene→Beat
Beat→AudienceTarget
Beat→Directing
Directing→Blocking
Blocking→Cinematography
Cinematography→ShotList
ShotList→Eligibility
Eligibility→FullShotSpec
FullShotSpec→ShotIR
```

---

# 59. SEMANTIC TESTS

Test against:

```text
family drama
horror
true crime
science documentary
romance
action
historical drama
comedy
```

Goal:

```text
same hierarchy
different cinematic decisions
```

---

# 60. ADVERSARIAL TESTS

Inject:

```text
random cinematic camera
generic 85mm close-up
unmotivated Dutch angle
unmotivated orbit
wrong screen direction
camera contradicting blocking
lighting contradicting time-of-day
shot with no beat
```

All must be caught.

---

# 61. EXPLAINABILITY UI

For each Shot, UI can show:

```text
WHY THIS SHOT?

Scene Beat:
B24.3 — suppressed heartbreak

Audience Target:
heartbreak 90%

Directing:
hold emotion; no tears yet

Blocking:
subject remains seated; empty chair opposite

Cinematography:
compress space after wide isolation

Therefore:
CU / 85mm / eye-level / push-in 3%
```

---

# 62. EXPERT OVERRIDE

Expert user may override:

```text
shot size
lens
movement
lighting
```

But override must include:

```text
reason
scope
version
```

and may trigger QA warning.

---

# 63. AUTOMATIC MODE

Automatic mode:

```text
Beat
→ Audience Target
→ Directing
→ Blocking
→ Cinematography
→ Shot List
→ Eligibility
→ Full Shot Spec
```

No confirmation required if project policy allows.

But every stage writes evidence.

---

# 64. HUMAN REVIEW MODE

Optional review points:

```text
Scene Beat lock
Directing lock
Cinematography lock
Shot List lock
```

---

# 65. NO “CINEMATIC” AS A SUFFICIENT REASON

Forbidden justification:

```text
"because it looks cinematic"
"for visual interest"
"to make it dramatic"
```

Valid justification must reference:

```text
beat function
audience target
spatial relation
performance
information reveal
continuity
```

---

# 66. VISUAL STYLE VS DRAMATIC FUNCTION

Style Pack may suggest:

```text
anamorphic
handheld
soft contrast
long lens
```

But style cannot override:

```text
dramatic legibility
scene geography
blocking
beat function
continuity
```

---

# 67. CAMERA DECISION PRECEDENCE

```text
1. Safety / hard production constraints
2. Scene continuity
3. Scene spatial contract
4. Scene Beat dramatic function
5. Audience Experience Target
6. Directing / Blocking
7. Active Production Profile
8. Cinematography preference
9. Provider capability
10. Cosmetic preference
```

---

# 68. PROVIDER CAPABILITY FALLBACK

If desired camera move unsupported:

```text
preserve dramatic function
↓
choose nearest supported visual solution
```

Never preserve technical choice at cost of dramatic intent.

---

# 69. MULTI-SHOT BEAT

Example:

```text
Beat:
recognition → denial → involuntary reaction
```

Could use:

```text
Shot A: reveal source
Shot B: reaction
Shot C: detail
Shot D: emotional compression
```

All shots share same parent beat but different shot functions.

---

# 70. ONE-SHOT SCENE BEAT

If Beat can be realized in one shot:

```text
do not force coverage expansion.
```

No arbitrary shot multiplication.

---

# 71. SHOT REDUNDANCY QA

Reject multiple shots with same function, information, emotion and coverage role unless an editorial reason exists.

---

# 72. COVERAGE SUFFICIENCY QA

Check:

```text
required information captured?
performance turn captured?
spatial continuity usable?
edit points sufficient?
```

---

# 73. PERFORMANCE-FIRST RULE

For performance-driven niche:

```text
do not sacrifice acting readability
for decorative camera movement.
```

---

# 74. HORROR RULE EXAMPLE

```text
Beat:
audience must anticipate unseen presence.

Cinematography:
preserve off-screen space.

Invalid:
tight CU removing threat space too early.
```

---

# 75. TRUE CRIME RULE EXAMPLE

```text
Beat:
viewer understands uncertainty in evidence.

Invalid:
dramatic camera implying certainty not supported by research.
```

---

# 76. SCIENCE DOCUMENTARY RULE EXAMPLE

```text
Beat:
viewer must understand scale comparison.

Invalid:
artistic shallow DOF obscuring required explanatory relation.
```

---

# 77. FAMILY DRAMA RULE EXAMPLE

```text
Beat:
viewer feels emotional distance.

Possible:
two-shot with physical separation.

Invalid:
romanticized close-up grammar implying intimacy.
```

---

# 78. ACTION RULE EXAMPLE

```text
Beat:
audience must understand tactical reversal.

Priority:
spatial legibility
before decorative kinetic camera.
```

---

# 79. COMEDY RULE EXAMPLE

```text
Beat:
timing + reaction are key.

Camera:
may need hold rather than cut,
depending on gag mechanics.
```

---

# 80. SHOT VALIDITY FORMULA

```text
VALID_SHOT
=
BeatBinding
× SceneFit
× AudienceTargetFit
× DirectingFit
× SpatialFit
× CinematographyFit
× ContinuityFit
× TechnicalFeasibility
```

Any blocking zero:

```text
→ FAIL
```

---

# 81. MASTER INVARIANT

```text
CAMERA / SHOT SIZE / ANGLE / LENS / MOVEMENT / LIGHTING
MUST NOT BE SELF-ORIGINATING DECISIONS.
```

They are derived decisions.

---

# 82. PRIMARY TRACE RULE

```text
SHOT
must trace DIRECTLY to
SCENE DRAMATIC BEAT

and INDIRECTLY to
SCENE
→ SEQUENCE
→ MACRO STORY BEAT
→ STORY CORE
```

---

# 83. WHAT “STANDARDIZED BEAT/SCENE” MEANS

## Standardized Scene

Must contain:

```text
space
time
participants
objective
opposition
state before
state after
scene turn
spatial contract
beat ordering
```

## Standardized Scene Beat

Must contain:

```text
intention
tactic
action
reaction
resistance/new information
micro-turn
state delta
audience experience target
```

If these are vague, camera will remain vague.

---

# 84. WHY UPSTREAM QUALITY MATTERS

```text
weak Scene
→ weak spatial authority

weak Beat
→ weak dramatic authority

weak Audience Target
→ generic visual intent

generic visual intent
→ random cinematic vocabulary
```

Therefore:

```text
SHOT QUALITY
depends on
UPSTREAM INTENT QUALITY.
```

---

# 85. FINAL STUDIO RULE

Use this exact policy:

```text
BEAT và SCENE phải được khóa trước khi viết SHOT.

Scene xác định:
WHERE / WHEN / WHO / STATE.

Scene Dramatic Beat xác định:
WHAT CHANGES IN THIS MOMENT.

Audience Experience Target xác định:
WHAT THE VIEWER MUST EXPERIENCE.

Directing / Blocking xác định:
HOW PERFORMANCE OCCURS IN SPACE.

Cinematography xác định:
HOW THAT INTENT IS TRANSLATED INTO VISUAL LANGUAGE.

Shot List xác định:
WHICH SHOTS MUST EXIST AND WHY.

Full Shot Spec xác định:
EXACTLY HOW EACH SHOT IS EXECUTED.
```

---

# 86. FINAL CANONICAL DIAGRAM

```text
                        STORY CORE
                            │
                            ▼
                   MACRO STORY BEAT
                            │
                            ▼
                        SEQUENCE
                            │
                            ▼
                          SCENE
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
      SCENE SPATIAL CONTRACT      SCENE DRAMATIC BEAT
                                             │
                                             ▼
                                  AUDIENCE EXPERIENCE
                                             │
                                             ▼
                                     DIRECTING INTENT
                                             │
                                             ▼
                                     BLOCKING / SPACE
                                             │
                                             ▼
                                  CINEMATOGRAPHY OBJECTIVE
                                             │
                                             ▼
                                       SHOT LIST
                                             │
                                             ▼
                                  SHOT ELIGIBILITY GATE
                                             │
                                             ▼
                                     FULL SHOT SPEC
                                             │
                                             ▼
                                       SHOT IR
                                             │
                                             ▼
                                  PROVIDER COMPILATION
```

---

# 87. FINAL DECISION

Canonical architecture is:

```text
MACRO STORY BEAT
→ SEQUENCE
→ SCENE
→ SCENE DRAMATIC BEAT
→ AUDIENCE EXPERIENCE TARGET
→ DIRECTING / BLOCKING
→ CINEMATOGRAPHY
→ SHOT LIST
→ FULL SHOT SPEC
```

The direct authority for camera is:

```text
SCENE DRAMATIC BEAT
+
SCENE SPATIAL CONTRACT
+
AUDIENCE EXPERIENCE TARGET
+
DIRECTING / BLOCKING
```

The indirect story lineage is:

```text
SEQUENCE
+
MACRO STORY BEAT
+
STORY CORE
```

This is the architecture that prevents uncontrolled camera invention while preserving bounded, explainable creative freedom.

---

# 88. MERGE INSTRUCTIONS FOR MASTER DESIGN

During final consolidation:

```text
1. Replace ambiguous persistent term "Beat" with:
   - MacroStoryBeat
   - SceneDramaticBeat

2. Add SceneSpatialDramaticContract.

3. Add AudienceExperienceTarget.

4. Add DirectingIntent + BlockingPlan.

5. Add CinematographyObjective.

6. Add ShotEligibilityGate.

7. Add ShotDecisionTrace.

8. Add camera decision defect codes.

9. Add authority precedence.

10. Add top-down and bottom-up trace tests.

11. Add dependency-based invalidation rules.

12. Update task graph so FullShotSpec cannot be implemented before upstream contracts.
```

---

# 89. ACCEPTANCE CRITERIA

This design is correctly implemented when:

```text
[ ] No persisted generic Beat type exists.
[ ] Every Shot has SceneDramaticBeat binding.
[ ] Every Shot has Scene binding.
[ ] Every Shot has AudienceExperienceTarget binding.
[ ] Every Shot has Directing/Blocking binding.
[ ] Every Shot has CinematographyObjective binding.
[ ] Shot eligibility rejects missing lineage.
[ ] Camera decisions include justification.
[ ] Fixed upstream fields cannot be overridden downstream.
[ ] Variable camera fields obey allowed constraints.
[ ] Random cinematic choices are detected.
[ ] Shot compression reconstructs Beat intent.
[ ] Scene Beat compression reconstructs Scene intent.
[ ] Bottom-up trace reaches Macro Story Beat and Story Core.
```

---

# 90. FINAL ONE-LINE PRINCIPLE

```text
SHOT MUST BE A VISUAL CONSEQUENCE OF A STANDARDIZED SCENE DRAMATIC BEAT,
NOT AN INDEPENDENT CINEMATIC INVENTION.
```

**End of document.**
