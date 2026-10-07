# FINAL MASTER REPAIR FM2-001 THROUGH FM2-008 V1

## STATUS

**REPAIR PASS ONLY — NOT AN INDEPENDENT AUDIT**

This document records the scoped design repair of FM2-001 through FM2-008 from FINAL_MASTER_INDEPENDENT_AUDIT_V2.

It does NOT claim:
- Independent Audit V3 PASS;
- baseline freeze;
- implementation readiness;
- runtime/build/test evidence;
- production/release readiness.

FINAL_MASTER_INDEPENDENT_AUDIT_V2.md remains unchanged and authoritative as the audit that triggered this repair.

## 1. Master snapshots

### Before repair

- Path: docs/design/canonical/MASTER_AI_FILM_STUDIO_FINAL_IMPLEMENTATION_BASELINE_V1.md
- Size: 195494 bytes
- Lines: 3215
- Numbered sections: 103
- Unique requirement IDs: 112
- SHA-256: 5cbd278aa3b148670754ecbab2650bed4716333cb32727c1acdc61c40113ed0b

### After scoped repair

- Size: 480568 bytes
- Lines: 6172
- Numbered sections: 103
- Unique requirement IDs: 112
- SHA-256: c533369c27f09814e44623ba970bd2e5df70ae27fd1d0a76050d6ceb4f1a7a77
- Master status remains: IMPLEMENTATION BASELINE CANDIDATE — NOT YET FROZEN

## 2. Local validation summary

- Audited numbered contract components §42→§98: 57
- Restored post-V0.16 subcontracts: 5
- Total audited contract components: 62
- Complete: 62
- Incomplete: 0
- Explicit N/A field declarations checked: 204
- N/A without explicit reason: 0
- Design dependency cycle count: 0
- Requirement IDs: 112
- Requirement rows: 112
- Duplicate requirement definitions: 0
- Missing requirement rows: 0
- Malformed requirement rows: 0
- Literal backslash-n table separators: 0
- Source-required Narrative Expansion defect codes: 36
- Missing defect codes: 0
- Duplicate defect codes: 0
- Four-axis GenerationJob transition rows: 62
- Undeclared states used by transition tables: 0
- Unreachable declared states: 0
- Final repair regression self-check: 20/20 PASS

This is local repair validation only, not an independent audit.

---

## FM2-001

**ID:** FM2-001

**ORIGINAL FINDING:** Accepted post-V0.16 requirements FR-056, FR-057, FR-058, FR-062 and FR-064 pointed to components that lacked explicit canonical implementation contracts.

**SEVERITY:** MAJOR in Audit V2.

**SOURCE AUTHORITY READ:**
- NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL.md
- ADR-0018 Narrative Artifact Identity
- ADR-0019 Dramatic-to-Camera Authority
- ADR-0020 Shot Identity / Spec / IR Boundary
- CANONICAL_DOCUMENT_AUTHORITY_MAP_V1.md
- CANONICAL_MERGE_CANDIDATE_SET_V1.md

**MASTER SECTIONS CHANGED:**
- §24B DurationBudget
- §26B SequencePlan
- §26C SceneBudget
- §47A ShotExpansion
- §62A NarrativeTrace
- §102 requirement traceability rows FR-056 / FR-057 / FR-058 / FR-062 / FR-064

**CANONICAL DECISION / CONTRACT RESTORED:**
- SequencePlan is a planning/projection artifact, not Sequence truth.
- DurationBudget is versioned runtime allocation policy/planning, not narrative truth.
- SceneBudget owns count/duration ranges only and never owns scene_id.
- NarrativeTrace owns bidirectional lineage/provenance only and never narrative truth.
- ShotExpansion is a transformation/service boundary; canonical shot_id still originates only at ShotListItem.
- Every restored component has explicit local PURPOSE, DEFINITION, OWNER, AUTHORITY, INPUTS, OUTPUTS, IDENTITY, STATE, MUTABILITY, VERSION, PROVENANCE, PERSISTENCE, REFERENCES, DEPENDENCIES, ORDERING, CONCURRENCY/TRANSACTION, INVALIDATION, FAILURE, RECOVERY, QA/GATE, OBSERVABILITY, IMPLEMENTATION and TESTABILITY.

