# CANONICAL_DECISION_REGISTRY_V0_10.md
# Canonical Decision Registry

**Purpose:** one compact current authority map so older research/drafts cannot silently override newer decisions.

**Current maturity authority:** `PROJECT_STATE.md`

---

| ID | Responsibility | Current decision | Status | Primary authority |
|---|---|---|---|---|
| D-001 | Topology | Local-first canonical-domain modular monolith | REVIEWED CANDIDATE | DESIGN_DRAFT + ADR-0002 |
| D-002 | Narrative hierarchy | Story → Sequence → Scene → Beat → Shot | REVIEWED CANDIDATE | PROJECT_VISION |
| D-003 | Generation unit | Shot | REVIEWED CANDIDATE | PROJECT_VISION |
| D-004 | Creative source of truth | ShotSpec + ShotIR, not prompt | REVIEWED CANDIDATE | DESIGN_DRAFT |
| D-005 | Continuity authority | Approved semantic StateSnapshot; parent image is conditioning artifact | REVIEWED CANDIDATE | DATA_MODEL / contradiction audit |
| D-006 | Reference system | Versioned Reference Bible + semantic resolver | REVIEWED CANDIDATE | DESIGN_DRAFT |
| D-007 | Provider boundary | Provider-neutral ShotIR → provider compiler → adapter | REVIEWED CANDIDATE | API_CONTRACTS |
| D-008 | Provider identity | provider + surface + region + model/version | REVIEWED CANDIDATE | Provider Matrix V0.10 |
| D-009 | Persistence | SQLite WAL + FULL candidate for V1 local operational metadata | PARTIAL PROOF | ADR-0001 |
| D-010 | Media storage | immutable/content-addressed files + DB metadata | REVIEWED CANDIDATE | PERSISTENCE_ARCHITECTURE |
| D-011 | Job ambiguity | UNKNOWN_REMOTE_STATE; no blind ambiguous resubmit | PARTIAL PROOF | ADR-0007 |
| D-012 | Security | sandboxed Renderer → Main Security Broker → trusted Utility backend | PARTIAL PROOF | ADR-0002/0008 |
| D-013 | Secret storage | Main-process safeStorage vault; project holds credential IDs only | PARTIAL PROOF | ADR-0008 |
| D-014 | Browser session | provider-specific isolated session, not generic credential lease | REVIEWED CANDIDATE | CREDENTIAL_BROKER_ARCHITECTURE |
| D-015 | Contracts | Zod 4 runtime candidate + JSON Schema Draft 2020-12 export | REVIEWED CANDIDATE | ADR-0003 |
| D-016 | QA acceptance | severity-based multi-dimensional; BLOCKING fail cannot average away | PARTIAL PROOF | ADR-0005 |
| D-017 | Repair | earliest responsible layer + preserve/patch/invalidate/recheck | PARTIAL PROOF | ADR-0006 |
| D-018 | Scheduler | hierarchical admission + priority/project fairness/oldest-ready | PARTIAL PROOF | ADR-0009 |
| D-019 | Cost | typed billing units; price snapshot tied to provider surface/profile | REVIEWED CANDIDATE | Provider Matrix V0.10 |
| D-020 | Observability | current-state DB authoritative; durable events are audit evidence | REVIEWED CANDIDATE | OBSERVABILITY_DESIGN |
| D-021 | 3D previs | optional plugin, not core prerequisite | REVIEWED CANDIDATE | REQUIREMENTS |
| D-022 | FlowKit | keep Entity/Reference/chaining/orchestration/Flow transport concepts behind adapters | REVIEWED CANDIDATE | REFERENCE_PROJECTS |
| D-023 | Google surfaces | Flow Product, Gemini Veo, Vertex Veo are separate provider profiles | REVIEWED CANDIDATE | Provider Matrix V0.10 |
| D-024 | Wan surfaces | local Wan and Alibaba Model Studio Wan are separate adapters | REVIEWED CANDIDATE | Provider Matrix V0.10 |
| D-025 | Freeze gate | no L6/L7 until remaining live/target visual/runtime evidence closes | ACTIVE | IMPLEMENTATION_READINESS |

---

# Authority Rule

If two files disagree:

```text
1. PROJECT_STATE / CURRENT_HANDOFF for current maturity/work
2. accepted ADR for a specific decision
3. Canonical Decision Registry
4. latest dedicated subsystem design
5. DESIGN_DRAFT
6. historical research/baseline text
```

A newer evidence-supported ADR can supersede an older registry row; update this registry in the same design cycle.
