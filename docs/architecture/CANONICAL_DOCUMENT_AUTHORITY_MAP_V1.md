# CANONICAL DOCUMENT AUTHORITY MAP V1

## 0. Status

PRE-MASTER AUTHORITY MAP. This file does not create the Master canonical design.

Authority is assigned from explicit ADR/review/registry/contract lineage, not filename recency or the words FINAL/FROZEN.

## 1. Source aliases

- V16-STATE — expanded/V0_16/.../PROJECT_STATE.md
- V16-HANDOFF — expanded/V0_16/.../CURRENT_HANDOFF.md
- V16-REGISTRY — V0.16 docs/design/CANONICAL_DECISION_REGISTRY_V0_10.md
- V16-STORY — V0.16 docs/design/STORY_INTELLIGENCE_ARCHITECTURE_V0_16.md
- V16-STORY-CONTRACTS — V0.16 docs/design/STORY_INTELLIGENCE_CANONICAL_CONTRACTS_V0_16.md
- V16-STORY-QA — V0.16 docs/design/STORY_QUALITY_CRITIQUE_REPAIR_V0_16.md
- V16-BRAIN — V0.16 docs/design/STORY_BRAIN_PACK_SPEC_V0_16.md
- V16-REPLACEMENT — V0.16 docs/design/FLOWKIT_STORY_REPLACEMENT_MAP_V0_16.md
- V16-DATA — V0.16 docs/design/DATA_MODEL.md
- V16-API — V0.16 docs/design/API_CONTRACTS.md
- V16-DRAFT — V0.16 docs/design/DESIGN_DRAFT.md
- V16-REQ — V0.16 docs/design/REQUIREMENTS.md
- V16-PERSIST — V0.16 docs/design/PERSISTENCE_ARCHITECTURE.md
- V16-SECURITY — V0.16 docs/design/SECURITY_MODEL.md
- V16-CRED — V0.16 docs/design/CREDENTIAL_BROKER_ARCHITECTURE.md
- V16-PROVIDER-RECOVERY — V0.16 docs/design/PROVIDER_SUBMISSION_RECOVERY_ARCHITECTURE.md
- V16-STATIC-QA — V0.16 docs/design/STATIC_QA_ARCHITECTURE.md
- V16-REPAIR — V0.16 docs/design/TARGETED_REPAIR_ARCHITECTURE.md
- V16-OBS — V0.16 docs/design/OBSERVABILITY_DESIGN.md
- V16-MIGRATION — V0.16 docs/design/UPDATE_MIGRATION_BACKUP_MODEL.md
- V16-PERF — V0.16 docs/design/PERFORMANCE_COST_CONCURRENCY_MODEL.md
- V16-EVIDENCE — V0.16 docs/design/EVIDENCE_CLASSIFICATION_POLICY_V0_13.md plus ledger/gate rules
- ADR-0013 — V0.16 docs/adr/ADR-0013-SINGLE-SQLITE-WRITE-OWNER.md
- ADR-0014 — V0.16 docs/adr/ADR-0014-HYBRID-STORY-INTELLIGENCE-DONOR-ARCHITECTURE.md
- ADR-0015 — V0.16 docs/adr/ADR-0015-DESIGN-FREEZE-VS-IMPLEMENTATION-EVIDENCE.md
- POST-NICHE — top-level UNIVERSAL_NICHE_COMPOSABLE_BRAIN_ARCHITECTURE_V1_FINAL.md
- POST-LADDER — top-level NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL.md
- POST-BEAT — top-level BEAT_SCENE_TO_SHOT_AUTHORITY_ARCHITECTURE_V1_FINAL.md
- HYBRID-FROZEN — top-level MASTER_STUDIO_OPTIMAL_HYBRID_ARCHITECTURE_V1_FROZEN.md
- FLOWKIT-AUDIT — top-level FLOWKIT_INDEPENDENT_MULTI_ROUND_PRODUCTION_AUDIT_2026-09-20.md

## 2. Authority map

