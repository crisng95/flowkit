# PROJECT_STATE.md

**Project:** Master AI-Native Visual & Film Studio  
**Stage:** DESIGN / RESEARCH  
**Design maturity:** L4.5 — Researched Design / Persistence Reviewed Candidate  
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

## Open blockers

1. Persistence candidate selected but DB spike not yet executed/frozen.
2. Security model not fully specified.
3. Formal API/contract schemas incomplete.
4. Requirement-to-test traceability incomplete.
5. Deployment/update design incomplete.

## Frozen sections

None. Strong candidate directions exist but are not yet L7 Frozen.

## Next milestone

Reach L5 Reviewed Design by completing:
- Security Model;
- formal API/contract schemas;
- observability event model;
- requirement→component→data→test traceability skeleton;
- deployment/process topology comparison;
- DB durability/concurrency design spike plan/evidence.
