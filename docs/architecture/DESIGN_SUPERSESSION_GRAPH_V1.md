# DESIGN SUPERSESSION GRAPH V1

## 0. Purpose

This is a pre-Master lineage graph for the historical design corpus. It does not create a Master design and does not modify historical sources.

Authority rule used in this graph is evidence-based, not recency-based:

1. Current PROJECT_STATE / CURRENT_HANDOFF for maturity and next-action lineage.
2. Accepted/scoped ADR for a specific decision.
3. Canonical Decision Registry.
4. Latest dedicated subsystem design whose authority is not contradicted by a stronger source.
5. DESIGN_DRAFT as baseline only where a dedicated subsystem source has not superseded it.
6. Historical research, review, harness and evidence records.

A later file is not a successor unless explicit text, ADR/review decisions, registry changes, or actual contract changes support that conclusion.

## 1. Graph notation

- A -> superseded by B
- A -> partially superseded by B
- A + B -> merged into C
- A -> renamed to B
- A -> historical only
- A -> extended by B

## 2. High-confidence explicit supersession edges

### SG-001 — Job state model

JOB_STATE_MODEL_V0_10
-> superseded by
JOB_STATE_MODEL_V0_13

Evidence:
- JOB_STATE_MODEL_V0_13 says "Supersedes: JOB_STATE_MODEL_V0_10.md".
- V0.10 copy is explicitly marked SUPERSEDED from V0.13 onward.
- DESIGN_DRAFT V0.13+ calls V0.13 the canonical job-state authority.

Effect:
- scheduler/provider/artifact/creative state are orthogonal.
- APPROVED/REJECTED no longer belong to artifact materialization state.
- WAITING_RECOVERY and QA_ERROR are explicit.

### SG-002 — Generic V0.1 Story Engine

V0.1 generic Story Engine in DESIGN_DRAFT
-> partially superseded by
STORY_INTELLIGENCE_ARCHITECTURE_V0_16
+ STORY_INTELLIGENCE_CANONICAL_CONTRACTS_V0_16
+ STORY_QUALITY_CRITIQUE_REPAIR_V0_16
+ STORY_BRAIN_PACK_SPEC_V0_16
+ FLOWKIT_STORY_REPLACEMENT_MAP_V0_16

Evidence:
- STORY_INTELLIGENCE_ARCHITECTURE_V0_16 explicitly says it supersedes the generic V0.1 Story Engine where conflicting.
- ADR-0014 gives Studio-owned Story Intelligence canonical authority and restricts donor repositories to donor roles.

Effect:
- premise/angle/theme/research/character/conflict/causality/emotion/scene-beat/dialogue/critique/repair/script lock move to the dedicated Story subsystem.
- FlowKit execution state is not Story authority.

### SG-003 — Stale DESIGN_DRAFT subsystem sections

DESIGN_DRAFT stale subsystem sections
-> partially superseded by
dedicated subsystem documents + scoped ADRs

Evidence:
- DESIGN_DRAFT header says later dedicated subsystem designs supersede stale sections.

Major split successors:
- persistence -> PERSISTENCE_ARCHITECTURE + ADR-0013 + PERSISTENCE_WRITE_OWNERSHIP.
- security/credentials -> SECURITY_MODEL + CREDENTIAL_BROKER_ARCHITECTURE + ADR-0008.
- provider ambiguous submit -> PROVIDER_SUBMISSION_RECOVERY_ARCHITECTURE + ADR-0007.
- static QA -> STATIC_QA_ARCHITECTURE + ADR-0005.
- repair -> TARGETED_REPAIR_ARCHITECTURE + ADR-0006.
- job state -> JOB_STATE_MODEL_V0_13.
- evidence governance -> EVIDENCE_CLASSIFICATION_POLICY + EVIDENCE_LEDGER + ADR-0011.
- story -> V0.16 Story subsystem documents + ADR-0014.

DESIGN_DRAFT remains useful as a cross-subsystem baseline but is not allowed to override these split successors.

### SG-004 — Persistence write topology

direct independent multiwriter SQLite production topology
-> superseded by
one logical SQLite write owner + bounded write queue

