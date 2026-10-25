# STORY_INTELLIGENCE_ARCHITECTURE_V0_16.md
# Canonical Story Intelligence System V0.16

**Status:** REVIEWED CANDIDATE after independent review rounds 133–144.  
**Purpose:** make screenplay/story quality a first-class production subsystem rather than a single prompt stage.  
**Authority:** this document supersedes the generic `Story Engine` description in the V0.1 design draft where the two conflict.

---

# 1. Quality thesis

The Studio treats story quality as a bottleneck system:

```text
GOOD SCRIPT
≈
PREMISE
× ANGLE
× THEME
× RESEARCH
× ACTIVE BRAIN FIT
× CHARACTER DEPTH
× CONFLICT/STAKES
× CAUSAL STRUCTURE
× EMOTIONAL ARC
× EMOTIONAL RHYTHM
× SCENE/BEAT MOVEMENT
× DIALOGUE/SUBTEXT
× PACING/TENSION
× SETUP/PAYOFF
× INDEPENDENT CRITIQUE
```

This multiplication is a **design metaphor for bottlenecks**, not literal uncalibrated AI arithmetic. A blocking weakness must not be averaged away by pretty prose.

---

# 2. Story Intelligence boundary

```text
INPUT / INGEST
│
├─ idea
├─ topic
├─ outline
├─ source article/research
├─ existing screenplay
└─ existing structured project
        ↓
STORY INTELLIGENCE SYSTEM
        ↓
SCRIPT LOCK
        ↓
DIRECTING ENGINE
        ↓
CINEMATOGRAPHY
        ↓
SHOT DESIGN / GENERATION
```

Story Intelligence owns **what changes and why**.

It does not own provider prompts, camera optics, reference-image selection or generation transport.

---

# 3. Canonical subsystem graph

```text
Story Intake
   ↓
Premise Lab ──────────────┐
   ↓                      │
Angle Lab                 │ candidate loop
   ↓                      │
Theme System              │
   ↓                      │
Research Intelligence ←───┘
   ↓
Research → Story Material Transformer
   ↓
Dynamic Brain Resolver
   ↓
Character Psychology ── Relationship / Knowledge State
   ↓                              ↓
Conflict & Stakes ←───────────────┘
   ↓
Causal StoryGraph / Structure Engine
   ↓
Emotional Arc Engine
   +
Emotional Rhythm Engine
   ↓
Sequence Planning
   ↓
Scene Contracts
   ↓
Beat Contracts
   ↓
Dialogue / Subtext Planning
   ↓
Drafting
   ↓
Critique Council
   ↓
Story Quality Gate
   ├─ PASS → Script Lock
   ├─ REPAIRABLE → Targeted Story Repair ↺
   └─ UPSTREAM DEFECT → reopen responsible upstream layer ↺
```

---

# 4. Premise Lab

## 4.1 Purpose

A premise is not a synopsis. It is a compact dramatic engine containing enough tension to generate a story.

Candidate structure:

```text
PremiseCandidate
= protagonist / focal subject
+ concrete situation
+ disruptive force
+ central dramatic problem
+ meaningful stakes
+ contradiction / irony / tension
+ transformation potential
```

## 4.2 Candidate generation

Use modular synthesis rather than one-shot generation:

```text
SOURCE IDEA
↓
world/situation candidates
character candidates
problem/pressure candidates
stakes candidates
thematic contradiction candidates
freshness/specificity candidates
↓
compose N premise candidates
↓
remove semantic near-duplicates
↓
critic + evidence-aware screening
↓
shortlist
```

MoPS contributes the pattern of modular candidate synthesis; licensed craft Brain Packs can contribute methodology/rubrics. The Studio owns the schema and selection logic.

## 4.3 Premise hard checks

A premise cannot pass if:
- no identifiable dramatic pressure exists;
- the protagonist/focal subject has nothing consequential to lose/change;
- the premise is only a topic (`"a film about grief"`);
- core causality depends on unexplained coincidence;
- documentary/nonfiction premise makes an unsupported factual assertion foundational to the story.

