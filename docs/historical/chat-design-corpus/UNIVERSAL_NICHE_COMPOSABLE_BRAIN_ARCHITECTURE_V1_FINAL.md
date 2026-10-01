# UNIVERSAL NICHE & COMPOSABLE BRAIN ARCHITECTURE V1 — FINAL DESIGN

**Project:** Enterprise AI-Native Film Studio  
**Subsystem:** Topic → Domain/Niche Resolution → Composable Brain Packs → Active Production Profile → Universal Studio Pipeline  
**Status:** FINAL DESIGN CANDIDATE FOR IMPLEMENTATION BASELINE CONSOLIDATION  
**Core principle:** **ADD PACK, NOT ADD PIPELINE.**

---

# 0. EXECUTIVE SUMMARY

Studio không được triển khai theo kiểu mỗi niche có một workflow riêng:

```text
if niche == horror:
    run_horror_pipeline()

if niche == true_crime:
    run_true_crime_pipeline()

if niche == family_drama:
    run_family_drama_pipeline()
```

Kiến trúc chuẩn phải là:

```text
ANY TOPIC
    ↓
TOPIC INTELLIGENCE
    ↓
DOMAIN / NICHE / GENRE / AUDIENCE / FORMAT / PLATFORM RESOLUTION
    ↓
COMPOSABLE BRAIN PACK RESOLUTION
    ↓
ACTIVE PRODUCTION PROFILE
    ↓
UNIVERSAL STUDIO PIPELINE
    ↓
STORY
→ DIRECTING
→ CINEMATOGRAPHY
→ SHOT
→ GENERATION
→ QA
→ TARGETED REPAIR
→ EDITORIAL
→ EXPORT
```

Điểm khác nhau giữa các niche không nằm ở workflow core. Điểm khác nhau nằm ở:

```text
Knowledge Pack
Creative Brain Pack
Production Style Pack
Audience Pack
Format Pack
Platform Pack
Factuality / Risk Pack
QA Rubric Pack
```

Tất cả được resolve thành một **Active Production Profile** duy nhất, có version, provenance, precedence và conflict-resolution rõ ràng.

---

# 1. NORTH-STAR PRINCIPLES

## 1.1 Universal Core

Một Studio đúng phải có một pipeline thống nhất:

```text
INPUT
→ TOPIC UNDERSTANDING
→ NICHE RESOLUTION
→ ACTIVE BRAIN
→ STORY INTELLIGENCE
→ SCRIPT LOCK
→ DIRECTING
→ CINEMATOGRAPHY
→ SHOT DESIGN
→ 8-LAYER SHOT SPEC
→ SHOT IR
→ COMPILER
→ PROVIDER EXECUTION
→ STATIC QA
→ MOTION QA
→ TARGETED REPAIR
→ STATE COMMIT
→ SEQUENCE QA
→ EDITORIAL
→ FINAL QA
→ EXPORT
```

## 1.2 Variable Intelligence

Những thứ thay đổi theo niche:

```text
what to know
what to prioritize
what to avoid
what makes a strong premise
what makes a strong angle
what research depth is required
what a believable character looks like
what conflict model is appropriate
what pacing curve is appropriate
what emotional rhythm is appropriate
what visual language is appropriate
what QA failures are blocking
```

## 1.3 Golden Rule

```text
NEW NICHE
≠ NEW PIPELINE

NEW NICHE
= NEW COMPOSITION OF PACKS
```

---

# 2. CANONICAL PIPELINE POSITION

Subsystem này nằm trước Story Intelligence:

```text
PROJECT INPUT
    ↓
TOPIC NORMALIZER
    ↓
TOPIC INTELLIGENCE
    ↓
DOMAIN RESOLVER
    ↓
NICHE RESOLVER
    ↓
GENRE / SUBGENRE RESOLVER
    ↓
AUDIENCE RESOLVER
    ↓
FORMAT RESOLVER
    ↓
PLATFORM RESOLVER
    ↓
FACTUALITY / RISK RESOLVER
    ↓
BRAIN PACK SELECTOR
    ↓
BRAIN PACK COMPOSER
    ↓
CONFLICT RESOLVER
    ↓
ACTIVE PRODUCTION PROFILE
    ↓
STORY INTELLIGENCE SYSTEM
```

---

# 3. TOPIC ≠ NICHE

## 3.1 Topic

Topic là nội dung thô mà user muốn làm.

Ví dụ:

```text
“Một người đàn ông trở về quê bán căn nhà sau khi mẹ mất.”
```

## 3.2 Niche Resolution

Resolver phải phân tích thành nhiều chiều:

```text
DOMAIN:
human / family / social

NICHE:
Vietnamese family emotional drama

GENRE:
intimate drama

SUBGENRE:
grief / homecoming / memory

FORMAT:
10-minute cinematic short

AUDIENCE:
Vietnamese adults 25–45

PLATFORM:
YouTube

FACTUALITY:
fiction + cultural realism

EMOTIONAL MODE:
restrained / bittersweet

VISUAL MODE:
grounded cinematic realism
```

## 3.3 Multi-label, không single-label

Một project có thể đồng thời là:

```text
history
+
family drama
+
mystery
+
documentary elements
+
period realism
```

Không được ép:

```text
niche = one string
```

Canonical model phải là tập nhãn có trọng số.

---

# 4. TOPIC INTELLIGENCE MODEL

## 4.1 Canonical Input

```yaml
TopicInput:
  raw_text: string
  language: string | null
  locale: string | null
  user_constraints: []
  target_duration: number | null
  target_platform: string | null
  target_format: string | null
  existing_materials: []
```

## 4.2 Normalized Topic

```yaml
NormalizedTopic:
  topic_id: string
  canonical_topic: string
  primary_subjects: []
  secondary_subjects: []
  people_entities: []
  place_entities: []
  time_periods: []
  explicit_genres: []
  implied_genres: []
  factuality_signals: []
  risk_signals: []
  ambiguity_notes: []
```

## 4.3 Topic Classification Output

```yaml
TopicClassification:
  domains:
    - id: family
      confidence: 0.96
    - id: social_drama
      confidence: 0.81

  niches:
    - id: vietnamese_family_drama
      confidence: 0.92
    - id: grief_homecoming
      confidence: 0.79

  genres:
    - id: intimate_drama
      confidence: 0.91

  subgenres:
    - id: memory_drama
      confidence: 0.74

  audience_candidates: []
  format_candidates: []
  platform_candidates: []
  factuality_class: FICTION_WITH_REALISM
  research_requirement: MEDIUM
  uncertainty: []
```