Primary successor:
- ADR-0013 — Single SQLite Write Owner.
- PERSISTENCE_WRITE_OWNERSHIP_V0_14.
- PERSISTENCE_ARCHITECTURE V0.14 patch.

Evidence:
- Windows Run-1 reproduced dropped/failed writes under direct multiwriter contention.
- Windows Run-2 single-writer queue committed 3000/3000 with zero writer/producer errors and integrity ok.
- review lineage explicitly says Run-2 PASS supersedes the production-topology decision while retaining Run-1 FAIL history.

Historical evidence is not deleted:
Run-1 FAIL -> historical characterization evidence.
Run-2 PASS -> decision evidence for intended topology.

### SG-005 — Pre-code lifecycle requiring all live gates

old process wording:
"all target/live provider/QA/repair/performance gates must pass before feature coding"
-> superseded by
ADR-0015 — Separate Design Freeze from Implementation/Live Evidence

ADR-0015 decision:
pre-code freeze requires coherent canonical architecture, resolved authority, contracts/data/state, license/dependency decisions, architecture-changing spikes, traceability/review, and task plan.

Post-implementation acceptance owns:
- packaged safeStorage proof,
- live provider ambiguity/fault injection,
- calibrated static/story QA benchmarks,
- real targeted-repair benchmark,
- representative performance/cost benchmark.

This process correction supersedes V0.3–V0.15 blanket "no production coding until L6/live evidence" language where they conflict.

### SG-006 — Generic overloaded status

generic one-field job/status semantics
-> superseded by
JOB_STATE_MODEL_V0_13

This is also reflected in:
- DATA_MODEL V0.13 clarification.
- Cross-document contradiction C-002.
- API/observability contracts that keep current-state rows authoritative.

### SG-007 — Provider brand conflation

generic "Google provider" / generic WAN provider assumptions
-> partially superseded by
surface-specific ProviderProfile identities and ADR-0010/provider evidence matrix

Canonical identity is at least:
provider + surface + region + model/version + evidence version.

Flow product, Gemini/Veo API and Vertex/Veo do not share one timeless capability/price/quota contract.

### SG-008 — Generic blind retry after uncertain paid submission

generic retry engine applied to all failures
-> superseded by
ADR-0007 + PROVIDER_SUBMISSION_RECOVERY_ARCHITECTURE

SUBMITTING -> UNKNOWN_REMOTE_STATE -> RECONCILING -> AMBIGUOUS_HOLD

No automatic resubmit after ambiguous acceptance unless idempotency/reconciliation proves it safe.

### SG-009 — Generic credential lookup/lease model

generic credential string lookup / renderer-visible secret patterns
-> partially superseded by
SECURITY_MODEL + CREDENTIAL_BROKER_ARCHITECTURE + ADR-0008

Decision candidate:
Renderer never receives plaintext secret.
Electron Main / security broker authorizes a scoped one-use lease to trusted production utility.
Browser/session credentials use a separate provider-specific isolated session boundary rather than generic serialized API-key lease semantics.

Evidence maturity remains partial for packaged Windows Electron safeStorage behavior.

### SG-010 — Weighted QA as final acceptance

weighted-average-only acceptance
-> superseded by
ADR-0005 + STATIC_QA_ARCHITECTURE

Metrics remain sensors/advisory inputs.
BLOCKING defects cannot be averaged into PASS.

### SG-011 — Retry/full-regenerate as "repair"

generic prompt suffix + full regeneration
-> partially superseded by
ADR-0006 + TARGETED_REPAIR_ARCHITECTURE

Repair canonical candidate:
classify earliest responsible layer -> preserve set -> patch set -> dependency invalidation -> scoped recheck.

Real generation repair efficacy remains an implementation acceptance question, not a reason to revert the design contract.

### SG-012 — Harness readiness as gate closure

harness exists
-> does not imply gate PASS

Superseded interpretation:
- ADR-0011 Evidence-Class Gating.
- evidence ledger/gate rules.

Local simulation/harness evidence cannot close a target/live evidence requirement.

## 3. Post-V0.16 supersession / extension edges

These three documents are not auto-canonical. They are pre-Master merge candidates.

### SG-013 — Topic/Niche/Brain architecture

