# STORY_QUALITY_CRITIQUE_REPAIR_V0_16.md
# Story Quality, Independent Critique & Targeted Repair V0.16

**Status:** REVIEWED CANDIDATE.  
**Principle:** beautiful prose cannot average away a broken story.

---

# 1. Quality dimensions

The baseline dimensions are:

1. premise strength;
2. angle specificity/distinctiveness;
3. theme coherence/non-didactic integration;
4. research quality/provenance when applicable;
5. active Brain fit;
6. character depth/motivation/knowledge consistency;
7. conflict/stakes/escalation;
8. causality/structure;
9. emotional arc;
10. emotional rhythm;
11. scene/beat state movement;
12. dialogue/subtext/voice;
13. pacing/tension;
14. setup/payoff;
15. continuity/timeline/audience knowledge;
16. overall audience experience/format fit.

---

# 2. Do not use a naive arithmetic average

Bad policy:

```text
premise 9
prose 9
dialogue 9
causality 2
payoff 2
average looks acceptable
→ false PASS
```

Candidate policy:

```text
A. HARD GATES
B. BOTTLENECK DETECTION
C. GEOMETRIC / BALANCED ADVISORY SCORE
D. SPECIALIST CRITIQUE EVIDENCE
```

The numeric score is a prioritization aid, not an objective artistic truth.

---

# 3. Hard gates

Blocking candidates include:

- foundational premise has no consequential pressure;
- character action violates locked motivation/knowledge without explanation;
- major causal discontinuity;
- major factual claim in factual mode is unsupported yet asserted as fact;
- scene required for progression has no state change and no deliberate exception;
- major payoff is impossible/unearned due missing setup;
- critical setup disappears unintentionally;
- timeline/knowledge contradiction breaks plot logic;
- climax depends on newly invented capability/rule;
- locked theme/character arc outcome contradicts preceding story without intentional reversal/ambiguity.

Blocking severity is evidence-sensitive. The system must not promote every subjective disagreement to BLOCKING.

---

# 4. Independent Critique Council

## 4.1 Role isolation

Each critic receives only the minimum relevant context.

Examples:

### Causality critic
Gets:
- story graph;
- scene/beat summaries;
- character objectives/beliefs;
- locked facts.

Does not need provider or camera data.

### Dialogue critic
Gets:
- scene/beat contracts;
- character voice registers;
- relationship/knowledge states;
- screenplay dialogue.

### Cold Audience critic
May intentionally **not** receive the full Bible, to detect information that only makes sense to the author.

### Continuity critic
Gets canonical state/timeline/knowledge, but should be blinded from writer explanations that could rationalize an actual error.

## 4.2 Critic output law

A critic finding should be located:

```text
where
what
why
severity
root-layer hypothesis
evidence
what must be preserved
```

`PASS` without checks/evidence is weak and may be flagged as a hollow review by the Meta-Critic.

---

# 5. Critic types

## Premise / Angle Critic
Checks:
- topic masquerading as premise;
- generic angle;
- low specificity;
- no tension/contradiction;
- mismatch with intended format/audience.

## Research / Fact Critic
Checks:
- unsupported claims;
- contradiction not represented;
- source monoculture;
- stale evidence;
- invented specificity;
- facts that never become story-relevant material.

## Character / Motivation Critic
Checks:
- action without intelligible reason;
- behavior written solely to serve plot;
- missing knowledge precondition;
- flat or contradictory psychology;
- identical voice/tactic across characters.

## Conflict / Stakes Critic
Checks:
- easy objectives;
- repetitive obstacle;
- arbitrary escalation;
- stakes stated but not dramatized;
- fake urgency.

## Structure / Causality Critic
Checks:
- coincidence chains;
- missing bridge;
- consequence not carried forward;
- reversible turning points;
- reveal without setup;
- act/sequence function gaps.

## Emotion / Rhythm Critic
Checks:
- monotone emotional register;
- unearned emotional peak;
- no recovery/breathing room;
- repeated scene emotional function;
- emotional turn not caused by story event.

## Scene / Beat Critic
Checks:
- static scenes;
- exposition without pressure/change;
- repeated tactic;
- no turn;
- beat sequence that does not accumulate.

## Dialogue / Subtext Critic
Checks:
- on-the-nose exposition;
- all characters share one voice;
- line violates knowledge state;
- declared emotion instead of behavior where subtext expected;
- conversation not connected to beat objective/change.

## Setup / Payoff Critic
Checks:
- missing plant;
- forgotten setup;
- payoff too obvious/too late/too early;
- payoff has no consequence;
- accidental unresolved promise.

