# UPDATE_MIGRATION_BACKUP_MODEL.md
# Update / Migration / Backup Recovery Model — V0.4

**Status:** REVIEWED CANDIDATE

---

# 1. Update Principle

An application update must not destroy the ability to reconcile in-flight paid provider jobs.

Before update:

```text
STOP_ACCEPTING_NEW_JOBS
↓
persist all local scheduler state
↓
record submitted remote job identities
↓
flush/close critical local state
↓
backup if migration risk requires
↓
update
↓
schema compatibility/migration
↓
recovery reconciliation
↓
resume scheduler
```

---

# 2. Compatibility

Application declares:

```text
min_read_schema
max_read_schema
write_schema
```

If project DB is newer than supported:
- read/write blocked;
- do not attempt “best effort” write.

---

# 3. Migration Classes

## A — Additive
New tables/columns/indexes.
Typically low risk.

## B — Transformative
Backfill/convert semantic representation.

Requires:
- checkpoint;
- progress marker;
- resumable backfill;
- verification.

## C — Destructive
Drop/rewrite old representation.

Requires:
- verified backup;
- explicit migration;
- rollback/restoration plan.

---

# 4. Migration State

Persist:

```text
migration_id
from_version
to_version
phase
status
cursor/progress
started_at
updated_at
error
```

Never infer completion from app version alone.

---

# 5. Interrupted Migration

Startup:

```text
if migration status RUNNING/FAILED:
  do not start scheduler
  inspect migration class
  resume or restore according to migration contract
```

No generation writes occur until data compatibility is restored.

---

# 6. Backup Manifest

```text
backup_id
project_id
schema_version
project_revision
created_at
db_snapshot_hash
artifact_hashes[]
application_version
manifest_hash
verification_status
```

Backup success requires:
- readable DB snapshot;
- valid schema;
- referenced artifact hashes present/verified per policy.

---

# 7. Retention

Candidate tiers:

```text
working candidates
rejected candidates
approved masters
canonical refs
proxies/cache
backups
```

Default deletion priority:
```text
cache/proxies
→ old rejected candidates
→ superseded temporary candidates
```

Never automatically delete:
```text
approved master
active canonical reference
artifact required by locked lineage
```

without explicit retention policy.

---

# 8. Restore

Always restore to a staging location first:

```text
verify manifest
↓
restore DB
↓
restore/verify artifacts
↓
run schema migration if needed
↓
integrity + lineage audit
↓
promote as restored project
```

---

# 9. Update Security

Update packages must come from trusted distribution channel.

Required later:
- platform signing/notarization strategy;
- update package signature/integrity validation;
- no arbitrary URL binary execution.

---

# 10. Design Spike

Simulate:
- crash mid-additive migration;
- crash mid-backfill;
- corrupt backup artifact;
- newer-schema open with older app;
- remote submitted jobs across app version change.

Architecture does not reach L6 until these recovery behaviors are proven by design spike/tests.
