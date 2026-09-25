# PERSISTENCE_WRITE_OWNERSHIP_V0_14.md
# Persistence Write Ownership — Windows Evidence Patch

**Status:** TARGET-RUNTIME EVIDENCE PASS  
**Trigger:** Windows Persistence Target Run 1

---

# 1. Rule

V1 SQLite is owned by the Production Utility Process.

Within that process:

```text
all mutating DB commands
→ bounded write queue
→ one logical write owner
→ one writer connection
```

Do not allow each provider-generation slot to become an independent SQLite writer.

---

# 2. Why

Remote provider concurrency and DB mutation concurrency are different dimensions.

A project may have:

```text
12 remote jobs in flight
```

while DB updates remain:

```text
small
serialized
fast
durable
```

This is appropriate because provider calls last seconds/minutes while metadata commits should last milliseconds.

---

# 3. Read access

Read-only/query connections may be separate if needed.

Rules:
- no long-lived read transaction that blocks checkpoint/maintenance policy;
- UI never owns the DB file directly;
- Renderer never opens SQLite;
- all canonical repository access remains in Production Utility.

---

# 4. Write command contract

Example logical command:

```text
UpdateJobProviderState
RecordArtifactReady
AcceptStateSnapshot
AppendOperationalEvent
CommitMigrationProgress
```

Every command:
- has correlation/request identity;
- executes a bounded local transaction;
- returns success/conflict/failure;
- never performs provider HTTP work inside the transaction.

---

# 5. Backpressure

The DB write queue is bounded.

If local writers outpace persistence:

```text
queue pressure
→ orchestrator slows local state mutation/admission
```

Do not create unbounded memory backlog.

---

# 6. Retry policy

The primary correctness mechanism is **write ownership serialization**, not endless SQLite retry.

A bounded busy retry may still exist for exceptional internal contention/maintenance, but:
- it is observable;
- it is bounded;
- exhausting it is a storage failure;
- it never silently drops a state transition.

---

# 7. Acceptance

Target Windows Run 2 must show, for the intended topology:

```text
12 producers
3000 write commands
1 writer owner
3000 committed
0 dropped commands
0 writer errors
integrity_check = ok
```

Adversarial direct-multiwriter errors do not fail the intended topology lane; they are characterization evidence.


# V0.15 Target Result

Windows Run 2:
```text
12 producers
3000 commands
1 SQLite write owner
3000 committed
0 writer errors
0 producer errors
integrity_check = ok
```

The adversarial 12-writer lane separately reproduced 126 `OperationalError: database is locked` failures, confirming why direct multiwriter ownership is rejected.
