# CANONICAL MERGE CANDIDATE SET V1

## 0. Purpose

This is the source-selection set for a future Master implementation baseline.

It does NOT create or merge the Master.

Selection is based on:
- explicit authority/supersession text;
- ADR decisions;
- current state/handoff lineage;
- independent review decisions;
- contradiction audit;
- actual contract changes;
- evidence maturity.

The words FINAL and FROZEN do not automatically promote a document.

## A. REQUIRED PRIMARY SOURCES

Count: **27**

These are required inputs to a future Master after the blocking conflicts in section F are resolved.

1. V0.16 docs/design/CANONICAL_DECISION_REGISTRY_V0_10.md
2. V0.16 docs/adr/ADR-0013-SINGLE-SQLITE-WRITE-OWNER.md
3. V0.16 docs/adr/ADR-0014-HYBRID-STORY-INTELLIGENCE-DONOR-ARCHITECTURE.md
4. V0.16 docs/adr/ADR-0015-DESIGN-FREEZE-VS-IMPLEMENTATION-EVIDENCE.md
5. V0.16 docs/design/STORY_INTELLIGENCE_ARCHITECTURE_V0_16.md
6. V0.16 docs/design/STORY_INTELLIGENCE_CANONICAL_CONTRACTS_V0_16.md
7. V0.16 docs/design/STORY_QUALITY_CRITIQUE_REPAIR_V0_16.md
8. V0.16 docs/design/DATA_MODEL.md
9. V0.16 docs/design/API_CONTRACTS.md
10. V0.16 docs/design/JOB_STATE_MODEL_V0_13.md
11. V0.16 docs/design/PERSISTENCE_ARCHITECTURE.md
12. V0.16 docs/design/PERSISTENCE_WRITE_OWNERSHIP_V0_14.md
13. V0.16 docs/design/SECURITY_MODEL.md
14. V0.16 docs/design/PROVIDER_SUBMISSION_RECOVERY_ARCHITECTURE.md
15. V0.16 docs/design/STATIC_QA_ARCHITECTURE.md
16. V0.16 docs/design/TARGETED_REPAIR_ARCHITECTURE.md
17. V0.16 docs/design/OBSERVABILITY_DESIGN.md
18. V0.16 docs/design/UPDATE_MIGRATION_BACKUP_MODEL.md
19. V0.16 docs/design/PERFORMANCE_COST_CONCURRENCY_MODEL.md
20. V0.16 docs/design/EVIDENCE_CLASSIFICATION_POLICY_V0_13.md
21. V0.16 docs/design/REQUIREMENTS.md
22. V0.16 docs/design/REQUIREMENT_TRACEABILITY.md
23. active docs/adr/ADR-0016-CREDENTIAL-AUTHORITY.md
24. active docs/adr/ADR-0017-BRAINPACK-ACTIVE-PRODUCTION-PROFILE-AUTHORITY.md
25. active docs/adr/ADR-0018-NARRATIVE-ARTIFACT-IDENTITY.md
26. active docs/adr/ADR-0019-DRAMATIC-TO-CAMERA-AUTHORITY.md
27. active docs/adr/ADR-0020-SHOT-IDENTITY-SPEC-IR-BOUNDARY.md

Rules:
- use latest content-bearing historical copy, not every byte-identical snapshot copy;
- do not physically deduplicate the historical corpus;
- scoped ADR overrides stale generic prose where conflict exists.

## B. REQUIRED SUPPORTING SOURCES

Count: **17**

1. V0.16 PROJECT_STATE.md — historical maturity/process authority.
2. V0.16 CURRENT_HANDOFF.md — historical next-action/lineage authority.
3. V0.16 docs/design/PROJECT_VISION.md.
4. V0.16 docs/design/DESIGN_DECISION_MATRIX.md.
5. V0.16 docs/design/FLOWKIT_STORY_REPLACEMENT_MAP_V0_16.md.
6. V0.16 docs/design/INDEPENDENT_REVIEW_LOG.md.
7. V0.16 docs/design/IMPLEMENTATION_READINESS.md.
8. V0.16 docs/diagrams/COMPONENT_GRAPH.md.
9. V0.16 docs/diagrams/DATA_FLOW.md.
10. V0.16 docs/diagrams/STORY_INTELLIGENCE_DEPENDENCY_GRAPH_V0_16.md.
11. V0.16 docs/diagrams/STORY_INTELLIGENCE_FLOW_V0_16.md.
12. V0.16 docs/adr/ADR-0005-STATIC-QA-ACCEPTANCE.md.
13. V0.16 docs/adr/ADR-0006-TARGETED-REPAIR.md.
14. V0.16 docs/adr/ADR-0007-PROVIDER-AMBIGUITY-RECOVERY.md.
15. V0.16 docs/adr/ADR-0009-HIERARCHICAL-ADMISSION.md.
16. V0.16 docs/adr/ADR-0010-PROVIDER-SURFACE-EVIDENCE.md.
17. V0.16 docs/adr/ADR-0011-EVIDENCE-CLASS-GATING.md.

