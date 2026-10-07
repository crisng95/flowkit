# IMPLEMENTATION TASK DECOMPOSITION V1

**Authority:** Frozen Master SHA `1ff9383d713dfaab309d3f36cc83cf05e8932c1bc07f68682e2e12a488c77287`
**Dependency graph:** `docs/architecture/IMPLEMENTATION_DEPENDENCY_GRAPH_V1.md`

## Execution law

Every task follows:

`CLAIM â†’ ANALYZE â†’ PLAN â†’ CODE â†’ TEST â†’ EVIDENCE â†’ VERIFY â†’ PASS â†’ COMMIT â†’ PR/PUSH â†’ REVIEW â†’ MERGE MAIN â†’ MAIN VERIFIED â†’ NEXT TASK`

A task cannot be marked PASS from document presence alone. Runtime/code tasks require executable evidence appropriate to the claim.

---

## FOUNDATION LANE

### IMP-001 â€” Frozen Baseline Guard
**Depends:** none
**Goal:** prevent silent Master drift after freeze.
**Targets:** durable verification utility/test + freeze manifest integration.
**Deliverables:** checker verifies canonical Master path, expected SHA, freeze manifest consistency and fails closed on mismatch.
**Tests:** pass on frozen SHA; fail on altered fixture/copy; path-missing failure.
**Evidence:** command output with expected/actual SHA.
**Done:** guard is part of normal test/CI path and does not edit the Master.

### IMP-002 â€” Canonical Contract Primitives
**Depends:** IMP-001
**Goal:** shared IDs, version refs, provenance, lifecycle/gate/result value objects.
**Targets:** new provider-neutral `agent/studio/` package (exact package placement may adapt to repo conventions without changing authority).
**Deliverables:** typed primitives for logical ID/version, source-version binding, provenance, gate verdict, finding severity, immutable semantic record metadata.
**Tests:** serialization, equality, invalid ID/version/provenance rejection, no provider fields in canonical primitives.
**Done:** later domains depend on these primitives rather than duplicating metadata shapes.

### IMP-003 â€” One-Writer Persistence / Migration Foundation
**Depends:** IMP-002
**Reuse:** current SQLite repository.
**Goal:** frozen SQLite WAL/FULL/foreign_keys + one logical writer contract.
**Deliverables:** repository write command boundary, bounded queue, optimistic revision/CAS helpers, migration table/version gate, no-network-in-transaction invariant.
**Tests:** serialized writes, CAS conflict, bounded pressure, migration compatibility, foreign keys, WAL/FULL checks.
**Done:** one writer owns canonical mutation; reads remain separately allowed.

### IMP-004 â€” Version / Provenance Repository Primitives
**Depends:** IMP-003
**Goal:** immutable semantic versions + mutable current pointer/status separation.
**Deliverables:** successor-version helpers, supersession history, current-pointer update with CAS, provenance persistence.
**Tests:** immutable approved version, successor creation, stale CAS rejection, restart/readback.
**Done:** no domain needs to invent version semantics.

### IMP-005 â€” DependencyGraph + Durable InvalidationRecord
**Depends:** IMP-004
**Goal:** selective invalidation across exact source versions.
**Deliverables:** typed dependency edge repository, reachability, InvalidationRecord, unresolvedâ†’resolved lifecycle, restart replay, dedupe/idempotency.
**Tests:** direct/transitive invalidation, preserved unrelated descendants, duplicate trigger, restart replay, cause immutability/status mutation.
**Done:** Reference/Profile/Story/Shot changes can invalidate only dependency-reachable consumers.

### IMP-006 â€” Observability / Error / Evidence Core
**Depends:** IMP-004
**Goal:** typed errors and correlation without becoming truth authority.
**Deliverables:** correlation IDs, structured decision/failure events, redaction, evidence references, error taxonomy integration.
**Tests:** secret redaction, correlation propagation, event-vs-current-state separation.
**Done:** later tasks can produce auditable evidence uniformly.

---

## PROFILE / POLICY LANE

