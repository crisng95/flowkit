# CANONICAL_DECISION_REGISTRY_V0_10.md
# Canonical Decision Registry

**Current maturity authority:** `PROJECT_STATE.md`

| ID | Responsibility | Current decision | Status |
|---|---|---|---|
| D-001 | Topology | Local-first canonical-domain modular monolith | REVIEWED CANDIDATE |
| D-002 | Narrative hierarchy | Story → Sequence → Scene → Beat → Shot | REVIEWED CANDIDATE |
| D-003 | Generation unit | Shot | REVIEWED CANDIDATE |
| D-004 | Creative source | ShotSpec + ShotIR, not prompt | REVIEWED CANDIDATE |
| D-005 | Continuity authority | Approved StateSnapshot; parent image is conditioning artifact | REVIEWED CANDIDATE |
| D-006 | Reference | Versioned Reference Bible + resolver | REVIEWED CANDIDATE |
| D-007 | Provider boundary | ShotIR → provider compiler → adapter | REVIEWED CANDIDATE |
| D-008 | Provider identity | provider + surface + region + model/version | REVIEWED CANDIDATE |
| D-009 | Persistence | SQLite WAL + FULL for V1 candidate | PARTIAL PROOF |
| D-010 | Media | immutable/content-addressed files + DB metadata | REVIEWED CANDIDATE |
| D-011 | Ambiguous submit | UNKNOWN_REMOTE_STATE; no blind resubmit | PARTIAL PROOF |
| D-012 | Desktop security | Renderer → Main Security Broker → trusted Utility | PARTIAL PROOF |
| D-013 | Credentials | safeStorage vault; project holds IDs only | PARTIAL PROOF |
| D-014 | Browser session | provider-specific isolated session boundary | REVIEWED CANDIDATE |
| D-015 | Contracts | Zod 4 candidate + JSON Schema 2020-12 export | REVIEWED CANDIDATE |
| D-016 | QA acceptance | severity gate; blocking cannot average away | PARTIAL PROOF |
| D-017 | Repair | earliest responsible layer + selective invalidation | PARTIAL PROOF |
| D-018 | Scheduler | hierarchical admission + fairness | PARTIAL PROOF |
| D-019 | Cost | typed billing units + evidence snapshots | REVIEWED CANDIDATE |
| D-020 | Observability | current-state DB authoritative; events are audit evidence | REVIEWED CANDIDATE |
| D-021 | 3D previs | optional plugin | REVIEWED CANDIDATE |
| D-022 | FlowKit role | keep entity/reference/chaining/orchestration behind adapters | REVIEWED CANDIDATE |
| D-023 | Google surfaces | Flow/Gemini/Vertex separate profiles | REVIEWED CANDIDATE |
| D-024 | Wan surfaces | local vs Model Studio separate adapters | REVIEWED CANDIDATE |
| D-025 | Freeze | no L6/L7 until remaining evidence gates close | ACTIVE |

Authority on conflict:

```text
PROJECT_STATE / CURRENT_HANDOFF
→ accepted ADR for specific decision
→ Canonical Decision Registry
→ latest subsystem design
→ DESIGN_DRAFT
→ historical research/baseline text
```

| D-026 | Job state axes | Scheduler / Provider / Artifact Materialization / Creative Acceptance are orthogonal; V0.13 removes approval from artifact state and adds WAITING_RECOVERY + QA_ERROR | REVIEWED CANDIDATE / MODEL-CHECKED | JOB_STATE_MODEL_V0_13 |
| D-027 | Evidence authority | Evidence claims are SHA-256 ledgered and L6 gates require minimum evidence classes; harness readiness alone cannot close a gate | REVIEWED CANDIDATE / LOCAL-VERIFIED | EVIDENCE_LEDGER_V0_13 + L6_GATE_RULES_V0_13 |
