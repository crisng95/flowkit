# Task Queue

## Pending

- Repository discovery and audit.
- Design work is intentionally not started yet.


---

## Discovery / Design Queue ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â 2026-09-22

### Verified discovery completed

- [x] Read governance/bootstrap files.
- [x] Map current repository topology and manifests.
- [x] Audit current Entity / Reference / Continuity / Story / Scene / Beat / Shot / Prompt subsystems.
- [x] Audit Generation / Provider / Queue / Retry / Resume / Persistence / QA / Repair subsystems.
- [x] Create current-state architecture audit.
- [x] Create FlowKit-to-target-Studio gap matrix.

### Pending design/discovery only

- [ ] Import canonical Studio design documents supplied/approved for this project.
- [ ] Build a Design Authority Map: concept ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ authoritative document ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ owner ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ version ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ lock state.
- [ ] Build terminology map between current FlowKit concepts and target Studio concepts.
- [ ] Resolve canonical hierarchy: Story ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ MacroStoryBeat ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Sequence ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Scene ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ SceneDramaticBeat ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ Shot.
- [ ] Resolve current Scene migration role without changing feature code.
- [ ] Define conceptual boundaries for Entity / Reference / State / Continuity.
- [ ] Define authority precedence for FIXED / INHERITED / VARIABLE production truth.
- [ ] Define conceptual Shot IR and Compiler responsibility boundaries.
- [ ] Define Provider Capability / Router responsibility boundaries.
- [ ] Define Orchestrator / ProductionRun / PlanNode / Attempt / Artifact conceptual boundaries.
- [ ] Define QA Finding / Evidence / Gate and Targeted Repair conceptual boundaries.
- [ ] Produce architecture/dependency diagrams after authority conflicts are resolved.
- [ ] Only after design authority is locked, derive implementation tasks in a later phase.

No feature implementation tasks are authorized in this queue section.


---

## Pre-Master Authority Resolution Queue ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â 2026-09-22

### Completed design/discovery work

- [x] Read and hash-inventory V0.1 through V0.16 expanded corpus.
- [x] Evaluate three post-V0.16 design patches independently.
- [x] Evaluate standalone frozen architecture and FlowKit production audit.
- [x] Build file-level historical inventory.
- [x] Build evidence-based supersession graph.
- [x] Build domain authority map.
- [x] Build canonical merge candidate set.
- [x] Build pre-Master contradiction register.
- [x] Run pre-Master authority coverage audit.

### Blocking design decisions ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â resolve before Master

- [x] Resolve credential-broker/secret-storage authority status ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ADR-0016.
- [x] Resolve one universal BrainPack registry + ActiveProductionProfile ownership/precedence ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ADR-0017.
- [x] Resolve Narrative Expansion artifact identities and canonical hierarchy ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ADR-0018.
- [x] Resolve MacroStoryBeat/SceneDramaticBeat and DramaticÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢Camera authority ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ADR-0018 + ADR-0019.
- [x] Resolve Shot identity / ShotListManifest / FullShotSpec / ShotIR boundary ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ADR-0020.

### After blockers reach zero ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â still design only

- [x] Update contradiction register statuses with exact ADR decisions.
- [x] Update authority map so blocker domains have one conflict-free primary owner.
- [x] Re-run PRE_MASTER_AUTHORITY_COVERAGE_AUDIT ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â V2 PASS, blocking conflicts = 0.
- [ ] Only then authorize canonical Master consolidation in a later step.
- [ ] During later Master consolidation, add one Compiler responsibility section and one Sequence QA contract section.

No feature implementation, coding, build, dependency installation, test execution, task decomposition for code, or commit is authorized by this queue section.



---

## Master Consolidation Design Queue ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â 2026-09-22

Authority gate:
- [x] Blocking authority conflicts resolved.
- [x] PRE_MASTER_AUTHORITY_COVERAGE_AUDIT_V2 PASS.
- [x] Blocking conflicts = 0.

Next design-only action:
- [x] Consolidate accepted canonical sources into Master Implementation Baseline candidate.
- [x] Resolve PM-014 in Master ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§64 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â one Production Compiler boundary.
- [x] Resolve PM-020 in Master ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§77 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â one Sequence QA contract.
- [x] Run MASTER_CONSOLIDATION_SELF_AUDIT_V1 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â PASS; unresolved=0, blocking=0.
- [ ] Freeze Master only after zero blocking contradiction is verified.

No feature coding, build/test, dependency installation, implementation task decomposition or commit is authorized by this queue section.



---

## Independent Final Master Audit Queue ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â 2026-09-22

