# ADR-0015 — Separate Design Freeze from Implementation/Live Evidence

**Status:** ACCEPTED PROCESS CORRECTION  
**Date:** 2026-09-21

## Context

Earlier design-gate language incorrectly implied that every target/live provider/QA benchmark must pass before production coding can begin. Several such proofs require the subsystem to exist first.

The Windows persistence spike was appropriate pre-code because it tested a high-risk architecture decision and changed the design from direct multiwriter SQLite to a single logical write owner. But running every future live acceptance benchmark before implementation would invert the development lifecycle.

## Decision

Pre-code freeze requires:
- coherent canonical architecture;
- resolved authority boundaries;
- contracts/data/state model;
- license/dependency decisions;
- high-risk design spikes where evidence can materially change architecture;
- traceability and independent review;
- implementation dependency/task plan.

It does **not** require every implementation/live acceptance gate.

Post-implementation acceptance owns:
- packaged Electron safeStorage proof;
- live provider ambiguity/fault injection for implemented adapters;
- calibrated real-image Story/Static QA benchmarks;
- real generation targeted-repair benchmark;
- representative performance/cost benchmark;
- live account quota/cost observation.

## Consequence

The project may enter implementation after `IMPLEMENTATION_BASELINE_FROZEN` even if production-hardening gates remain open. Those gates become acceptance criteria for corresponding implementation milestones and release readiness.
