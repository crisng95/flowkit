# FINAL MASTER REPAIR FM001-FM008 V1

## STATUS

REPAIR PASS ONLY — NOT AN INDEPENDENT AUDIT.

This evidence records the scoped repair of FM-001 through FM-008 against FINAL_MASTER_INDEPENDENT_AUDIT_V1.md.

It does not claim independent audit PASS, implementation baseline freeze, implementation readiness, runtime/build/test evidence, or release readiness. The failed audit V1 remains unchanged as historical evidence.

## MASTER SNAPSHOT

Before repair:
- Size: 87969 bytes
- Lines: 1761
- SHA-256: 2f5a7d3e2d6fcf0bd671907a43ca3920017783c238f27868783cd3d511b492df

After scoped repair:
- Size: 195494 bytes
- Lines: 3215
- SHA-256: 5cbd278aa3b148670754ecbab2650bed4716333cb32727c1acdc61c40113ed0b
- Numbered Master sections: 103, from 00 through 102
- Unique explicit requirement IDs: 112
- New requirement IDs: FR-053 through FR-065; NFR-017 through NFR-019

---

## FM-001

ID: FM-001

ORIGINAL DEFECT:
MacroBeatSheet, SceneListManifest and SceneBreakdownManifest projection/planning contracts were absent.

SOURCE AUTHORITY READ:
- ADR-0018 Narrative Artifact Identity
- NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL.md
- canonical Story supporting sources referenced by ADR-0018

MASTER SECTIONS CHANGED:
- §24 + §24A MacroBeatSheet
- §26 + §26A SceneListManifest
- §27 + §27A SceneBreakdownManifest
- §99, §101.6, §102.1

EXACT DECISION RESTORED:
- MacroBeatSheet = ordered structural projection of canonical MacroStoryBeat IDs.
- SceneListManifest = ordered projection of canonical Scene IDs.
- SceneBreakdownManifest = ordered projection of canonical SceneDramaticBeat IDs plus planning metadata.
- Manifest/projection != canonical entity truth.

TRACEABILITY UPDATED:
FR-055, FR-059, FR-060, §101.6.

LOCAL CHECK RESULT:
All three contracts and explicit no-shadow invariants are present.

STATUS: REPAIRED

---

## FM-002

ID: FM-002

ORIGINAL DEFECT:
Canonical components in §06–§41 did not all expose component-local lifecycle/version/invalidation/failure/QA semantics.

SOURCE AUTHORITY READ:
- STORY_INTELLIGENCE_CANONICAL_CONTRACTS_V0_16.md
- STORY_INTELLIGENCE_ARCHITECTURE_V0_16.md
- NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL.md
- Master §01 completeness invariant

MASTER SECTIONS CHANGED:
§06 through §41, component-local completion/field normalization only.

EXACT DECISION RESTORED:
Every §06–§41 component explicitly declares PURPOSE, CANONICAL DEFINITION, OWNER, AUTHORITY, INPUTS, OUTPUTS, IDENTITY, STATE, MUTABILITY, VERSION, PROVENANCE, PERSISTENCE, DEPENDENCIES, INVALIDATION, FAILURE MODES, QA / GATE, IMPLEMENTATION IMPLICATION.

Where a service or diagnostic does not own canonical narrative identity/state, the Master records N/A with reason instead of inventing authority.

TRACEABILITY UPDATED:
§101.6 plus existing/new requirement rows as applicable.

LOCAL CHECK RESULT:
Strict scanner reports zero missing required fields across §06–§41.

STATUS: REPAIRED

---

## FM-003

ID: FM-003

ORIGINAL DEFECT:
Four GenerationJob axes existed but exact canonical enums and transition ownership were absent.

SOURCE AUTHORITY READ:
- ADR-0012 Orthogonal Job State Correction
- JOB_STATE_MODEL_V0_13.md
- JOB_STATE_MODEL_CHECK_V0_13.md/.json
- FAILURE_RECOVERY_MODEL.md
- DATA_MODEL.md

MASTER SECTIONS CHANGED:
§68.