Completed:
- [x] Canonical Master candidate consolidated.
- [x] PM-014 Compiler responsibility resolved in Master ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§64.
- [x] PM-020 Sequence QA resolved in Master ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§77.
- [x] Requirement traceability repaired so every historical requirement ID is explicitly represented.
- [x] MASTER_CONSOLIDATION_SELF_AUDIT_V1 PASS.
- [x] Unresolved conflicts = 0.
- [x] Blocking conflicts = 0.

Next design-only gate:
- [x] Run independent final Master audit ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â FAIL: BLOCKER=0, MAJOR=8, MINOR=0, NOTE=2.
- [ ] Freeze is BLOCKED until all FINAL_MASTER_INDEPENDENT_AUDIT_V1 MAJOR findings are repaired and independently re-audited.
- [ ] Do not create dependency graph/task decomposition until the freeze step explicitly authorizes it.

No feature coding, build/test, dependency installation or commit is authorized by this queue section.



---

## Final Master Audit Repair Queue ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â 2026-09-22

Design-document repair only. No implementation tasks are authorized.

- [x] FM-001 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â restore MacroBeatSheet / SceneListManifest / SceneBreakdownManifest projection contracts without creating second truth stores.
- [x] FM-002 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â make Story/Pre-production component lifecycle contracts explicit at component level.
- [x] FM-003 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â restore JOB_STATE_MODEL_V0_13 exact state enums/transition ownership into Master.
- [x] FM-004 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â restore explicit Electron hardening flags and IPC/navigation security baseline.
- [x] FM-005 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â add durable InvalidationRecord ownership/persistence/version semantics and explicit Reference invalidation.
- [x] FM-006 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â allocate non-colliding requirement IDs for accepted post-V0.16 obligations and complete bidirectional traceability.
- [x] FM-007 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â make ApprovedEndState identity boundary explicit with StateSnapshot authority and no shadow state.
- [x] FM-008 ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â add ShotEligibilityGate identity/version and invalidation/re-evaluation semantics.
- [ ] Re-run FINAL MASTER INDEPENDENT AUDIT after exact repairs - NEXT_EXACT_ACTION; intentionally not run in this repair turn.
- [ ] Freeze only after independent re-audit returns BLOCKER=0 and MAJOR=0.

Do not create dependency graph, implementation task decomposition, feature code, build/test runtime, dependency install or commit before the freeze gate authorizes them.


Repair completion:
- [x] FM-001 through FM-008 local repair = 8/8 REPAIRED.
- [x] FINAL_MASTER_REPAIR_FM001_FM008_V1.md created.
- [x] Master remains candidate and unfrozen.
- [ ] Independent re-audit required next.
- [ ] Freeze remains blocked until independent re-audit returns BLOCKER=0 and MAJOR=0.

No feature code, build/test runtime, dependency installation, commit, dependency graph or coding task decomposition is authorized by this repair completion.

---

## Independent Final Master Audit V2 Queue - 2026-09-22

Design-document repair only. No implementation/coding tasks are authorized.

- [x] Run FINAL_MASTER_INDEPENDENT_AUDIT_V2 - FAIL: BLOCKER=0, MAJOR=6, MINOR=1, NOTE=1.
- [x] FM2-001 - restore explicit accepted contracts/mappings for SequencePlan, DurationBudget, SceneBudget, NarrativeTrace and ShotExpansion.
- [x] FM2-002 - freeze complete legal GenerationJob per-axis transition contract with guards/evidence.
- [x] FM2-003 - satisfy Ã‚Â§01 canonical component-contract completeness outside Ã‚Â§06-Ã‚Â§41.
- [x] FM2-004 - remove/resolve Topic Intelligence -> Profile Resolver bootstrap cycle.
- [x] FM2-005 - remove/resolve StoryCore <-> StoryGraph authority/order cycle.
- [x] FM2-006 - restore required Narrative Expansion defect-code registry and QA/repair/test mapping.
- [x] FM2-007 - repair malformed literal \n separators in Ã‚Â§102 traceability rows without semantic change.
- [x] FM2-008 - update stale Ã‚Â§100 self-status wording after scoped repair.
- [x] Run Independent Final Master Audit V3 after exact FM2-001 through FM2-008 repairs - NEXT_EXACT_ACTION; intentionally not run in this repair turn.
- [ ] Freeze remains blocked until independent audit returns BLOCKER=0 and MAJOR=0.

No feature code, runtime build/test, dependency installation, commit, dependency graph, implementation task decomposition or coding task is authorized by this queue section.

Repair completion:
- [x] FM2-001 through FM2-008 local repair = 8/8 REPAIRED.
- [x] FINAL_MASTER_REPAIR_FM2_001_FM2_008_V1.md created.
- [x] Contract completeness = 62/62; incomplete = 0.
- [x] Design dependency cycle count = 0.
- [x] Requirement registry = 112/112 independent valid rows.
- [x] Narrative Expansion defect registry = 36/36 exact source-required codes.
- [x] Repair regression self-check = 20/20 PASS.
- [x] Master remains candidate and unfrozen.
- [x] Independent Final Master Audit V3 completed - FAIL: BLOCKER=0, MAJOR=2, MINOR=0, NOTE=0.
- [ ] Freeze remains blocked until an independent audit returns BLOCKER=0 and MAJOR=0.

