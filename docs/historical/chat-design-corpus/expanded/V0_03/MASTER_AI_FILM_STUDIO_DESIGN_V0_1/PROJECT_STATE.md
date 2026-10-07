# PROJECT_STATE.md

**Project:** Master AI-Native Visual & Film Studio  
**Stage:** DESIGN / RESEARCH  
**Design maturity:** L5 — Reviewed Design Candidate
**Implementation status:** NOT STARTED  
**Feature coding:** BLOCKED BY DESIGN FREEZE

## Accepted design directions

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

No unresolved conceptual BLOCKER remains in the current V0.3 draft after review patches.

Evidence/hardening still required:
1. SQLite concurrency/crash design spikes.
2. provider UNKNOWN_REMOTE_STATE reconciliation proof.
3. main↔utility-process secret handoff spike.
4. migration/update recovery proof.
5. QA calibration/labeled benchmark.
6. targeted-repair effectiveness benchmark.

## Frozen sections

None at L7. Several modules are REVIEWED CANDIDATES, not frozen:
- persistence;
- security boundary;
- contract format;
- desktop topology;
- observability.

## Next milestone

Reach **L6 — Hardened Design** by designing/executing evidence-oriented design spikes and closing remaining HIGH risks:

```text
DB durability/concurrency spike
→ provider ambiguity/reconciliation spike
→ credential broker spike
→ update/migration recovery spike
→ QA/Repair calibration
→ performance/cost model
→ independent review rounds 26..N
```

Do not create FINAL_FROZEN_DESIGN.md yet.
