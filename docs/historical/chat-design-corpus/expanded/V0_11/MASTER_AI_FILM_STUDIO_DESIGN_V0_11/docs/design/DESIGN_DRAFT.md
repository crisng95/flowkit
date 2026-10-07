# DESIGN_DRAFT.md
# Master AI-Native Visual & Film Studio — Architecture Draft V0.1

**Status:** DRAFT  
**Current maturity:** L5.5 — Reviewed + Partial Hardening Evidence  
**Origin:** V0.1 architecture baseline; later dedicated subsystem designs supersede stale sections.  
**Freeze status:** NOT FROZEN

---

# 1. Architecture Principles

1. Canonical domain is provider-neutral.
2. Shot is the generation unit.
3. Beat owns dramatic change; Shot owns visual execution.
4. Prompt is an output artifact, not source of truth.
5. Continuity is persistent state, not a final-stage checklist.
6. Accepted output becomes state authority only after QA.
7. One responsibility has one authority.
8. Provider adapters cannot mutate story truth.
9. Technical retry is different from creative repair.
10. Failure should return to the earliest responsible layer.
11. Long-form projects must not depend on chat context.
12. Optional complexity (3D, specialized genre packs) stays outside the minimal core.

---

# 2. Architecture Options

## OPTION A — FlowKit-Centric Extended Monolith

```text
FlowKit Project/Scene
+ add Beat fields
+ add State fields
+ add Static QA
+ add more providers
```

### Advantages
- fastest initial implementation;
- maximum reuse of existing FlowKit execution;
- fewer boundaries.

### Problems
- `Scene` remains overloaded;
- prompt fields remain too authoritative;
- provider and domain concerns remain coupled;
- difficult to introduce formal ShotSpec/IR cleanly;
- risks permanent architectural debt.

**Status:** REJECT as target architecture. May be useful as migration starting point only.

---

## OPTION B — Canonical Domain Modular Monolith

```text
Domain Core
├── Story
├── Sequence
├── Scene
├── Beat
├── Shot
├── Entity
├── State
├── ShotSpec
└── ShotIR

Application Modules
├── Story/Director
├── Cinematography
├── Reference
├── Compiler
├── QA
├── Repair
└── Editorial

Runtime
├── Job Orchestrator
├── Dependency Graph
├── Provider Router
└── Adapters
```

All modules run inside one local application/process boundary initially, with durable DB and explicit internal contracts.

### Advantages
- strong boundaries without distributed-system overhead;
- easiest path to local-first desktop;
- provider adapters replaceable;
- unit/component/integration testing straightforward;
- future split into services remains possible.

### Problems
- requires deliberate schema/migration work;
- more up-front design than FlowKit-centric extension;
- cannot simply copy one repo.

**Status:** PREFERRED CANDIDATE.

---

## OPTION C — Service-Oriented Production Pipeline

```text
Story Service
Asset Service
Shot Service
Compiler Service
Orchestrator Service
QA Service
Artifact Service
```

### Advantages
- strong failure isolation;
- independent scale;
- multi-worker deployment natural.

### Problems
- networking, auth, tracing, deployment and versioning complexity;
- premature for local-first single-user/creator workflow;
- much larger operational burden;
- harder desktop packaging.

**Status:** DEFER. Revisit only if multi-machine/team workload proves requirement.

---

# 3. Candidate Decision

**Candidate architecture: OPTION B — Canonical Domain Modular Monolith.**

Reason:

It achieves most of the correctness, testability and extensibility benefits of service boundaries while avoiding service-discovery/network/deployment complexity before it is justified.

This decision is not yet a frozen ADR. It must survive security, persistence, performance and recovery reviews.

---

# 4. High-Level Components

```text
INPUT / INGEST
      ↓
STORY ENGINE
      ↓
FILM BIBLE / PRODUCTION MEMORY
      ↓
NARRATIVE STRUCTURE
Story → Sequence → Scene → Beat
      ↓
DIRECTING ENGINE
      ↓
CINEMATOGRAPHY ENGINE
      ↓
SHOT / 8-LAYER SHOT SPEC
      ↓
STATE + REFERENCE RESOLVER
      ↓
SHOT IR
      ↓
PREFLIGHT VALIDATOR
      ↓
STATIC COMPILER
      ↓
PROVIDER ROUTER
      ↓
GENERATION ORCHESTRATOR
      ↓
STATIC ARTIFACT
      ↓
STATIC QA
  ↙ fail     pass ↘
REPAIR          MOTION COMPILER
  ↑                  ↓
  └──────── VIDEO GENERATION
                      ↓
                  VIDEO QA
                 ↙       ↘
             REPAIR     ACCEPT END STATE
                            ↓
                       NEXT SHOT
                            ↓
                       SEQUENCE QA
                            ↓
                   EDITORIAL / EXPORT
```