No feature code, runtime build/test, dependency installation, commit, implementation dependency graph, implementation task decomposition or coding task is authorized by this repair completion.

---

## Independent Final Master Audit V3 Queue - 2026-09-23

Design-document repair only. No implementation/coding tasks are authorized.

- [x] Run FINAL_MASTER_INDEPENDENT_AUDIT_V3 - FAIL: BLOCKER=0, MAJOR=2, MINOR=0, NOTE=0.
- [x] Verify FM2-001 - VERIFIED CLOSED.
- [x] Verify FM2-002 - REGRESSED under FM3-002.
- [x] Verify FM2-003 - NOT CLOSED under FM3-001/FM3-002.
- [x] Verify FM2-004 - VERIFIED CLOSED.
- [x] Verify FM2-005 - VERIFIED CLOSED.
- [x] Verify FM2-006 - VERIFIED CLOSED.
- [x] Verify FM2-007 - VERIFIED CLOSED.
- [x] Verify FM2-008 - VERIFIED CLOSED.
- [ ] FM3-001 - repair exact parent-only/nested-only component contract completeness findings.
- [ ] FM3-002 - separate immutable semantic/version data from mutable coordination state/status semantics in §63/§68/§69/§71.
- [ ] Re-run independent final Master audit only after FM3 findings are repaired.
- [ ] Freeze remains blocked until an independent audit returns BLOCKER=0 and MAJOR=0.

No feature code, runtime build/test, dependency installation, commit, implementation dependency graph, implementation task decomposition or coding task is authorized by this audit result.

Repair claim:
- [>] FM3-001 / FM3-002 = ACTIVE.
- [ ] Local self-audit after repair.
- [ ] Independent final audit after local self-audit.
- [ ] Freeze only if independent final audit returns BLOCKER=0 and MAJOR=0.

Repair claim:
- [>] FM3-001 / FM3-002 = ACTIVE.
- [ ] Local self-audit after repair.
- [ ] Independent final audit after local self-audit.
- [ ] Freeze only if independent final audit returns BLOCKER=0 and MAJOR=0.

FM3 repair completion:
- [x] FM3-001 local repair complete.
- [x] FM3-002 local repair complete.
- [x] Local self-audit complete: 101/101 component contracts.
- [ ] Run Independent Final Master Audit V4.
- [ ] Freeze only if V4 returns BLOCKER=0 and MAJOR=0.

---

## Frozen Baseline V1 Gate - 2026-09-25

- [x] FM3-001 repaired and independently verified.
- [x] FM3-002 repaired and independently verified.
- [x] FINAL_MASTER_INDEPENDENT_AUDIT_V4 = PASS.
- [x] Frozen status mutation completed.
- [x] FROZEN_MASTER_INDEPENDENT_AUDIT_V5 = PASS.
- [x] Freeze manifest created.
- [x] Frozen SHA = 1ff9383d713dfaab309d3f36cc83cf05e8932c1bc07f68682e2e12a488c77287.
- [x] Master implementation-design baseline V1 = FROZEN.
- [ ] Build implementation dependency graph from frozen Master.
- [ ] Decompose implementation into dependency-ordered tasks with acceptance/evidence gates.
- [ ] Only then claim first implementation task.

Implementation work is now design-authorized but must follow frozen authority, dependency order, per-task verification, evidence, review and MAIN VERIFIED lifecycle.

---

## IMP-001 - Frozen Baseline Guard

- [>] CLAIMED / ACTIVE on chatgpt/IMP-001-frozen-baseline-guard.
- [ ] Implement durable guard.
- [ ] Add fail-closed unit tests.
- [ ] Integrate guard into CI.
- [ ] Run targeted test.
- [ ] Run full unit regression.
- [ ] Capture evidence and verify frozen Master SHA.
- [ ] Commit / push / PR / review / merge / MAIN VERIFIED.

IMP-001 verification:
- [x] Implement durable guard.
- [x] Add fail-closed unit tests.
- [x] Integrate guard into CI.
- [x] Targeted Python 3.13: 9/9 PASS.
- [x] Local unaffected regression: 371 PASS / 3 exact Windows-only path cases deselected.
- [x] Evidence captured.
- [x] Frozen Master SHA unchanged.
- [ ] Commit.
- [ ] Push branch.
- [ ] Open PR.
- [ ] Ubuntu CI full unit suite.
- [ ] Review exact PR head.
- [ ] Merge main.
- [ ] Verify main and mark MAIN VERIFIED.
