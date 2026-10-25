# ADR-0017 — BrainPack and Active Production Profile Authority

## STATUS

**ACCEPTED FOR PRE-MASTER CONSOLIDATION**

Design/authority decision only. No implementation or benchmark evidence is claimed.

## CONTEXT

V0.16 defines Story Brain Packs and a Dynamic Brain Resolver. The post-V0.16 Universal Niche & Composable Brain Architecture expands that concept into reusable Knowledge, Creative, Production, Audience, Format, Platform and QA packs plus a resolved ActiveProductionProfile.

Without an explicit owner split, two policy registries or downstream re-resolution could create divergent effective rules.

## PROBLEM

The Studio needs exactly one answer to:

- where reusable policy/knowledge packs live;
- who resolves inheritance/composition/conflicts;
- what downstream stages consume;
- how project overrides interact with hard constraints and canonical facts;
- how changes invalidate dependent artifacts.

## CANONICAL DECISION

```text
BrainPack Registry
= owner of reusable versioned pack definitions

Profile Resolver
= owner of inheritance + composition + conflict + precedence resolution

ActiveProductionProfile
= immutable resolved/pinned effective snapshot for project/run/version

Downstream systems
= read the pinned ActiveProductionProfile; do not independently re-resolve packs
```

StoryBrainPack is not a parallel registry. It is a typed specialization/composition role inside the universal BrainPack model.

Every effective resolved rule must retain provenance.

## OWNERSHIP

- **BrainPack Registry:** pack definitions, versions, parent relationships, applicability, status and provenance.
- **Profile Resolver:** pack selection, inheritance, merge, conflicts, precedence, project-override validation and resolution trace.
- **ActiveProductionProfile:** authoritative effective policy snapshot consumed downstream.
- **Project/run/version:** pins a specific profile identity/version.
- **Story/Directing/Cinematography/Shot/QA:** consumers, not policy re-resolvers.

## AUTHORITY PRECEDENCE

At minimum:

1. locked canonical facts/invariants and safety/factuality hard constraints;
2. other explicit hard constraints permitted by canonical policy;
3. allowed project locks/overrides;
4. inherited pack policy according to declared precedence;
5. soft preferences;
6. local downstream intent only where policy permits.

**Hard constraints > soft preferences.**

A project override may override only paths that policy declares overrideable. It cannot break a locked canonical fact or immutable invariant.

## INVARIANTS

1. One BrainPack Registry.
2. One Profile Resolver authority for effective composition.
3. One immutable ActiveProductionProfile snapshot per pinned project/run/version context.
4. Downstream stages never silently recompute effective pack policy.
5. Every effective rule records provenance.
6. Hard constraints cannot be weakened by lower-precedence soft preferences.
7. Project overrides are allowlisted/scoped, not unrestricted last-write-wins.
8. Canonical story facts/invariants cannot be altered through profile preference resolution.
9. Profile changes trigger dependency-aware invalidation, not unconditional full regeneration.

## DATA IDENTITY

Canonical identities:

```text
pack_id
pack_version
profile_id
profile_version
resolver_version
project_id
run_id? / production_version?
```

Each resolved field records at least:

```text
effective_path
value
source_pack
source_version
precedence
override_source?
resolution_reason
```

## VERSIONING

- BrainPacks use explicit versions.
- Profile Resolver has an explicit version.
- ActiveProductionProfile is immutable once emitted/pinned.
- any re-resolution that changes effective policy creates a new profile version/snapshot.
- downstream artifacts record the profile ID/version they consumed.

## INVALIDATION

A profile version change computes dependency-aware invalidation from changed effective paths.

Examples:
- dialogue-register change invalidates dependent dialogue/voice/QA artifacts, not unrelated world references.
- factuality-policy change may invalidate research synthesis, claims, narration and their QA.
- cinematography policy change may invalidate dependent shot realization/compile artifacts without rewriting locked StoryCore.

## LEGACY FLOWKIT IMPACT

Current FlowKit material/project/provider flags may be imported as compatibility inputs or projected into profile inputs.

They are not canonical policy authorities after resolution.

## MIGRATION IMPLICATION

- map V0.16 StoryBrainPack into typed BrainPack definitions.
- define one registry namespace/version model.
- route project/user policy inputs into Profile Resolver.
- bind downstream canonical artifacts to ActiveProductionProfile identity/version.
- prevent direct downstream reads of unresolved pack stacks where effective policy is required.

## REJECTED ALTERNATIVES

- separate StoryBrainPack and universal BrainPack registries — rejected.
- downstream subsystem independently selects/re-merges packs — rejected.
- unrestricted project override/last-write-wins — rejected.
- mutable effective profile shared in place — rejected.
- copy all pack contents directly into each downstream artifact without profile identity/provenance — rejected.

## CONSEQUENCES

Positive:
- deterministic policy ownership;
- reproducible runs;
- clear provenance;
- safe inheritance/override semantics;
- selective invalidation.

Cost:
- requires resolver trace and dependency metadata.
- profile changes become explicit version transitions.

## TRACEABILITY SOURCES

- historical V0.16 docs/design/STORY_BRAIN_PACK_SPEC_V0_16.md
- historical V0.16 docs/design/STORY_INTELLIGENCE_ARCHITECTURE_V0_16.md
- historical V0.16 docs/design/STORY_INTELLIGENCE_CANONICAL_CONTRACTS_V0_16.md
- top-level UNIVERSAL_NICHE_COMPOSABLE_BRAIN_ARCHITECTURE_V1_FINAL.md
- PRE_MASTER_CONTRADICTION_REGISTER_V1.md PM-006 / PM-021
