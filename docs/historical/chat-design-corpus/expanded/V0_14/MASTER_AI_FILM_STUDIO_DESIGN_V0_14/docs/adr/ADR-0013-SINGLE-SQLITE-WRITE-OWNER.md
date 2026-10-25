# ADR-0013 — Single SQLite Write Owner in Production Utility

**Status:** PROPOSED / TARGET-EVIDENCE DRIVEN

## Context

Windows target Run 1 used 12 independent SQLite writer connections and committed only 2888 of 3000 attempted writes. The database remained intact, but 112 write attempts failed.

The application architecture does not require 12 SQLite writers merely because it permits multiple provider jobs.

## Decision

For V1 local-first desktop operation:

```text
Production Utility Process
→ one logical SQLite write owner
→ bounded write queue
→ short transactions
```

Provider/network workers submit state-update commands to this owner.

Read connections may be separate under repository policy.

## Rejected

```text
one SQLite writer connection per generation slot
```

as the production topology.

## Evidence limitation

Run 1 did not record error messages, so the exact exception mix is not asserted. Run 2 adds exact error classification.

## Revisit

Revisit PostgreSQL/multi-writer architecture only when multi-process/multi-machine team requirements justify it.
