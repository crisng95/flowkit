# PERSISTENCE_ARCHITECTURE.md
# Persistence Architecture — Deep Dive V0.2

**Status:** CANDIDATE  
**Historical maturity contribution:** originated during L4→L5 hardening; current package maturity is L5.5  
**Feature coding:** NOT STARTED  
**Decision:** SQLite WAL is the preferred V1 operational store, pending design re-review and a small durability/concurrency spike.

---

# 1. Problem

The studio needs a durable operational state store for:

- story/version metadata;
- narrative hierarchy;
- entities/reference metadata;
- state snapshots;
- shot specs / shot IR versions;
- provider request/job state;
- dependency graph;
- QA results;
- repair plans;
- lineage;
- timeline/export metadata.

The database must survive:

- application crashes;
- machine restarts;
- remote provider ambiguity;
- concurrent background jobs;
- user edits while jobs are running;
- schema upgrades;
- artifact-store partial failures.

Large media files are not the database's responsibility.

---

# 2. Workload Assumptions

**ASSUMPTION DB-A01** — local-first modular monolith on one machine for V1.

**ASSUMPTION DB-A02** — up to 12 independent remote generation slots may execute concurrently, but DB writes are short metadata transitions, not heavy analytical writes.

**ASSUMPTION DB-A03** — one local orchestrator process is authoritative for write scheduling in V1, while UI/background readers may use separate connections.

**ASSUMPTION DB-A04** — project size target is initially hundreds of shots, potentially thousands of metadata rows per project, not billions.

**ASSUMPTION DB-A05** — generated images/video are immutable files in an artifact store; DB stores paths/content hashes/metadata only.

These assumptions must be revisited if multi-machine collaboration becomes a V1 requirement.

---

# 3. Technology Options

## OPTION A — SQLite + WAL

### Strengths

- embedded, zero external server;
- very strong fit for desktop/local-first packaging;
- transactional and mature;
- WAL allows readers and a writer to operate concurrently;
- simple backup/restore story;
- easy test isolation;
- small operational footprint.

SQLite's own WAL documentation states that WAL improves concurrency because readers do not block writers and a writer does not block readers, while also noting WAL is for processes on the same host rather than a network filesystem.

### Constraints

- one write transaction at a time;
- WAL database must stay on same host/local filesystem;
- long write transactions can create contention;
- app must deliberately handle `SQLITE_BUSY`;
- remote multi-machine/team access is not a natural direct extension.

### Fit

**Excellent for V1 local-first studio.**

---

## OPTION B — PostgreSQL

### Strengths

- MVCC designed for many concurrent sessions;
- row/table/advisory locking;
- mature isolation and multi-user semantics;
- better direct fit for cloud/team/multi-machine deployment.

### Costs

- external server/process lifecycle;
- credentials/network/auth;
- backup/upgrade/deployment burden;
- desktop packaging complexity;
- larger support surface.

### Fit

**Excellent future server/team backend, but likely premature as mandatory V1 dependency.**

---

## OPTION C — DuckDB as primary operational store

### Strengths

- embedded;
- strong analytical performance;
- ACID transactions;
- convenient for future analytics.

### Problems for this workload

DuckDB's official concurrency documentation says its primary design is analytical/bulk work, not many small operational transactions, and historically multi-process writing was not the primary design goal.

### Fit

**Reject as primary orchestration DB.**
Potential future role:

```text
SQLite operational data
→ exported analytical snapshots
→ DuckDB analytics/reporting
```

---

# 4. Candidate Decision

Use:

```text
SQLite
+ WAL
+ foreign_keys=ON
+ short explicit transactions
+ application-level optimistic concurrency
+ durable job state machine
+ immutable/versioned creative records
+ content-addressed artifact files
```

For V1, prefer durability over micro-optimizing DB commits because remote generation latency dominates overall production time.

Candidate durability policy:

```text
journal_mode = WAL
synchronous = FULL
foreign_keys = ON
busy_timeout = configured
```

SQLite documents that `synchronous=FULL` in WAL mode provides ACID durability across power loss; `NORMAL` is faster but can lose the most recent committed transactions after power loss. For production job metadata where duplicate paid work matters, `FULL` is the safer default candidate.

A performance spike may compare FULL vs NORMAL, but NORMAL must not become the default merely because it benchmarks faster.

---

# 5. Database Ownership

The DB is authoritative for **semantic and operational metadata**.

The file artifact store is authoritative for **artifact bytes**.

Neither side alone is sufficient.

```text
DATABASE
├── artifact_id
├── relative_path
├── sha256
├── byte_size
├── mime
├── status
└── lineage

ARTIFACT STORE
└── immutable bytes
```

No image/video BLOBs in the core DB by default.

---

# 6. Connection / Write Model

V1 candidate:

```text
UI/read models
     │
     ├── read connection(s)
     │
Orchestrator
     │
     └── write transactions
```