---

# 5. Angle Lab

## 5.1 Why angle is separate

The same topic can produce radically different films depending on what lens controls information and attention.

```text
TOPIC: a factory closes

Angle A: owner facing bankruptcy
Angle B: worker hiding closure from family
Angle C: town's final week before closure
Angle D: investigation into why it closed
Angle E: child returning home after decades
```

## 5.2 Angle candidate fields

- `lens` — whose/what perspective organizes the material;
- `central_question`;
- `information_advantage` — what this angle reveals that generic coverage does not;
- `emotional_access`;
- `research_potential`;
- `visual_potential`;
- `novelty_basis`;
- `risk` — sensationalism, overfamiliarity, access/fact gaps;
- `fit` with audience/format/platform.

STORM-style persona/perspective generation is a donor pattern. Angle selection remains Studio authority.

---

# 6. Theme System

## 6.1 Theme representation

Theme is not a slogan injected into dialogue.

```text
ThemeHypothesis
├── thematic_question
├── value_A
├── value_B
├── working_argument
├── counter_argument
├── protagonist_initial_belief
├── opposing_character/world belief
├── tests_of_belief[]
├── final_story_position (may remain ambiguous)
└── anti_didacticism_constraints
```

## 6.2 Theme integration law

Theme should appear through:
- choices;
- consequences;
- relationship conflicts;
- repeated but evolving motifs;
- setup/payoff;
- character transformation or refusal to transform.

It should not require characters to explain the writer's thesis directly.

---

# 7. Research Intelligence

## 7.1 Modes

```text
RESEARCH_MODE =
NONE
LIGHT_CONTEXT
DEEP_FACTUAL
DOCUMENTARY
HISTORICAL
TECHNICAL
CULTURAL
MARKET/AUDIENCE
```

Not every fictional short needs deep web research. The Brain Resolver decides research depth from project risk.

## 7.2 Research pipeline

```text
ResearchBrief
↓
question decomposition
↓
perspective/persona decomposition
↓
parallel retrieval
↓
source capture
↓
atomic claim extraction
↓
claim relationship graph
SUPPORTS / CONTRADICTS / QUALIFIES / EXTENDS
↓
contradiction + disconfirmation search
↓
confidence / unresolved gaps
↓
ResearchEvidencePackage
```

Donor composition:
- GPT Researcher: breadth/depth/concurrency/source-tracking/review patterns;
- STORM: perspective/persona-guided questioning and learned-outline refinement;
- Evidence Graph: atomic claims, contradiction hunter, skeptic, stability stopping.

## 7.3 Research authority

A fetched page or LLM synthesis is not a locked story fact.

```text
RAW SOURCE
→ Extracted Claim
→ Evidence relationship
→ accepted factual proposition / unresolved proposition
→ Story Material
→ Story Fact (only when project policy accepts it)
```

## 7.4 Contradiction policy

Contradictions are stored, not silently averaged.

For nonfiction/documentary/historical projects:
- unresolved material claims may block Script Lock;
- disputed claims must retain attribution/scope;
- uncertainty can be represented narratively when appropriate.

---

# 8. Research → Story Material Transformer

Research becomes useful only when converted into dramatic material.

```text
FACT / SOURCE DETAIL
↓
why it matters to this story
↓
possible human consequence
↓
character pressure
↓
concrete sensory/detail opportunity
↓
scene / beat / prop / environment / dialogue opportunity
```

Example:

```text
raw fact:
old cassette tape can wrinkle and jam

story material:
- character uses pencil to turn spool
- distorted fragment of mother's voice
- motor stalls before final sentence
- physical act forces character to stay and listen
- damaged audio creates uncertainty before payoff
```

Every `StoryMaterial` item retains evidence provenance when factual.

---

# 9. Dynamic Brain Resolver

## 9.1 Principle

Core workflow is stable; behavior is data-driven.

```text
CORE STORY ENGINE
+
PROJECT CONTEXT
+
DOMAIN BRAIN
+
GENRE BRAIN
+
AUDIENCE BRAIN
+
FORMAT BRAIN
+
PLATFORM BRAIN
=
ACTIVE STORY BRAIN
```

