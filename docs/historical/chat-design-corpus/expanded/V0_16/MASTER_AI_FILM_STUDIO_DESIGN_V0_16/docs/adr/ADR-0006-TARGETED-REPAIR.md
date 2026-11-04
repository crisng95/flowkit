# ADR-0006 — Targeted Repair

**Status:** PROPOSED

## Decision

Creative failures are repaired at the earliest responsible semantic layer.

Repair modes:
- PATCH_IN_PLACE;
- REGENERATE_FROM_ANCHOR;
- REPLAN_SHOT;
- ESCALATE_UPSTREAM.

A RepairPlan explicitly records preserve/patch/invalidate/recheck scopes.

## Consequences

Requires lineage and QA dimensions to be precise; prevents unnecessary rewriting/regeneration.