### IMP-010 â€” Project / Topic / Domain Resolution
**Depends:** IMP-004, IMP-006
**Goal:** typed ProjectInputâ†’Topicâ†’Domain/Niche/Genre classification without profile cycle.
**Deliverables:** Topic resolution contracts/persistence and bootstrap-input boundary.
**Tests:** no ActiveProductionProfile dependency during Topic resolution; exact-version provenance.
**Done:** FM2-004 cycle cannot be represented by interfaces.

### IMP-011 â€” BrainPack Registry
**Depends:** IMP-010
**Goal:** one versioned registry for reusable packs, including Story specialization.
**Deliverables:** pack schema, versions, parent/applicability/status/provenance.
**Tests:** versioning, inheritance references, no parallel Story registry.
**Done:** registry owns definitions only, never effective resolved policy.

### IMP-012 â€” Profile Resolver
**Depends:** IMP-011, IMP-005
**Goal:** single authority for selection/composition/precedence/conflicts/overrides.
**Deliverables:** resolver + ResolutionTrace.
**Tests:** hard>soft precedence, allowlisted overrides, conflict resolution, reproducibility.
**Done:** downstream cannot re-resolve packs independently.

### IMP-013 â€” ActiveProductionProfile
**Depends:** IMP-012
**Goal:** immutable pinned effective policy snapshot.
**Deliverables:** profile identity/version/persistence, effective-path provenance, changed-path invalidation.
**Tests:** immutable snapshot, new version on re-resolution, selective invalidation.
**Done:** all downstream policy consumers bind exact profile version.

---

## STORY INTELLIGENCE LANE

### IMP-020 â€” Idea / Logline / Premise / Angle / Theme
**Depends:** IMP-002, IMP-004, IMP-013
**Goal:** replace project.story-only authority with typed early-story artifacts.
**Deliverables:** contracts/repos/services/gates for Idea, Logline, Premise, Angle, Theme.
**Tests:** blocking premise/logline defects, version/provenance, no silent in-place accepted mutation.
**Done:** FR-033/034/035 and related canonical intake are executable.

### IMP-021 â€” Research Intelligence + StoryMaterial
**Depends:** IMP-020, IMP-006
**Goal:** evidence-grounded research claims and story-material transformation.
**Deliverables:** ResearchBrief, EvidenceClaim, StoryMaterial, contradiction/uncertainty handling.
**Tests:** claim-source provenance, unsupported synthesis rejection, disputed-claim representation.
**Done:** factuality constraints are structured inputs, not prompt-only prose.

### IMP-022 â€” Character Psychology / Relationship / Knowledge
**Depends:** IMP-020, IMP-021, IMP-040
**Goal:** typed character desire/need/fear/secret plus relationship and knowledge/belief state.
**Deliverables:** versioned psychology/state contracts and chronology rules.
**Tests:** impossible knowledge, relationship-state chronology, version invalidation.
**Done:** dialogue/story decisions can query canonical character state.

### IMP-023 â€” StoryCore + CausalStoryGraph + Lock
**Depends:** IMP-020, IMP-021, IMP-022, IMP-005
**Goal:** one story_core_id with DRAFTâ†’graph validationâ†’locked/frozen successor lifecycle.
**Deliverables:** StoryCore repository, StoryGraph nodes/edges, causal gate, lock transition.
**Tests:** no StoryCore/StoryGraph cycle, causal gaps, same logical identity across lock successor, invalidation.
**Done:** locked StoryCore can drive structure without second StoryCore truth.

### IMP-024 â€” StructureProfile / MacroBeatSheet / DurationBudget
**Depends:** IMP-023, IMP-013
**Goal:** structure/count/runtime planning without narrative authority leakage.
**Deliverables:** StructureProfile, MacroBeatSheet projection, DurationBudget.
**Tests:** profile-driven ranges, parent-child budget tolerance, no MacroStoryBeat duplication.
**Done:** macro expansion has typed planning/budget constraints.