---

# 5. ACTIVE PRODUCTION BRAIN

Canonical formula:

```text
ACTIVE PRODUCTION BRAIN
=
CORE STORY BRAIN
+
DOMAIN BRAIN
+
NICHE BRAIN
+
GENRE BRAIN
+
AUDIENCE BRAIN
+
FORMAT BRAIN
+
PLATFORM BRAIN
+
RESEARCH BRAIN
+
FACTUALITY BRAIN
+
PRODUCTION STYLE BRAIN
+
PROJECT OVERRIDES
```

Ví dụ:

```text
CORE
+
SCIENCE
+
SPACE DOCUMENTARY
+
EDUCATIONAL MYSTERY
+
GENERAL ADULT
+
12-MIN YOUTUBE
+
YOUTUBE RETENTION
+
HIGH-FACTUALITY
+
CINEMATIC DOCUMENTARY
```

khác hoàn toàn với:

```text
CORE
+
FICTION
+
VIETNAMESE FAMILY DRAMA
+
INTIMATE DRAMA
+
25–45 ADULT
+
10-MIN SHORT FILM
+
YOUTUBE
+
LOW EXTERNAL-FACT DEPENDENCY
+
NATURALISTIC CINEMA
```

Nhưng cả hai vẫn chạy cùng một Universal Studio Pipeline.

---

# 6. PACK TAXONOMY

Kiến trúc chia thành ba nhóm pack chính và bốn nhóm bổ trợ.

## 6.1 LEVEL A — KNOWLEDGE PACK

Trả lời:

```text
“Studio phải biết gì?”
```

Chứa:

```text
domain facts
terminology
source preferences
source exclusions
research depth
citation expectations
uncertainty policy
cultural context
legal/ethical constraints
scientific/historical constraints
factuality requirements
```

## 6.2 LEVEL B — CREATIVE BRAIN PACK

Trả lời:

```text
“Câu chuyện nên được kể như thế nào?”
```

Chứa:

```text
premise grammar
angle strategies
theme models
character psychology priorities
conflict patterns
stakes patterns
causal story patterns
structure profiles
emotional arc profiles
emotional rhythm profiles
scene patterns
beat patterns
dialogue/subtext rules
pacing/tension rules
setup/payoff patterns
anti-patterns
```

## 6.3 LEVEL C — PRODUCTION STYLE PACK

Trả lời:

```text
“Phim nên được thể hiện như thế nào?”
```

Chứa:

```text
directing priors
blocking priors
framing priors
lens priors
camera motion priors
lighting priors
color / atmosphere priors
editing priors
audio priors
music priors
visual realism/stylization priors
motion priors
continuity constraints
```

## 6.4 Audience Pack

Chứa:

```text
audience knowledge
audience expectations
sensitivity
attention profile
cultural assumptions
emotional tolerance
complexity tolerance
language register
```

## 6.5 Format Pack

Ví dụ:

```text
short film
feature film
YouTube 8 min
YouTube 20 min
documentary
vertical short
TV episode
commercial
explainer
```

Chứa:

```text
duration constraints
act/segment expectations
scene density
beat density
hook timing
turn timing
ending expectations
CTA rules if applicable
```

## 6.6 Platform Pack

Ví dụ:

```text
YouTube
TikTok
Reels
Cinema
TV
Streaming
Education
```

Chứa:

```text
retention expectations
first-30-second behavior
aspect ratio
subtitle expectations
safe-area constraints
distribution-specific metadata
```

## 6.7 QA Rubric Pack

Mỗi niche có QA-specific criteria:

```text
blocking criteria
high severity criteria
medium severity criteria
cosmetic criteria
niche-specific anti-patterns
required evidence
```

---

# 7. CANONICAL PACK CONTRACT

Mọi pack phải cùng contract.

```yaml
BrainPack:
  pack_id: string
  pack_type: KNOWLEDGE | CREATIVE | PRODUCTION | AUDIENCE | FORMAT | PLATFORM | QA
  version: semver
  status: DRAFT | VALIDATED | FROZEN | DEPRECATED

  identity:
    name: string
    description: string
    parent_pack_ids: []
    tags: []

  applicability:
    domains: []
    niches: []
    genres: []
    subgenres: []
    audiences: []
    formats: []
    platforms: []
    factuality_classes: []

  policies:
    premise: {}
    angle: {}
    theme: {}
    research: {}
    character: {}
    conflict: {}
    stakes: {}
    structure: {}
    emotion_arc: {}
    emotion_rhythm: {}
    scene: {}
    beat: {}
    dialogue: {}
    pacing: {}
    payoff: {}
    directing: {}
    cinematography: {}
    visual: {}
    audio: {}
    editing: {}
    qa: {}

  hard_constraints: []
  preferences: []
  forbidden_patterns: []
  recommended_patterns: []

  inheritance:
    strategy: MERGE
    override_paths: []
    immutable_paths: []

  provenance:
    source_type: HUMAN | RESEARCH | DONOR_PATTERN | GENERATED | HYBRID
    source_refs: []
    created_at: string
    updated_at: string

  validation:
    benchmark_ids: []
    last_validated_at: string | null
    validation_status: string
```

---

# 8. INHERITANCE MODEL

Ví dụ:

```text
CORE
└── FICTION
    └── DRAMA
        └── FAMILY_DRAMA
            └── VIETNAMESE_FAMILY_DRAMA
                └── GRIEF_HOMECOMING
```

Mỗi tầng chỉ override phần cần thay đổi.

Ví dụ:

```yaml
DRAMA:
  character.depth: HIGH
  scene.state_change_required: true

FAMILY_DRAMA:
  conflict.relationship_weight: HIGH
  dialogue.subtext_weight: HIGH

VIETNAMESE_FAMILY_DRAMA:
  culture.locale: vi-VN
  dialogue.register: LOCAL_NATURALISTIC
  family_hierarchy_awareness: REQUIRED

GRIEF_HOMECOMING:
  emotion.primary: restrained_grief
  payoff.type: memory_acceptance
```

Không được copy lại toàn bộ parent pack.

---

# 9. MERGE STRATEGY

Resolver merge theo property path.

