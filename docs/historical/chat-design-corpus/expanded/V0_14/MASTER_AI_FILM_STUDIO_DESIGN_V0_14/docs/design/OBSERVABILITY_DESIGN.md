# OBSERVABILITY_DESIGN.md
# Observability Design — Deep Dive V0.3

**Status:** REVIEWED CANDIDATE

---

# 1. Goal

Answer production questions without opening source code or guessing:

```text
What happened?
Where?
To which project/shot/job?
With which input version?
Which provider?
How long?
How many attempts?
How much cost?
What failed?
Was it recovered?
What artifact/QA/repair followed?
```

---

# 2. Three Layers

```text
A. Durable Domain/Operational Events
B. Structured Local Logs
C. Metrics / Traces adapter
```

Durable events are the primary local forensic record.

OpenTelemetry is an optional export/instrumentation adapter, not the canonical event store.

Current OpenTelemetry JavaScript documentation reports traces and metrics as stable while logs are still development status. Therefore do not couple core logging correctness to OTel JS Logs.

---

# 3. Correlation IDs

All major work carries:

```text
project_id
request_id
correlation_id
job_id
shot_id
artifact_id (when applicable)
```

Provider calls also include:
```text
provider_request_id
provider_job_id
```

where available.

---

# 4. Durable Operational Event

Candidate:

```text
event_id
event_type
occurred_at
project_id
correlation_id
entity_type
entity_id
from_state?
to_state?
reason_code?
duration_ms?
attempt?
provider?
model?
cost_delta?
metadata_redacted_json
```

Events include:
- JOB_PREPARED
- PROVIDER_SUBMIT_STARTED
- PROVIDER_SUBMITTED
- PROVIDER_UNKNOWN_REMOTE_STATE
- PROVIDER_RECONCILED
- ARTIFACT_STAGED
- ARTIFACT_READY
- QA_STARTED
- QA_COMPLETED
- REPAIR_PLANNED
- STATE_ACCEPTED
- DEPENDENCY_INVALIDATED
- RECOVERY_ACTION
- MIGRATION_STARTED/COMPLETED/FAILED

---

# 5. Structured Logs

JSON lines or equivalent structured sink.

Levels:
```text
DEBUG
INFO
WARN
ERROR
FATAL
```

Production default avoids full creative content.

Fields:
```text
timestamp
level
component
event
correlation_id
project_id?
job_id?
shot_id?
provider?
error_code?
message
```

Redaction occurs before sink.

---

# 6. Metrics

Core counters/gauges/histograms:

## Execution

```text
jobs_queued
jobs_running
jobs_succeeded
jobs_failed
jobs_unknown_remote_state
job_duration_ms
provider_submit_latency_ms
provider_poll_duration_ms
download_duration_ms
retry_count
rate_limit_count
```

## Creative production

```text
static_first_pass_rate
video_first_pass_rate
identity_failure_rate
continuity_failure_rate
repair_success_rate
average_regenerations_per_accepted_shot
sequence_rework_rate
```

## Cost

```text
estimated_cost
actual_cost
cost_per_candidate
cost_per_accepted_shot
wasted_cost_stale_results
wasted_cost_failed_candidates
```

## Storage

```text
artifact_bytes
staging_bytes
orphan_count
missing_artifact_count
wal_size
db_size
backup_duration
```

---

# 7. Tracing

Candidate trace hierarchy:

```text
project production run
└── sequence
    └── shot
        ├── compile
        ├── provider submit
        ├── provider poll
        ├── artifact download
        ├── static/video QA
        └── repair
```

Do not create a span per video frame or other high-volume internal detail.

---

# 8. Privacy

Telemetry default:
- no screenplay text;
- no raw prompt;
- no image/video bytes;
- no credentials;
- no cookies/session headers.

Diagnostic content capture is separate explicit opt-in.

---

# 9. Local Health Dashboard

Minimum operations view:

```text
DB health
artifact store health
scheduler state
active jobs
queued jobs
unknown remote jobs
provider rate-limit state
last backup
schema version
recovery actions
disk remaining
```

---

# 10. OpenTelemetry Decision

Candidate:

```text
internal event/log/metric abstractions
↓ optional adapter
OpenTelemetry traces + metrics
```

Do not require OTel collector for normal desktop operation.

Official reference:
https://opentelemetry.io/docs/languages/js/