---

# 5. Component Responsibilities

## 5.1 Ingest
Owns:
- source documents;
- parsing;
- source version;
- source ranges;
- raw facts.

Does not own:
- story rewriting;
- camera decisions.

## 5.2 Story Engine
Owns:
- causal spine;
- objectives;
- obstacles;
- relationship pressure;
- story facts;
- scene intent;
- rough screenplay.

Does not own:
- provider prompts.

## 5.3 Production Memory / Film Bible
Owns:
- world rules;
- story timeline;
- character state;
- locked facts;
- visual DNA pointer;
- state history.

## 5.4 Narrative Domain
Owns stable:
- sequence;
- scene;
- beat;
- shot IDs and relationships.

## 5.5 Directing Engine
Owns:
- audience endpoint;
- information order;
- performance intention;
- rhythm intent;
- shot function.

## 5.6 Cinematography Engine
Owns:
- camera strategy;
- framing;
- optics;
- movement;
- focus;
- composition;
- lighting strategy;
- decision basis.

## 5.7 Entity/Reference Service
Owns:
- typed entities;
- reference versions;
- canonical/variant references;
- approval state;
- provider-neutral reference roles.

## 5.8 State Engine
Owns:
- approved state snapshots;
- start/end states;
- state deltas;
- continuity inheritance.

## 5.9 ShotSpec
Owns:
- canonical 8 layers;
- all visual constraints required to compile a shot.

## 5.10 Shot IR
Owns:
- provider-neutral executable semantics;
- resolved refs/state;
- QA expectations;
- generation mode candidates.

## 5.11 Compiler
Owns:
- provider-specific prompt/request generation;
- static/motion separation;
- prompt dialect;
- reference ordering.

Does not own:
- story truth;
- new camera decisions.

## 5.12 Provider Router
Owns:
- capability matching;
- model selection;
- fallback;
- unsupported-capability diagnostics.

## 5.13 Orchestrator
Owns:
- job state;
- dependencies;
- concurrency;
- retry;
- resume;
- cancel;
- idempotency;
- invalidation.

## 5.14 Artifact Store
Owns:
- generated artifact metadata;
- hashes/checksums;
- lineage;
- file lifecycle.

## 5.15 QA
Owns:
- observations;
- pass/fail by dimension;
- severity;
- evidence.

Does not own:
- silent creative rewrite.

## 5.16 Repair Engine
Owns:
- root-cause layer;
- preserve set;
- patch set;
- invalidation set;
- recheck scope.

## 5.17 Editorial
Owns:
- selected takes;
- non-destructive timeline;
- audio attachment;
- export manifest.

---

# 6. Canonical Domain

```text
Project
├── StoryVersion[]
├── Sequence[]
│   └── Scene[]
│       └── Beat[]
│           └── Shot[]
├── Entity[]
├── ReferenceAsset[]
├── StateSnapshot[]
├── SpatialBaseline[]
├── ShotSpec[]
├── ShotIR[]
├── GenerationJob[]
├── Artifact[]
├── QAResult[]
└── RepairPlan[]
```

---

# 7. State Authority

Authority order:

```text
1. locked story facts
2. approved entity/reference versions
3. approved state snapshot
4. approved directing/cinematography decision
5. ShotSpec
6. Shot IR
7. compiled provider request
8. candidate artifact
```

A generated artifact becomes an authoritative continuity source only after QA/approval.

---

# 8. ShotSpec — V0.1

```yaml
shot_spec:
  shot_id:
  beat_id:
  scene_id:
  sequence_id:

  intent:
    narrative_function:
    emotional_target:
    audience_distance:
    information_priority:
    rhythm_role:
    decision_basis:

  L1_subject:
    entity_refs: []
    identity_versions: []

  L2_state:
    wardrobe:
    props:
    hair_makeup:
    physical_state:
    state_snapshot_id:

  L3_action:
    start_pose:
    action_path:
    reaction:
    end_pose:
    performance_notes:

  L4_environment:
    location_ref:
    spatial_baseline_id:
    blocking:
    landmarks:
    foreground_midground_background:

  L5_time_atmosphere:
    story_time:
    time_of_day:
    weather:
    atmosphere:

  L6_camera:
    shot_size:
    camera_position:
    camera_height:
    angle:
    distance:
    lens:
    movement:
    movement_phases:
    focus:
    depth_of_field:
    composition:
    screen_direction:

  L7_lighting_style:
    motivated_sources:
    contrast:
    palette:
    material_response:
    project_visual_dna_id:

  L8_continuity:
    parent_shot_id:
    edge_type:
    must_preserve: []
    must_change: []
    forbidden_changes: []
    start_state_id:
    expected_end_state:
```