Rules:

1. transactions must be short;
2. never hold a DB transaction open across a provider network call;
3. never hold a DB transaction open while downloading large media;
4. write transitions are explicit;
5. retry `SQLITE_BUSY` only under bounded DB-specific retry policy;
6. business idempotency is handled by job/request keys, not by hoping the DB lock prevents duplicates.

For write claims where contention matters, use `BEGIN IMMEDIATE` or equivalent transaction behavior deliberately rather than read-then-upgrade patterns that may race.

---

# 7. Versioning Model

Mutable canonical objects carry:

```text
id
revision
created_at
updated_at
active_version_id (where applicable)
```

Accepted creative versions are preferably immutable records.

Example:

```text
shot
  id=S001
  active_shot_spec_version=SSV-12

shot_spec_versions
  SSV-10
  SSV-11
  SSV-12
```

Do not silently mutate an approved `ShotSpecVersion`.

---

# 8. Optimistic Concurrency

For mutable coordination records:

```sql
UPDATE shots
SET active_shot_spec_version = ?, revision = revision + 1
WHERE id = ? AND revision = ?;
```

If affected row count = 0:

```text
CONCURRENCY_CONFLICT
```

Do not overwrite a newer user decision.

Use this especially for:

- shot active version pointers;
- production stage state;
- manual approvals;
- job ownership/lease;
- provider selection overrides.

---

# 9. Input Fingerprint / Stale Result Protection

Every generation request stores immutable input identity:

```text
story_version
shot_spec_version
shot_ir_version
state_snapshot_version
reference_versions[]
compiler_version
provider_profile_version
model
generation_mode
```

Canonicalized and hashed:

```text
input_fingerprint = SHA-256(canonical input manifest)
```

When provider output arrives:

```text
job.expected_input_fingerprint
vs
current active input fingerprint
```

If different:

```text
ARTIFACT = STALE_RESULT
```

The artifact may be retained for inspection, but it cannot silently become the active accepted output.

---

# 10. Remote Provider Submission Protocol

A network call cannot be made transactionally with SQLite. Therefore use an application protocol.

## Step A — PREPARE

DB transaction:

```text
create GenerationRequest
create GenerationJob
set immutable input fingerprint
create idempotency key
status = PREPARED
COMMIT
```

## Step B — SUBMIT

No DB transaction held.

Send request to provider.

## Step C1 — provider returns remote job ID

DB transaction:

```text
provider_job_id = ...
status = SUBMITTED
submitted_at = ...
COMMIT
```

## Step C2 — timeout/connection break after request may have been accepted

Do **not** blind retry.

Set:

```text
status = UNKNOWN_REMOTE_STATE
```

Then run provider-specific reconciliation:

```text
provider idempotency lookup
provider request-id lookup
job history lookup
poll known remote ID if any
```

Only resubmit when adapter policy proves duplicate generation will not occur or requires explicit user/repair decision.

---

# 11. Job Claim / Worker Lease

Design for future multiple local worker loops even if V1 uses one process.

Job fields:

```text
worker_id
lease_until
heartbeat_at
attempt
```

Claim operation is atomic:

```text
QUEUED
→ CLAIMED
```

Expired lease:

```text
CLAIMED/RUNNING + lease expired
→ RECOVERY_REQUIRED
```

Do not automatically resubmit remote work; first inspect `provider_job_id` / remote state.

---

# 12. Artifact Commit Protocol

Do not write final file path first and metadata later without recovery markers.

Candidate:

```text
1. allocate artifact_id
2. download to staging path:
   .staging/<artifact_id>.partial

3. stream checksum + byte count
4. close file
5. durability flush according to platform policy
6. move/rename into immutable final path on same volume
7. DB transaction:
      insert/update artifact metadata
      status = READY
      checksum
      final relative path
      lineage
8. startup reconciler checks:
      stale staging files
      final files missing DB rows
      DB READY rows missing files
```

Where atomic file replacement semantics differ by OS/filesystem, the implementation must use platform-tested primitives and reconciliation rather than assume POSIX behavior.

---

# 13. Artifact Addressing

Preferred:

```text
projects/<project-id>/artifacts/<sha256-prefix>/<sha256>.<ext>
```

or an equivalent immutable content-addressed scheme.

Benefits:

- duplicate detection;
- integrity verification;
- safe backup manifests;
- artifact immutability;
- easier orphan reconciliation.

User-facing names remain metadata, not physical identity.

---

# 14. Foreign Keys / Constraints

Candidate core invariants:

- foreign keys enabled;
- every shot references existing beat;
- every beat references existing scene;
- every scene references existing sequence/project;
- job references existing compiled request and shot;
- artifact lineage references generation attempt/job;
- active version pointer must belong to same logical object;
- dependency graph must reject self-edge;
- dependency graph cycle check performed at application/validation layer;
- approved state snapshot cannot reference non-approved source artifact.

