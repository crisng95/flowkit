# ADR-0020 — Shot Identity, Manifest, FullShotSpec and ShotIR Boundary

## STATUS

**ACCEPTED FOR PRE-MASTER CONSOLIDATION**

Design/authority decision only.

## CONTEXT

V0.16 has Shot identity, ShotSpecVersion and ShotIRVersion. Post-V0.16 design introduces ShotListManifest, ShotListItem, ShotEligibilityGate, FullShotSpec and ShotDecisionTrace.

Without a canonical boundary these can become parallel Shot masters.

## PROBLEM

The Studio needs one answer for:

- where canonical Shot identity originates;
- what the shot list owns;
- when eligibility is checked;
- what FullShotSpec owns;
- how legacy ShotSpec maps;
- what ShotIR represents;
- whether provider prompt/request can ever be canonical truth.

## CANONICAL DECISION

```text
ShotListManifest
= ordered collection of ShotListItem references

ShotListItem
= origin of canonical Shot identity

ShotEligibilityGate
= gate before detailed production realization

FullShotSpec
= detailed production realization of the SAME canonical shot_id

ShotIR
= provider-neutral executable representation compiled from resolved canonical inputs

Provider Prompt / Provider Request
= derivative compiled artifacts; never canonical truth
```

ShotListItem owns at minimum:

```text
shot_id
parent_scene_dramatic_beat_id
dramatic_function
coverage_function
reason_for_exist
duration_budget
basic_shot_intent
```

FullShotSpec does not create another Shot identity.

Legacy generic ShotSpec is **deprecated as an independent authority** and must either:
- compatibility-map to FullShotSpec; or
- be migrated/renamed into FullShotSpec during canonical consolidation.

ShotIR owns its own ir_id/version but always references canonical shot_id.

## OWNERSHIP

- **ShotListManifest:** ordering/collection projection.
- **ShotListItem:** canonical Shot identity and basic purpose.
- **ShotEligibilityGate:** eligibility verdict/evidence before detailed realization.
- **FullShotSpec:** complete detailed production realization for one shot_id.
- **ShotIR:** provider-neutral executable representation.
- **Compiler:** transforms FullShotSpec + resolved dependencies into ShotIR/provider derivatives according to canonical compiler rules.
- **Provider Prompt/Request:** provider-specific compiled derivative only.

## AUTHORITY PRECEDENCE

```text
SceneDramaticBeat + upstream dramatic/directing authority
> ShotListItem identity/function
> ShotEligibilityGate
> FullShotSpec
> resolved State / References / ActiveProductionProfile + compiler rules
> ShotIR
> provider-specific compiled prompt/request
> generated artifact
```

Generated artifact cannot retroactively redefine canonical Shot truth without an explicit accepted repair/revision.

## INVARIANTS

1. One canonical shot_id.
2. shot_id originates at ShotListItem.
3. ShotListManifest does not create separate Shot truth.
4. FullShotSpec always references an existing eligible shot_id.
5. FullShotSpec cannot create a second shot identity.
6. no independent canonical generic ShotSpec remains.
7. ShotIR references canonical shot_id.
8. ShotIR is provider-neutral.
9. provider-specific syntax/IDs/parameters are not canonical Shot truth.
10. provider prompt/request is derived and reproducible from canonical inputs/compiler version.
11. ShotIR is derived from FullShotSpec + resolved canonical State + resolved References + pinned ActiveProductionProfile + provider-neutral compiler constraints.

## DATA IDENTITY

Minimum identities:

```text
shot_list_manifest_id/version
shot_id
shot_eligibility_gate_id/version
full_shot_spec_id/version
ir_id/version
compiled_request_id/version?
```

Foreign-key/trace requirements:

```text
ShotListItem.parent_scene_dramatic_beat_id
FullShotSpec.shot_id
ShotIR.shot_id
ShotIR.full_shot_spec_id/version
ShotIR.profile_id/version
ShotIR.resolved_state/version
ShotIR.resolved_reference_bindings/version/hash
```

## VERSIONING

- Shot identity remains stable across spec/IR revisions unless it is intentionally removed/replaced as a narrative shot.
- FullShotSpec revisions create new spec versions for the same shot_id.
- ShotIR revisions create new ir_id/version or IR version bound to the same shot_id and exact input versions.
- compiler/profile/state/reference changes create a new derived IR/compiled request as required; they do not silently mutate prior immutable versions.

## INVALIDATION

- ShotListItem purpose/parent change invalidates its FullShotSpec, IR and compiled provider derivatives.
- FullShotSpec change invalidates dependent IR/provider artifacts.
- resolved State/Reference/Profile change invalidates dependent IR/compiled requests according to dependency graph.
- provider adapter-only transport changes may invalidate provider request artifacts without changing FullShotSpec or narrative Shot identity.

## LEGACY FLOWKIT IMPACT

Current FlowKit Scene/render records may map to compatibility render targets or generation jobs associated with canonical shot_id.

Existing generic ShotSpec terminology in historical design is deprecated as independent authority.

Prompt/image_prompt/video_prompt are compiled/compatibility artifacts, not Shot truth.

## MIGRATION IMPLICATION

Future canonical schema must:

- introduce ShotListItem as canonical shot identity origin;
- add parent_scene_dramatic_beat_id;
- define ShotEligibilityGate contract;
- rename/map ShotSpecVersion into FullShotSpecVersion or a compatibility alias;
- ensure ShotIR references canonical shot_id and exact source versions;
- mark provider prompt/request as derivatives.

## REJECTED ALTERNATIVES

- ShotListManifest stores independent full Shot copies — rejected.
- FullShotSpec allocates a new shot_id — rejected.
- keep legacy ShotSpec as a parallel canonical master — rejected.
- ShotIR becomes provider-specific request body — rejected.
- provider prompt/request becomes source of truth — rejected.
- generated artifact becomes canonical Shot state automatically — rejected.

## CONSEQUENCES

Positive:
- one Shot identity;
- clear planning vs realization vs executable boundaries;
- deterministic lineage;
- provider independence;
- cleaner selective invalidation.

Cost:
- historical ShotSpec references require compatibility mapping during Master consolidation.

## TRACEABILITY SOURCES

- historical V0.16 DATA_MODEL.md
- historical V0.16 API_CONTRACTS.md
- historical V0.16 DESIGN_DRAFT.md
- historical V0.16 REQUIREMENTS.md FR-007 / FR-014 / FR-028
- top-level NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL.md
- top-level BEAT_SCENE_TO_SHOT_AUTHORITY_ARCHITECTURE_V1_FINAL.md
- ADR-0018-NARRATIVE-ARTIFACT-IDENTITY.md
- ADR-0019-DRAMATIC-TO-CAMERA-AUTHORITY.md
- PRE_MASTER_CONTRADICTION_REGISTER_V1.md PM-010 / PM-023