## 9.2 Brain Pack

A Brain Pack is versioned policy/knowledge data, not a new source of story truth.

```text
BrainPack
├── id / version
├── type: domain|genre|audience|format|platform|craft
├── applicability rules
├── required research dimensions
├── premise heuristics
├── structure strategies
├── character rubrics
├── conflict/stakes heuristics
├── scene/beat patterns
├── dialogue/subtext guidance
├── emotional rhythm profiles
├── pacing guidance
├── critic rubrics
├── examples
├── anti-patterns
└── provenance/license
```

## 9.3 Merge precedence

When policies conflict:

```text
locked project facts / explicit user constraints
>
format hard constraints
>
domain factual constraints
>
project-selected craft methodology
>
genre/audience/platform soft guidance
```

No Brain Pack may override locked canon.

---

# 10. Character Psychology Engine

## 10.1 Character model

```text
CharacterModelVersion
├── identity/core facts
├── external_want
├── internal_need
├── fear
├── wound / formative pressure
├── lie_or_mistaken_belief
├── values
├── contradictions
├── strengths
├── flaws / defense mechanisms
├── secrets
├── social mask
├── private self
├── preferred strategies
├── boundaries / taboos
├── voice registers[]
├── relationships[]
├── arc hypothesis
└── provenance/version
```

Not every project must populate every psychological field. Required fields depend on format and genre.

## 10.2 Knowledge State

Character psychology and character knowledge are different.

```text
CharacterKnowledgeState
├── character_id
├── knows[]
├── believes[]
├── suspects[]
├── misunderstands[]
├── hides[]
├── source_event_ids[]
└── effective_story_time
```

This enables dramatic irony and prevents knowledge leaks.

## 10.3 Intentional action rule

Borrowing the principle from narrative planning:

```text
CHARACTER ACTION SHOULD HAVE
preconditions
+ perceived reason
+ expected consequence from character viewpoint
+ actual consequence
```

A character may make a bad decision, but it should be intelligible from that character's information/belief/value state unless randomness is explicitly intentional.

---

# 11. Conflict & Stakes Engine

## 11.1 Conflict model

Conflict is not merely "an antagonist exists."

```text
ConflictModel
├── protagonist objective
├── opposition forces[]
│   ├── external
│   ├── interpersonal
│   ├── internal
│   ├── systemic/environmental
│   └── time/resource
├── incompatible objectives
├── leverage / power asymmetry
├── escalation rules
├── reversals
└── resolution conditions
```

## 11.2 Stakes ladder

```text
immediate practical stake
→ relationship/social stake
→ identity/value stake
→ irreversible consequence
```

Not every story needs all levels. Escalation must fit genre/scale.

## 11.3 Stakes test

At major turns, the system asks:
- what can now be lost that could not be lost earlier?
- what option disappeared?
- what cost increased?
- what relationship/value is newly endangered?

---

# 12. Causal StoryGraph / Structure Engine

## 12.1 Canonical graph

```text
StoryGraph
nodes:
  events
  decisions
  revelations
  reversals
  setups
  payoffs
  state transitions

edges:
  CAUSES
  ENABLES
  MOTIVATES
  BLOCKS
  REVEALS
  ESCALATES
  PAYS_OFF
  CONTRADICTS_EXPECTATION
```

## 12.2 Structural hierarchy

```text
Story
└── Sequence[]
    └── Scene[]
        └── Beat[]
            └── Shot[]  # downstream
```

Structure templates from Brain Packs are strategy candidates, not canonical law.

## 12.3 Causality gate

A major beat must answer:

```text
Why now?
Because of what prior event/decision?
Why this character?
What changes after it?
What future event does it enable/force?
```

Coincidence may introduce trouble; coincidence should not repeatedly solve core dramatic problems unless intentionally part of the form.

---

# 13. Emotional Arc Engine

## 13.1 Arc vs rhythm

