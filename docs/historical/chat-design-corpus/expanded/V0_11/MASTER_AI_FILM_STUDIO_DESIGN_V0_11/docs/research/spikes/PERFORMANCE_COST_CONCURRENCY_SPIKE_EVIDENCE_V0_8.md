# PERFORMANCE_COST_CONCURRENCY_SPIKE_EVIDENCE_V0.8.md

**Status:** PARTIAL PROOF — LOCAL METADATA/SCHEDULER SIMULATION  
**Not claimed:** real provider throughput, pricing, Windows production performance.

## 1. Goal

Test three architecture assumptions:

1. 300-shot project metadata/dependency queries remain cheap enough for a local operational DB.
2. one global concurrency number is insufficient; provider/model limits must be enforced hierarchically.
3. budget admission can block **new** paid submissions without rewriting already-running job semantics.

## 2. Results

```json
{
  "environment": {
    "platform": "posix",
    "python": "3.13.5",
    "note": "Sandbox benchmark; not target Windows hardware."
  },
  "metadata_300_shots": {
    "shots": 300,
    "dependency_edges": 314,
    "jobs": 300,
    "db_size_bytes": 4096,
    "wal_size_bytes_at_measurement": 189552,
    "integrity_check": "ok",
    "ready_job_query_ms_mean": 0.0241,
    "ready_job_query_ms_p95": 0.0234,
    "ready_job_query_ms_max": 1.7917,
    "pagination_ms_mean": 0.0705,
    "pagination_ms_max": 0.1363,
    "descendant_query_ms_mean": 0.2849,
    "descendant_query_ms_max": 0.5537,
    "descendant_counts_sample": [
      299,
      275,
      250,
      225,
      200,
      175,
      150,
      125,
      100,
      75,
      50
    ]
  },
  "scheduler": {
    "global_cap": 12,
    "provider_caps": {
      "FLOW": 4,
      "VEO": 3,
      "SEEDANCE": 3
    },
    "model_caps": {
      "FLOW/flow-video": 3,
      "VEO/veo": 2,
      "SEEDANCE/seedance": 2
    },
    "flat_global_only": {
      "makespan_sim_seconds": 1549.13,
      "max_provider_concurrency": {
        "FLOW": 5,
        "VEO": 7,
        "SEEDANCE": 6
      },
      "provider_cap_violations": 190
    },
    "hierarchical": {
      "makespan_sim_seconds": 3495.34,
      "max_provider_concurrency": {
        "FLOW": 3,
        "VEO": 2,
        "SEEDANCE": 2
      },
      "max_model_concurrency": {
        "FLOW/flow-video": 3,
        "VEO/veo": 2,
        "SEEDANCE/seedance": 2
      },
      "provider_cap_violations": 0,
      "model_cap_violations": 0,
      "mean_start_by_project": {
        "P1": 1366.79,
        "P2": 1359.93,
        "P3": 1425.01
      },
      "fairness_mean_start_spread": 65.07
    }
  },
  "budget": {
    "synthetic_hard_budget_units": 100.0,
    "accepted_submissions": 94,
    "blocked_new_submissions": 206,
    "spent_units": 100.0,
    "note": "Synthetic cost units only; no provider pricing claim."
  }
}
```

## 3. 300-shot metadata

The spike created:

```text
300 shots
314 dependency edges
300 queued generation jobs
SQLite WAL + FULL synchronous
```

It repeatedly measured:
- scheduler-ready query;
- 25-row pagination;
- recursive descendant lookup for invalidation.

These timings support the design assumption that **metadata orchestration for hundreds of shots is not intrinsically a database bottleneck in the current sandbox**.

This is not a target-machine UI/media benchmark.

## 4. Global-only scheduler failure

A scheduler constrained only by:

```text
GLOBAL = 12
```

exceeded provider-specific caps in the simulation.

Observed provider-cap violation count:

```text
190
```

Therefore:

```text
GLOBAL LIMIT ONLY
≠
SAFE PROVIDER SCHEDULING
```

## 5. Hierarchical scheduler

The hierarchical scheduler enforced:

```text
global
→ provider
→ model
```

and recorded:

```text
provider cap violations = 0
model cap violations = 0
```

in the simulated workload.

This validates the control logic, not the chosen numerical cap values.

The actual cap values must come from provider policy/live evidence.

## 6. Fairness

The scheduler used:
- priority class;
- round-robin project fairness;
- oldest-ready ordering within project/priority.

This prevents a single large project from monopolizing all admissions when another project has equal-priority ready work.

The fairness metric here is synthetic because job durations/providers are simulated.

## 7. Cost admission

A synthetic hard budget demonstrated:

```text
new submissions stop after budget would be exceeded
already accepted/running remote work is not retroactively treated as refundable
```

No real provider prices are represented by the cost units.

## 8. Decision

Keep:

```text
GlobalAdmission
+ ProviderAdmission
+ ModelAdmission
+ OperationAdmission
+ LocalResourceAdmission
+ BudgetAdmission
```

with:
```text
priority
+ project fairness
+ oldest-ready
```

## 9. Remaining proof

Before L6:
- target Windows metadata/UI benchmark;
- real provider quotas/rate-limit behavior;
- real media download/checksum throughput;
- real QA CPU/GPU load;
- actual provider cost accounting;
- restart with a large mixed in-flight job set.