EXACT DECISION RESTORED:
- exact Scheduler enum including WAITING_RECOVERY;
- exact Provider enum including UNKNOWN_REMOTE_STATE, RECONCILING, AMBIGUOUS_HOLD;
- exact Artifact enum including STALE_RESULT;
- exact Creative enum including QA_ERROR;
- per-axis transition owner;
- source-backed legal-path constraints and valid/invalid cross-axis examples;
- generic status remains non-authoritative;
- NO RETRY WITHOUT PROOF remains locked.

TRACEABILITY UPDATED:
FR-019, REL-009, §101.6.

LOCAL CHECK RESULT:
Exact enum members, owners, ambiguity chain, invalid-state handling, persistence and observability are present.

STATUS: REPAIRED

---

## FM-004

ID: FM-004

ORIGINAL DEFECT:
Explicit Electron target security hardening baseline was omitted.

SOURCE AUTHORITY READ:
- SECURITY_MODEL.md §§1–5
- ADR-0002 Desktop Process Topology
- ADR-0016 Credential Authority

MASTER SECTIONS CHANGED:
§84, §85, §101.6.

EXACT DECISION RESTORED:
- nodeIntegration = false
- contextIsolation = true
- sandbox = true
- webSecurity = true
- allowRunningInsecureContent = false
- narrow capability-scoped contextBridge
- typed/allowlisted IPC
- sender/origin/frame validation
- navigation/new-window/external URL restrictions
- no generic shell/filesystem/secret bridge to Renderer
- Renderer never receives long-lived secrets
- Electron Main / Host Security Broker owns safeStorage
- Utility receives scoped short-lived leases
- CSP/remote-content policy direction retained
- current FlowKit explicitly distinguished from TARGET Electron architecture

TRACEABILITY UPDATED:
SEC lineage and §101.6.

LOCAL CHECK RESULT:
All five required flags and target-not-current warning are present.

STATUS: REPAIRED

---

## FM-005

ID: FM-005

ORIGINAL DEFECT:
Invalidation was conceptual only; there was no durable InvalidationRecord, restart/replay semantics, or explicit ReferenceVersion trigger.

SOURCE AUTHORITY READ:
- NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL.md §§44–45
- ADR-0017 invalidation direction
- ADR-0020 state/reference/profile invalidation direction
- canonical persistence/recovery sources

MASTER SECTIONS CHANGED:
§57, §63, §72, §99, §101.6, §102.1.

EXACT DECISION RESTORED:
Durable InvalidationRecord includes invalidation identity/cause, source old/new versions, affected object/version, dependency edge/reason, scope/status, provenance, repair/recompute requirement, resolution and deterministic dedupe key.

Records are serialized through one logical SQLite writer, replayed on restart, deduplicated idempotently and do not own DependencyGraph truth.

ReferenceVersion change -> dependency lookup -> durable InvalidationRecord(s) -> affected descendants stale/invalid -> recompute/regenerate/re-QA as required.

TRACEABILITY UPDATED:
FR-023, NFR-019, §101.6.

LOCAL CHECK RESULT:
Required durability/restart/idempotency fields and ReferenceVersion trigger are present.

STATUS: REPAIRED

---

## FM-006

ID: FM-006

ORIGINAL DEFECT:
Post-V0.16 Narrative Expansion obligations lacked stable requirement IDs.

SOURCE AUTHORITY READ:
- NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL.md §§79, 85–86
- ADR-0018
- existing §102 numbering scheme

MASTER SECTIONS CHANGED:
§102.1, §101.6.

EXACT DECISION RESTORED:
Existing IDs were not renumbered.

Added:
- FR-053 Logline
- FR-054 StructureProfile
- FR-055 MacroBeatSheet
- FR-056 SequencePlan
- FR-057 DurationBudget
- FR-058 SceneBudget
- FR-059 SceneListManifest
- FR-060 SceneBreakdownManifest
- FR-061 Screenplay Realization
- FR-062 Narrative Expansion Trace
- FR-063 ShotBudget
- FR-064 Shot Expansion
- FR-065 ShotListManifest
- NFR-017 deterministic narrative traceability
- NFR-018 immutable approved creative versions
- NFR-019 durable dependency-based invalidation