**TRACEABILITY CHANGE:**
- FR-056 -> SequencePlan (§26B)
- FR-057 -> DurationBudget (§24B)
- FR-058 -> SceneBudget (§26C)
- FR-062 -> NarrativeTrace (§62A)
- FR-064 -> ShotExpansion (§47A)

**LOCAL VALIDATION:**
- 5/5 restored contracts complete.
- zero second Sequence/Scene/Shot/narrative truth introduced.
- all five requirement rows independently parse and resolve to explicit Master contracts.

**STATUS:** REPAIRED

---

## FM2-002

**ID:** FM2-002

**ORIGINAL FINDING:** Exact V0.13 state enums/owners were restored, but the legal transition relation was not complete enough to implement or machine-check.

**SEVERITY:** MAJOR in Audit V2.

**SOURCE AUTHORITY READ:**
- JOB_STATE_MODEL_V0_13.md
- JOB_STATE_MODEL_CHECK_V0_13.md/.json
- ADR-0012 Orthogonal Job State Correction
- FAILURE_RECOVERY_MODEL.md
- PROVIDER_SUBMISSION_RECOVERY_ARCHITECTURE.md
- STATIC_QA_ARCHITECTURE.md
- PERSISTENCE_ARCHITECTURE.md
- independent review lineage for rounds 109-112

**MASTER SECTIONS CHANGED:**
- §68 Generation Job Model

**CANONICAL DECISION / CONTRACT RESTORED:**
A closed transition contract now exists for all four independent axes with:
FROM_STATE, EVENT/COMMAND, GUARD, TO_STATE, TRANSITION_OWNER, SIDE EFFECT, PERSISTENCE REQUIREMENT, ILLEGAL TRANSITION BEHAVIOR, RECOVERY BEHAVIOR, OBSERVABLE EVIDENCE.

Exact V0.13 state vocabulary is retained:
- Scheduler: QUEUED, WAITING_DEPENDENCY, WAITING_CAPACITY, CLAIMED, RUNNING, WAITING_RECOVERY, TERMINAL.
- Provider: NOT_SUBMITTED, SUBMITTING, SUBMITTED, POLLING, UNKNOWN_REMOTE_STATE, RECONCILING, AMBIGUOUS_HOLD, REMOTE_SUCCEEDED, REMOTE_FAILED, CANCEL_REQUESTED, REMOTE_CANCELED.
- Artifact: NONE, STAGING, READY, STALE_RESULT, QUARANTINED, MISSING, CORRUPT, ARCHIVED.
- Creative: NOT_APPLICABLE, PENDING_QA, QA_RUNNING, QA_ERROR, QA_FAILED, REPAIR_PENDING, NEEDS_HUMAN_REVIEW, APPROVED, LOCKED, REJECTED.

Unspecified transitions are explicitly illegal/unsupported.
Restart, one-writer persistence, optimistic revision/CAS, cross-axis invariant validation and side-effect boundaries are explicit.
UNKNOWN_REMOTE_STATE -> RECONCILING -> AMBIGUOUS_HOLD remains the ambiguity safety path.
TIMEOUT / CONNECTION BREAK / CRASH after possible submit cannot directly authorize another SUBMITTING transition.
NO RETRY WITHOUT PROOF remains hard authority.

**TRACEABILITY CHANGE:**
No requirement IDs changed. Existing FR-019 / FR-022 / REL-002 / REL-006 / REL-009 semantics now point to an executable transition contract rather than distributed prose.

**LOCAL VALIDATION:**
- Scheduler transition rows: 15; all seven declared states reachable.
- Provider transition rows: 19; all eleven declared states reachable.
- Artifact transition rows: 14; all eight declared states reachable.
- Creative transition rows: 14; all ten declared states reachable.
- Total transition rows: 62.
- Every row has all 10 required columns.
- undeclared states used: 0.
- ambiguity chain present: PASS.
- blind resubmit prohibition present: PASS.
- CAS/restart rules present: PASS.

**STATUS:** REPAIRED

---

## FM2-003

**ID:** FM2-003