```text
EMOTIONAL ARC
= long-horizon transformation of emotional/value state

EMOTIONAL RHYTHM
= local intensity/valence/tension variation over time
```

They must not be collapsed.

## 13.2 Emotional Arc plan

```text
EmotionalArcPlan
├── focal_character / audience track
├── initial emotional/value state
├── pressure points[]
├── turning points[]
├── reversals[]
├── peak / breaking point
├── release / integration / refusal
└── final emotional/value state
```

Arc may be positive, negative, flat/tested, cyclical or intentionally unresolved.

---

# 14. Emotional Rhythm / Tension Engine

## 14.1 Per-scene signals

- tension 0–10 candidate/estimated;
- emotional valence;
- arousal/intensity;
- uncertainty;
- hope/fear balance;
- release/breathing room;
- information pressure;
- relationship pressure.

These are diagnostics, not objective truth.

## 14.2 Deterministic analytics worth porting

From inspected donor patterns:
- delta/velocity between scenes;
- flatline windows;
- abrupt whiplash;
- peaks/valleys;
- breathing room after high-intensity peaks;
- climax position;
- repeated scene-mode detection.

## 14.3 Anti-gaming rule

A perfect numerical curve is not evidence of a moving story. Metrics cannot PASS a static scene or a causal gap.

---

# 15. Scene Engine

## 15.1 NO STATIC SCENE law

A scene is a dramatic state transition, not a location containing dialogue.

```text
START_STATE
↓
character objective / expectation
↓
resistance / conflict
↓
tactics / escalation
↓
turn / revelation / decision / reversal
↓
END_STATE
```

At least one meaningful dimension should change:

```text
knowledge
power
relationship
goal
risk
emotion
belief
resources
available options
social position
commitment
```

If `STATE_BEFORE == STATE_AFTER`, the scene must justify its existence as deliberate atmosphere/setup/comedy/etc.; otherwise it is a static-scene defect candidate.

## 15.2 SceneContract

Owns:
- narrative function;
- entering state;
- POV/focal relation;
- objective;
- obstacle/opposition;
- audience knowledge entering;
- character knowledge asymmetry;
- conflict tactic;
- escalation;
- turn;
- key change;
- audience effect;
- emotional target;
- tension target/range;
- setup/payoff obligations;
- exit state;
- downstream causal edges.

---

# 16. Beat Engine

A Beat is a micro-transition inside a Scene.

```text
INTENTION
→ ACTION / TACTIC
→ REACTION
→ RESISTANCE / NEW INFORMATION
→ MICRO-CHANGE
```

Beat sequence should avoid multiple consecutive beats with identical tactic and state effect unless repetition is an intentional dramatic device.

---

# 17. Dialogue & Subtext Engine

## 17.1 Dialogue input authority

Dialogue should be conditioned by:
- speaker objective;
- listener objective;
- relationship state;
- knowledge asymmetry;
- emotional state;
- current tactic;
- social context;
- voice register;
- what cannot/should not be said directly;
- beat change required.

## 17.2 DialogueIntent

```text
surface_intent
hidden_intent
requested_outcome
avoidance
pressure_point
current_tactic
possible_tactic_shift
knowledge_constraints
voice_register
subtext_target
```

## 17.3 Subtext principle

`spoken meaning != complete dramatic meaning` for scenes where concealment, power, intimacy, fear, negotiation or denial are active.

A direct informational line is not automatically bad; the system should not force subtext where clarity is the point.

---

# 18. Setup / Payoff Ledger

```text
SetupPayoffLink
├── id
├── setup_story_location
├── promise / question / object / motif / skill / relationship seed
├── audience_visibility
├── characters_aware[]
├── reinforcement[]
├── escalation[]
├── expected_payoff_window
├── payoff_story_location
├── payoff_type
├── consequence
├── status
└── intentional_non_payoff_reason
```

Lifecycle:

```text
PLANT
→ REMIND / DEVELOP
→ COMPLICATE / ESCALATE
→ PAYOFF
→ CONSEQUENCE
```

Unresolved setups are not automatically errors; they become errors when the script promises resolution and neither pays off nor intentionally leaves ambiguity.