Ví dụ:

```text
core.story.pacing.default
domain.documentary.pacing
genre.slow_burn.pacing
format.youtube_10m.pacing
platform.youtube.retention
project.override.pacing
```

Final value không đơn giản là “last write wins”.

Mỗi field phải có:

```yaml
ResolvedField:
  path: "story.pacing.opening"
  value: "quiet curiosity with early promise"
  source_pack: "youtube_slow_burn_hybrid"
  inherited_from: []
  overridden_sources: []
  resolution_reason: string
  authority: string
```

---

# 10. PRECEDENCE MODEL

Canonical precedence:

```text
1. SAFETY / FACTUALITY LOCKS
2. PROJECT LOCKS
3. CANONICAL STORY FACTS
4. DOMAIN PACK
5. NICHE PACK
6. GENRE PACK
7. FORMAT PACK
8. PLATFORM PACK
9. AUDIENCE PACK
10. SCENE / SHOT LOCAL INTENT
```

Một lower layer không được phá higher authority.

Ví dụ:

```text
Genre Pack:
dramatic reveal

Factuality Pack:
do not present unresolved hypothesis as fact
```

Kết quả:

```text
reveal the hypothesis dramatically
BUT
label it as hypothesis / uncertainty
```

---

# 11. CONFLICT RESOLUTION ENGINE

## 11.1 Conflict Types

```text
VALUE_CONFLICT
PRIORITY_CONFLICT
HARD_CONSTRAINT_CONFLICT
STYLE_CONFLICT
TIMING_CONFLICT
FACTUALITY_CONFLICT
AUDIENCE_CONFLICT
PLATFORM_CONFLICT
```

## 11.2 Example

Input:

```text
Genre:
slow-burn drama

Platform:
YouTube retention

Audience:
older adults

Format:
8 minutes
```

Naive merge:

```text
slow + fast
```

Canonical resolution:

```text
slow-burn emotional storytelling
+
early curiosity promise
+
clear causal progression
+
controlled open loops
+
no hyperactive cutting
```

## 11.3 Conflict Record

```yaml
PolicyConflict:
  conflict_id: string
  paths: []
  sources: []
  severity: LOW | MEDIUM | HIGH | BLOCKING
  resolution_strategy: string
  final_value: any
  explanation: string
```

---

# 12. ACTIVE PRODUCTION PROFILE

Đây là output duy nhất mà downstream pipeline tiêu thụ.

```yaml
ActiveProductionProfile:
  profile_id: string
  version: string
  project_id: string

  topic:
    normalized_topic_id: string

  classification:
    domains: []
    niches: []
    genres: []
    subgenres: []
    audiences: []
    formats: []
    platforms: []

  brain_stack:
    knowledge_packs: []
    creative_packs: []
    production_packs: []
    audience_packs: []
    format_packs: []
    platform_packs: []
    qa_packs: []

  effective_policies:
    research: {}
    premise: {}
    angle: {}
    theme: {}
    character: {}
    conflict: {}
    stakes: {}
    structure: {}
    emotional_arc: {}
    emotional_rhythm: {}
    scene: {}
    beat: {}
    dialogue: {}
    pacing: {}
    payoff: {}
    directing: {}
    cinematography: {}
    visual: {}
    audio: {}
    editing: {}
    qa: {}
    repair: {}

  hard_constraints: []
  forbidden_patterns: []

  provenance:
    resolver_version: string
    pack_versions: {}
    resolved_at: string

  diagnostics:
    ambiguities: []
    conflicts: []
    warnings: []
```

---

# 13. PROFILE VERSION LOCK

Sau khi Story draft bắt đầu:

```text
ACTIVE_PRODUCTION_PROFILE v1.4
```

phải được pin.

Không được để:

```text
writer uses v1.4
camera uses v1.2
QA uses v1.0
```

Mọi downstream artifact phải ghi:

```yaml
profile_binding:
  profile_id: "APP-001"
  profile_version: "1.4.0"
```

Khi profile đổi:

```text
v1.4 → v1.5
```

hệ thống phải tính invalidation.

---

# 14. INVALIDATION RULES

Ví dụ:

```text
change: dialogue register
```

Invalidate:

```text
dialogue drafts
dialogue QA
voice performance notes
```

Không nhất thiết invalidate:

```text
world bible
camera framing
environment references
```

Ví dụ:

```text
change: factuality policy
```

Có thể invalidate:

```text
research synthesis
premise assumptions
script claims
narration
onscreen text
citations
QA
```

Canonical invalidation graph phải dựa trên dependency, không full-regenerate.

---

# 15. UNIVERSAL STORY INTELLIGENCE PIPELINE

Mọi niche dùng cùng pipeline:

```text
PREMISE
→ ANGLE
→ THEME
→ RESEARCH
→ STORY MATERIAL
→ BRAIN RESOLUTION
→ CHARACTER / SUBJECT
→ CONFLICT
→ STAKES
→ CAUSAL STORYGRAPH
→ STRUCTURE
→ EMOTIONAL ARC
→ EMOTIONAL RHYTHM
→ SEQUENCE
→ SCENE
→ BEAT
→ DIALOGUE / SUBTEXT
→ PACING
→ SETUP / PAYOFF
→ DRAFT
→ CRITIQUE
→ TARGETED REPAIR
→ STORY QUALITY GATE
→ SCRIPT LOCK
```

---

# 16. STORY QUALITY MODEL

Canonical quality concept:

```text
STORY QUALITY
=
PREMISE
× ANGLE
× THEME
× RESEARCH
× BRAIN FIT
× CHARACTER DEPTH
× CONFLICT / STAKES
× CAUSALITY
× STRUCTURE
× EMOTIONAL ARC
× EMOTIONAL RHYTHM
× SCENE MOVEMENT
× BEAT MOVEMENT
× DIALOGUE / SUBTEXT
× PACING / TENSION
× SETUP / PAYOFF
× INDEPENDENT CRITIQUE QUALITY
```

Máy không dùng phép nhân thô.

Production evaluation:

```text
HARD BLOCKING GATES
+
BOTTLENECK SCORE
+
GEOMETRIC QUALITY SCORE
```

Critical principle:

```text
BLOCKING defect
cannot be averaged away.
```

---

# 17. NICHE-SPECIFIC STORY POLICIES

## 17.1 True Crime

