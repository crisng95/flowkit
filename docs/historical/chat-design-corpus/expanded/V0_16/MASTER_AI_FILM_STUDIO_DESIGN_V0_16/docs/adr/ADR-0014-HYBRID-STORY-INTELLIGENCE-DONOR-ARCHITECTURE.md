# ADR-0014 — Hybrid Story Intelligence Donor Architecture

**Status:** ACCEPTED FOR FINAL CONSOLIDATION  
**Date:** 2026-09-21

## Context

FlowKit is strong in generation execution/reference/orchestration but insufficient as the canonical intelligence layer for premise, angle, research, psychology, causality, emotion, dialogue, payoff, critique and story repair.

No audited repository covers all Story Intelligence responsibilities with suitable license, architecture and quality evidence.

## Decision

Build a Studio-owned canonical Story Intelligence System and use repositories only as donors through explicit boundaries.

```text
KEEP: FlowKit Gold Core
ADAPT/EXTRACT: licensed research/critique algorithms/assets
PATTERN-ONLY: GPL or no-license donors
BRAIN-PACK: licensed methodology/rubric assets
OPTIONAL ADAPTER: heavyweight memory/research services when justified
```

Primary donor composition:
- Research: GPT Researcher + STORM + Evidence Graph patterns.
- Causality/intentionality: Sabre pattern, independently implemented.
- Hierarchical screenplay decomposition: Dramatron pattern.
- Rolling beat/tension/selective repair: StoryDaemon pattern, independently implemented.
- Pacing/tension analytics: Beatlume pattern, independently implemented.
- Character/social evaluation: SOTOPIA pattern.
- Critique/callback/completion: Open-Write licensed assets/patterns.
- Craft specialization: versioned Brain Packs derived/adapted from licensed methodology repos.

## Canonical authority

Third-party repositories may never own:
- locked story facts;
- canonical Character/Knowledge/Relationship state;
- Scene/Beat identity;
- Story Quality verdict authority;
- Script Lock.

## Consequences

Positive:
- avoids coding every idea from zero;
- avoids framework zoo and competing state stores;
- avoids license contamination;
- keeps model/provider independence.

Cost:
- requires adapter/port work;
- some strong unlicensed patterns must be independently reimplemented;
- creative benchmark remains implementation acceptance work.
