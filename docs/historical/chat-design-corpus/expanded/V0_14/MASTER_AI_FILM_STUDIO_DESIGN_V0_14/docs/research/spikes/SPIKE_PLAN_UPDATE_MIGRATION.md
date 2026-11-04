# SPIKE_PLAN_UPDATE_MIGRATION.md
# Design Spike Plan — Update / Migration Recovery

**Status:** REQUIRED BEFORE L6

## Scenarios

1. additive migration interrupted;
2. resumable backfill interrupted at 50%;
3. destructive migration interrupted after backup;
4. newer schema opened by older app;
5. app update while remote jobs are SUBMITTED/POLLING;
6. artifact manifest mismatch during restore.

## Acceptance

- scheduler never starts on incompatible/incomplete schema;
- migration state detects exact incomplete phase;
- recovery is deterministic;
- pre-destructive backup verified;
- remote job identities survive app version change;
- restore occurs in staging, not over active project.
