# WINDOWS_PERSISTENCE_RUN1_ANALYSIS_V0_14.md
# Windows Persistence / Recovery — Target Run 1 Analysis

**Evidence:** `docs/research/evidence/windows/EVIDENCE_WINDOWS_PERSISTENCE_20260921_RUN1.json`  
**Platform:** `win32`  
**Python:** `3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]`  
**Gate result:** FAIL / PARTIAL EVIDENCE

---

# 1. What passed

The target Windows run provides real target-runtime evidence for:

```text
WAL database integrity              PASS
abrupt exit: committed survives     PASS
abrupt exit: uncommitted absent     PASS
migration interruption detected     PASS
migration resumed to 1000/1000      PASS
backup/restore logical integrity    PASS
newer-schema write gate             PASS
```

---

# 2. What failed

The direct 12-writer stress lane produced:

```text
expected writes = 3000
committed       = 2888
failed attempts = 112
failure rate    = 3.733%
errors          = 112
integrity       = ok
max latency     = 5539.680 ms
```

Therefore the Windows persistence gate cannot close from Run 1.

---

# 3. Important distinction

Run 1 used:

```text
12 independent Python threads
→ 12 independent SQLite connections
→ each thread executes BEGIN IMMEDIATE
→ no application retry/backoff after an exception
```

This is **not** the intended V1 production write topology.

The architecture already places persistence inside one Production Utility Process. SQLite permits concurrent readers but serializes writes. Therefore:

```text
12 generation slots
≠
12 simultaneous SQLite write owners
```

The intended topology should be:

```text
generation/provider workers
        ↓ durable update commands
single DB write owner / write queue
        ↓
one short SQLite writer connection
```

Separate read connections may be used where needed.

---

# 4. What can and cannot be concluded from Run 1

## Proven

- direct 12-connection write contention on this Windows target is not acceptable under the Run-1 harness policy;
- the database remained structurally healthy (`integrity_check=ok`);
- crash, migration, backup and schema-gate behaviors passed their tested scenarios.

## Not proven

The Run-1 JSON stores only:

```text
"errors": 112
```

It does **not** store exception types/messages.

Therefore we must not state as fact that all 112 errors were `database is locked`.

The ~5.540s maximum latency is consistent with the harness's 5-second busy timeout being involved, but this is a **diagnostic hypothesis**, not final root-cause evidence.

---

# 5. Design correction

The target evidence does not justify abandoning SQLite.

It justifies making the V1 DB ownership rule explicit:

```text
ONE PRODUCTION UTILITY PROCESS
ONE LOGICAL WRITE OWNER
ONE BOUNDED WRITE QUEUE
SHORT TRANSACTIONS
NO PROVIDER NETWORK CALL INSIDE TRANSACTION
READ CONNECTIONS SEPARATE IF NEEDED
```

Provider/job concurrency remains independent from SQLite writer concurrency.

---

# 6. Harness correction

Run 2 must separate two lanes.

## Lane A — adversarial direct multi-writer characterization

Purpose:
- reproduce/measure contention;
- record exact exception class/message;
- never use it as the production acceptance lane.

## Lane B — intended single-writer queue

Purpose:
- 12 producer threads submit 3000 update commands;
- one DB writer connection commits short transactions;
- acceptance requires:

```text
3000 / 3000 committed
writer errors = 0
integrity_check = ok
```

The existing crash/migration/backup/schema tests remain mandatory.

---

# 7. Gate decision

```text
RUN 1 target evidence = INGESTED
PERSISTENCE WINDOWS GATE = OPEN
SQLite candidate = RETAINED
direct multi-writer production topology = REJECTED
single-writer queue topology = REQUIRED CANDIDATE
```

Run 2 is required before this gate can close.
