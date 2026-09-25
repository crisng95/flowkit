# RESEARCH_LOG.md
# Research Log — V0.1

## R-001 — Is FlowKit a full studio architecture?
**Finding:** No. It is strongest in entity/reference execution, parent-image continuity, generation integration, queue/dependency execution, and video review.  
**Decision:** Keep those parts. Replace its scene-centric creative authority with canonical Story→Sequence→Scene→Beat→Shot.

## R-002 — Is a first-class Beat needed?
**Finding:** Yes for narrative intent and shot motivation. `take` and `film-production-skills` both provide structured beat/shot concepts.  
**Decision:** Beat becomes first-class.

## R-003 — Is a free-form prompt sufficient as source of truth?
**Finding:** No. Prompt overrides can bypass higher-level locks and are provider-specific.  
**Decision:** ShotSpec + Shot IR become source of truth; prompts are compiled artifacts.

## R-004 — Can parent-image continuity replace state?
**Finding:** No. Parent images carry implicit state but can also carry defects.  
**Decision:** Use canonical refs + approved state + parent visual + current shot delta.

## R-005 — Is camera vocabulary enough for cinematography?
**Finding:** No. A professional decision system must begin with story function, audience information, blocking, performance and rhythm.  
**Decision:** camera/lens/movement dictionaries are tools, not the decision brain.

## R-006 — Can QA be one weighted score?
**Finding:** No. A critical identity/prop/state failure must not be averaged away by aesthetic scores.  
**Decision:** use severity-based multi-dimensional gates.

## R-007 — Can retry equal repair?
**Finding:** No. Technical retry and creative repair are different.  
**Decision:** technical retry stays in execution; creative repair uses root-cause/layer ownership.

## R-008 — Do we need restart-safe state?
**Finding:** Yes. Continuity Studio demonstrates stage persistence and resume patterns.  
**Decision:** production state machine is persistent and restart-safe.

## R-009 — Should 3D previs be mandatory?
**Finding:** No. It adds cost/complexity; value is high only for spatially complex/action shots.  
**Decision:** optional plugin.

## R-010 — Should one fixed screenplay framework be mandatory?
**Finding:** No. It harms universality.  
**Decision:** story frameworks are plugins; causality/state are core.

---

# Deep Research Still Required

1. Persistence technology and migration strategy.
2. Exact local-first desktop/backend split.
3. Secret storage on Windows/macOS if cross-platform.
4. Provider capability discovery/versioning.
5. Job reconciliation after ambiguous network timeout.
6. Storage retention and artifact cleanup.
7. Cost accounting model.
8. Concurrency/backpressure targets.
9. Static semantic QA implementation and benchmark.
10. Targeted Repair success criteria.
11. Long-form 300-shot benchmark methodology.
12. Plugin security boundary.
13. Exact licensing before code import.
14. Packaging/update strategy.
15. NLE/export target formats.


## R-011 — SQLite WAL design spike
**Evidence:** `docs/research/spikes/SQLITE_WAL_DESIGN_SPIKE_EVIDENCE.md`.  
**Result:** 12-thread short-write spike completed 1,800/1,800 transactions in the current sandbox with no reported write errors; optimistic revision conflict detected; abrupt-process-exit transaction behavior matched design expectations; artifact reconciler classifications worked.  
**Limitation:** not target Windows/power-loss evidence.  
**Decision:** persistence candidate strengthened, not frozen.

## R-012 — Static QA
**Finding:** one aggregate score is unsafe for continuity anchors.  
**Decision:** severity-based multi-dimensional QA with blocking dimensions.

## R-013 — Targeted Repair
**Finding:** defect labels do not always identify causal owner; repair must diagnose earliest responsible layer and regression-check preserved fields.  
**Decision:** bounded four-mode repair architecture.

## R-014 — Concurrency
**Finding:** provider capacity is hierarchical and cost-sensitive.  
**Decision:** global/provider/model/operation/local-resource admission tokens + fairness.

## R-015 — Update/migration
**Finding:** scheduler startup must be gated by schema compatibility and recovery.  
**Decision:** migration/recovery precedes scheduler.


## R-016 — Provider ambiguity / duplicate paid generation
**Sources:** FlowKit source/test audit + current official Veo/Google Gen AI documentation + local fault-injection simulator.  
**Finding:** FlowKit correctly re-polls once a remote operation ID has been stored, but its current submit→persist interval remains ambiguous if the response/process fails before that durable write.  
**Evidence:** legacy-like simulator produced two remote jobs after a crash at this exact point; safety-first state machine produced zero automatic duplicates in 1,500 randomized mock recovery runs.  
**Decision:** add `SUBMITTING`, `UNKNOWN_REMOTE_STATE`, `RECONCILING`, `AMBIGUOUS_HOLD`; generic retry prohibited after uncertain acceptance.  
**Residual risk:** live provider semantics not yet fault-injected.