V0.16 Story Brain Pack scope
-> extended by
UNIVERSAL_NICHE_COMPOSABLE_BRAIN_ARCHITECTURE_V1_FINAL

Relationship:
EXTENSION, not wholesale replacement.

Why:
V0.16 has Story Brain Packs inside Story Intelligence.
The post-V0.16 document introduces a broader pre-Story layer:
Topic Intelligence -> Niche/Genre/Audience/Format/Platform/Factuality resolution -> Composable Brain Packs -> Active Production Profile -> Story.

New ownership questions introduced:
- Project vs ActiveProductionProfile.
- Story Brain Pack vs universal Brain Pack taxonomy.
- precedence between project locks, factuality locks, story facts, packs and local intent.
- profile-version invalidation.

Status:
NEEDS_MERGE before Master.
No evidence supports replacing the V0.16 Story subsystem wholesale.

### SG-014 — Narrative expansion ladder

V0.16 implicit expansion:
Story core -> Sequence -> Scene -> Beat -> Script Lock -> Directing -> Shot
-> partially superseded / made explicit by
NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL

Patch introduces first-class:
- Idea Contract.
- Logline.
- Story Core Lock.
- Macro Beat Sheet.
- Sequence Plan.
- Scene List.
- Scene Breakdown.
- Micro Beats.
- Screenplay Realization.
- Shot Budget.
- Shot Expansion.
- Shot List Manifest.

Patch explicitly instructs final consolidation to mark old implicit expansion wording as superseded.

Status:
NEEDS_MERGE. This is a live pre-Master contract expansion.

### SG-015 — Beat terminology and camera authority

V0.16 persistent generic Beat / BeatContract terminology
-> partially superseded / renamed by
BEAT_SCENE_TO_SHOT_AUTHORITY_ARCHITECTURE_V1_FINAL

Required terminology split:
Beat -> MacroStoryBeat + SceneDramaticBeat

The patch also adds:
- AudienceExperienceTarget.
- SceneSpatialDramaticContract.
- DirectingIntent.
- BlockingPlan.
- CinematographyObjective.
- CoverageStrategy.
- ShotEligibilityGate.
- ShotDecisionTrace.
- FullShotSpec authority path.

Direct camera authority becomes:
SceneDramaticBeat
+ Scene spatial contract
+ AudienceExperienceTarget
+ Directing/Blocking
-> Cinematography objective
-> Coverage
-> Shot decision.

Status:
BLOCKING merge decision because existing V0.16 canonical contracts/data model use generic Beat identity.

### SG-016 — FullShotSpec vs 8-Layer ShotSpec

V0.16 ShotSpec/ShotIR generation contract
+ post-V0.16 FullShotSpec/directing authority contract
-> must be merged, not treated as competing masters

Proposed relation:
FullShotSpec is the resolved production-level shot contract.
8-Layer structure is its canonical semantic realization for generation.
ShotIR is provider-neutral compiled/resolved generation intent.
Provider prompt/request is downstream compiled artifact.

Status:
NEEDS_MERGE; terminology and schema ownership must be locked in Master consolidation.

## 4. Historical-only sources

### SG-017 — MASTER_STUDIO_OPTIMAL_HYBRID_ARCHITECTURE_V1_FROZEN

MASTER_STUDIO_OPTIMAL_HYBRID_ARCHITECTURE_V1_FROZEN
-> historical/supporting baseline

Reason:
It is a strong multi-repo frozen baseline dated 2026-09-20, but V0.16 later adds accepted ADR-0014/0015, Story contracts, evidence governance, corrected job state, persistence Run-2 evidence and post-V0.16 patches.

Use:
- supporting design intent,
- donor/KEEP-TAKE-REPLACE rationale,
- authority principles.

Do not merge wholesale over later scoped authorities.

### SG-018 — FLOWKIT_INDEPENDENT_MULTI_ROUND_PRODUCTION_AUDIT

FLOWKIT_INDEPENDENT_MULTI_ROUND_PRODUCTION_AUDIT_2026-09-20
-> historical/optional evidence

Use:
- evidence for FlowKit KEEP areas: entity/reference/continuity execution/orchestration.
- evidence for FlowKit gaps.

Not authority for Studio story/directing/shot contracts.