Each maps source authority -> component -> contract/persistence-interface -> QA/Test -> acceptance.

TRACEABILITY UPDATED:
§102.1, §101.6.

LOCAL CHECK RESULT:
All 16 new IDs have exactly one requirement-row definition; prior FR-001–052 and NFR-001–016 remain present.

STATUS: REPAIRED

---

## FM-007

ID: FM-007

ORIGINAL DEFECT:
ApprovedEndState could be interpreted as a second canonical state truth store.

SOURCE AUTHORITY READ:
- DATA_MODEL.md StateSnapshot
- REQUIREMENTS FR-012 acceptance
- Universal Niche/Brain approval-state rule

MASTER SECTIONS CHANGED:
§61, §80, §99, §101.6.

EXACT DECISION RESTORED:
- ApprovedEndState is an approval-qualified designation/reference to immutable/versioned StateSnapshot.
- canonical world-state payload remains only in StateSnapshot.
- semantic state identity/version is the referenced StateSnapshot identity/version.
- approval record carries lineage/provenance only.
- designation MUST NOT duplicate canonical state payload.

TRACEABILITY UPDATED:
FR-012, FR-029, §101.6.

LOCAL CHECK RESULT:
Explicit no-shadow boundary and StateSnapshot authority are present.

STATUS: REPAIRED

---

## FM-008

ID: FM-008

ORIGINAL DEFECT:
ShotEligibilityGate had no explicit identity/version and no stale-gate re-evaluation lineage.

SOURCE AUTHORITY READ:
- ADR-0020 Shot Identity/Spec/IR Boundary
- BEAT_SCENE_TO_SHOT_AUTHORITY_ARCHITECTURE_V1_FINAL.md

MASTER SECTIONS CHANGED:
§49, §99, §101.6.

EXACT DECISION RESTORED:
- shot_eligibility_gate_id/version
- canonical shot_id reference
- evaluated input versions/hashes
- rule/profile version
- result/blocking reasons/provenance/timestamp
- immutable persisted evidence
- dependency/version change forces re-evaluation
- stale gate cannot authorize FullShotSpec
- Gate != ShotListItem != FullShotSpec != ShotIR
- gate never creates a second shot_id

TRACEABILITY UPDATED:
FR-006/007/014 lineage and §101.6.

LOCAL CHECK RESULT:
Gate identity/version, no-second-Shot rule and stale-evidence rejection are explicit.

STATUS: REPAIRED

---

## CROSS-FINDING CONSISTENCY CHECK

1. MacroBeatSheet does not become MacroStoryBeat truth — PASS.
2. SceneListManifest does not become Scene truth — PASS.
3. SceneBreakdownManifest does not become SceneDramaticBeat truth — PASS.
4. ApprovedEndState does not become independent State truth — PASS.
5. InvalidationRecord does not own DependencyGraph truth — PASS.
6. ShotEligibilityGate does not create a second Shot identity — PASS.
7. Exact job enums remain consistent with ambiguity/retry rules — PASS.
8. Electron security remains TARGET, not a current-implementation claim — PASS.
9. Requirement IDs are unique definitions; old IDs are not renumbered — PASS.
10. §06–§41 strict contract field check reports zero missing fields — PASS.

## LOCAL REPAIR RESULT

FM-001: REPAIRED
FM-002: REPAIRED
FM-003: REPAIRED
FM-004: REPAIRED
FM-005: REPAIRED
FM-006: REPAIRED
FM-007: REPAIRED
FM-008: REPAIRED

8/8 local repair complete.

This is repair evidence only and is NOT independent audit evidence.

Master remains IMPLEMENTATION BASELINE CANDIDATE — NOT YET FROZEN.

NEXT required design action:

RE-RUN INDEPENDENT FINAL MASTER AUDIT AFTER FM-001 THROUGH FM-008 REPAIR