---

# 15. Schema Migration

Maintain:

```text
schema_migrations
  version
  applied_at
  checksum
  app_version
```

Rules:

1. migrations are monotonic;
2. destructive migration requires pre-migration backup;
3. migration step should be transactional where SQLite operation permits;
4. application refuses to open newer unsupported schema in write mode;
5. downgrade is not assumed safe;
6. schema migration and data backfill are distinguishable;
7. long backfills are resumable and versioned.

---

# 16. Backup Strategy

SQLite provides an Online Backup API for live snapshots and also `VACUUM INTO`.

Project backup must include both DB snapshot and immutable referenced artifacts.

Candidate:

```text
1. create BackupManifest record
2. capture project logical revision/cutoff
3. list referenced immutable artifact hashes
4. produce consistent DB snapshot
5. copy/hash only manifest artifacts
6. write backup manifest
7. verify
```

Because artifact bytes are immutable/content-addressed, they can be copied after the DB snapshot without changing meaning.

---

# 17. Restore Strategy

```text
1. validate backup manifest
2. validate DB file
3. validate artifact hashes
4. restore into new staging project location
5. run compatible schema migration if required
6. run consistency audit
7. atomically promote restored project
```

Never restore directly over a live active project without staged validation.

---

# 18. Checkpoint Strategy

Do not manually checkpoint after every transaction.

Candidate:

- let WAL auto-checkpoint handle normal operation;
- observe WAL growth;
- run controlled checkpoint on idle/shutdown/backup boundaries when appropriate;
- avoid aggressive blocking checkpoints during active generation-state bursts.

Exact thresholds are benchmark items, not frozen constants.

---

# 19. Network Filesystem Rule

SQLite WAL is same-host/local-filesystem architecture.

Do not place active WAL DB on:

```text
SMB share
NAS path
cloud-synced network mount
multi-host shared filesystem
```

as a supported production configuration.

If multi-machine shared writes become a requirement, revisit PostgreSQL/server storage rather than stretching SQLite beyond its design.

---

# 20. Why Not PostgreSQL Now?

PostgreSQL has superior direct multi-user concurrency and MVCC semantics.

It becomes the preferred reconsideration when any of these become MUST requirements:

```text
multi-machine writers
team collaboration
remote web clients
shared centralized projects
high write concurrency
server-side scheduling
organization-wide RBAC
```

Until then, making every local creator run/maintain PostgreSQL adds operational complexity with little benefit to remote-generation-heavy workloads.

---

# 21. Why Not DuckDB as Operational DB?

DuckDB is excellent for analytics but is not the natural fit for:

```text
many small state-machine writes
job claiming
status transitions
desktop multi-connection orchestration
```

Potential future:

```text
SQLite operational store
→ export metrics/events
→ DuckDB analytics
```

---

# 22. Candidate Persistence Decision

```text
V1:
SQLite WAL
+ FULL synchronous
+ short transactions
+ optimistic revision control
+ durable job state
+ input fingerprints
+ artifact files outside DB
+ startup reconciliation
+ online backups
```

**Status:** PROPOSED, not frozen.

---

# 23. Required Design Spikes Before Freeze

### SPIKE-DB-001 — Concurrent state updates
Simulate:
- UI editing ShotSpec;
- 12 worker status updates;
- QA writes;
- checkpoint activity.

Measure:
- busy rate;
- write latency;
- conflict handling.

### SPIKE-DB-002 — Crash after provider submit
Inject crash at:
- before submit;
- immediately after provider receives;
- before local `SUBMITTED` commit.

Prove no blind duplicate resubmit.

### SPIKE-DB-003 — Artifact crash consistency
Inject crash at every artifact write stage and prove reconciler categorizes all outcomes.

### SPIKE-DB-004 — Power/durability policy benchmark
Compare `WAL + FULL` and `WAL + NORMAL` for metadata workload. Performance alone cannot override durability requirement.

---

# 24. Sources

Official SQLite:
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/pragma.html
- https://www.sqlite.org/lang_transaction.html
- https://www.sqlite.org/backup.html

Official PostgreSQL:
- https://www.postgresql.org/docs/current/mvcc.html

Official DuckDB:
- https://duckdb.org/docs/current/connect/concurrency


# V0.14 Windows Target Evidence Patch

Windows target Run 1 committed 2888/3000 writes under 12 independent writer connections while database integrity remained OK.

Production V1 therefore adopts:

```text
Production Utility Process
→ one logical SQLite write owner
→ bounded write queue
→ one writer connection
→ short transactions
```

Provider concurrency does not imply DB-writer concurrency. Read/query connections may remain separate under repository policy.

The direct multi-writer pattern is retained only as adversarial characterization in the V2 design spike.

Canonical patch: `PERSISTENCE_WRITE_OWNERSHIP_V0_14.md`.