### IMP-025 â€” MacroStoryBeat / SequencePlan / Sequence / SceneBudget / Scene / SceneBreakdown / SceneDramaticBeat
**Depends:** IMP-024, IMP-005
**Goal:** canonical narrative hierarchy with projection manifests.
**Deliverables:** explicit IDs/repos/contracts and parent-child trace.
**Tests:** no generic Beat, bidirectional ancestry, no manifest shadow truth, scene state-change gate, beat microchange gate.
**Done:** StoryCoreâ†’MacroStoryBeatâ†’Sequenceâ†’Sceneâ†’SceneDramaticBeat is fully persisted.

### IMP-026 â€” Dialogue / Setup-Payoff / Screenplay Realization
**Depends:** IMP-025, IMP-022
**Goal:** screenplay realization without changing locked upstream truth.
**Deliverables:** DialogueIntent, SetupPayoffLink, versioned screenplay scenes/full screenplay.
**Tests:** knowledge discipline, setup/payoff integrity, realization drift.
**Done:** screenplay is a realization over canonical structure.

### IMP-027 â€” Story Critique / Root Cause / Story Repair / Quality Gate / ScriptLock
**Depends:** IMP-026, IMP-006
**Goal:** independent critique and targeted story repair.
**Deliverables:** CritiqueFinding, StoryRepairPlan, StoryQualityResult, ScriptLockManifest.
**Tests:** role isolation, blocking finding cannot average away, preserve-set regression, lock preconditions.
**Done:** no script lock with unresolved blocking findings.

### IMP-028 â€” NarrativeTrace
**Depends:** IMP-025, IMP-027, IMP-005
**Goal:** bidirectional exact-version ancestry.
**Deliverables:** trace repo/index, orphan/cycle detection, why-exists traversal.
**Tests:** top-down, bottom-up, TRACE_ORPHAN_ARTIFACT, TRACE_MISSING_PARENT, TRACE_CYCLE.
**Done:** every canonical expansion child can explain its ancestry.

---

## ENTITY / REFERENCE / STATE LANE

### IMP-040 â€” Canonical Entity Versioning Adapter
**Depends:** IMP-004
**Reuse:** current character/entity records and project linkage.
**Goal:** keep useful entity IDs/media integration while introducing canonical EntityVersion.
**Deliverables:** compatibility mapping, entity/version repo, no second entity store.
**Tests:** current legacy entity mapping, version successor, stable logical ID.
**Done:** current character-centric schema cannot become competing canonical identity.

### IMP-041 â€” ReferenceAsset / Reference Resolver
**Depends:** IMP-040, IMP-005, IMP-013
**Reuse:** current upload/media UUID/reference mechanisms.
**Goal:** versioned roles, provenance, approval/current reference selection.
**Deliverables:** ReferenceAsset/version/hash/role, resolver trace, provider binding projection.
**Tests:** role selection, stale ref invalidation, UUID/media compatibility, no reference-as-state.
**Done:** changed ReferenceVersion creates durable dependent invalidation.

### IMP-042 â€” StateSnapshot / ContinuityLedger / ApprovedEndState
**Depends:** IMP-041, IMP-004, IMP-005
**Goal:** semantic state separate from image/video chaining.
**Deliverables:** StateSnapshot, state delta, ContinuityLedger, approval designation/reference.
**Tests:** generated artifact != State, only approved/locked snapshot propagates, no duplicate state payload, selective invalidation.
**Done:** current media-chain continuity is an execution input, not canonical state authority.

---

## DIRECTING / SHOT / COMPILER LANE

### IMP-030 â€” Audience / Directing / Spatial / Blocking / Cinematography
**Depends:** IMP-025, IMP-027, IMP-028, IMP-042, IMP-013
**Goal:** enforce dramaticâ†’camera authority chain.
**Deliverables:** AudienceExperienceTarget, DirectingIntent, SceneSpatialDramaticContract, BlockingPlan, CinematographyObjective.
**Tests:** hard-gate bypass negative tests, exact upstream version binding.
**Done:** camera choices cannot exist without required dramatic/directing parents.