```yaml
research.depth: EXTREME
source_provenance: MANDATORY
claim_evidence_link: MANDATORY
uncertainty_explicit: true
invented_psychology_as_fact: FORBIDDEN
structure: EVIDENCE_PROGRESSION
tension_source: INFORMATION
dialogue_reconstruction: RESTRICTED
qa:
  chronology: BLOCKING
  unsupported_claim: BLOCKING
  attribution_error: BLOCKING
  speculation_as_fact: BLOCKING
```

## 17.2 Family Drama

```yaml
research.depth: MEDIUM
character_depth: EXTREME
internal_conflict: EXTREME
relationship_conflict: HIGH
subtext: EXTREME
emotional_arc: CENTRAL
emotional_rhythm: CENTRAL
dialogue_style: RESTRAINED_NATURALISTIC
payoff: EMOTIONAL_CONSEQUENCE
qa:
  character_truth: BLOCKING
  emotional_causality: HIGH
  false_sentimentality: HIGH
  unearned_payoff: BLOCKING
```

## 17.3 Science Documentary

```yaml
research.depth: EXTREME
factuality: BLOCKING
claim_provenance: REQUIRED
character: OPTIONAL
conflict_model: QUESTION_UNCERTAINTY_CONSEQUENCE
structure: QUESTION_TO_MODEL_TO_CONSEQUENCE
emotion: WONDER_TO_CONCERN_TO_UNDERSTANDING
dialogue_mode: NARRATION
qa:
  scientific_correctness: BLOCKING
  scale_error: BLOCKING
  causal_error: BLOCKING
```

## 17.4 Horror

```yaml
information_control: EXTREME
reveal_delay: HIGH
tension: EXTREME
dialogue_density: LOW
negative_space: HIGH
audio_dependency: HIGH
emotional_rhythm:
  - dread
  - partial_relief
  - renewed_dread
  - escalation
  - reveal
qa:
  premature_reveal: BLOCKING
  threat_overexposure: HIGH
  tension_flatline: HIGH
```

---

# 18. NICHE PACK CONTENT CHECKLIST

Mỗi niche pack chuẩn phải có:

```text
01 Niche Identity
02 Scope Definition
03 Parent Pack
04 Audience Model
05 Premise Rules
06 Angle Library
07 Theme Profile
08 Research Profile
09 Source Policy
10 Domain Vocabulary
11 Character Model
12 Conflict Model
13 Stakes Model
14 Structure Profiles
15 Emotional Arc Profiles
16 Emotional Rhythm Profiles
17 Scene Patterns
18 Beat Patterns
19 Dialogue / Subtext Rules
20 Pacing Rules
21 Retention Rules
22 Setup / Payoff Rules
23 Visual DNA
24 Directing Priors
25 Cinematography Priors
26 Audio Priors
27 Editing Priors
28 QA Rubric
29 Anti-Patterns
30 Benchmark Cases
31 Inheritance Rules
32 Version / Provenance
```

---

# 19. DYNAMIC BRAIN RESOLVER

## 19.1 Input

```text
Normalized Topic
Project Constraints
User Intent
Existing Script/Bible
Audience
Format
Platform
Research/Factuality Signals
```

## 19.2 Resolver Stages

```text
Stage 1 — classify
Stage 2 — candidate pack retrieval
Stage 3 — applicability scoring
Stage 4 — parent/child expansion
Stage 5 — hard-lock application
Stage 6 — policy merge
Stage 7 — conflict detection
Stage 8 — conflict resolution
Stage 9 — profile validation
Stage 10 — version pin
```

## 19.3 Output

```text
Active Production Profile
+
Resolution Trace
+
Conflict Report
+
Ambiguity Report
```

---

# 20. RESOLUTION TRACE

Không được chỉ output final policy.

Phải trace được:

```yaml
ResolutionTrace:
  path: "dialogue.register"
  final_value: "restrained_local_naturalistic"
  sources:
    - core_drama@1.0
    - family_drama@1.2
    - vietnamese_family_drama@2.1
  overridden:
    - youtube_fast_dialogue@1.0
  reason:
    "Project lock prioritizes naturalistic dialogue; platform retention handled through scene construction instead."
```

---

# 21. AMBIGUITY HANDLING

Nếu classifier không chắc:

```text
horror 0.48
psychological thriller 0.45
family drama 0.43
```

Không được arbitrary pick 1.

Resolver:

```text
retain top candidates
→ build hybrid provisional profile
→ mark uncertainty
→ evaluate first premise/angle outputs
→ resolve with evidence
```

Nếu ambiguity ảnh hưởng blocking policy:

```text
ASK USER
```

Chỉ hỏi khi ambiguity thực sự thay đổi production outcome đáng kể.

---

# 22. UNKNOWN NICHE HANDLING

Mục tiêu là hỗ trợ niche chưa có.

```text
UNKNOWN NICHE
↓
analyze topic
↓
find nearest parent domains
↓
compose existing packs
↓
identify missing expertise
↓
research missing domain
↓
generate provisional pack
↓
independent critique
↓
benchmark
↓
validate
↓
promote to reusable pack
```

State:

```text
PROVISIONAL
→ REVIEWED
→ VALIDATED
→ FROZEN
```

Không auto-promote pack mới chỉ vì một output trông ổn.

---

# 23. SELF-EXPANDING NICHE LIBRARY

Studio có thể tích lũy:

```text
Brain Pack Registry
```

Mỗi project mới:

```text
reuse existing packs
+
create missing delta only
```

Không tạo lại từ đầu.

Registry fields:

```yaml
BrainPackRegistryEntry:
  pack_id: string
  latest_version: string
  parent_ids: []
  validation_score: number
  benchmark_count: number
  projects_used: number
  known_failure_modes: []
  deprecated: boolean
```

---

# 24. PROJECT OVERRIDE LAYER

User/project có quyền override pack.

Ví dụ:

```text
Niche Pack:
family drama = restrained dialogue

Project:
stylized theatrical dialogue
```

Nếu không vi phạm higher lock:

```text
Project override wins.
```

Mọi override phải trace:

```yaml
ProjectOverride:
  path: "dialogue.style"
  old_value: "restrained"
  new_value: "stylized_theatrical"
  reason: string
  author: USER | SYSTEM
  timestamp: string
```

---

# 25. BRAIN PACK REGISTRY

Registry có trách nhiệm:

```text
discovery
version resolution
parent graph validation
cycle detection
deprecation
compatibility
benchmark lineage
pack provenance
```

Không cho inheritance cycle:

```text
A → B → C → A
```

---

# 26. BRAIN PACK COMPATIBILITY

Ví dụ:

```text
true_crime
+
children_audience
```

có thể conflict.

Pack có:

```yaml
compatibility:
  compatible_with: []
  incompatible_with: []
  requires: []
  warns_with: []
```

Resolver phải raise:

```text
BLOCKING compatibility conflict
```

nếu không có safe resolution.

---

# 27. FACTUALITY CLASSES

Canonical:

```text
PURE_FICTION
FICTION_WITH_REALISM
INSPIRED_BY_REAL_EVENTS
DOCUDRAMA
DOCUMENTARY
HISTORICAL_DOCUMENTARY
SCIENCE_EXPLAINER
NEWS_CURRENT_AFFAIRS
TRUE_CRIME
BIOGRAPHICAL
```

Mỗi class có research/claim rules khác nhau.

---

# 28. RESEARCH DEPTH MODEL

```text
R0 — no external research required
R1 — light contextual research
R2 — structured background research
R3 — evidence-backed research
R4 — contradiction-aware source research
R5 — claim-level provenance + disconfirmation
```

Ví dụ:

```text
fiction fantasy → R0/R1
family drama → R1/R2
historical drama → R3
science documentary → R4
true crime → R5
```

---

# 29. RESEARCH → STORY MATERIAL TRANSFORMER

Raw research không được dump vào script.

Pipeline:

```text
RAW SOURCES
↓
CLAIMS
↓
EVIDENCE
↓
CONTRADICTIONS
↓
CONTEXT
↓
HUMAN DETAIL
↓
STORY OPPORTUNITIES
↓
SCENE MATERIAL
```

Canonical output:

```yaml
StoryMaterial:
  fact_id: string
  source_refs: []
  narrative_use: []
  scene_opportunities: []
  emotional_relevance: []
  character_relevance: []
  uncertainty: string
  forbidden_distortions: []
```

---

# 30. CHARACTER POLICY COMPOSITION

Character policy có thể đến từ:

```text
Core Character Brain
+
Domain
+
Genre
+
Audience
+
Niche
```

Ví dụ:

```text
true crime
→ do not invent hidden motives

family drama
→ deep internal contradictions

children story
→ age-appropriate psychological complexity

historical drama
→ social-role constraints
```

---

# 31. CONFLICT MODEL COMPOSITION

Các conflict dimensions:

```text
internal
interpersonal
social
institutional
environmental
moral
epistemic
survival
resource
time
identity
belief
```

Niche pack định trọng số.

---

# 32. STAKES MODEL

Canonical stakes:

```text
physical
emotional
relational
social
financial
moral
existential
epistemic
reputational
temporal
```

Không phải niche nào cũng dùng cùng loại stakes.

---

# 33. STRUCTURE PROFILE SYSTEM

Structure không hard-code một model.

Profiles:

```text
three_act
five_act
hero_journey
mystery_reveal
investigative
procedural
escalation
slice_of_life
nonlinear_memory
parallel_story
essay_documentary
question_answer
case_study
```

Pack chọn:

```text
allowed
preferred
discouraged
forbidden
```

---

# 34. EMOTIONAL ARC VS EMOTIONAL RHYTHM

## Emotional Arc

Macro journey:

```text
DENIAL
→ RESISTANCE
→ DISCOVERY
→ REGRET
→ GRIEF
→ ACCEPTANCE
```

## Emotional Rhythm

Intensity over time:

```text
LOW
↗ MEDIUM
↘ QUIET
↗ HIGH
↓ SILENCE
↗ PEAK
↓ RELEASE
```

Hai engine tách riêng.

---

# 35. SCENE CONTRACT

Mỗi scene:

```yaml
SceneContract:
  scene_id: string
  narrative_function: string
  incoming_state: {}
  objective: string
  opposition: string
  stakes: {}
  information_change: []
  relationship_change: []
  emotional_change: []
  power_change: []
  turn: string
  outgoing_state: {}
  required_payoff_links: []
```

Rule:

```text
NO STATIC SCENE
```

Nếu:

```text
STATE_BEFORE == STATE_AFTER
```

scene cần được review.

---

# 36. BEAT CONTRACT

```yaml
BeatContract:
  beat_id: string
  scene_id: string
  intention: string
  action: string
  reaction: string
  resistance: string
  new_information: string
  micro_change: string
```

---

# 37. DIALOGUE / SUBTEXT POLICY

Dialogue engine không chỉ generate lời nói.

Canonical fields:

```text
speaker objective
surface statement
hidden intention
relationship pressure
knowledge asymmetry
emotional register
voice register
forbidden exposition
subtext target
turn consequence
```

---

# 38. SETUP / PAYOFF LEDGER

```yaml
SetupPayoff:
  setup_id: string
  setup_scene: string
  promise: string
  reinforcement_scenes: []
  complication_scenes: []
  payoff_scene: string | null
  payoff_type: string
  consequence: string | null
  status: PLANTED | REINFORCED | PAID | ABANDONED
```

---

# 39. INDEPENDENT CRITIQUE COUNCIL

Canonical critic roles:

```text
Premise Critic
Angle Critic
Theme Critic
Research Critic
Character Critic
Conflict/Stakes Critic
Causality Critic
Structure Critic
Emotional Critic
Scene/Beat Critic
Dialogue/Subtext Critic
Pacing Critic
Payoff Critic
Audience/Retention Critic
Devil's Advocate
Meta-Critic
```

Không cho writer tự chấm chính mình là authority duy nhất.

---

# 40. TARGETED STORY REPAIR

Pipeline:

```text
DEFECT
↓
ROOT CAUSE
↓
RESPONSIBLE STORY LAYER
↓
MINIMUM REWRITE SCOPE
↓
DEPENDENT INVALIDATION
↓
REWRITE
↓
RE-CHECK
```

Repair modes:

```text
PATCH_LOCAL
REWRITE_BEAT
REWRITE_SCENE
REPLAN_SEQUENCE
REPLAN_ARC
RESEARCH_AGAIN
ESCALATE_TO_PREMISE
```

---

# 41. NICHE-SPECIFIC QA

QA không generic.

Ví dụ Horror:

```text
premature reveal
tension flatline
threat overexposure
sound cue mismatch
```

True Crime:

```text
unsupported claim
chronology error
source attribution
speculation as fact
```

Family Drama:

```text
unearned emotion
generic dialogue
character behavior contradiction
false sentimentality
payoff without setup
```

---

# 42. PRODUCTION STYLE PROPAGATION

Niche không dừng ở script.

```text
NICHE
↓
STORY
↓
DIRECTING
↓
CINEMATOGRAPHY
↓
SHOT DESIGN
↓
STATIC PROMPT
↓
MOTION PROMPT
↓
AUDIO
↓
EDITING
↓
QA
```

Ví dụ Horror:

```text
Story:
withhold information

Directing:
delay confirmation

Camera:
negative space

Lighting:
controlled darkness

Motion:
slow motivated movement

Audio:
off-screen cues

Edit:
hold before reveal

QA:
premature reveal = BLOCKING
```

---

# 43. STORY → FILM BIBLE HANDOFF

Sau Script Lock:

```text
Locked Story Facts
Character Canon
Relationship Graph
Timeline
World Rules
Locations
Props
Wardrobe
Theme/Motif
Setup/Payoff Ledger
Audience Knowledge
Visual DNA
```

được frozen thành Film Bible version.

---

# 44. FILM BIBLE → DIRECTING HANDOFF

Directing Engine nhận:

```text
scene contract
beat contracts
story facts
character states
relationship states
audience knowledge
emotional target
niche production policy
```

Output:

```text
performance intent
blocking intent
information emphasis
reveal strategy
scene rhythm
transition intent
```

---

# 45. DIRECTING → CINEMATOGRAPHY HANDOFF

Cinematography nhận directing intent và Active Production Profile.

Output:

```text
shot function
framing
camera position
lens intent
movement
focus
composition
lighting
color
coverage
```

---

# 46. CINEMATOGRAPHY → SHOT SYSTEM

Canonical hierarchy:

```text
PROJECT
→ STORY
→ SEQUENCE
→ SCENE
→ BEAT
→ SHOT
```

Một Shot:

```text
1 STATIC KEYFRAME SPEC
+
1 MOTION DELTA SPEC
```

---

# 47. 8-LAYER SHOT SPEC

```text
L1 SUBJECT
L2 STATE / WARDROBE
L3 ACTION / PERFORMANCE
L4 ENVIRONMENT
L5 TIME / ATMOSPHERE
L6 CAMERA
L7 LIGHTING / STYLE
L8 CONTINUITY
```

Mỗi field:

```text
FIXED
INHERITED
VARIABLE
```

có provenance và authority.

---

# 48. SHOT IR

Provider-neutral:

```yaml
ShotIR:
  shot_id: string
  beat_ids: []
  entity_ids: []
  reference_bindings: []
  narrative_facts: []
  state_facts: []
  static_observable_state: {}
  temporal_action: {}
  performance: {}
  camera_design: {}
  lighting_design: {}
  continuity_constraints: []
  must_preserve: []
  must_change: []
  forbidden_changes: []
  qa_expectations: []
```

---

# 49. PROVIDER-NEUTRAL RULE

Provider-specific behavior không được trở thành canonical truth.

```text
CANONICAL SHOT IR
↓
PROVIDER COMPILER
↓
PROVIDER REQUEST
```

Không làm ngược:

```text
provider prompt
→ trở thành state authority
```

---

# 50. UNIVERSAL EXECUTION BACKBONE

FlowKit-style Gold Core giữ:

```text
queue
dependency DAG
wave scheduling
retry
resume
skip-completed
invalidation
artifact lineage
parent chaining
generation integration
```

Nhưng không sở hữu Story authority.

---

# 51. PERSISTENCE MODEL

Production metadata:

```text
many producers
→ bounded command queue
→ one logical SQLite write owner
→ SQLite WAL
→ short transactions
```

Generation concurrency và DB write concurrency độc lập.

---

# 52. STATE AUTHORITY

Canonical order:

```text
1 Locked Story Facts
2 Approved Entity / Reference Version
3 Approved State Snapshot
4 Script Lock
5 Directing Decision
6 Cinematography Decision
7 ShotSpec
8 Shot IR
9 Compiled Provider Request
10 Generated Artifact
```

Generated artifact không tự trở thành truth.

---

# 53. ARTIFACT APPROVAL

```text
GENERATE
→ QA
→ APPROVE
→ STATE COMMIT
```

Chỉ `APPROVED_END_STATE` mới đi tiếp làm authority cho shot sau.

---

# 54. NICHE REGISTRY FOLDER STRUCTURE

Recommended logical structure:

```text
brain-packs/
├── core/
├── domains/
│   ├── fiction/
│   ├── science/
│   ├── history/
│   ├── crime/
│   ├── business/
│   └── education/
├── niches/
│   ├── family-drama/
│   ├── true-crime/
│   ├── horror/
│   ├── science-documentary/
│   └── ...
├── genres/
├── audiences/
├── formats/
├── platforms/
├── factuality/
├── production-styles/
└── qa/
```

---

# 55. PACK FILE STRUCTURE

Một pack:

```text
family-drama/
├── pack.yaml
├── premise.md
├── angle.md
├── theme.md
├── character.md
├── conflict.md
├── structure.md
├── emotion.md
├── scene.md
├── beat.md
├── dialogue.md
├── pacing.md
├── payoff.md
├── directing.md
├── cinematography.md
├── qa.md
├── anti_patterns.md
└── benchmarks/
```

Canonical source vẫn là structured contract; markdown là human-readable guidance.

---

# 56. BENCHMARK SYSTEM

Một pack không được coi là validated nếu chưa có benchmark.

Benchmark set tối thiểu:

```text
happy path
edge case
cross-genre case
ambiguous case
adversarial case
anti-pattern case
long-form case
short-form case
```

Outputs được chấm bằng niche-specific QA.

---

# 57. BENCHMARK SUBJECT SET

Studio-level standard benchmark nên bao gồm:

```text
Vietnamese family drama
true crime documentary
historical drama
romance
horror
business documentary
children story
science explainer
YouTube retention documentary
short cinematic film
```

Mục tiêu không phải mọi niche đạt cùng style.

Mục tiêu:

```text
same engine
+
correct niche-specific intelligence
```

---

# 58. ANTI-PATTERN PROTECTION