## 5. Merge/split view

### Split successors

DESIGN_DRAFT baseline
-> persistence
+ security
+ provider recovery
+ job state
+ static QA
+ repair
+ evidence governance
+ Story Intelligence

generic V0.1 Story Engine
-> Story Architecture
+ Story Contracts
+ Story Brain Pack
+ Story Quality/Critique/Repair
+ Story Replacement Map

generic Beat concept
-> MacroStoryBeat
+ SceneDramaticBeat

### Merge targets required later

The following are candidate merge equations for a future Master. They are not performed in this phase.

V0.16 Story Architecture
+ Narrative Expansion Ladder
+ Beat/Scene-to-Shot Authority
-> future canonical Narrative/Directing/Shot authority

V0.16 Story Brain Pack
+ Universal Niche/Composable Brain Architecture
-> future Brain/Profile authority

DATA_MODEL + API_CONTRACTS
+ post-V0.16 narrative/shot contracts
-> future canonical contract/data model

V0.16 ShotSpec/ShotIR
+ FullShotSpec / ShotDecisionTrace additions
-> future canonical Shot authority

## 6. Edges intentionally NOT asserted

No edge is asserted merely because:
- one filename says FINAL or FROZEN;
- one version number is higher;
- one document is longer;
- one document has more examples.

No physical deduplication or source deletion follows from this graph.

## 7. Graph conclusion

The corpus has substantial resolved lineage, but the pre-Master graph still contains live merge decisions around:

1. generic Beat -> MacroStoryBeat / SceneDramaticBeat;
2. narrative expansion artifacts and IDs;
3. FullShotSpec vs existing ShotSpec contract boundaries;
4. universal Active Production Profile vs V0.16 project/story Brain Pack boundaries;
5. credential/desktop secret decision status conflict between PROJECT_STATE pending list and ADR/security design.

These are carried into PRE_MASTER_CONTRADICTION_REGISTER_V1.md rather than silently resolved here.


## 8. Accepted pre-Master blocker-resolution edges

### SG-019 ? Credential authority

historical credential/security candidates + stale PROJECT_STATE pending item
? authority resolved by
**ADR-0016 ? Credential Authority**

Canonical owner: Host Security Broker abstraction.
Electron Main + safeStorage owns long-lived secret in target topology.
Production Utility receives scoped short-lived leases.
Renderer has no long-lived secret authority.
FlowKit credential/session behavior is compatibility-only.

### SG-020 ? BrainPack/Profile authority

V0.16 StoryBrainPack + POST-NICHE universal pack/profile proposal
? merged authority resolved by
**ADR-0017 ? BrainPack and Active Production Profile Authority**

One BrainPack Registry + one Profile Resolver + immutable pinned ActiveProductionProfile.
StoryBrainPack is a specialization, not a second registry.

### SG-021 ? Narrative identity

V0.16 generic Story?Sequence?Scene?Beat + POST-LADDER + POST-BEAT
? terminology/identity resolved by
**ADR-0018 ? Narrative Artifact Identity**

Canonical: StoryCore?MacroStoryBeat?Sequence?Scene?SceneDramaticBeat.
No generic persistent Beat.
SceneList/SceneBreakdown are manifests/projections only.

### SG-022 ? Dramatic-to-camera authority

V0.16 directing/cinematography decision fields + POST-BEAT authority proposal
? ownership resolved by
**ADR-0019 ? Dramatic-to-Camera Authority**

SceneDramaticBeat is immediate narrative authority of Shot.
AudienceExperienceTarget?DirectingIntent?SceneSpatialDramaticContract?BlockingPlan?CinematographyObjective precedes ShotListItem.
Camera parameters cannot self-author.

### SG-023 ? Shot identity/spec/IR

V0.16 Shot/ShotSpec/ShotIR + POST-LADDER/POST-BEAT shot artifacts
? boundary resolved by
**ADR-0020 ? Shot Identity, Manifest, FullShotSpec and ShotIR Boundary**

ShotListItem creates canonical shot_id.
FullShotSpec realizes same shot_id.
Legacy generic ShotSpec has no independent canonical authority.
ShotIR is provider-neutral derived representation and always references shot_id.
Provider prompt/request are derivatives.
