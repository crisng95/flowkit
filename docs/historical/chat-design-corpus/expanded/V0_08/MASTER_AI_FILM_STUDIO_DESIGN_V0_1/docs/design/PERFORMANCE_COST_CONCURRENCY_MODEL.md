# PERFORMANCE_COST_CONCURRENCY_MODEL.md
# Performance / Cost / Concurrency Model — V0.4

**Status:** REVIEWED CANDIDATE

---

# 1. Primary Bottleneck Model

This studio is expected to be predominantly:

```text
remote-provider-latency bound
+
network bound
+
media I/O bound
```

rather than SQLite CPU bound.

Local expensive tasks may include:
- ffmpeg frame extraction;
- vision QA;
- image embeddings;
- video metrics;
- checksum/media inspection.

---

# 2. Concurrency Hierarchy

Do not use one global `12` limit alone.

```text
Global Limit
├── Provider Limit
│   ├── Model Limit
│   │   └── Operation-Type Limit
└── Local Resource Pools
    ├── CPU media
    ├── GPU QA
    └── disk/download
```

Candidate settings are policy/config, not canonical schema.

Example:

```text
global_generation = 12
provider_flow = 4
provider_seedance = 4
provider_wan_remote = 4
video_jobs_per_model = 2
local_ffmpeg = min(physical_core_policy)
qa_gpu = 1 or 2
```

Numbers are placeholders until measured.

---

# 3. Backpressure

Queue accepts more work than can execute, but scheduler only claims jobs when all required capacity tokens exist:

```text
global token
provider token
model token
operation token
budget token (if configured)
dependency ready
```

No busy loop.

---

# 4. Fairness

Candidate scheduling:

```text
priority class
+
project fairness
+
oldest-ready
```

Avoid one 300-shot project starving interactive user requests indefinitely.

Priority examples:
- INTERACTIVE;
- NORMAL;
- BULK;
- RECOVERY.

---

# 5. Rate Limits

Provider adapter owns normalized rate-limit state:

```text
limit_type
remaining?
reset_at?
retry_after?
cooldown_until
source
```

Scheduler should stop submitting before repeated 429 storms.

---

# 6. Cost Model

Every compiled request may carry:

```text
estimated_cost
cost_basis
currency
estimate_version
```

Completed job records:
```text
actual_cost
provider_billing_reference?
```

Aggregate:

```text
cost per candidate
cost per accepted shot
cost per project
repair cost
wasted stale-result cost
failed-generation cost
```

---

# 7. Budget Gates

Optional project policy:

```text
soft_budget
hard_budget
per_shot_budget?
```

Hard budget blocks new paid submissions except explicitly approved recovery/critical operations.

Never cancel already-charged remote work blindly if provider cannot refund.

---

# 8. Caching

Safe caches:

```text
reference normalized derivatives by content hash
image embeddings by artifact hash + model version
contact sheets by artifact hash + extractor version
provider capability profile by version/TTL
compiled request by ShotIR hash + compiler/profile versions
```

Do not cache secret-bearing request objects.

---

# 9. Incremental Recompute

Editing one shot should not re-run:
- project-wide embeddings;
- unrelated sequence QA;
- unrelated references;
- all provider prompts.

Use dependency/lineage graph to recompute affected windows only.

---

# 10. Memory

Do not load all full-resolution media into memory.

Use:
- streaming;
- thumbnails/proxies;
- bounded frame samples;
- lazy project pagination;
- separate metadata/media caches.

---

# 11. Disk

Track:
```text
artifact bytes
proxy bytes
cache bytes
staging bytes
DB/WAL bytes
free disk
```

Before large video batches, estimate required disk budget.

Low disk becomes scheduler admission failure, not mid-download surprise.

---

# 12. Benchmark Scenarios

## PERF-01 — Metadata DB
12 concurrent worker status writers + UI reads.

## PERF-02 — 300-shot scheduling
Dependency graph readiness, invalidation and pagination.

## PERF-03 — Artifact ingest
parallel image/video downloads + checksums.

## PERF-04 — QA
static reviewer throughput; video frame extraction; metric cost.

## PERF-05 — Recovery
restart with 100 mixed in-flight/unknown/staging jobs.

## PERF-06 — UI
open 300-shot project without loading original media.

---

# 13. Production Metrics

```text
queue_wait_ms
time_to_first_candidate
time_to_accepted_shot
provider_latency
qa_latency
repair_latency
cost_per_accepted_shot
scheduler_utilization
rate_limit_idle_time
local_cpu/gpu utilization
disk throughput
```


# V0.8 Local Benchmark Evidence

A 300-shot local metadata/scheduler spike was executed.

Observed in the current sandbox:
- 300 shots;
- 314 dependency edges;
- 300 queued jobs;
- recursive descendant and ready-job queries remained sub-millisecond on average;
- flat global-only scheduling violated provider caps in the synthetic workload;
- hierarchical global/provider/model scheduling recorded zero cap violations under the same simulation.

Important:
- these are sandbox timings;
- provider caps were synthetic;
- no real provider throughput/pricing is inferred.

This evidence strengthens the architecture but does not replace target Windows/provider benchmarks.
