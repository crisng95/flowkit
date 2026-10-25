# PROJECT_STATE.md

**Project:** Master AI-Native Visual & Film Studio  
**Stage:** DESIGN / RESEARCH  
**Design maturity:** L5.5 — Reviewed + Partial Hardening Evidence
**Implementation status:** NOT STARTED  
**Feature coding:** BLOCKED BY DESIGN FREEZE

## Accepted design directions

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

The design has reached a point where remaining L6 blockers require target/live evidence rather than more speculative architecture prose.

```text
EXECUTE:
- Windows persistence/update harness
- Windows Electron credential harness
- shipping-provider ambiguity harness
- 240-image QA calibration
- 90-case real-generation repair benchmark
- shipping-provider live quota/cost observations

THEN:
→ independent evidence reviews 105..N
→ re-run contradiction + traceability audit
→ decide L6 HARDENED
```

If target/live environments are unavailable, continue only evidence preparation/research; do not manufacture a PASS.
