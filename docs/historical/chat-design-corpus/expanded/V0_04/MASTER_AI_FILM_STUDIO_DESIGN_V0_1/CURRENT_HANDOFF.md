# CURRENT_HANDOFF.md

**Current phase:** DESIGN / RESEARCH  
**Current maturity:** L5.5 — Reviewed + Partial Hardening Evidence
**Last completed action:** Ran a real SQLite WAL design spike; deep-designed Static QA, Targeted Repair, Performance/Cost/Concurrency, and Update/Migration/Backup; independent reviews now 1–35.

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

Continue hardening without production feature code:

```text
1. Provider Ambiguity Spike:
   verify idempotency/reconciliation behavior for the first real V1 provider adapter.

2. Credential Broker Spike:
   Electron main safeStorage ↔ utilityProcess, renderer denial, log/export secret scan.

3. Target Windows Persistence/Update Spike:
   WAL concurrency, crash/restart, migration interruption, backup/restore.

4. Static QA Calibration Spike:
   labeled identity/state/prop/camera/continuity near-miss set.

5. Targeted Repair Benchmark:
   compare PATCH / RE-ANCHOR / REPLAN against full-regenerate baseline.

6. Performance/Cost Benchmark:
   12-slot scheduler, provider limits, QA load, 300-shot metadata project.

7. Independent review rounds 36..N.

8. Only then decide whether L6 Hardened is justified.
```