| DOMAIN | PRIMARY CANONICAL SOURCE (pre-Master candidate) | SUPPORTING SOURCES | SUPERSEDED SOURCES | HISTORICAL SOURCES | CONFLICTING SOURCES | NEEDS_MERGE | Unresolved questions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PROJECT / PROFILE | ADR-0017 | POST-NICHE, V16-REQ, V16-BRAIN | implicit distributed project/material/provider policy in old draft | HYBRID-FROZEN | none | YES ? consolidation only | BrainPack Registry owns definitions; Profile Resolver owns composition/precedence; immutable ActiveProductionProfile is pinned for project/run/version and is the only downstream effective-policy source. |
| TOPIC / NICHE | POST-NICHE | V16-STORY research/brain inputs | none explicit | older Story-only pipeline | none direct | YES | Persisted TopicClassification/NicheResolution IDs and lock timing. |
| BRAIN PACK | ADR-0017 | POST-NICHE, V16-BRAIN, ADR-0014 | ad-hoc prompt-policy composition and parallel pack registries | HYBRID-FROZEN | none | YES ? consolidation only | One BrainPack Registry. StoryBrainPack is a typed specialization/role, not a second registry. Hard constraints and locked invariants outrank soft/project preferences. |
| IDEA | POST-LADDER | V16-STORY, V16-STORY-CONTRACTS | opaque Idea→Script jumps | IDEA_INBOX historical | none direct | YES | Exact IdeaContract schema/ID and acceptance gate. |
| LOGLINE | POST-LADDER | V16-STORY | absent/implicit | none | none | YES | Contract integration into Story canonical contracts. |
| PREMISE | V16-STORY | V16-STORY-CONTRACTS, POST-LADDER | FlowKit weak story field | FLOWKIT-AUDIT | none material | YES | StoryCoreLock relationship to Premise approval. |
| ANGLE | V16-STORY | V16-STORY-CONTRACTS, POST-LADDER | FlowKit weak/not canonical angle | FLOWKIT-AUDIT | none material | YES | Angle lock timing relative to research iteration. |
| THEME | V16-STORY | V16-STORY-CONTRACTS, POST-LADDER | implicit theme prose | FLOWKIT-AUDIT | none material | YES | Theme ambiguity/lock semantics. |
| RESEARCH | V16-STORY | ADR-0014, POST-NICHE factuality/risk packs | generic fact-check-only workflow | FLOWKIT-AUDIT | POST-NICHE adds research-depth/factuality precedence not yet integrated | YES | ResearchPolicy ownership between profile and Story Research Intelligence. |
| CHARACTER | V16-STORY-CONTRACTS | V16-STORY, ADR-0014, V16-DATA Entity links | FlowKit visual entity as full character truth | FLOWKIT-AUDIT | none | NO | Keep production Entity separate from dramatic Character state. |
| RELATIONSHIP | V16-STORY-CONTRACTS | V16-STORY | absent in FlowKit | FLOWKIT-AUDIT | none | NO | Exact dynamic relationship delta/version contract. |
| KNOWLEDGE | V16-STORY-CONTRACTS | V16-STORY, ADR-0014 | visual/reference continuity treated as story knowledge | FLOWKIT-AUDIT | none | NO | Knowledge vs belief vs objective truth linking. |
| BELIEF | V16-STORY-CONTRACTS | V16-STORY | absent in FlowKit | FLOWKIT-AUDIT | none | NO | Misbelief transition model. |
| CONFLICT | V16-STORY | V16-STORY-CONTRACTS, POST-LADDER | free prose conflict | FLOWKIT-AUDIT | none | YES | Map macro conflict to SceneDramaticBeat resistance. |
| STAKES | V16-STORY | V16-STORY-CONTRACTS, POST-LADDER | free prose stakes | FLOWKIT-AUDIT | none | YES | Stakes escalation contract at macro/sequence/scene levels. |
| CAUSAL STORYGRAPH | V16-STORY | V16-STORY-CONTRACTS, ADR-0014 | linear scene order as causality | FLOWKIT-AUDIT | none | NO | StoryGraph edge taxonomy/versioning finalization. |
| MACRO STORY BEAT | ADR-0018 | POST-BEAT, POST-LADDER, V16-STORY | generic persistent Beat terminology | V16 BeatContract as historical precursor | none | YES ? schema consolidation | MacroStoryBeat is a first-class canonical identity distinct from SceneDramaticBeat; no generic persistent Beat. |
| SEQUENCE | ADR-0018 | POST-LADDER, V16-STORY, V16-STORY-CONTRACTS | implicit/overloaded planning representations | HYBRID-FROZEN | none | YES ? consolidation only | Sequence is canonical narrative identity. SequencePlan/manifest artifacts may reference it but cannot become second Sequence truth. |
| SCENE | ADR-0018 | POST-BEAT, V16-STORY SceneContract, POST-LADDER, V16-REPLACEMENT | FlowKit operational Scene as cinematic authority | FLOWKIT-AUDIT | none | YES ? consolidation only | Scene is canonical narrative identity; SceneListManifest references Scene IDs. Legacy FlowKit Scene is compatibility/execution projection only. |
| SCENE DRAMATIC BEAT | ADR-0018 | ADR-0019, POST-BEAT, POST-LADDER, V16-STORY precursor BeatContract | generic BeatContract naming | V16 BeatContract as historical precursor | none | YES ? schema consolidation | SceneDramaticBeat is the intra-scene canonical dramatic unit and immediate narrative authority/parent for Shot. ADR-0019 consumes this identity for the dramatic-to-camera chain. No generic persistent Beat. |
| AUDIENCE EXPERIENCE TARGET | POST-BEAT | POST-NICHE Audience Pack, V16-STORY emotion/rhythm | implicit emotional target prose | HYBRID-FROZEN | no direct contradiction | YES | Numeric relative targets vs qualitative contract representation. |
| SCREENPLAY | POST-LADDER | V16-STORY, V16-STORY-CONTRACTS | prompt/narrator text as screenplay substitute | FLOWKIT-AUDIT | none | YES | ScreenplayRealization artifact format and canonical script serialization. |
| SCRIPT LOCK | V16-STORY-CONTRACTS | V16-STORY, POST-LADDER | implicit accepted script | FLOWKIT-AUDIT | none | YES | Lock invalidation when upstream profile/research changes. |
| DIRECTING | ADR-0019 | POST-BEAT, V16-DATA/V16-DRAFT historical decision fields | camera/prompt prose as implicit directing authority | HYBRID-FROZEN | none | YES ? consolidation only | DirectingIntent owns performance/reveal/staging intention downstream of SceneDramaticBeat and AudienceExperienceTarget. |
| SPATIAL CONTRACT | ADR-0019 | POST-BEAT, V16-DATA state/location | free-form spatial/blocking prose | HYBRID-FROZEN | none | YES ? consolidation only | SceneSpatialDramaticContract owns spatial dramatic constraints; it is upstream of BlockingPlan and camera realization. |
| BLOCKING | ADR-0019 | POST-BEAT, V16-DATA historical blocking_json | blocking embedded in cinematography/prompt prose | HYBRID-FROZEN | none | YES ? consolidation only | BlockingPlan uniquely owns actor/object movement and spatial execution. |
| CINEMATOGRAPHY | ADR-0019 | POST-BEAT, V16-DATA, V16-REQ, HYBRID-FROZEN | self-originating camera technique selection | FLOWKIT-AUDIT | none | YES ? consolidation only | CinematographyObjective is visual-language translation of dramatic/directing authority; it is not narrative authority. |
| COVERAGE | POST-BEAT | POST-LADDER Shot Expansion, V16-REQ Sequence QA | ad-hoc multi-angle prompts | FLOWKIT-AUDIT | no existing first-class coverage owner | YES | CoverageStrategy schema and relation to ShotBudget. |
| SHOT LIST | ADR-0020 | POST-BEAT, POST-LADDER, V16-DATA | FlowKit Scene list as shot list; duplicate shot masters | FLOWKIT-AUDIT | none | YES ? consolidation only | ShotListManifest is an ordered collection/projection; ShotListItem is the origin of canonical shot_id. |
| SHOT ELIGIBILITY | ADR-0020 | POST-BEAT, V16-REQ/provider capabilities/continuity | implicit feasibility checks | HYBRID-FROZEN | none | YES ? consolidation only | ShotEligibilityGate must pass before FullShotSpec production realization. |
| FULL SHOT SPEC | ADR-0020 | POST-BEAT, V16-DATA historical ShotSpecVersion, V16-REQ, POST-LADDER | prompt-as-master and independent legacy ShotSpec authority | FLOWKIT-AUDIT | none | YES ? schema consolidation | FullShotSpec is detailed realization of the same canonical shot_id. Legacy generic ShotSpec is deprecated/compatibility-mapped and has no independent authority. |
| SHOT DECISION TRACE | POST-BEAT | V16-DATA dependency edges, V16-OBS correlation | no persistent rationale trace | HYBRID-FROZEN | absent from V16 canonical contracts | YES | Required trace fields and invalidation behavior. |
| SHOT IR | ADR-0020 | V16-DATA, V16-API, V16-DRAFT, POST-BEAT | raw prompt/provider request as intent | FLOWKIT-AUDIT | none | YES ? consolidation only | ShotIR has its own ir_id/version, always references canonical shot_id, and is provider-neutral executable representation derived from FullShotSpec + resolved State/References + pinned ActiveProductionProfile + compiler rules. |
| ENTITY | V16-DATA | V16-REPLACEMENT, FlowKit current-state audit | character table as universal ontology | FLOWKIT-AUDIT | none | NO | Entity vs dramatic Character linkage remains explicit. |
| REFERENCE | V16-DATA | V16-STATIC-QA, HYBRID-FROZEN, FlowKit execution evidence | one-current-media-id as canonical reference authority | FLOWKIT-AUDIT | none conceptual | NO | ReferenceBible naming vs ReferenceAsset/role bundle naming can be normalized during Master. |
| STATE | V16-DATA | V16-DRAFT, V16-STATIC-QA, V16-REGISTRY D-005 | parent image as semantic state | FLOWKIT-AUDIT | none conceptual | NO | StateSnapshot type partitions and approval/lock rules. |
| CONTINUITY | V16-DATA | V16-DATA dependency constraints, V16-STATIC-QA, V16-DRAFT, V16-REGISTRY D-005 | parent image as continuity authority | FLOWKIT-AUDIT | none conceptual | NO | StateSnapshot is semantic authority; dependency/continuity constraints and accepted parent artifacts are referenced conditioning/evidence, not a second truth store. |
| COMPILER | V16-DRAFT | V16-DATA ShotIR/CompiledRequest, V16-API | prompt as source of truth | FLOWKIT-AUDIT | no dedicated Compiler Architecture document | YES | Dedicated ownership, compile stages, diagnostics/hash contract. Important but can be resolved during Master. |
| PROVIDER | V16-API | provider profiles, V16-REGISTRY, ADR-0010, V16-PERF | brand-level timeless provider facts | older research examples | none conceptual | NO | ProviderProfile schema version binding and live evidence refresh policy. |
| ROUTER | V16-DRAFT | V16-API capability profile, V16-PERF admission | provider-specific selection hidden in adapters | FLOWKIT-AUDIT | no dedicated Router document | YES | Routing objective function and degradation policy owner. |
| QUEUE | V16-DRAFT | V16-PERF, ADR-0009, FlowKit execution donor | FlowKit queue as complete Studio orchestration | FLOWKIT-AUDIT | none | NO | Map queue jobs to ProductionRun/PlanNode after Master. |
| ORCHESTRATION | V16-DRAFT | V16-PERF, V16-DATA GenerationJob/DependencyEdge, ADR-0009 | skill/procedural pipeline as authority | FLOWKIT-AUDIT | no dedicated Orchestrator document | YES | ProductionRun/PlanNode/Attempt contracts and persistent DAG. |
| RETRY | V16-PROVIDER-RECOVERY | V16-PERSIST, V16-FAILURE_RECOVERY_MODEL, ADR-0007 | blind generic retry | FLOWKIT-AUDIT | technical retry vs creative repair must remain separate | NO | Per-provider retry classifications. |
| RESUME | V16-FAILURE_RECOVERY_MODEL | V16-PERSIST, V16-PROVIDER-RECOVERY, FlowKit operation re-poll evidence | only skill-level stage resume | FLOWKIT-AUDIT | none | NO | Exact checkpoint model for ProductionRun/PlanNode. |
| PERSISTENCE | V16-PERSIST | ADR-0013, PERSISTENCE_WRITE_OWNERSHIP_V0_14, Windows Run-2 evidence | direct multiwriter production topology | Run-1 FAIL kept as evidence | V16 PROJECT_STATE still lists target Windows SQLite evidence as blocker despite saying gate closed | NO | Treat design gate closed; later implementation/performance acceptance remains. Documentation cleanup needed, not conceptual blocker. |
| ARTIFACT | V16-DATA | V16-PERSIST, V16-API, JOB_STATE_MODEL_V0_13 | artifact READY conflated with creative APPROVED | older job-state model | none | NO | Artifact bytes vs metadata ownership fully explicit in Master. |
| QA | V16-STATIC-QA | ADR-0005, V16-STORY-QA, V16-DATA QAResult | provider success/weighted average as PASS | FLOWKIT video QA as donor | broad QA domains need shared envelope | YES | Common QA Finding/Evidence/Gate contract across Story/Static/Motion/Sequence. |
| REPAIR | V16-REPAIR | ADR-0006, V16-STORY-QA, POST-NICHE invalidation | retry/full regeneration as repair | FLOWKIT repair heuristics | Story repair and generation repair share concepts but have different targets | YES | Shared RepairPlan envelope vs domain-specific planners. |
| SEQUENCE QA | V16-DRAFT | V16-REQ FR-026, POST-BEAT coverage, POST-LADDER sequence gates | only per-shot QA | HYBRID-FROZEN | no dedicated Sequence QA document | YES | Sequence QA dimensions, authority and approval interaction. |
| SECURITY | V16-SECURITY | ADR-0016, historical ADR-0004/0008, V16-CRED | renderer/raw filesystem/secrets and ambiguous secret ownership | HYBRID-FROZEN | none | NO | V16-SECURITY owns the broader security model; ADR-0016 uniquely owns credential authority within that model. Packaged platform proof remains later implementation acceptance. |
| CREDENTIAL BROKER | ADR-0016 | V16-CRED, V16-SECURITY, historical ADR-0004/0008 | Renderer/Utility/legacy FlowKit as long-lived secret owner | credential simulation evidence | none | YES ? consolidation only | HOST SECURITY BROKER is canonical credential authority. Electron Main + safeStorage owns long-lived secret; Utility receives scoped short-lived lease; Renderer cannot read/hold long-lived secret; FlowKit auth is compatibility adapter only. |
| OBSERVABILITY | V16-OBS | V16-API events, V16-DATA | event log as current-state authority | older logging prose | none | NO | Metrics retention/export policy. |
| MIGRATION | V16-MIGRATION | V16-PERSIST, migration spikes | update without provider-job reconciliation | older baseline | none | NO | Version compatibility window and rollback policy final values. |
| BENCHMARK | V16-PERF | Static QA and repair benchmark protocols, evidence ledger | synthetic/local result treated as production proof | old maturity claims | none conceptual | NO | Targets/calibration remain implementation/release acceptance under ADR-0015. |
| EVIDENCE GOVERNANCE | V16-EVIDENCE | ADR-0011, evidence ledger, gate rules, gate board as derived | harness/readiness prose treated as proof | V0.12 harness-only claims | none | NO | Master should preserve class distinction and hash binding. |