---

# 9. Dependency Edges

```text
ROOT
CONTINUATION
INSERT
BRANCH
```

### ROOT
Fresh generation anchored to canonical refs/current state.

### CONTINUATION
Uses accepted parent visual state plus canonical refs/current state.

### INSERT
Same story state but different attention/coverage.

### BRANCH
Alternative take/candidate from same approved source state.

---

# 10. Continuity Transform Modes

Replace universal continuation wording with:

```text
PRESERVE
EVOLVE
REFRAME
TRANSFORM
```

Each mode compiles explicit:

```text
must_preserve
must_change
forbidden_changes
```

---

# 11. Generation Job State

V0.10 correction: state is orthogonal. Canonical authority: `JOB_STATE_MODEL_V0_10.md`.

```text
SCHEDULER: QUEUED / WAITING_DEPENDENCY / WAITING_CAPACITY / CLAIMED / RUNNING / TERMINAL
PROVIDER: NOT_SUBMITTED / SUBMITTING / SUBMITTED / POLLING / UNKNOWN_REMOTE_STATE / RECONCILING / AMBIGUOUS_HOLD / REMOTE_SUCCEEDED / REMOTE_FAILED / CANCEL_REQUESTED / REMOTE_CANCELED
ARTIFACT: NONE / STAGING / READY / STALE_RESULT / QUARANTINED / MISSING / REJECTED / APPROVED
CREATIVE: NOT_APPLICABLE / PENDING_QA / QA_RUNNING / QA_FAILED / REPAIR_PENDING / NEEDS_HUMAN_REVIEW / APPROVED / LOCKED / REJECTED
```

A UI summary may be derived but is not the persistence authority.

---

# 12. Static QA

Gate categories:

1. technical;
2. prompt/semantic adherence;
3. identity;
4. state/wardrobe;
5. prop;
6. environment/location;
7. camera/composition;
8. lighting/style;
9. continuity;
10. narrative intent.

Critical/blocking failures cannot be averaged away.

---

# 13. Video QA

Gate categories:

1. identity consistency;
2. prompt/action adherence;
3. motion quality;
4. temporal coherence;
5. composition;
6. start-state compliance;
7. end-state compliance;
8. motion/camera intent;
9. continuity;
10. narrative function.

---

# 14. Targeted Repair

```text
failure
→ classify
→ find earliest responsible owner
→ freeze unaffected accepted decisions
→ patch responsible fields
→ invalidate affected artifacts only
→ recompile
→ regenerate
→ recheck targeted dimensions
```

Example routing:

```text
IDENTITY_MISMATCH        → Reference/L1
WARDROBE_MISMATCH        → State/L2
ACTION_MISMATCH          → L3/Motion compiler
SPATIAL_FAIL             → L4/L8
CAMERA_FAIL              → L6
LIGHTING_STYLE_FAIL      → L7
PARENT_DRIFT             → L8
CAPABILITY_FAIL          → Provider Router
NARRATIVE_INTENT_FAIL    → Directing/Cinematography
```

---

# 15. Provider Boundary

Canonical domain MUST NOT know upload position or provider-specific parameter names.

```text
Shot IR
↓
Provider Capability Match
↓
Provider Compiler
↓
Adapter Request
↓
Transport
```

---

# 16. Migration Strategy from FlowKit Concepts

### Keep
- entity/reference persistence concepts;
- media ID/reference resolution;
- parent-image editing;
- dependency waves;
- queue/retry/resume;
- invalidation;
- video review ideas.

### Replace
- Scene as universal generation unit;
- prompt fields as canonical master;
- untyped `character_names`;
- hard-coded continuation wording;
- visual style as simple prefix lock.

### Adapt
- ROOT/CONTINUATION into richer edge model;
- Flow generation code into provider adapter;
- video reviewer into one QA sensor.

---

# 17. Open Design Questions

1. SQLite vs another embedded DB?
2. Is the product Windows-only or cross-platform?
3. How are provider secrets stored?
4. Is a background local service acceptable?
5. What is target project size: 100, 300, 1000+ shots?
6. What is expected concurrency?
7. How much generated media is retained locally?
8. Are cloud sync/team collaboration goals in v1?
9. What commercial license constraints are mandatory?
10. Which providers must ship in v1?
11. Which providers can be plugin-only?
12. What is the target packaging/update mechanism?

These do not block conceptual architecture, but several block L7 freeze.
