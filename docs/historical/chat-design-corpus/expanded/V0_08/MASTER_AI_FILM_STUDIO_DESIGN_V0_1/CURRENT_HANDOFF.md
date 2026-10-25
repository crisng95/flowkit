# CURRENT_HANDOFF.md

**Current phase:** DESIGN / RESEARCH  
**Current maturity:** L5.5 — Reviewed + Partial Hardening Evidence
**Last completed action:** Ran 300-shot metadata/scheduler/cost local hardening spike, created target-Windows persistence/update harness, and completed reviews 59–66.

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

Continue according to evidence availability:

```text
A. If target Windows runtime is available:
   run tools/design-spikes/windows-persistence-update/run-windows-spike.ps1
   and capture evidence.

B. If authorized Electron target runtime is available:
   execute safeStorage/utilityProcess credential broker proof.

C. If authorized V1 provider test access is available:
   run live ambiguity fault injection.

D. Independently continue:
   prepare/run real-image Static QA calibration dataset/protocol;
   prepare real-generation Targeted Repair benchmark;
   collect provider quota/cost evidence;
   review 67..N.
```

Do not promote to L6 based only on local simulations.