---

# 19. Story Continuity / Memory

## 19.1 Canonical truth

```text
SQLite canonical records
= authority

vector index / semantic memory / Mem0 adapter
= retrieval aid only
```

## 19.2 Memory classes

- locked canon;
- accepted story facts;
- character knowledge/belief;
- relationship state;
- timeline;
- setup/payoff ledger;
- unresolved questions/loops;
- research evidence;
- audience knowledge;
- draft-only hypotheses.

No derived memory may silently promote itself to locked canon.

---

# 20. Independent Critique Council

Critics are independent roles, not one giant "review this script" prompt.

Recommended minimum council:

```text
Premise / Angle Critic
Research / Fact Critic
Causality / Structure Critic
Character / Motivation Critic
Conflict / Stakes Critic
Emotion / Rhythm Critic
Scene / Beat Critic
Dialogue / Subtext Critic
Continuity / Knowledge Critic
Setup / Payoff Critic
Audience / Retention Critic (when applicable)
Theme Critic
Devil's Advocate / Skeptic
Meta-Critic
```

Each finding must contain located evidence and responsible layer.

Critics should be blinded from one another where cross-contamination would reduce independence. A synthesis stage merges findings afterward.

---

# 21. Story Quality Gate

## 21.1 Verdict vocabulary

```text
PASS
WARN
FAIL
NOT_EVALUATED
```

Severity:

```text
BLOCKING
HIGH
MEDIUM
LOW
COSMETIC
```

## 21.2 Blocking examples

- protagonist action contradicts established knowledge/motivation without narrative explanation;
- required causal bridge missing;
- documentary core assertion unsupported/contradicted and presented as fact;
- climax/payoff depends on unplanted ability/information;
- scene required by structure does not change state and has no justified alternate function;
- major setup promised then accidentally disappears;
- Script Lock contains unresolved critical continuity contradiction.

BLOCKING cannot be averaged away.

---

# 22. Targeted Story Repair

```text
CritiqueFinding
↓
root-cause diagnosis
↓
earliest responsible layer
↓
RepairPlan
├── preserve
├── patch
├── invalidate
├── regenerate/rewrite
└── recheck
```

Repair scopes:

```text
LINE
EXCHANGE
BEAT
SCENE
SEQUENCE
CHARACTER_MODEL
RESEARCH_PACKAGE
STORY_STRUCTURE
PREMISE/ANGLE
```

Whole-script rewrite is an escalation mode, not the default.

---

# 23. Script Lock

`Script Lock` is a versioned transition, not "LLM says done."

Required:
- current StoryVersion identified;
- no unresolved BLOCKING story findings;
- critical research claims resolved or explicitly represented as disputed/uncertain;
- character/story/timeline state internally consistent;
- required setup/payoff obligations accounted for;
- scene/beat hierarchy valid;
- critique lineage preserved;
- lock manifest/hash written;
- explicit project/user approval according to project policy.

After lock, downstream Directing/Cinematography bind to the locked script version. Upstream revision creates a new version and invalidates affected downstream decisions through dependency edges.

---

# 24. Donor boundary

```text
DONOR REPO
   ↓
license check
   ↓
extract algorithm / rubric / pattern
   ↓
Studio adapter or independent implementation
   ↓
canonical Story contract
   ↓
Studio repository
```

A donor never writes directly into canonical tables without validation/application-service ownership.

---

# 25. Relationship to FlowKit

KEEP from FlowKit:
- entity/reference mechanics where useful;
- continuity execution/chaining mechanics;
- generation integration;
- queue/waves/retry/resume/dependency ordering/artifact handling.

REPLACE/UPGRADE in Story layer:
- generic scene generation;
- implicit story hierarchy;
- prompt-as-intent;
- weak narrative-state authority;
- lack of premise/angle/theme/research/character psychology/conflict/emotion/payoff/critique/repair systems.

Canonical rule:

```text
Story Intelligence output
→ locked narrative domain
→ Directing
→ ShotSpec/IR
→ FlowKit-derived execution mechanisms
```
