# L6_EVIDENCE_GATE_BOARD_V0_14.md

**Current maturity:** L5.5 — Reviewed + Partial Hardening Evidence  
**Update:** first real Windows persistence run ingested.

## Persistence Windows

```text
required class = TARGET_RUNTIME
present target evidence = FAIL
gate closed = False
evidence IDs = EV-PERSIST-LOCAL-001, EV-PERSIST-WIN-RUN1-001
```

Subtests from Run 1:
- crash durability: PASS
- migration resume: PASS
- backup/restore: PASS
- newer-schema write block: PASS
- direct 12-writer acceptance lane: FAIL (2888/3000, 112 errors)

V0.14 production candidate uses a single logical SQLite write owner and requires Windows V2 rerun.

All other live/target gates remain as defined in V0.13.
