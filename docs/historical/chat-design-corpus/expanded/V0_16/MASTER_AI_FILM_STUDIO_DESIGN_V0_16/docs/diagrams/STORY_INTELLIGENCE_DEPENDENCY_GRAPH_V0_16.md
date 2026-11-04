# STORY_INTELLIGENCE_DEPENDENCY_GRAPH_V0_16.md
# Story Intelligence — Design Dependency Graph

This is a **subsystem dependency graph**, not yet the implementation task queue.

```text
S0 Contract Foundation
│
├─ IDs / versions / statuses / provenance
├─ validation/error vocabulary
├─ Story/Sequence/Scene/Beat identity
└─ repository interfaces
        ↓
S1 Brain Pack Registry + Resolver
        ↓
S2 Research Evidence Contracts ────────────────┐
│                                              │
├─ ResearchBrief                               │
├─ EvidenceClaim/Edge                          │
└─ StoryMaterial                               │
        ↓                                      │
S3 Premise / Angle / Theme                     │
        ↓                                      │
S4 Character / Knowledge / Relationship ←─────┘
        ↓
S5 Conflict / Stakes
        ↓
S6 StoryGraph / Structure
        ↓
S7 Emotional Arc + Rhythm
        ↓
S8 Scene Contract
        ↓
S9 Beat Contract
        ↓
S10 DialogueIntent / Drafting
        ↓
S11 Setup/Payoff + Audience/Timeline checks
        ↓
S12 Critique Council
        ↓
S13 Story Quality Gate
        ↓
S14 Targeted Story Repair ───────↺ S3..S11 by root cause
        ↓
S15 Script Lock
        ↓
EXISTING DOWNSTREAM
Directing → Cinematography → ShotSpec → ShotIR → Generation
```

## Parallelizable design/implementation lanes after foundation

After S0:

```text
Lane A: Brain Registry
Lane B: Research Evidence
Lane C: Character base contracts
Lane D: deterministic pacing/quality utilities
```

But Scene/Beat/Draft must wait for Character + Structure foundations.

## Critical-path rule

Do not start LLM prompt polishing first. Build canonical contracts/state/repositories/validators before model-specific generation prompts.

## Donor integration order

```text
1 import/adapt Brain Pack assets
2 implement research adapter interfaces
3 port deterministic evidence/pacing utilities
4 implement canonical story planning services
5 add semantic LLM generators behind interfaces
6 add critics/repair
7 benchmark models/policies
```
