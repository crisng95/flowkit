# PROJECT_STATE.md

**Project:** Master AI-Native Visual & Film Studio  
**Stage:** FINAL DESIGN CONSOLIDATION PREPARATION  
**Design maturity:** L5.5 — Reviewed + Partial Hardening Evidence
**Implementation status:** NOT STARTED  
**Feature coding:** BLOCKED ONLY UNTIL IMPLEMENTATION BASELINE + TASK GRAPH/QUEUE ARE FROZEN

## Accepted design directions

- Story Intelligence V0.16: 12-round repo harvest complete; Studio owns canonical Premise→Angle→Theme→Research→Brain→Character→Conflict→Causality→Emotion→Scene/Beat→Dialogue→Critique/Repair→Script Lock.
- Repo donor policy: licensed ADAPT/EXTRACT or Brain Pack; GPL/no-license PATTERN-ONLY by default; no donor state is canonical.
- Development phase rule (ADR-0015): implementation/live benchmarks attach to subsystem acceptance after code unless a pre-code spike can materially change architecture.

- Windows Persistence / Recovery gate: CLOSED with target-runtime Run-2 evidence; SQLite V1 uses one logical write owner + bounded write queue.

- Evidence governance: SHA-256 ledger + explicit evidence classes + gate-specific minimum evidence requirements.
- Job state V0.13: four orthogonal axes; artifact state is materialization-only; WAITING_RECOVERY and QA_ERROR are explicit.

- Provider profiles are surface-specific and evidence-versioned; no brand-level quota/billing assumptions.
- Job state is orthogonal: scheduler + provider submission + artifact + creative acceptance.
- Cost uses typed billing units; no universal price/job.

- Scheduler admission: global + provider + model + operation + local-resource + budget gates; priority + project fairness + oldest-ready ordering.

- Static QA acceptance: severity-based multi-dimensional gate; BLOCKING defects cannot be averaged away.
- Targeted Repair: typed preserve/patch/invalidate/recheck plan; selective invalidation; real repair success still unproven.

- Credential broker: Renderer never receives plaintext secret; Main/safeStorage authorizes short-lived one-use leases to trusted Utility by provider+operation+credential-version.

- Provider ambiguity architecture: `SUBMITTING → UNKNOWN_REMOTE_STATE → RECONCILING → AMBIGUOUS_HOLD`; no blind resubmit after uncertain acceptance.

- Canonical hierarchy: Story → Sequence → Scene → Beat → Shot.
- Shot is generation unit.
- 8-Layer ShotSpec + Shot IR are canonical generation intent.
- Prompt strings are compiled artifacts.
- Keep FlowKit strengths in Entity/Reference/Continuity execution/Generation integration/Orchestration.
- Add persistent State Engine.
- Add Reference Bible.
- Add provider capability registry + adapters.
- Add Static QA.
- Extend Video QA.
- Add Targeted Repair.
- Use best-of-breed reference repos through adapters/concepts, not multiple competing masters.
- Prefer modular monolith as current architecture candidate.

## Pending decisions

- DB/storage technology.
- desktop/backend process boundary.
- secret storage.
- provider set for v1.
- precise concurrency and rate-limit targets.
- artifact retention.
- update/migration strategy.
- plugin permission model.
- exact QA metric implementation.
- commercial license policy.

## Completed reviews

- Product completeness
- Architecture
- Data/state
- Security
- Reliability/recovery
- Performance/concurrency
- Maintainability/extensibility
- Testing/acceptance
- Deployment/operations
- Devil's Advocate

## Open blockers / hardening gaps

No unresolved conceptual BLOCKER remains after current design patches.

Evidence blockers:
1. target Windows SQLite/update evidence;
2. live provider UNKNOWN_REMOTE_STATE reconciliation evidence (architecture + mock proof complete);
3. Windows Electron safeStorage/utilityProcess credential-broker evidence (architecture + local simulation complete);
4. Static QA calibration evidence;
5. Targeted Repair benchmark evidence;
6. representative performance/cost benchmark.

## Frozen sections

None at L7. Several modules are REVIEWED CANDIDATES, not frozen:
- persistence;
- security boundary;
- contract format;
- desktop topology;
- observability.

## Next milestone

Story repo harvest is complete. Do not continue open-ended Story repo search.

```text
FINAL DESIGN CONSOLIDATION
→ create authority/supersession map for V0.1–V0.16
→ resolve stale contradictions
→ IMPLEMENTATION_BASELINE_FROZEN
→ component dependency graph
→ task decomposition + TASK_QUEUE
→ BEGIN CODE
```

Live Electron/provider/QA/repair/performance evidence remains required for the corresponding implementation/release milestones, not as a universal prerequisite to start coding.
