# SQLITE WAL DESIGN SPIKE EVIDENCE

**Type:** DESIGN SPIKE — NOT PRODUCTION CODE  
**Date:** 2026-09-20  
**Environment:** Python stdlib `sqlite3` in current sandbox  
**Purpose:** test selected design assumptions, not benchmark production hardware.

## 1. WAL short-transaction contention

```json
{
  "journal_mode": "wal",
  "synchronous_pragma_numeric": 2,
  "threads": 12,
  "transactions_per_thread": 150,
  "expected_transactions": 1800,
  "counter_value": 1800,
  "event_count": 1800,
  "revision": 1800,
  "busy_retries": 0,
  "errors": [],
  "elapsed_seconds": 0.138,
  "throughput_tx_per_sec": 13068.8,
  "latency_ms_mean": 0.293,
  "latency_ms_p50": 0.013,
  "latency_ms_p95": 0.03,
  "latency_ms_p99": 0.096,
  "latency_ms_max": 130.797
}
```

Interpretation:
- all expected short write transactions were committed if `counter_value` and `event_count` equal expected;
- no semantic correctness was delegated to timing;
- the result supports the design assumption that 12 application workers can share a local SQLite WAL metadata store when writes are short and bounded;
- this does **not** prove production throughput on the user's Windows machine.

## 2. Optimistic revision conflict

```json
{
  "reader_A_revision": 0,
  "reader_B_revision": 0,
  "A_rows_updated": 1,
  "B_rows_updated": 0,
  "final_revision": 1,
  "final_active_spec": "vA",
  "conflict_detected": true
}
```

Two readers observed the same revision. A committed first. B's `WHERE revision=?` update affected 0 rows, proving the proposed pattern can detect a stale concurrent editor instead of silently overwriting it.

## 3. Abrupt-process-exit durability behavior

```json
{
  "committed_row_survived_abrupt_exit": true,
  "uncommitted_row_absent_after_abrupt_exit": true,
  "integrity_check": "ok"
}
```

The committed row survived abrupt process exit, the uncommitted transaction did not become visible, and SQLite reported database integrity as shown above.

This is evidence for the transaction design, but **not** a literal power-cut test of storage hardware/cache behavior.

## 4. Artifact reconciliation classification

```json
[
  {
    "artifact": "A",
    "classification": "STALE_STAGING"
  },
  {
    "artifact": "B",
    "classification": "ORPHAN_OR_UNCOMMITTED_FINAL"
  },
  {
    "artifact": "C",
    "classification": "READY_METADATA_FILE_MISSING"
  }
]
```

The spike verifies that startup reconciliation can deterministically classify:
- stale staging partials;
- final files not committed as READY;
- READY metadata whose file is missing.

## 5. Design impact

This evidence strengthens, but does not fully freeze, ADR-0001:

```text
SQLite WAL
+ short transactions
+ optimistic revisions
+ staged artifact writes
+ startup reconciler
```

Remaining evidence before L6:
- Windows-target spike;
- `synchronous=FULL` vs `NORMAL` workload comparison;
- long-running concurrent reader/checkpoint test;
- update/migration interruption test;
- provider ambiguity reconciliation with a real adapter.