Pack phải chứa lỗi cần tránh.

Ví dụ generic:

```text
generic premise
generic characters
exposition dialogue
flat scene
random twist
payoff without setup
emotion without cause
research dump
style over story
visual spectacle replacing narrative
```

---

# 59. CROSS-NICHE HYBRID

Ví dụ:

```text
Historical Family Mystery
```

Brain Stack:

```text
history knowledge
+
family drama creative
+
mystery structure
+
period realism production
+
adult audience
+
YouTube long-form
```

Resolver tạo một effective policy duy nhất.

---

# 60. PACK WEIGHTING

Candidate packs có applicability score.

Ví dụ:

```yaml
PackSelection:
  pack_id: family_drama
  applicability: 0.94
  authority_weight: 0.85
  confidence: 0.91
```

Score không dùng để phá hard constraint.

Hard constraint luôn thắng weighted preference.

---

# 61. HARD VS SOFT POLICY

Mỗi policy field:

```text
HARD_LOCK
REQUIRED
PREFERRED
ADVISORY
FORBIDDEN
```

Ví dụ:

```text
true crime:
unsupported claim = FORBIDDEN

family drama:
subtext = PREFERRED
```

---

# 62. POLICY EXPLAINABILITY

Mọi downstream decision quan trọng có thể hỏi:

```text
WHY?
```

Ví dụ:

```text
Why dialogue is restrained?
→ family_drama@2.1
→ vietnamese_family_drama@1.4
→ project_override#7
```

---

# 63. HUMAN OVERRIDE

User có thể:

```text
lock pack
disable pack
override policy
freeze profile
force niche classification
```

Nhưng system cảnh báo khi override gây conflict.

---

# 64. UI MODEL

UI không nên hiển thị hàng trăm fields mặc định.

Recommended layers:

```text
Simple Mode:
Topic
Genre
Audience
Duration
Platform

Advanced Mode:
Resolved Brain Stack
Policy Overrides
Niche Packs
Factuality
Research Depth
QA Profile

Expert Mode:
Full provenance
Conflict report
Inheritance tree
Version pin
Invalidation impact
```

---

# 65. RESOLUTION UX

Ví dụ:

```text
Detected:
Vietnamese Family Drama 92%
Grief/Homecoming 79%
Intimate Drama 91%

Loaded:
Core Story 1.0
Fiction 1.0
Drama 2.2
Family Drama 3.1
Vietnamese Family Drama 2.0
YouTube 10-min 1.4
Adult 25–45 1.0
Naturalistic Cinema 2.3
```

User có thể inspect nhưng không phải chỉnh từng field.

---

# 66. PACK LIFECYCLE

```text
DRAFT
→ REVIEWED
→ BENCHMARKED
→ VALIDATED
→ FROZEN
→ DEPRECATED
```

Không auto-edit frozen pack.

Mọi thay đổi tạo version mới.

---

# 67. MIGRATION

Khi pack v1 → v2:

```text
identify affected projects
compare effective policies
compute invalidation
user chooses:
  stay pinned
  migrate
  partial migrate
```

---

# 68. OBSERVABILITY

Log:

```text
classification decisions
pack selection
conflicts
resolutions
overrides
profile version
policy usage
QA failures by niche
repair outcomes
benchmark performance
```

Không log secrets/raw sensitive data by default.

---

# 69. METRICS

Useful metrics:

```text
niche classification confidence
profile conflict count
pack override count
story QA fail rate by niche
repair success rate
premise rejection rate
scene static-state violation rate
payoff failure rate
research contradiction rate
provider artifact fail rate
```

---

# 70. FEEDBACK LOOP

Production outcomes feed back into pack evaluation:

```text
QA failures
+
repair outcomes
+
human edits
+
benchmark results
↓
Pack Evaluation
```

Nhưng không auto-modify canonical pack without review.

---

# 71. SECURITY / TRUST

External donor repos không trực tiếp trở thành runtime authority.

Rule:

```text
DONOR REPO
→ inspect
→ extract pattern
→ license check
→ adapt/port
→ canonical contract
→ tests
```

Không dynamically execute arbitrary donor code in production.

---

# 72. DONOR REPO ROLE

Current design philosophy:

```text
FlowKit
→ execution skeleton

GPT Researcher
→ deep research patterns

STORM
→ multi-perspective research

Evidence Graph
→ claims / contradiction / skeptic

MoPS
→ premise synthesis concepts

Sabre
→ intentionality / causal planning concepts

StoryDaemon
→ beat / tension / memory / selective repair patterns

Dramatron
→ hierarchical screenplay generation patterns

SOTOPIA
→ social goals / relationship / interaction patterns

Beatlume
→ pacing / tension analytics patterns

Open-Write
→ bible / callbacks / blinded critics / meta-critic / completion verification

OUR STUDIO
→ canonical authority
```

---

# 73. KEEP / ADAPT / EXTRACT / REWRITE POLICY

Allowed decisions:

```text
KEEP
ADAPT
EXTRACT
REWRITE
REPLACE
PATTERN_ONLY
DROP
```

No repo is automatically trusted because it is popular.

---

# 74. FINAL END-TO-END FLOW

```text
ANY TOPIC
    ↓
TOPIC NORMALIZATION
    ↓
MULTI-LABEL CLASSIFICATION
    ↓
DOMAIN / NICHE / GENRE / SUBGENRE
    ↓
AUDIENCE / FORMAT / PLATFORM
    ↓
FACTUALITY / RESEARCH DEPTH
    ↓
PACK CANDIDATE RETRIEVAL
    ↓
PACK INHERITANCE EXPANSION
    ↓
POLICY MERGE
    ↓
CONFLICT RESOLUTION
    ↓
ACTIVE PRODUCTION PROFILE
    ↓
STORY INTELLIGENCE
    ↓
STORY QUALITY GATE
    ↓
SCRIPT LOCK
    ↓
FILM BIBLE
    ↓
DIRECTING
    ↓
CINEMATOGRAPHY
    ↓
SHOT DESIGN
    ↓
8-LAYER SHOT SPEC
    ↓
SHOT IR
    ↓
COMPILER
    ↓
PROVIDER EXECUTION
    ↓
STATIC / VIDEO QA
    ↕
TARGETED REPAIR
    ↓
STATE COMMIT
    ↓
SEQUENCE QA
    ↓
EDITORIAL / AUDIO
    ↓
FINAL FILM QA
    ↓
EXPORT
```

