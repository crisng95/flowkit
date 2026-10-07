# ADR-0001 — V1 Operational Persistence Engine

**Status:** PROPOSED  
**Date:** 2026-09-20

## Context

The studio is currently designed as a local-first modular monolith that orchestrates long-running remote media jobs and persists creative state, lineage, QA, and repair data.

The DB workload is primarily many short metadata transactions rather than large analytical scans.

## Problem

Choose an operational database architecture that provides:

- crash recovery;
- transactional state transitions;
- low deployment burden;
- restart-safe job tracking;
- local desktop fit;
- acceptable concurrency for UI + background orchestration;
- upgrade/backup capability.

## Options

### A — SQLite WAL
Embedded, low-ops, strong local fit, single writer.

### B — PostgreSQL
Excellent multi-user concurrency and server features, higher operational burden.

### C — DuckDB
Excellent analytics, less natural fit for frequent operational state transitions and multi-process orchestration.

## Decision

**Propose SQLite WAL for V1**, with:

```text
WAL
synchronous=FULL
foreign_keys=ON
short transactions
optimistic revisions
artifact bytes outside DB
durable job state
input fingerprints
startup reconciliation
```

## Why

Remote provider latency dominates workload, so SQLite's single-writer constraint is unlikely to be the limiting bottleneck at the initial target. In exchange, it dramatically simplifies local-first packaging, backup, testing, and operations.

## Rejected / Deferred

PostgreSQL is deferred until multi-machine/team/shared-server writes become a real requirement.

DuckDB is rejected as the primary operational store but remains a possible analytics companion.

## Consequences

Positive:
- no DB server dependency;
- easy per-test databases;
- strong local portability.

Negative:
- one active writer;
- local filesystem requirement for WAL;
- careful busy/retry and transaction discipline required.

## Risks

- write contention if future workload changes;
- accidental long transactions;
- network filesystem misuse;
- upgrade path to centralized server may require repository/adaptor work.

## Mitigation

- repository/data-access interfaces;
- short transactions;
- performance spike;
- no provider calls inside transactions;
- explicit threshold for revisiting PostgreSQL.

## Revisit Conditions

Reopen ADR if any becomes MUST:

- multi-machine writers;
- centralized multi-user collaboration;
- sustained high write concurrency;
- server-side organization RBAC;
- remote shared projects.