**ORIGINAL FINDING:** Master §01 required explicit component-local contracts, but many major canonical components outside §06-§41 relied on abbreviated/global prose.

**SEVERITY:** MAJOR in Audit V2.

**SOURCE AUTHORITY READ:**
- Master §01 component completeness law
- ADR-0015 Design Freeze vs Implementation Evidence
- ADR-0016 through ADR-0020
- accepted canonical Story/Shot/State/Persistence/Security/QA sources
- supporting V0.16 contracts referenced by the affected sections

**MASTER SECTIONS CHANGED:**
- every numbered major component §42 through §98 was structurally checked;
- local FM2-003 completion fields were added only where missing.

**CANONICAL DECISION / CONTRACT RESTORED:**
Each numbered component §42→§98 now locally exposes or explicitly marks N/A with reason for:
PURPOSE, CANONICAL DEFINITION, OWNER, AUTHORITY, INPUTS, OUTPUTS, IDENTITY, STATE, MUTABILITY, VERSION, PROVENANCE, PERSISTENCE, PARENT/CHILD OR REFERENCES, DEPENDENCIES, ORDERING, CONCURRENCY/TRANSACTION BOUNDARY, INVALIDATION, FAILURE MODES, RECOVERY, QA/GATE, OBSERVABILITY, IMPLEMENTATION IMPLICATION, TESTABILITY and LEGACY FLOWKIT MAPPING.

N/A was used where a service/policy/taxonomy genuinely has no independent canonical domain identity/state/persistence; it was not used to hide an undecided architecture boundary.

**TRACEABILITY CHANGE:**
No requirement renumbering. Existing requirement/component mappings now terminate at locally explicit contracts rather than implicit global defaults.

**LOCAL VALIDATION:**
- numbered components §42→§98: 57.
- complete: 57.
- incomplete: 0.
- restored post-V0.16 subcontracts complete: 5/5.
- total audited contract components: 62.
- explicit N/A field declarations: 204.
- N/A without reason: 0.

**STATUS:** REPAIRED

---

## FM2-004

**ID:** FM2-004

**ORIGINAL FINDING:** Topic Intelligence depended on Profile Resolver even though Topic/Niche classification is an upstream input to Profile resolution, creating a bootstrap authority/order cycle.

**SEVERITY:** MAJOR in Audit V2.

**SOURCE AUTHORITY READ:**
- UNIVERSAL_NICHE_COMPOSABLE_BRAIN_ARCHITECTURE_V1_FINAL.md canonical pipeline and Dynamic Brain Resolver
- ADR-0017 BrainPack / ActiveProductionProfile Authority

**MASTER SECTIONS CHANGED:**
- §06 Project / Topic Intelligence
- §07 Domain / Niche / Genre Resolution
- §09 Profile Resolver

**CANONICAL DECISION / CONTRACT RESTORED:**
The explicit order is now:

PROJECT INPUT / PROJECT INTENT
-> TOPIC INTELLIGENCE
-> DOMAIN / NICHE / GENRE / AUDIENCE / FORMAT / PLATFORM / FACTUALITY RESOLUTION
-> BRAINPACK CANDIDATE SELECTION / COMPOSITION INPUTS
-> PROFILE RESOLVER
-> ACTIVE PRODUCTION PROFILE
-> DOWNSTREAM STORY / PRODUCTION.

Topic uses source-supported bootstrap/project context only.
Topic Intelligence MUST NOT depend on final Profile Resolver/ActiveProductionProfile.
Downstream systems read the pinned ActiveProductionProfile and do not independently re-resolve packs.

**TRACEABILITY CHANGE:**
No ID changes; ownership/order text and dependencies were corrected.

**LOCAL VALIDATION:**
- design graph cycle count for Topic/Profile chain: 0.
- §06 dependencies contain explicit prohibition on Profile Resolver/ActiveProductionProfile prerequisite.
- classification and final effective-policy resolution are separate.

**STATUS:** REPAIRED

---

## FM2-005

**ID:** FM2-005

**ORIGINAL FINDING:** §22/§23 created StoryCore -> StoryGraph -> StoryCoreLock prerequisite cycle.

**SEVERITY:** MAJOR in Audit V2.