### IMP-031 â€” ShotExpansion / ShotListManifest / ShotListItem
**Depends:** IMP-030, IMP-028, IMP-024
**Goal:** one canonical shot_id origin.
**Deliverables:** planning transformation, versioned manifest, ShotListItem creation boundary.
**Tests:** no orphan shot, no duplicate manifest truth, no parallel shot ID, coverage/redundancy/budget.
**Done:** shot_id originates exactly once at ShotListItem.

### IMP-032 â€” ShotEligibilityGate / FullShotSpec / StaticKeyframeSpec / MotionDeltaSpec / ShotDecisionTrace
**Depends:** IMP-031, IMP-042, IMP-041, IMP-013
**Goal:** detailed provider-neutral realization for existing shot_id.
**Deliverables:** eligibility evidence, FullShotSpec L1-L8, static and motion contracts, decision trace.
**Tests:** stale gate rejection, required upstream gates, same shot_id across revisions, L1-L8 only.
**Done:** NO TRACEABLE SHOT FUNCTION â†’ NO FULL SHOT SPEC is executable.

### IMP-033 â€” ShotIR + Production Compiler
**Depends:** IMP-032
**Goal:** deterministic provider-neutral executable representation and compiler provenance.
**Deliverables:** ShotIR, compiler rule version, compile diagnostics, request metadata/hashes.
**Tests:** deterministic golden compile, exact input-version bindings, no provider-specific authority in IR.
**Done:** ad-hoc prompt concatenation is no longer canonical compilation.

---

## PROVIDER / EXECUTION / PERSISTENCE LANE

### IMP-050 â€” CapabilityRegistry / ProviderProfile / Router
**Depends:** IMP-033, IMP-013, IMP-006
**Goal:** evidence-versioned provider capabilities and deterministic routing.
**Deliverables:** ProviderProfile, capability registry, routing decision/evidence.
**Tests:** capability constraints, stale profile, unsupported requirement, deterministic selection.
**Done:** provider brand assumptions cannot bypass profile evidence.

### IMP-051 â€” Flow/Omni ProviderAdapter Anti-Corruption
**Depends:** IMP-050
**Reuse:** current FlowClient, Flow batch, Omni execution.
**Goal:** consume compiled requests without leaking Flow semantics upward.
**Deliverables:** adapter ports, normalized submit/poll/cancel/reconcile results.
**Tests:** existing transport regression, adapter contract, unsupported capability failure.
**Done:** current transport remains reusable but canonical domains do not import Flow payloads.

### IMP-052 â€” GenerationJob Four-Axis State Machine
**Depends:** IMP-003, IMP-004, IMP-033, IMP-051
**Goal:** implement exact 62-row closed transition relation.
**Deliverables:** persisted four axes, transition validator, owners, CAS, transition history, generic-status projection only.
**Tests:** all states reachable, all 62 legal rows, every unspecified transition rejected, V0.13 scenario fixtures.
**Done:** state conflation is impossible through public application interfaces.

### IMP-053 â€” Scheduler / Queue / DAG / Leases / Admission
**Depends:** IMP-052, IMP-005
**Reuse:** current worker priority/concurrency/cooldown/prerequisite logic.
**Goal:** dependency-aware bounded scheduling.
**Deliverables:** durable readiness/checkpoints, lease claim, fairness, provider/model/resource/budget admission.
**Tests:** lease conflict, starvation, backpressure, dependency gating, restart readiness.
**Done:** no work executes before required dependencies/gates.

### IMP-054 â€” Retry / Resume / Remote Ambiguity Recovery
**Depends:** IMP-052, IMP-051, IMP-006
**Goal:** NO RETRY WITHOUT PROOF.
**Deliverables:** failure taxonomy, recovery coordinator, reconciliation, idempotency/absence evidence, AMBIGUOUS_HOLD.
**Tests:** crash-before-submit, crash-after-possible-submit, timeout, recovered handle, proven absent, still ambiguous, cancellation race.
**Done:** no possible-paid-submit path can blind-resubmit.