Supporting means:
- required for rationale, traceability or evidence boundary;
- not a second canonical owner for the same contract.

## C. OPTIONAL EVIDENCE SOURCES

These should be available during Master consolidation but should not be copied as architecture prose unless needed to support a decision.

Representative required-access evidence set:

- V0.16 docs/research/PROVIDER_CAPABILITY_EVIDENCE_MATRIX_V0_10.md.
- V0.16 docs/research/provider-profiles/*.json.
- Windows persistence Run-1/Run-2 evidence and analyses.
- PROVIDER_AMBIGUITY_PROOF_V0_5.md and simulation results.
- CREDENTIAL_BROKER_PROOF_V0_6.md and simulation results.
- STATIC_QA_POLICY_SPIKE_EVIDENCE_V0_7.md.
- TARGETED_REPAIR_PLANNER_SPIKE_EVIDENCE_V0_7.md.
- PERFORMANCE_COST_CONCURRENCY_SPIKE_EVIDENCE_V0_8.md.
- REAL_IMAGE_STATIC_QA_CALIBRATION_PROTOCOL_V0_9.md.
- REAL_GENERATION_TARGETED_REPAIR_BENCHMARK_PROTOCOL_V0_9.md.
- V0.16 Story 12-round audit, donor decision matrix and source snapshot.
- evidence ledger JSON/Markdown and evidence-gate reports.
- static verification / final static audit reports.

These sources prove or limit claims; they do not independently own the target schema.

## D. SUPERSEDED — DO NOT MERGE AS CURRENT AUTHORITY

1. JOB_STATE_MODEL_V0_10.md current-state semantics.
   - explicitly superseded by JOB_STATE_MODEL_V0_13.md.

2. Generic V0.1 Story Engine sections in DESIGN_DRAFT.
   - explicitly superseded where conflicting by STORY_INTELLIGENCE_ARCHITECTURE_V0_16.

3. Stale generic DESIGN_DRAFT subsystem sections where a dedicated subsystem design/ADR exists.
   - retain only non-conflicting cross-system context.

4. Direct-multiwriter SQLite production topology.
   - superseded by ADR-0013 + single logical write owner.

5. Blanket process rule requiring all live provider/QA/repair/performance gates before coding.
   - superseded by ADR-0015.

6. Generic one-field job status/approval semantics.
   - superseded by four-axis V0.13 job-state model.

7. Brand-level provider capability/quota/cost assumptions.
   - superseded by surface-specific evidence-versioned ProviderProfile.

8. Weighted-average-only QA acceptance.
   - superseded by severity/blocking gate.

9. Generic blind resubmit after ambiguous paid submission.
   - superseded by provider reconciliation/AMBIGUOUS_HOLD model.

10. Parent image as semantic continuity authority.
    - superseded by approved StateSnapshot as semantic authority; parent media remains conditioning/evidence.

11. Prompt prose as canonical generation intent.
    - superseded by ShotSpec + ShotIR + compiler architecture.

12. FlowKit operational Scene as cinematic Scene authority.
    - superseded by Studio cinematic Scene / Shot / GenerationJob mapping.

Historical copies remain untouched.

## E. HISTORICAL ONLY

Logical standalone count: **2**

1. MASTER_STUDIO_OPTIMAL_HYBRID_ARCHITECTURE_V1_FROZEN.md
   - strong frozen pre-V0.16 architecture baseline;
   - use for rationale and donor composition;
   - do not merge wholesale over later scoped ADR/contracts.

2. FLOWKIT_INDEPENDENT_MULTI_ROUND_PRODUCTION_AUDIT_2026-09-20.md
   - evidence for FlowKit strengths/gaps;
   - not Studio contract authority.

Additionally:
- prior physical copies from V0.1–V0.15 remain historical lineage even when byte-identical with V0.16;
- no historical file is deleted or physically deduplicated.

## F. PREVIOUS CONFLICT SOURCES ? RESOLVED BY ACCEPTED PRE-MASTER ADRS

These sources remain mandatory merge inputs, but their blocking authority questions are now resolved by ADR-0016 through ADR-0020. They do not become independent parallel masters.

### F-01 — Universal Niche / Composable Brain

UNIVERSAL_NICHE_COMPOSABLE_BRAIN_ARCHITECTURE_V1_FINAL.md

Reason:
- adds Topic/Niche/Genre/Audience/Format/Platform/Factuality resolution;
- introduces universal BrainPack taxonomy and ActiveProductionProfile;
- overlaps V0.16 StoryBrainPack and project policy authority.

Required decision:
- one BrainPack type hierarchy;
- one profile/project precedence model;
- one version/invalidation owner.

### F-02 — Narrative Expansion Ladder

NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL.md

Reason:
- adds first-class IdeaContract, Logline, MacroBeatSheet, SequencePlan, SceneList, SceneBreakdown, MicroBeats, ScreenplayRealization, ShotBudget, ShotExpansion and ShotListManifest;
- explicitly says old implicit expansion wording must be superseded.

Required decision:
- integrate artifact identities into V0.16 Story canonical contracts;
- avoid duplicate Scene/Sequence/Beat authorities.

### F-03 — Beat/Scene-to-Shot Authority

BEAT_SCENE_TO_SHOT_AUTHORITY_ARCHITECTURE_V1_FINAL.md

Reason:
- explicitly replaces ambiguous persistent Beat with MacroStoryBeat + SceneDramaticBeat;
- adds AudienceExperienceTarget, SceneSpatialDramaticContract, DirectingIntent, BlockingPlan, CinematographyObjective, CoverageStrategy, ShotEligibilityGate, ShotDecisionTrace.

Required decision:
- migrate V0.16 BeatContract/Data Model naming;
- define one canonical Directing/Cinematography/Shot contract chain.

### F-04 — V0.16 Story Brain Pack Spec

V0.16 docs/design/STORY_BRAIN_PACK_SPEC_V0_16.md

Reason:
- valid Story-domain candidate;
- may become a subtype or subset of F-01 universal BrainPack rather than remain a parallel registry.

Required decision:
- no two independent pack registries.

### F-05 — Credential Broker authority status

V0.16 docs/design/CREDENTIAL_BROKER_ARCHITECTURE.md
+ ADR-0008
+ SECURITY_MODEL
vs
V0.16 PROJECT_STATE pending "secret storage method".

Reason:
- subsystem docs clearly specify safeStorage + Main security broker + scoped lease candidate;
- PROJECT_STATE still lists secret storage as pending and is ranked above ADR by the registry's conflict rule.

Required decision:
- either promote the scoped broker design as the Master baseline with packaged proof deferred under ADR-0015;
- or explicitly leave credential storage unresolved and block implementation dependency planning.

## Candidate-set conclusion

The future Master should NOT be assembled by concatenating all latest files.

The correct source process is:

A required primary
+ B supporting rationale
+ selected C evidence
- D superseded semantics
- E historical-only prose
+ F explicit decisions

Only after F is resolved can a Master implementation baseline be safely consolidated.

## G. Accepted blocker-resolution source map

- F-01 Universal Niche / Composable Brain ? resolved by **ADR-0017**.
- F-02 Narrative Expansion Ladder ? identity/manifest authority resolved by **ADR-0018**.
- F-03 Beat/Scene-to-Shot Authority ? dramatic/camera authority resolved by **ADR-0018 + ADR-0019 + ADR-0020**.
- F-04 V0.16 Story Brain Pack ? folded under the one-registry rule of **ADR-0017**; no parallel registry.
- F-05 Credential Broker authority status ? resolved by **ADR-0016**.

The three post-V0.16 documents remain required source material for Master consolidation, but the accepted ADRs own the final authority boundaries.

### Candidate-set gate after blocker resolution

Blocking authority conflicts: **0**.

Non-blocking consolidation gaps remain:
- Compiler responsibility consolidation.
- Sequence QA contract consolidation.

These do not prevent Master consolidation because they do not create competing canonical identity owners.