**SOURCE AUTHORITY READ:**
- NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL.md StoryCoreLock
- STORY_INTELLIGENCE_ARCHITECTURE_V0_16.md
- STORY_INTELLIGENCE_CANONICAL_CONTRACTS_V0_16.md
- ADR-0018 Narrative Artifact Identity

**MASTER SECTIONS CHANGED:**
- §22 Causal StoryGraph
- §23 Story Core Lock

**CANONICAL DECISION / CONTRACT RESTORED:**
One canonical story_core_id uses versioned phases, not two StoryCore authorities:

StoryCore DRAFT version
-> Causal StoryGraph construction
-> causal/structural validation
-> StoryCore lock transition
-> FROZEN_FOR_STRUCTURE successor version
-> MacroBeatSheet / MacroStoryBeat expansion.

StoryGraph consumes exact StoryCore DRAFT.
StoryGraph MUST NOT require StoryCoreLock/FROZEN_FOR_STRUCTURE as an input.
Lock creates an immutable successor version of the same story_core_id.
There is no in-place unlock; approved revision creates a successor DRAFT and repeats validation.

**TRACEABILITY CHANGE:**
No identity or requirement renumbering; exact draft/graph/lock version lineage is now explicit.

**LOCAL VALIDATION:**
- StoryCore design graph cycle count: 0.
- no second StoryCore identity introduced.
- reverse locked-StoryCore prerequisite is explicitly prohibited.

**STATUS:** REPAIRED

---

## FM2-006

**ID:** FM2-006

**ORIGINAL FINDING:** Accepted Narrative Expansion source required a stable defect taxonomy, but the Master had only broad error classes.

**SEVERITY:** MAJOR in Audit V2.

**SOURCE AUTHORITY READ:**
- NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL.md §51 and §80
- ADR-0018/0019/0020 terminology boundaries

**MASTER SECTIONS CHANGED:**
- §87A Canonical Narrative Expansion Defect Registry

**CANONICAL DECISION / CONTRACT RESTORED:**
All 36 exact source-required codes are restored without renaming.
Each registry row defines:
CODE, OWNER/DETECTOR, STAGE, TRIGGER CONDITION, SEVERITY CLASS, AFFECTED ARTIFACT, ROOT-CAUSE LAYER, BLOCKING/NON-BLOCKING SEMANTICS, REPAIR TARGET, MINIMUM REPAIR SCOPE, INVALIDATION EXPECTATION and RECHECK/QA REQUIREMENT.

The source fixes the code set but does not assign one immutable severity to every code. Therefore severity/blocking is POLICY_BOUND and must be emitted by a versioned QA/gate policy rather than invented in this repair.

The source spelling SHOT_NOT_BOUND_TO_BEAT is preserved; under ADR-0018 its canonical meaning is missing SceneDramaticBeat binding, not resurrection of a generic persistent Beat.

Repair chain remains:
DEFECT -> ROOT CAUSE -> RESPONSIBLE LAYER -> MINIMUM REPAIR SCOPE -> INVALIDATION -> RECOMPUTE/REGENERATE -> RE-QA.

**TRACEABILITY CHANGE:**
Defect findings now have stable canonical code identity usable by QA/repair/test evidence.

**LOCAL VALIDATION:**
- source-required code count: 36.
- registry data rows: 36.
- missing codes: 0.
- duplicate codes: 0.
- extra invented codes in this registry: 0.

**STATUS:** REPAIRED

---

## FM2-007

**ID:** FM2-007

**ORIGINAL FINDING:** Six physical §102 lines contained literal backslash-n separators that merged 21 logical requirement rows.

**SEVERITY:** MINOR in Audit V2.

**SOURCE AUTHORITY READ:**
- existing Master §102 registry
- historical/current requirement IDs and traceability contracts

**MASTER SECTIONS CHANGED:**
- §102 only, mechanical row separation plus FM2-001 component-link strengthening for five new requirements.

**CANONICAL DECISION / CONTRACT RESTORED:**
All literal backslash-n table separators were converted to real Markdown row boundaries. Requirement meaning and IDs were not renumbered or removed.