### IMP-055 â€” Artifact Lifecycle / Store / Reconciler
**Depends:** IMP-052, IMP-003, IMP-005
**Goal:** staged immutable bytes + DB metadata lifecycle.
**Deliverables:** STAGING/READY/STALE_RESULT/QUARANTINED/MISSING/CORRUPT/ARCHIVED transitions, hashes, startup reconciliation.
**Tests:** crash at each stage, missing file, orphan final file, corruption, stale result, recovery.
**Done:** artifact materialization cannot imply creative approval.

---

## QA / REPAIR / APPROVAL LANE

### IMP-060 â€” Static QA
**Depends:** IMP-032, IMP-042, IMP-041, IMP-055
**Reuse:** existing review infrastructure where appropriate.
**Goal:** inspect actual image against canonical expectations.
**Tests:** blocking identity/state defect, evaluator failureâ†’QA_ERROR, evidence binding.
**Done:** blocking finding cannot be averaged away.

### IMP-061 â€” Motion / Video QA
**Depends:** IMP-032, IMP-042, IMP-055
**Reuse:** current video review donor.
**Goal:** time-bound motion/continuity/intent QA.
**Tests:** provider success != pass, time-range findings, evaluator error.
**Done:** generated video reaches approval only through QA.

### IMP-062 â€” Continuity QA + Sequence QA
**Depends:** IMP-060, IMP-061, IMP-042, IMP-025
**Goal:** cross-shot/scene/sequence validation.
**Tests:** state contradiction over visual similarity, adjacent shot drift, sequence causality/coverage.
**Done:** per-shot PASS cannot hide sequence-level blocking defects.

### IMP-063 â€” Defect Localization + Targeted Production Repair
**Depends:** IMP-060, IMP-061, IMP-062, IMP-005
**Goal:** map visible defect to earliest responsible layer and minimum repair scope.
**Deliverables:** stable defect codes, RepairPlan preserve/patch/invalidate/recheck.
**Tests:** wrong-layer repair rejection, preserve-set regression, mandatory re-QA.
**Done:** repair does not default to vague prompt suffix/full regeneration.

### IMP-064 â€” Approval / Canonical State Commit
**Depends:** IMP-063, IMP-042
**Goal:** explicit QA/approval/state boundary.
**Tests:** NO QA APPROVALâ†’NO STATE COMMIT, stale candidate approval rejected, designation references exact StateSnapshot.
**Done:** provider completion cannot propagate semantic state directly.

---

## ELECTRON / SECURITY LANE

### IMP-070 â€” Electron Host Shell Security Baseline
**Depends:** IMP-003, IMP-006
**Goal:** target desktop shell with frozen security flags.
**Deliverables:** BrowserWindow/main/preload packaging skeleton, nodeIntegration=false, contextIsolation=true, sandbox=true, webSecurity=true, insecure-content=false.
**Tests:** config/static security tests, navigation/new-window denial.
**Done:** target Electron shell exists without weakening current service boundaries.

### IMP-071 â€” Typed IPC / Production Utility Bridge
**Depends:** IMP-070
**Goal:** narrow contextBridge and allowlisted privileged capabilities.
**Tests:** invalid sender/schema/channel denial, no raw ipcRenderer/fs/child_process exposure.
**Done:** Renderer cannot gain generic OS privilege.

### IMP-072 â€” Credential Broker / safeStorage / Leases
**Depends:** IMP-071
**Goal:** Host Security Broker owns long-lived secrets.
**Tests:** renderer denial, lease scope/expiry/revocation/rotation, secret scan.
**Done:** Utility uses scoped short-lived credential authorization only.

### IMP-073 â€” Renderer / Dashboard Adaptation
**Depends:** IMP-071, IMP-013, IMP-023, IMP-031, IMP-052, IMP-064
**Reuse:** current React/Vite dashboard.
**Goal:** Studio views consume typed application read models, not DB/provider internals.
**Tests:** state views, provenance/authority views, recovery/QA/repair UX.
**Done:** UI can hide complexity without changing canonical contracts.

---

## LEGACY / MIGRATION / BACKUP LANE

