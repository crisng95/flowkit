# ADR-0011 — Evidence-Class Gate Closure

**Status:** PROPOSED / LOCAL-EVIDENCE SUPPORTED

## Decision

Architecture maturity gates consume evidence through a SHA-256 ledger.

Each gate declares the minimum acceptable evidence class. A harness or local simulation cannot close a target/live gate.

## Why

The project repeatedly distinguishes:
- plausible architecture;
- local simulation;
- runnable harness;
- real target/live proof.

Without a formal evidence layer, comprehensive documentation can accidentally be treated as proof.

## Consequences

Positive:
- exact claims and limitations are attached to evidence;
- changed evidence files invalidate their ledger hash;
- failures remain auditable;
- future L6/L7 decisions can cite evidence IDs rather than prose impressions.

Cost:
- evidence ingestion/review adds process overhead.

## Authority

`EVIDENCE_CLASSIFICATION_POLICY_V0_13.md`
`EVIDENCE_LEDGER_V0_13.json`
`L6_GATE_RULES_V0_13.json`
