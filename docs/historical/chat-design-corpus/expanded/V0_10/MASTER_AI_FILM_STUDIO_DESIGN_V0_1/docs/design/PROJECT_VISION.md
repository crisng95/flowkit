# PROJECT_VISION.md
# Master AI-Native Visual & Film Studio

**Version:** 0.1 baseline, patched through V0.10  
**Current design maturity:** L5.5 — Reviewed + Partial Hardening Evidence  
**Status:** DRAFT — NOT FROZEN  
**Feature coding:** PROHIBITED until architecture freeze gates are satisfied.

---

## 1. Project Understanding

Build a production-scale AI-native visual and film studio that can accept an idea, outline, screenplay, or existing project state and carry the work through a controlled, inspectable production pipeline.

The system is not intended to be a single giant prompt or a thin UI around one image/video provider. It is intended to be a production system with explicit story structure, directing intent, cinematography decisions, persistent entities and references, shot-level state, provider-independent generation contracts, continuity control, QA, targeted repair, orchestration, resumability, and editorial handoff.

The core creative hierarchy is:

```text
PROJECT
→ STORY
→ SEQUENCE
→ SCENE
→ BEAT
→ SHOT
```

Only `SHOT` is the canonical image/video generation unit.

Each shot is represented by a structured specification rather than by a free-form prompt:

```text
SHOT
→ DIRECTING INTENT
→ CINEMATOGRAPHY DECISION
→ 8-LAYER SHOT SPEC
→ SHOT IR
→ PROVIDER-SPECIFIC COMPILED REQUEST
→ GENERATION
→ QA
→ TARGETED REPAIR
```

---

## 2. Primary Product Goal

Create a studio that can produce high-volume, multi-shot visual/video work while preserving:

- story causality;
- character identity;
- wardrobe and physical state;
- location and prop identity;
- spatial continuity;
- visual style;
- cinematography intent;
- shot-to-shot state;
- production traceability;
- restart/resume capability;
- provider portability;
- measurable QA.

The desired result is not merely “good prompts.” The desired result is a production system in which every accepted artifact can be traced to the story, shot specification, references, state, provider request, QA evidence, and repair history that produced it.

---

## 3. Goals

### G-001 — Idea to production-ready screenplay structure

Support:

```text
Idea / Topic
→ premise
→ story causality
→ character objectives
→ film bible
→ rough screenplay
→ script review
→ script lock
→ sequence
→ scene
→ beat
→ shot
```

The system must distinguish creative reasoning from execution data.

### G-002 — Film-language-aware shot planning

Camera decisions must be motivated by:

- narrative function;
- audience information;
- audience distance;
- character objective;
- blocking;
- spatial relationships;
- rhythm;
- continuity with adjacent shots.

The system must not reduce cinematography to a fixed mapping such as:

```text
sad = close-up
power = low-angle
tension = Dutch angle
```

### G-003 — Strong persistent visual identity

Persistent entities include at least:

- characters;
- locations;
- props;
- recurring visual assets;
- costumes/state variants.

Canonical references must be reusable and versioned.

### G-004 — Long-form continuity

Continuity is a cross-cutting state system, not a post-generation check.

Every shot must have:

```text
approved start state
→ visible action/change
→ expected end state
```

Only an accepted end state may become authority for dependent shots.

### G-005 — Provider-neutral generation architecture

The project model must not be coupled to one model/provider.

Provider adapters should receive a provider-neutral `Shot IR` and compile it to the capabilities and prompt dialect of:

- Google Flow / Veo / image generation routes;
- WAN;
- Seedance;
- Kling;
- other future providers.

### G-006 — Real production orchestration

Support:

- queue;
- dependency graph;
- wave execution;
- retry;
- timeout;
- cancellation;
- idempotency;
- resume;
- skip completed;
- provider rate limits;
- artifact persistence;
- dependency invalidation;
- crash recovery.

### G-007 — Multi-stage QA

Require separate:

- static image QA;
- motion/video QA;
- sequence QA;
- project-level QA.

### G-008 — Targeted repair

A failed field/layer must not cause unrelated accepted decisions to be rewritten.

Example:

```text
L6 camera fails
→ preserve L1–L5 + L7–L8
→ patch L6
→ recompile affected request
→ regenerate
→ recheck L6 and dependencies
```

### G-009 — Evidence-driven status

“Request completed” is not equivalent to “creative output accepted.”

The system must keep technical completion, QA status, user approval, and production lock as separate states.

### G-010 — Scale without losing explainability

The system should work for small clips and scale toward long-form work with hundreds of shots without making chat context the source of truth.

---

## 4. Non-goals

### NG-001
Do not make one LLM prompt the entire architecture.

### NG-002
Do not make a specific image/video model the canonical domain model.

### NG-003
Do not require all projects to use one screenplay formula such as Save the Cat or Hero's Journey.

### NG-004
Do not claim pixel-perfect consistency from prompt wording alone.

### NG-005
Do not make generated assets authoritative before QA/approval.

### NG-006
Do not require 3D previs for every shot.

### NG-007
Do not make AI aesthetic scores the sole creative acceptance criterion.

### NG-008
Do not rewrite the entire product merely because a reference repository uses a different stack.

### NG-009
Do not start production feature coding before the design reaches L7 Frozen Design and implementation gates are explicit.

---

## 5. Target Users

### Primary
AI visual/film creators producing multi-shot content at high volume.

### Secondary
Editors, directors, prompt designers, storyboard artists, production supervisors, and technical operators who need inspectable production state rather than a black-box generation button.

### Advanced
Teams building provider adapters, QA engines, or production automation around the canonical studio contracts.

---

## 6. Core Use Cases

1. Idea → rough screenplay.
2. Existing screenplay → structured production breakdown.
3. Script → sequence/scene/beat/shot.
4. Character/location/prop → canonical reference bible.
5. Beat → cinematography decision → shot specification.
6. ShotSpec → static keyframe request.
7. Approved static frame → motion request.
8. Parent shot → continuity-aware child shot.
9. Generation failure → retry/resume.
10. Creative failure → targeted repair.
11. Regenerated parent → invalidate affected descendants only.
12. Long sequence → sequence QA.
13. Finished shots → editorial/audio/export handoff.
14. Restart application → resume exact production state.

---

## 7. Core Value Proposition

```text
Creative intent
+
explicit production state
+
canonical references
+
provider-neutral contracts
+
durable execution
+
evidence-based QA
+
targeted repair
```

instead of:

```text
prompt
→ model
→ hope
```

---

## 8. Product Boundary

The studio owns:

- project/story production data;
- entity/reference metadata;
- continuity state;
- shot specifications;
- provider-neutral generation intent;
- job orchestration;
- artifact lineage;
- QA and repair state;
- editorial handoff data.

Provider models own neural generation quality.

The studio must not claim that model quality is proprietary intelligence of the orchestration layer.

---

## 9. Initial Constraints

1. Provider APIs and capabilities change frequently.
2. Reference limits vary by model.
3. Video jobs can be slow and expensive.
4. Long-form projects cannot rely on in-memory state.
5. Some reference repositories have GPL/AGPL or restrictive licensing.
6. Creative QA is partly semantic and cannot be reduced to one metric.
7. User may revise previously approved story/asset decisions.
8. Parent visual inheritance can propagate both good state and defects.

---

## 10. Current Design Maturity

**L5.5 — Reviewed + Partial Hardening Evidence**

The product vision originated at L4, but the design has since completed:
- persistence/data/failure-recovery deep design;
- security/contracts/observability/deployment reviews;
- provider ambiguity proof at code/docs/mock level;
- credential broker local security simulation;
- Static QA acceptance-policy spike;
- Targeted Repair planner/invalidation spike;
- 300-shot metadata/scheduler simulation;
- provider capability/quota/billing research;
- cross-document contradiction audit.

Why not L6/L7 yet:
- Windows persistence/update harness has not run on the target Windows machine;
- Electron `safeStorage`/`utilityProcess` proof has not run on target Windows;
- live provider ambiguity fault injection remains open;
- real-image Static QA calibration remains open;
- real-generation Targeted Repair benchmark remains open;
- provider-specific quota/cost observations still need live/account evidence where docs are dynamic.

`PROJECT_STATE.md` is the current maturity authority.