### IMP-080 â€” Legacy Import Anti-Corruption
**Depends:** IMP-005, IMP-023, IMP-031, IMP-052
**Goal:** classify legacy rows without inventing canonical narrative truth.
**Deliverables:** mapping records/findings, explicit NOT_PROVABLE path.
**Tests:** prompt prose cannot auto-create SceneDramaticBeat/FullShotSpec truth.
**Done:** all migration inference is bounded and auditable.

### IMP-081 â€” Operational Scene â†’ Execution Projection
**Depends:** IMP-080, IMP-031, IMP-052
**Goal:** retain current Scene render/media usefulness behind canonical Shot/Job compatibility mapping.
**Tests:** legacy scene never becomes cinematic Scene authority, media/results still reachable.
**Done:** old execution flow can run during migration without shadow Studio truth.

### IMP-082 â€” Backup / Restore / Migration Safety
**Depends:** IMP-003, IMP-055, IMP-080
**Goal:** schema/artifact backup and staged restore.
**Tests:** interrupted migration, unsupported newer schema, manifest/hash validation, staged restore.
**Done:** no destructive auto-fix or partial backup can be reported successful.

---

## SYSTEM ACCEPTANCE LANE

### IMP-100 â€” Full Contract Regression
**Depends:** IMP-006, IMP-013, IMP-028, IMP-033, IMP-042, IMP-055, IMP-064, IMP-073, IMP-082
**Goal:** run all provider-neutral unit/contract/architecture tests.
**Acceptance:** zero blocking contract failures.

### IMP-101 â€” Migration Dry Run
**Depends:** IMP-080, IMP-081, IMP-082, IMP-100
**Goal:** real representative legacy DB/project migration into canonical model.
**Acceptance:** no silent narrative inference, restart-safe, evidence retained.

### IMP-102 â€” Failure / Recovery Fault Injection
**Depends:** IMP-052, IMP-053, IMP-054, IMP-055, IMP-100
**Goal:** crash/restart/provider ambiguity/artifact failure proof.
**Acceptance:** no blind duplicate submit; all outcomes reconciled deterministically.

### IMP-103 â€” 300-Shot Scale Benchmark
**Depends:** IMP-003, IMP-053, IMP-060, IMP-061, IMP-062, IMP-100
**Goal:** bounded memory/queue/DB behavior for long-form project scale.
**Acceptance:** no starvation/unbounded queue/data-loss; measured evidence recorded.

### IMP-104 â€” Electron Security Acceptance
**Depends:** IMP-070, IMP-071, IMP-072, IMP-073, IMP-100
**Goal:** negative security tests on packaged target topology.
**Acceptance:** no secret/privilege boundary break.

### IMP-105 â€” Packaged Clean-Install Smoke
**Depends:** IMP-104, IMP-082
**Goal:** clean packaged Windows first-run/start/restart smoke.
**Acceptance:** fresh-copy startup, schema gate, utility/renderer/IPC health, no development-path dependency.

### IMP-106 â€” Controlled Live Provider E2E
**Depends:** IMP-055, IMP-064, IMP-105
**Goal:** one bounded real provider lane proving compiled requestâ†’submitâ†’artifactâ†’QAâ†’approval lineage.
**Acceptance:** real evidence IDs/artifact/hash/QA lineage; side effects/cost explicitly recorded; ambiguity policy remains active.

### IMP-107 â€” Final Product Readiness Audit
**Depends:** IMP-100, IMP-101, IMP-102, IMP-103, IMP-104, IMP-105, IMP-106
**Goal:** independent clean-package audit.
**Acceptance:** no unresolved BLOCKER/MAJOR for agreed production scope; design PASS alone is not sufficient.

---

## Immediate executable order

1. IMP-001
2. IMP-002
3. IMP-003
4. IMP-004
5. IMP-005 + IMP-006
6. Start parallel Profile / Story / Entity-State lanes according to graph
7. Continue automatically by dependency-ready task only

## Current next task

**NEXT_EXACT_ACTION = CLAIM IMP-001 FROZEN BASELINE GUARD**
