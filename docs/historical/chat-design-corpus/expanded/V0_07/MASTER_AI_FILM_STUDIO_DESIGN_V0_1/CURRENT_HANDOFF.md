# CURRENT_HANDOFF.md

**Current phase:** DESIGN / RESEARCH  
**Current maturity:** L5.5 — Reviewed + Partial Hardening Evidence
**Last completed action:** Continued beyond Credential Broker: ran Static QA acceptance-policy spike and Targeted Repair planner/invalidation spike; reviews now 1–58.

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

Continue hardening:

```text
1. Performance / Cost / Concurrency local benchmark
   - 12-slot scheduler
   - hierarchical provider/model limits
   - fairness/backpressure
   - 300-shot metadata graph
   - stale/invalidation workload

2. Prepare exact Windows persistence/update proof harness for target machine.

3. Prepare real Static QA labeled-image calibration protocol.

4. Prepare real Targeted Repair generation benchmark protocol.

5. Independent review 59..N.

6. Keep live-provider and Windows-Electron proofs explicitly open.
```
