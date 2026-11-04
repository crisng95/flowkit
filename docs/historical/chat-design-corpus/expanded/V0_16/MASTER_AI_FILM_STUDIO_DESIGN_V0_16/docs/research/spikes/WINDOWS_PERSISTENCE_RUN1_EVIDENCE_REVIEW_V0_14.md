# WINDOWS_PERSISTENCE_RUN1_EVIDENCE_REVIEW_V0_14.md

**Evidence class:** TARGET_RUNTIME  
**Platform:** `win32`  
**Overall gate evidence status:** FAIL  

## Verified target results

```text
WAL mode                = wal
expected writes         = 3000
committed writes        = 2888
failed attempts         = 112
reported errors         = 112
DB integrity            = ok

abrupt committed survives = True
abrupt uncommitted absent  = True
migration resumed rows     = 1000
backup restored rows       = 100
newer schema write allowed = False
```

## Decision

Run 1 is real Windows target evidence and is retained even though it failed the concurrency acceptance lane.

It supports these subclaims:
- WAL database remained structurally intact;
- committed/uncommitted abrupt-exit behavior passed;
- interrupted migration resumed to completion;
- backup/restore passed logical integrity;
- newer unsupported schema was blocked from write.

It disproves this Run-1 acceptance assumption:

```text
12 independent SQLite writer connections
+ no application retry/serialization
= safe production write topology
```

## Limitation

The Run-1 JSON records only `errors=112` and not exception messages. Therefore the exact exception mix cannot be asserted from this evidence alone.

## Patch

V0.14 makes one logical SQLite write owner + bounded queue the production candidate and introduces a V2 harness that separately measures:
1. adversarial direct multi-writer contention with exact error messages;
2. intended single-writer-queue production lane.