---

# 75. IMPLEMENTATION MODULE MAP

Recommended boundaries:

```text
topic-intelligence/
niche-resolver/
brain-pack-registry/
brain-pack-resolver/
policy-conflict-resolver/
active-profile/
story-intelligence/
film-bible/
directing/
cinematography/
shot-spec/
shot-ir/
compiler/
provider-router/
orchestrator/
qa/
repair/
editorial/
persistence/
observability/
```

---

# 76. MINIMUM IMPLEMENTATION ORDER

```text
P0  Contracts + schemas
P1  Brain Pack Registry
P2  Topic Intelligence
P3  Multi-label Niche Resolver
P4  Pack Inheritance
P5  Policy Merge
P6  Conflict Resolver
P7  Active Production Profile
P8  Story Intelligence integration
P9  Niche QA integration
P10 Production-style propagation
P11 UI inspection/override
P12 benchmark harness
```

Sau đó subsystem mới nối sâu vào Directing/Cinematography/Shot generation.

---

# 77. ACCEPTANCE CRITERIA

Subsystem đạt implementation-ready khi:

```text
[ ] same topic produces deterministic normalized classification contract
[ ] multiple niches can be selected simultaneously
[ ] inheritance graph detects cycles
[ ] hard constraints cannot be averaged away
[ ] precedence conflicts are traceable
[ ] active profile has stable version
[ ] downstream modules consume pinned profile version
[ ] unknown niche can fall back to parent packs
[ ] provisional pack workflow exists
[ ] QA rules vary by niche without branching pipeline code
[ ] profile changes compute invalidation scope
[ ] project overrides are traceable
[ ] donor-specific internals never become canonical authority
```

---

# 78. NON-GOALS

This subsystem does NOT:

```text
replace Story Intelligence
replace provider adapters
replace Shot IR
replace State Engine
replace QA engine
hard-code one genre grammar
hard-code one platform
```

Nó là lớp intelligence composition đứng trước và xuyên suốt toàn bộ Studio.

---

# 79. FINAL CANONICAL RULES

```text
RULE 1
One universal pipeline for every niche.

RULE 2
Niche changes intelligence, not workflow topology.

RULE 3
Add Pack, Not Pipeline.

RULE 4
Multi-label composition, not single-label classification.

RULE 5
Hard constraints beat weighted preferences.

RULE 6
All effective policies must be traceable.

RULE 7
All downstream stages use the same pinned Active Production Profile.

RULE 8
Pack inheritance must be explicit and cycle-free.

RULE 9
Unknown niche falls back compositionally, not via ad-hoc prompt.

RULE 10
New niche packs require validation before becoming canonical.

RULE 11
QA is niche-aware.

RULE 12
Research depth follows factuality/risk.

RULE 13
Production style propagates from story to directing, camera, shot, audio and edit.

RULE 14
Generated artifacts never become canonical truth without QA approval.

RULE 15
External repos are donors, not authority.

RULE 16
Profile changes trigger dependency-based invalidation, not full reset.

RULE 17
User overrides are allowed but must be recorded.

RULE 18
Story quality remains a hard-gated system; no average-away blocking defects.

RULE 19
The resolver explains why every critical policy exists.

RULE 20
The system must scale to hundreds/thousands of niches without creating hundreds/thousands of code paths.
```

---

# 80. FINAL ARCHITECTURE IN ONE DIAGRAM

```text
                           ANY TOPIC
                               │
                               ▼
                    ┌─────────────────────┐
                    │ TOPIC INTELLIGENCE  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  NICHE RESOLVER     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
      ┌─────────────┐  ┌──────────────┐  ┌───────────────┐
      │ KNOWLEDGE   │  │ CREATIVE     │  │ PRODUCTION    │
      │ PACKS       │  │ BRAIN PACKS  │  │ STYLE PACKS   │
      └──────┬──────┘  └──────┬───────┘  └──────┬────────┘
             │                │                  │
             └────────────────┼──────────────────┘
                              ▼
                    ┌─────────────────────┐
                    │  POLICY RESOLVER    │
                    │ inheritance         │
                    │ precedence          │
                    │ conflicts           │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │ ACTIVE PRODUCTION   │
                    │ PROFILE             │
                    │ versioned + pinned  │
                    └──────────┬──────────┘
                               ▼
          ┌───────────────────────────────────────────┐
          │         UNIVERSAL STUDIO CORE             │
          │                                           │
          │ Story Intelligence                        │
          │       ↓                                   │
          │ Script Lock                               │
          │       ↓                                   │
          │ Film Bible / State                        │
          │       ↓                                   │
          │ Directing                                 │
          │       ↓                                   │
          │ Cinematography                            │
          │       ↓                                   │
          │ Shot Design / 8 Layers / Shot IR          │
          │       ↓                                   │
          │ Generation / Orchestration                │
          │       ↓                                   │
          │ QA ↔ Targeted Repair                      │
          │       ↓                                   │
          │ Editorial / Audio / Final QA              │
          │       ↓                                   │
          │ Export                                    │
          └───────────────────────────────────────────┘
```

---

# 81. FINAL DESIGN DECISION

**Canonical decision:**

```text
Studio sẽ không có một pipeline riêng cho từng niche.

Studio sẽ có:
1 Universal Pipeline
+
1 Composable Brain Pack System
+
1 Active Production Profile Resolver
+
Niche-specific QA / Policy / Production Intelligence
```

Đây là kiến trúc cho phép:

```text
mọi topic
→ mọi domain
→ mọi niche
→ mọi genre
→ mọi format
→ mọi platform
```

mà vẫn giữ:

```text
một source of truth
một state model
một authority model
một orchestration core
một QA philosophy
một repair philosophy
```

và chỉ thay đổi intelligence composition theo project.

---

# 82. NEXT STEP AFTER THIS DESIGN

```text
THIS DOCUMENT
↓
FINAL DESIGN CONSOLIDATION
↓
merge into overall Studio authority
↓
IMPLEMENTATION BASELINE FREEZE
↓
DEPENDENCY GRAPH
↓
TASK DECOMPOSITION
↓
TASK_QUEUE
↓
CODE
```

Không mở thêm một pipeline mới cho niche.

Không code feature production trước khi baseline được freeze.

**End of document.**
