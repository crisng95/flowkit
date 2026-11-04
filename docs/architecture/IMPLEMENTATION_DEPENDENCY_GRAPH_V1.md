# IMPLEMENTATION DEPENDENCY GRAPH V1

**Authority:** Frozen Master SHA `1ff9383d713dfaab309d3f36cc83cf05e8932c1bc07f68682e2e12a488c77287`

**Purpose:** Convert the frozen design baseline into an implementation ordering without changing canonical authority.

## 1. Reuse policy

Current FlowKit disposition:
- FastAPI application shell: KEEP + EXTEND
- Flow browser transport / Chrome MV3 bridge: KEEP + EXTEND behind adapter boundaries
- current Entity/reference media lifecycle: KEEP + EXTEND
- current request queue/retry primitives: KEEP + EXTEND behind GenerationJob/Scheduler
- current video review implementation: KEEP + EXTEND as a QA donor
- SQLite repository: ADAPT to frozen one-writer/version/invalidation contracts
- provider layer: ADAPT behind CapabilityRegistry/Router/ProviderAdapter
- current operational Scene: ADAPT only as legacy execution projection
- Story domain: REWRITE as typed canonical domain
- generic Beat runtime: REPLACE with MacroStoryBeat + SceneDramaticBeat
- Shot runtime: REPLACE with ShotListItem/FullShotSpec/ShotIR
- prompt string assembly: REWRITE as compiler/lowering
- continuity: REWRITE as StateSnapshot/ContinuityLedger while retaining media-chain execution utility
- repair: REWRITE as typed localization/RepairPlan
- Electron host/security layer: NEW target layer; current web runtime is not evidence of it

## 2. Global implementation invariants

Every implementation task must preserve:
1. Frozen Master is read-only authority.
2. One canonical owner per responsibility.
3. No generic persistent Beat.
4. ShotListItem is the only canonical shot_id origin.
5. Provider prompt/request is derivative.
6. Generated media is not approved State.
7. Mutable coordination state is separate from immutable semantic versions/history.
8. One logical SQLite writer; no provider/network call inside DB transaction.
9. NO RETRY WITHOUT PROOF.
10. NO QA APPROVAL → NO CANONICAL STATE COMMIT.
11. FlowKit operational Scene never becomes cinematic Scene authority.
12. Every persisted derived artifact binds exact source versions/provenance.
13. Every task carries tests/evidence before dependent tasks may claim PASS.

## 3. Dependency DAG

