# ADR-0003 — Contract Format

**Status:** PROPOSED

## Decision

If V1 implementation is TypeScript:
- author runtime contracts in Zod 4;
- export JSON Schema Draft 2020-12 for interoperability/documentation;
- prohibit non-JSON-serializable/unrepresentable constructs on public/persisted boundaries.

## Why

TypeScript types alone do not validate runtime data. JSON Schema alone is language-neutral but adds authoring/tooling friction. Zod 4 provides runtime validation and first-party JSON Schema conversion.

## Risk

Schema source becomes tied to Zod/TypeScript.

## Mitigation

Version and ship exported Draft 2020-12 schemas; keep domain semantics independent from library implementation.
