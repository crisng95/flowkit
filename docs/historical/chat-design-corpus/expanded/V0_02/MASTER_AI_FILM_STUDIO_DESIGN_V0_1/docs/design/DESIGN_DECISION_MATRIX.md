# DESIGN_DECISION_MATRIX.md
# Architecture Decision Matrix — V0.1

| Decision | Option A | Option B | Option C | Candidate |
|---|---|---|---|---|
| Overall topology | FlowKit-centric monolith | Canonical-domain modular monolith | microservices | **B** |
| Generation unit | Scene | Shot | provider clip | **Shot** |
| Creative source of truth | prompt | ShotSpec/ShotIR | generated artifact | **ShotSpec/ShotIR** |
| Continuity authority | parent image | semantic StateSnapshot + parent visual | prompt prose | **State + parent visual** |
| Story framework | one fixed beat system | framework plugins over causal core | no structure | **plugin over causal core** |
| Provider integration | provider fields in domain | adapter + capability registry | separate app per provider | **adapter** |
| Reference strategy | one canonical image | Reference Bible + resolver | upload all refs | **Bible + resolver** |
| QA strategy | one weighted score | severity-based multi-gate | manual-only | **multi-gate** |
| Repair | retry same request | layer-targeted repair | rebuild entire project | **targeted** |
| 3D previs | mandatory | optional plugin | none | **optional** |
| State persistence | chat/RAM | durable local DB | cloud-only | **durable local DB candidate** |
| External repo reuse | merge schemas | anti-corruption adapters | rewrite all | **adapters/selective reuse** |

---

# Weighted Evaluation of Overall Topology

Scoring 1–5. This is a design aid, not proof.

| Criterion | Weight | A FlowKit-centric | B Modular monolith | C Services |
|---|---:|---:|---:|---:|
| correctness | 5 | 3 | 5 | 5 |
| simplicity | 4 | 5 | 4 | 1 |
| maintainability | 5 | 2 | 5 | 4 |
| testability | 4 | 3 | 5 | 4 |
| extensibility | 4 | 2 | 5 | 5 |
| failure isolation | 3 | 2 | 4 | 5 |
| implementation effort | 4 | 5 | 3 | 1 |
| local-first fit | 5 | 5 | 5 | 2 |
| provider independence | 4 | 2 | 5 | 5 |
| future scale | 3 | 2 | 4 | 5 |

Candidate remains **Option B**, subject to deeper persistence/security/operations research.


## Persistence Decision Added

| Decision | Option A | Option B | Option C | Candidate |
|---|---|---|---|---|
| Operational DB | SQLite WAL | PostgreSQL | DuckDB | **SQLite WAL** |
| SQLite durability | WAL+NORMAL | WAL+FULL | rollback journal | **WAL+FULL candidate** |
| Media storage | DB BLOB | immutable filesystem/object-like store | provider URL only | **immutable file store + DB metadata** |
| concurrency conflict | last-write-wins | optimistic revision | global UI lock | **optimistic revision** |
| remote timeout | blind retry | reconcile-first | manual only | **reconcile-first** |