## Continuity / Knowledge Critic
Checks:
- what character can know;
- location/time contradictions;
- relationship state drift;
- object/rule/fact mismatch;
- audience knowledge inconsistencies.

## Audience / Retention Critic
Enabled by format Brain Pack. Checks:
- unanswered question density;
- information-order clarity;
- dead zones;
- hook/payoff timing;
- repetitive withholding;
- manipulative cliffhangers that damage story credibility.

## Theme Critic
Checks whether theme is embodied in choices/consequences rather than speeches.

## Devil's Advocate / Skeptic
Attempts to disprove high-confidence positive conclusions and searches for alternate interpretations.

## Meta-Critic
Reviews critic behavior across units:
- hollow passes;
- repeated blind spots;
- inconsistent standards;
- recurring defects that repair failed to eliminate.

---

# 6. Story defect registry extension

Recommended codes:

```text
STORY_PREMISE_TOPIC_ONLY
STORY_PREMISE_WEAK_PRESSURE
STORY_ANGLE_GENERIC
STORY_THEME_DIDACTIC
STORY_RESEARCH_UNGROUNDED
STORY_RESEARCH_CONTRADICTION_UNRESOLVED
STORY_CHARACTER_FLAT
STORY_MOTIVATION_BREAK
STORY_KNOWLEDGE_LEAK
STORY_RELATIONSHIP_STATE_BREAK
STORY_CONFLICT_WEAK
STORY_STAKES_FLAT
STORY_CAUSAL_GAP
STORY_COINCIDENCE_RESOLUTION
STORY_STRUCTURE_REVERSAL_WEAK
STORY_EMOTIONAL_ARC_BREAK
STORY_EMOTIONAL_MONOTONY
STORY_TENSION_FLATLINE
STORY_TENSION_WHIPLASH
STORY_SCENE_STATIC
STORY_SCENE_NO_TURN
STORY_BEAT_NO_MICROCHANGE
STORY_DIALOGUE_ON_NOSE
STORY_DIALOGUE_VOICE_DRIFT
STORY_SUBTEXT_MISSING
STORY_SETUP_MISSING
STORY_PAYOFF_UNEARNED
STORY_PAYOFF_MISSING
STORY_PAYOFF_NO_CONSEQUENCE
STORY_TIMELINE_BREAK
STORY_AUDIENCE_KNOWLEDGE_BREAK
```

Observed defect code is not automatically root cause.

Example:

```text
Observed: STORY_DIALOGUE_ON_NOSE
Possible root cause:
- weak hidden intent in DialogueIntent
- weak scene conflict
- missing knowledge asymmetry
- character model has no defensive tactic
```

Repair should target the earliest supported cause.

---

# 7. Targeted Story Repair

## 7.1 Repair order

```text
1 locate defect
2 identify evidence
3 test root-cause hypotheses
4 choose earliest responsible layer
5 define preserve set
6 define patch scope
7 invalidate only dependent artifacts
8 rewrite/replan
9 rerun responsible critic
10 rerun regression critics on preserve dimensions
```

## 7.2 Scope selection

### LINE / EXCHANGE
Use when line-level surface expression is wrong but beat intent is valid.

### BEAT
Use when tactic/reaction/micro-change fails but scene transition remains valid.

### SCENE
Use when scene has wrong turn/objective/end state.

### SEQUENCE
Use when escalation/information order/structural progression fails across scenes.

### CHARACTER MODEL
Use when repeated behavior defects trace to an underdefined/wrong psychology model.

### RESEARCH PACKAGE
Use when story problem comes from insufficient/contradictory factual basis.

### STORY STRUCTURE
Use when major causal chain/setup/payoff fails.

### PREMISE / ANGLE
Escalate only when downstream defects reveal the story engine itself is weak.

## 7.3 Preserve obligations

Borrowing the strongest selective-revision idea:

```text
preserve != suggestion
preserve = post-repair verification obligation
```

If the repair was intended to keep Character A's voice and setup S17 unchanged, regression checks must verify both.

---

# 8. Rewrite loop limits

No endless critique/rewrite cycle.

Candidate policy:

```text
local repair attempts: bounded
same defect persists N times:
→ escalate one layer upstream
repeated regressions:
→ human/project review or alternative strategy
```

Model self-critique cannot silently iterate forever.

---

# 9. Script-lock acceptance

A script may lock when:
- all BLOCKING findings resolved;
- HIGH findings explicitly accepted or resolved per project policy;
- research requirements satisfied;
- hierarchy/causal/knowledge/timeline validation passes;
- setup/payoff ledger has no unintended critical broken promise;
- critique snapshot is complete;
- lock manifest written.

Aesthetic perfection is not mechanically provable. Script Lock means the project has passed its explicit production criteria and accepted residual creative risk.