## 3. Authority principles extracted from corpus

1. Story truth belongs to Studio-owned structured Story contracts, never donor repositories or provider prompts.
2. FlowKit remains an execution/reference/continuity donor, not cinematic Scene/Story authority.
3. Prompt strings are compiled artifacts; ShotSpec/ShotIR structured state owns generation intent.
4. StateSnapshot is semantic continuity authority; parent media is conditioning/evidence.
5. Provider facts are profile/evidence-versioned, not timeless brand constants.
6. Current-state database rows are operational authority; event logs are audit/observability evidence.
7. Artifact materialization and creative approval are separate state axes.
8. Ambiguous paid submission is not a generic retry condition.
9. BLOCKING QA findings cannot be averaged away.
10. Third-party story repos are donors, not canonical truth stores.

## 4. Primary-source uniqueness check

After ADR-0016 through ADR-0020:

- credential authority has one primary owner: ADR-0016 / Host Security Broker;
- BrainPack/Profile authority has one primary owner: ADR-0017;
- narrative identity has one primary owner: ADR-0018;
- dramatic-to-camera authority has one primary owner: ADR-0019;
- Shot identity/spec/IR boundary has one primary owner: ADR-0020.

No requested domain retains an ambiguous dual PRIMARY authority.

Remaining open work is consolidation detail, not canonical-owner ambiguity:
- dedicated Compiler responsibility section;
- dedicated Sequence QA contract section.

These remain non-blocking because existing sources do not compete for the same canonical identity.

## 5. Authority-map conclusion

The five blocking authority groups are resolved by ADR-0016 through ADR-0020.

The pre-Master authority map now has:
- one credential authority;
- one BrainPack/Profile resolution authority chain;
- explicit StoryCore?MacroStoryBeat?Sequence?Scene?SceneDramaticBeat identities;
- one dramatic?directing?camera authority chain;
- one canonical Shot identity origin and clear FullShotSpec/ShotIR/provider-derivative boundaries.

Remaining Compiler and Sequence QA consolidation details are non-blocking.

This authority map is ready to serve as an input to a later Master consolidation step. It is not itself the Master.
