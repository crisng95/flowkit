# ADR-0019 — Dramatic-to-Camera Authority

## STATUS

**ACCEPTED FOR PRE-MASTER CONSOLIDATION**

Design/authority decision only.

## CONTEXT

V0.16 contains directing/cinematography decisions, while post-V0.16 authority work makes the dramatic-to-visual chain explicit.

A production-scale Studio cannot permit camera/lens/lighting choices to become self-originating style suggestions disconnected from dramatic function.

## PROBLEM

Without a strict chain:

- camera can bypass scene dramatic intent;
- blocking may be owned by multiple documents;
- cinematography can become a parallel narrative authority;
- a Shot can exist without a traceable reason in the story.

## CANONICAL DECISION

Canonical chain:

```text
StoryCore
→ MacroStoryBeat
→ Sequence
→ Scene
→ SceneDramaticBeat
→ AudienceExperienceTarget
→ DirectingIntent
→ SceneSpatialDramaticContract
→ BlockingPlan
→ CinematographyObjective
→ ShotListItem
```

Immediate narrative parent/authority of a Shot is **SceneDramaticBeat**.

Inherited narrative context:
- Scene;
- Sequence;
- MacroStoryBeat;
- StoryCore.

Authority roles:

- **AudienceExperienceTarget:** intended viewer effect/information/tension/expectation.
- **DirectingIntent:** performance, reveal, staging and dramatic presentation intent.
- **SceneSpatialDramaticContract:** dramatic spatial constraints/geography/sightlines/zones.
- **BlockingPlan:** actor/object movement and spatial execution.
- **CinematographyObjective:** visual-language translation of upstream dramatic/directing authority.
- **ShotListItem:** selected shot identity/function.

Camera size, angle, lens, movement, focus, lighting and composition cannot self-author narrative intent.

## OWNERSHIP

- StoryCore/MacroStoryBeat/Sequence/Scene/SceneDramaticBeat own narrative context.
- AudienceExperienceTarget owns viewer-effect target.
- DirectingIntent owns performance/reveal/staging intention.
- SceneSpatialDramaticContract owns spatial dramatic constraints.
- BlockingPlan owns executable actor/object blocking.
- CinematographyObjective owns visual translation objectives.
- ShotListItem owns the chosen shot identity and shot-level dramatic/coverage function.

## AUTHORITY PRECEDENCE

```text
locked narrative truth
> SceneDramaticBeat
> AudienceExperienceTarget
> DirectingIntent
> SceneSpatialDramaticContract
> BlockingPlan
> CinematographyObjective
> ShotListItem basic intent
> FullShotSpec realization
> ShotIR
> provider lowering
```

Downstream representation cannot rewrite upstream dramatic authority.

## INVARIANTS

Hard gates:

```text
NO SCENE DRAMATIC BEAT
→ NO SHOT

NO AUDIENCE EXPERIENCE TARGET
→ NO CINEMATOGRAPHY DECISION

NO DIRECTING/BLOCKING
→ NO FINAL SHOT DESIGN

NO TRACEABLE SHOT FUNCTION
→ NO FULL SHOT SPEC
```

Additional invariants:

1. Shot.parent_scene_dramatic_beat_id is mandatory for canonical narrative shots.
2. cinematography is visual translation, not narrative authority.
3. camera technique must have traceable decision basis.
4. lighting/composition/focus choices must be explainable by upstream objective/constraints or explicit production constraints.
5. inherited narrative context is referenced, not copied into a competing truth store.

## DATA IDENTITY

Canonical/versioned records may include:

```text
audience_experience_target_id/version
directing_intent_id/version
scene_spatial_dramatic_contract_id/version
blocking_plan_id/version
cinematography_objective_id/version
```

Each record traces to scene_dramatic_beat_id and relevant parent IDs/versions.

## VERSIONING

Every accepted downstream authority binds to the exact upstream versions it consumed.

Changing an upstream accepted authority creates a new downstream version or invalidates the dependent artifact.

## INVALIDATION

Examples:

- SceneDramaticBeat change invalidates dependent audience/directing/spatial/blocking/cinematography/shot planning.
- AudienceExperienceTarget change invalidates cinematography and shot choices that depended on the viewer-effect target.
- BlockingPlan change invalidates camera/composition/shot realization dependent on positions/movement.
- CinematographyObjective change invalidates shot realization but not the narrative beat itself.

## LEGACY FLOWKIT IMPACT

FlowKit prompt/camera fields and operational Scene camera language are compatibility inputs/outputs only.

They cannot become canonical DirectingIntent, BlockingPlan or CinematographyObjective merely because a prompt contains camera words.

## MIGRATION IMPLICATION

- replace ambiguous V0.16 blocking_json ownership with explicit BlockingPlan.
- map old DirectingDecision/CinematographyDecision fields into versioned realization records under the authority chain.
- require ShotListItem trace to SceneDramaticBeat.
- compiler/provider layers consume resolved visual authority; they do not invent it.

## REJECTED ALTERNATIVES

- camera model self-selects shots from style priors without dramatic parent — rejected.
- cinematography owns narrative purpose — rejected.
- blocking remains an opaque cinematography JSON field as sole authority — rejected.
- Shot can exist with only a visual prompt and no dramatic function — rejected.

## CONSEQUENCES

Positive:
- explainable shot design;
- prevents decorative/self-originating camera decisions;
- clear invalidation path;
- stronger QA and repair attribution.

Cost:
- more explicit upstream artifacts must be resolved before final shot design.

## TRACEABILITY SOURCES

- historical V0.16 DATA_MODEL.md
- historical V0.16 DESIGN_DRAFT.md
- historical V0.16 REQUIREMENTS.md FR-008
- top-level BEAT_SCENE_TO_SHOT_AUTHORITY_ARCHITECTURE_V1_FINAL.md
- top-level NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL.md
- PRE_MASTER_CONTRADICTION_REGISTER_V1.md PM-009 / PM-023