```text
IMP-001 Frozen-baseline guard
  ├─> IMP-002 Canonical primitives/contracts
  │    ├─> IMP-003 Persistence write-owner + migration foundation
  │    │    ├─> IMP-004 Version/provenance repository primitives
  │    │    │    ├─> IMP-005 DependencyGraph + InvalidationRecord
  │    │    │    └─> IMP-006 Observability/Error/Evidence primitives
  │    │    │
  │    │    ├─> IMP-010 Topic/Domain resolution
  │    │    │    └─> IMP-011 BrainPack Registry
  │    │    │         └─> IMP-012 Profile Resolver
  │    │    │              └─> IMP-013 ActiveProductionProfile
  │    │    │
  │    │    ├─> IMP-040 Canonical Entity versioning adapter
  │    │    │    └─> IMP-041 ReferenceAsset/Resolver
  │    │    │         └─> IMP-042 StateSnapshot/Continuity foundation
  │    │    │
  │    │    └─> IMP-052 GenerationJob four-axis persistence
  │    │         ├─> IMP-053 Scheduler/DAG/leases/admission
  │    │         └─> IMP-054 Retry/Recovery/Ambiguity
  │    │
  │    └─> IMP-020 Story intake primitives
  │         └─> IMP-021 Research/Evidence/StoryMaterial
  │              └─> IMP-022 Character/Relationship/Knowledge
  │                   └─> IMP-023 StoryCore + StoryGraph + lock
  │                        └─> IMP-024 StructureProfile/Budgets/Manifests
  │                             └─> IMP-025 MacroBeat/Sequence/Scene/SceneDramaticBeat
  │                                  └─> IMP-026 Screenplay/Dialogue/SetupPayoff
  │                                       └─> IMP-027 Story Critique/Repair/Quality/ScriptLock
  │                                            └─> IMP-028 NarrativeTrace
  │
  ├──────────────────────── IMP-013 ─┐
  ├──────────────────────── IMP-028 ─┤
  ├──────────────────────── IMP-042 ─┤
  │                                  v
  │                         IMP-030 Audience/Directing/Spatial/Blocking/Cine
  │                                  └─> IMP-031 ShotExpansion/Manifest/ShotListItem
  │                                       └─> IMP-032 Eligibility/FullShotSpec/Static/Motion/Trace
  │                                            └─> IMP-033 ShotIR + Production Compiler
  │
  IMP-033 + IMP-013 + IMP-041
       └─> IMP-050 CapabilityRegistry/ProviderProfile/Router
             └─> IMP-051 Flow/Omni ProviderAdapter anti-corruption
                   └─> IMP-052 GenerationJob integration completion
                         └─> IMP-055 Artifact lifecycle/reconciler

  IMP-032 + IMP-042 + IMP-055
       ├─> IMP-060 Static QA
       ├─> IMP-061 Motion/Video QA
       └─> IMP-062 Continuity + Sequence QA
              └─> IMP-063 Defect localization + Production Repair
                   └─> IMP-064 Approval + State Commit

  IMP-003 + IMP-006
       └─> IMP-070 Electron shell/security baseline
             └─> IMP-071 Typed IPC + Utility bridge
                   └─> IMP-072 Credential Broker/safeStorage leases
                         └─> IMP-073 Renderer/dashboard adaptation

  IMP-005 + IMP-023 + IMP-031 + IMP-052
       └─> IMP-080 Legacy migration/import anti-corruption
             ├─> IMP-081 Legacy Scene → execution projection
             └─> IMP-082 Backup/restore/export migration safety

  Core domains + execution + QA + security + migration
       └─> IMP-100 Full contract regression
             ├─> IMP-101 Migration dry-run
             ├─> IMP-102 Failure/recovery fault injection
             ├─> IMP-103 300-shot scale benchmark
             ├─> IMP-104 Electron security acceptance
             ├─> IMP-105 Packaged clean-install smoke
             ├─> IMP-106 Controlled live provider E2E
             └─> IMP-107 Final product readiness audit
```

## 4. Critical path

```text
IMP-001
→ IMP-002
→ IMP-003
→ IMP-004
→ IMP-005
→ IMP-010
→ IMP-011
→ IMP-012
→ IMP-013
→ IMP-020
→ IMP-021
→ IMP-022
→ IMP-023
→ IMP-024
→ IMP-025
→ IMP-026
→ IMP-027
→ IMP-028
→ IMP-030
→ IMP-031
→ IMP-032
→ IMP-033
→ IMP-050
→ IMP-051
→ IMP-052
→ IMP-053/054
→ IMP-055
→ IMP-060/061/062
→ IMP-063
→ IMP-064
→ IMP-100
→ IMP-107
```

Electron/security and legacy migration run as dependency-constrained parallel lanes after persistence/observability foundations but must close before packaged/product acceptance.

## 5. Parallelizable lanes

After IMP-004:
- Story lane: IMP-020→028
- Entity/Reference/State lane: IMP-040→042
- Job persistence lane: initial IMP-052 repository/state-machine foundation
- Observability lane: IMP-006

After IMP-013 + IMP-028 + IMP-042:
- Directing/Shot lane IMP-030→033

After IMP-033:
- Provider lane IMP-050→051
- Job/scheduler lane IMP-052→055

After artifact + shot/state foundations:
- QA lanes IMP-060, IMP-061, IMP-062 can run independently before IMP-063.

## 6. Dependency rules

- A task may be CLAIMED only when all hard dependencies are VERIFIED.
- A dependent task may use a predecessor interface only after its contract tests PASS.
- Parallel work may not create alternative canonical owners.
- Temporary compatibility adapters must be named and tested as compatibility boundaries.
- Schema changes must be migration-backed and restart-safe before dependent runtime use.
- Provider/live tests never substitute for provider-neutral contract tests.
- Implementation detail may vary, but frozen authority/acceptance semantics may not.

## 7. Completion gate

Implementation dependency graph is complete when every frozen requirement family has:
- a task owner;
- an implementation target;
- dependency edges;
- contract/persistence/interface target;
- tests/evidence;
- acceptance gate;
- migration/compatibility impact where applicable.

The task decomposition document is the executable queue derived from this graph.
