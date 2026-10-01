# CURRENT_HANDOFF.md

**Current phase:** DESIGN / RESEARCH  
**Current maturity:** L5 — Reviewed Design Candidate
**Last completed action:** Completed deep Security, Contracts, Observability, Desktop Process Topology and Traceability design; independent review rounds now 1–25.

## Current findings

- FlowKit remains valuable as execution/reference backend, not as full creative domain.
- `ShotSpec + Shot IR` is the strongest candidate for canonical generation intent.
- Persistent semantic state is required in addition to parent-image inheritance.
- provider-specific prompts must be compiled, never canonical.
- static QA and targeted repair are mandatory gaps.
- modular monolith is the current topology candidate.
- long-form support requires Sequence/Scene/Beat/Shot and restart-safe production state.

## Current design decisions

Candidate only, not frozen:
- Story → Sequence → Scene → Beat → Shot.
- Shot is generation unit.
- keep/adapt FlowKit entity/ref/chaining/queue.
- use provider adapters.
- use severity-based QA.
- targeted repair maps failure to earliest responsible layer.

## Unresolved questions

1. What local DB and transaction strategy?
2. Windows-only or cross-platform?
3. Required v1 providers?
4. Target concurrency/project scale?
5. Secret storage method?
6. Artifact retention policy?
7. Commercial licensing constraints?
8. Packaging/update strategy?

## Files updated

- docs/ideas/IDEA_INBOX.md
- docs/research/RESEARCH_LOG.md
- docs/research/REFERENCE_PROJECTS.md
- docs/design/PROJECT_VISION.md
- docs/design/REQUIREMENTS.md
- docs/design/DESIGN_DRAFT.md
- docs/design/DESIGN_DECISION_MATRIX.md
- docs/design/INDEPENDENT_REVIEW_LOG.md
- docs/design/IMPLEMENTATION_READINESS.md
- docs/diagrams/COMPONENT_GRAPH.md
- docs/diagrams/DATA_FLOW.md
- PROJECT_STATE.md
- CURRENT_HANDOFF.md

## NEXT_EXACT_ACTION

Proceed to **hardening**, still without feature coding.

```text
1. DESIGN SPIKE PLAN — SQLite concurrency/durability/crash points.
2. DESIGN SPIKE PLAN — provider ambiguous timeout/reconciliation/idempotency.
3. DESIGN SPIKE PLAN — safeStorage credential broker across main↔utilityProcess.
4. Deep QA architecture:
   Static semantic QA + metrics + thresholds + severity policy.
5. Deep Targeted Repair architecture:
   failure taxonomy, layer ownership, re-anchor/replan escalation.
6. Performance / cost / concurrency model:
   global/provider/model limits, backpressure, budget.
7. Update / migration / backup recovery proof plan.
8. Independent reviews 26..N.
9. Only if L6 hardening passes, run final traceability/contradiction audit for L7.
```

No production feature coding.
