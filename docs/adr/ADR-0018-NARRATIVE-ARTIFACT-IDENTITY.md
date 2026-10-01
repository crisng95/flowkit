# ADR-0018 — Narrative Artifact Identity

## STATUS

**ACCEPTED FOR PRE-MASTER CONSOLIDATION**

Design/authority decision only.

## CONTEXT

V0.16 uses a generic Story → Sequence → Scene → Beat hierarchy. Post-V0.16 design adds explicit narrative expansion artifacts and identifies ambiguity between macro structural beats and intra-scene dramatic beats.

The future Master must prevent planning manifests from becoming duplicate truth stores.

## PROBLEM

Without canonical identity boundaries:

- generic persistent Beat can mean macro structure or scene microchange;
- SceneList can become a second Scene truth;
- SceneBreakdown can become a second Beat truth;
- StructureProfile can accidentally own narrative facts instead of budgets/policy.

## CANONICAL DECISION

Canonical first-class narrative identities are:

```text
StoryCore
→ MacroStoryBeat
→ Sequence
→ Scene
→ SceneDramaticBeat
```

**MacroStoryBeat != SceneDramaticBeat.**

There is **no generic persistent Beat** canonical entity.

Projection/planning artifacts:

```text
SceneListManifest
= ordered manifest/projection referencing canonical Scene IDs

SceneBreakdownManifest
= projection referencing canonical SceneDramaticBeat IDs

StructureProfile
= structure/budget/count-range policy; not narrative truth
```

Narrative hierarchy must trace both directions:

```text
SceneDramaticBeat
→ Scene
→ Sequence
→ MacroStoryBeat
→ StoryCore

StoryCore
→ MacroStoryBeat[]
→ Sequence[]
→ Scene[]
→ SceneDramaticBeat[]
```

## OWNERSHIP

- **StoryCore:** accepted core story truth/version.
- **MacroStoryBeat:** macro structural dramatic movement.
- **Sequence:** dramatic progression container.
- **Scene:** canonical scene identity and scene-level narrative state/change.
- **SceneDramaticBeat:** intra-scene intention/action/reaction/resistance/microchange unit.
- **SceneListManifest:** ordering/projection only.
- **SceneBreakdownManifest:** breakdown/projection only.
- **StructureProfile:** planning policy/budgets, never narrative truth.

## AUTHORITY PRECEDENCE

1. locked StoryCore facts/invariants.
2. canonical parent narrative entity.
3. accepted child narrative entity.
4. manifests/projections.
5. StructureProfile recommendations/budgets.

A manifest cannot mutate canonical entity truth merely by reordering or restating it.

## INVARIANTS

1. no generic persistent Beat authority.
2. MacroStoryBeat and SceneDramaticBeat have distinct IDs/contracts.
3. every Sequence references its macro/story ancestry.
4. every Scene references its Sequence.
5. every SceneDramaticBeat references its Scene.
6. parent-to-children and child-to-parent traversal are both supported.
7. SceneListManifest stores Scene references/order, not duplicate Scene content authority.
8. SceneBreakdownManifest stores SceneDramaticBeat references/projection, not duplicate beat truth.
9. StructureProfile cannot overwrite accepted narrative truth.

## DATA IDENTITY

Minimum identities:

```text
story_core_id
macro_story_beat_id
sequence_id
scene_id
scene_dramatic_beat_id

scene_list_manifest_id/version
scene_breakdown_manifest_id/version
structure_profile_id/version
```

Manifest entries reference canonical IDs.

## VERSIONING

Narrative entities and their accepted versions are versioned independently from manifests.

Changing a manifest layout/order without changing canonical narrative truth does not create new Scene/Beat identities.

A substantive narrative change creates a new version/revision of the affected canonical entity and invalidates dependent projections.

## INVALIDATION

Upstream canonical narrative change invalidates dependent children/projections according to dependency edges.

Manifest-only presentation/order changes invalidate only consumers that depend on that ordering where narrative semantics are unchanged.

StructureProfile change invalidates planning decisions/budgets that depend on it, not already locked narrative facts unless an explicit revision is accepted.

## LEGACY FLOWKIT IMPACT

Current FlowKit Scene remains a compatibility/execution projection and cannot become canonical cinematic Scene truth.

Any legacy generic Beat field/type must migrate to an explicit macro or scene-dramatic meaning; ambiguous persistence is prohibited.

## MIGRATION IMPLICATION

- replace generic persistent Beat contract/table naming in future canonical schema.
- introduce explicit IDs above.
- map old V0.16 BeatContract semantics to SceneDramaticBeat where they describe intra-scene microchange.
- map macro structure artifacts to MacroStoryBeat.
- map SceneList/Breakdown into manifests referencing canonical IDs.

## REJECTED ALTERNATIVES

- keep one generic Beat type with a subtype flag — rejected as canonical persistence because ambiguity remains at authority boundaries.
- SceneList duplicates full Scene truth — rejected.
- SceneBreakdown duplicates independent Beat truth — rejected.
- StructureProfile owns accepted narrative events/facts — rejected.
- FlowKit Scene becomes canonical cinematic Scene — rejected.

## CONSEQUENCES

Positive:
- stable IDs;
- no duplicate narrative truth;
- clear macro vs micro dramatic structure;
- strong traceability into directing/shot systems.

Cost:
- V0.16 generic Beat references require migration during Master contract consolidation.

## TRACEABILITY SOURCES

- historical V0.16 STORY_INTELLIGENCE_ARCHITECTURE_V0_16.md
- historical V0.16 STORY_INTELLIGENCE_CANONICAL_CONTRACTS_V0_16.md
- historical V0.16 DATA_MODEL.md
- top-level NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL.md
- top-level BEAT_SCENE_TO_SHOT_AUTHORITY_ARCHITECTURE_V1_FINAL.md
- PRE_MASTER_CONTRADICTION_REGISTER_V1.md PM-007 / PM-008 / PM-022 / PM-023
