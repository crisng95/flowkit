# WINDOWS_PERSISTENCE_RUN2_ANALYSIS_V0_15.md
# Windows Persistence / Recovery — Target Run 2

**Date:** 2026-09-21  
**Evidence:** `docs/research/evidence/windows/EVIDENCE_WINDOWS_PERSISTENCE_20260921_RUN2_PASS.json`  
**Evidence class:** TARGET_RUNTIME  
**Gate result:** PASS

---

# 1. Target Environment

```text
platform = win32
python   = 3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
threads  = 12
commands_per_producer = 250
busy_timeout_ms       = 5000
```

---

# 2. Adversarial Raw Multi-Writer Lane

This lane intentionally does **not** represent the production topology.

```text
expected  = 3000
committed = 2874
errors    = 126
integrity = ok
```

Exact error evidence:

```json
[
  {
    "error": "OperationalError: database is locked",
    "count": 126
  }
]
```

Run 2 confirms the Run-1 hypothesis: the direct 12-connection writer lane fails because of SQLite write-lock contention (`OperationalError: database is locked`).

This is diagnostic evidence, not a production-lane failure.

---

# 3. Production Acceptance Lane — Single Writer Queue

```text
producer_threads = 12
expected         = 3000
committed        = 3000
revision         = 3000
writer_errors    = 0
producer_errors  = 0
integrity        = ok
```

Result:

```text
3000/3000 committed
0 writer errors
0 producer errors
integrity_check = ok
```

This validates the V1 write-ownership design:

```text
many generation/provider producers
→ bounded local command queue
→ one logical SQLite write owner
→ short transactions
```

---

# 4. Crash / Recovery / Migration / Backup

## Abrupt Exit

```text
committed_survived = true
uncommitted_absent = true
integrity          = ok
```

## Migration Interruption / Resume

```text
status_after_crash = RUNNING
phase_after_crash  = 500
rows_after_crash   = 500
rows_after_resume  = 1000
integrity          = ok
```

## Backup / Restore

```text
restored_rows = 100
integrity     = ok
```

## Newer Schema Gate

```text
db_schema_version = 999
supported_max     = 7
write_allowed     = false
```

---

# 5. Performance Observation — Not a Performance Gate Closure

The production lane measured:

```text
elapsed_s                = 124.484
tx_per_s                 = 24.100
writer_latency_mean_ms   = 41.456
writer_latency_p95_ms    = 88.900
writer_latency_max_ms    = 141.243
producer_queue_wait_mean = 418.299 ms
producer_queue_wait_p95  = 531.287 ms
producer_queue_wait_max  = 649.811 ms
```

These timings are useful characterization only.

They do **not** close the separate `PERFORMANCE_TARGET` gate because:
- Python harness overhead is not the Electron/production implementation;
- media I/O/provider wait/QA load are not included;
- batching/group-commit policy has not been benchmarked.

Correctness is proven for this target run; end-to-end performance remains a separate gate.

---

# 6. Gate Decision

```text
PERSISTENCE_WINDOWS
TARGET_RUNTIME = PASS
GATE = CLOSED
```

Evidence lineage is preserved:

```text
Run 1 = FAIL
→ exposed direct-multiwriter defect
→ architecture patch: single write owner
→ Run 2 = PASS
```

No historical failure evidence is deleted.