**TRACEABILITY CHANGE:**
FR-056/057/058/062/064 now explicitly identify their restored Master contract sections.

**LOCAL VALIDATION:**
- unique requirement IDs: 112.
- independent requirement rows: 112.
- duplicate definitions: 0.
- missing rows: 0.
- malformed row shape: 0.
- source column empty: 0.
- component column empty: 0.
- contract column empty: 0.
- enforcement/test column empty: 0.
- acceptance column empty: 0.
- literal backslash-n pipe separators: 0.

**STATUS:** REPAIRED

---

## FM2-008

**ID:** FM2-008

**ORIGINAL FINDING:** §100 self-status text said no unresolved design contradiction blocked the candidate, which was stale after Audit V2 found MAJOR implementation-design findings.

**SEVERITY:** NOTE in Audit V2.

**SOURCE AUTHORITY READ:**
- PRE_MASTER_CONTRADICTION_REGISTER_V1.md
- PRE_MASTER_AUTHORITY_COVERAGE_AUDIT_V2.md
- FINAL_MASTER_INDEPENDENT_AUDIT_V2.md
- ADR-0015 process separation between design freeze and later implementation/live evidence

**MASTER SECTIONS CHANGED:**
- §100 Open Non-Blocking Decisions
- §101.7 repair provenance

**CANONICAL DECISION / CONTRACT RESTORED:**
§100 now distinguishes:
- resolved pre-Master authority contradictions;
- Audit V2 implementation-design findings;
- current candidate status;
- future independent re-audit gate.

The Master explicitly remains IMPLEMENTATION BASELINE CANDIDATE — NOT YET FROZEN.
Repair text explicitly states that this repair is not Independent Audit V3 evidence.

**TRACEABILITY CHANGE:**
§101.7 records Audit V2 repair provenance without claiming independent PASS.

**LOCAL VALIDATION:**
- candidate wording present.
- NOT YET FROZEN present.
- no standalone IMPLEMENTATION READY / PRODUCTION READY / READY FOR RELEASE status claim found.

**STATUS:** REPAIRED

---

## 3. Design-only cycle check

This is a repair validation graph only, NOT an implementation dependency graph.

### Topic/Profile

ProjectInput
-> TopicIntelligence
-> DomainNicheGenreResolution
-> BrainPackResolution
-> ProfileResolver
-> ActiveProductionProfile
-> DownstreamStoryProduction

Cycle count: 0.

### StoryCore

StoryCoreDraft
-> CausalStoryGraph
-> CausalValidation
-> StoryCoreLock
-> StoryCoreFrozen
-> MacroBeatSheet

Cycle count: 0.

Total design-cycle count for the two Audit V2 cycle findings: 0.

---

## 4. Repair regression self-check

1. no second Scene truth — PASS
2. no second Beat truth — PASS
3. no second Shot identity — PASS
4. no second State truth — PASS
5. no second Profile authority — PASS
6. manifests remain projections — PASS
7. compiler authority unchanged — PASS
8. dramatic-to-camera authority unchanged — PASS
9. L1-L8 remain semantic layers — PASS
10. T9-T12 remain technical stages — PASS
11. no semantic L9-L12 invented — PASS
12. FlowKit Scene remains legacy/adapted — PASS
13. Provider Prompt/Request remains derivative — PASS
14. Generated Artifact remains non-canonical / not approved state — PASS
15. no new dependency cycle — PASS
16. no new authority cycle — PASS
17. no security regression — PASS
18. no retry-ambiguity regression — PASS
19. no requirement-ID regression — PASS
20. no false implementation/readiness claim — PASS

Result: 20/20 PASS.

---

## 5. Local repair verdict

- FM2-001: REPAIRED
- FM2-002: REPAIRED
- FM2-003: REPAIRED
- FM2-004: REPAIRED
- FM2-005: REPAIRED
- FM2-006: REPAIRED
- FM2-007: REPAIRED
- FM2-008: REPAIRED

**8/8 local repair complete.**

This does NOT mean Audit V3 passed.

NEXT required design action:

RUN INDEPENDENT FINAL MASTER AUDIT V3 AFTER FM2-001 THROUGH FM2-008 REPAIR
