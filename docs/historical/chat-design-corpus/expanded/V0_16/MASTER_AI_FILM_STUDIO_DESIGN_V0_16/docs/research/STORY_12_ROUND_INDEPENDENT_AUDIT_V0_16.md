# STORY_12_ROUND_INDEPENDENT_AUDIT_V0_16.md
# Story Intelligence Repo Harvest — 12 Independent Audit Rounds

**Date:** 2026-09-21  
**Scope:** replace/upgrade FlowKit's weak Story Intelligence without replacing its stronger Entity / Reference / Continuity execution / Generation integration / Orchestration core.  
**Method:** every round restarts from a different review question. A later round may reject a candidate favored by an earlier round.  
**Coding policy:** this document selects donors and contracts; it does **not** implement production features.  
**Evidence policy:** repository README/code/tests/license/activity were inspected. A standardized output-quality benchmark across all candidates was **not** fabricated; where no comparable benchmark exists, the gap is recorded.

---

# Executive conclusion

There is no single repository that should replace FlowKit's story layer wholesale.

The strongest architecture is a **canonical Story Intelligence System owned by the Studio**, fed by selectively reused donor algorithms, rubrics and patterns:

```text
FLOWKIT GOLD CORE
Entity / Reference / Continuity execution / Generation integration / Orchestration
                              │
                              ▼
                 CANONICAL STUDIO DOMAIN
                              │
                              ▼
                 STORY INTELLIGENCE SYSTEM
                              │
       ┌──────────────────────┼───────────────────────┐
       │                      │                       │
RESEARCH DONORS        NARRATIVE DONORS        CRITIQUE DONORS
GPT Researcher         Dramatron                Open-Write
STORM                  StoryDaemon*             GPT Researcher
Evidence Graph         Sabre*                   Evidence Graph
                       Beatlume*                 StoryDaemon*
                       SOTOPIA                  

* pattern-only by default because of license/integration constraints
```

The most reusable licensed areas are:

1. **Research orchestration:** GPT Researcher + STORM + Evidence Graph.
2. **Critique protocols:** Open-Write + GPT Researcher reviewer/reviser + Evidence Graph skeptic.
3. **Craft knowledge packs:** Writers Room / Story Architect / Script Doctor / Open-Write.
4. **Social-character evaluation patterns:** SOTOPIA.

The areas that still require a Studio-owned canonical implementation are the most important ones:

- Premise / Angle / Theme authority;
- Dynamic Brain Resolver;
- Character psychology and knowledge state;
- Conflict / Stakes;
- causal StoryGraph;
- Emotional Arc / Emotional Rhythm authority;
- Scene / Beat contracts;
- Dialogue/Subtext contracts;
- Setup/Payoff ledger;
- Story Quality Gate;
- Targeted Story Repair;
- Script Lock.

This is not "code everything from zero." It is **reuse without surrendering authority**.

---

# ROUND 1 — Canonical Contract Reviewer

## Independent question

Before looking at repos, what must a professional Story Intelligence subsystem own so that repo selection is not biased by whichever repo happens to expose the most attractive API?

## Finding R133-F01 — BLOCKING

A generic `Story Engine` box is too weak. It hides multiple authorities and makes it impossible to know what should be reused vs. rebuilt.

## Required canonical modules

```text
01 Idea / Premise Lab
02 Angle Lab
03 Theme System
04 Research Intelligence
05 Research → Story Material Transformer
06 Dynamic Brain Resolver
07 Character Psychology Engine
08 Relationship / Knowledge-State Engine
09 Conflict & Stakes Engine
10 Structure / Causality Engine
11 Emotional Arc Engine
12 Emotional Rhythm Engine
13 Scene Engine
14 Beat Engine
15 Dialogue / Subtext Engine
16 Pacing / Tension Engine
17 Setup / Payoff Ledger
18 Story Continuity / Memory
19 Independent Critique Council
20 Targeted Story Repair
21 Story Quality Gate
22 Script Lock
```

## Required separation of authority

```text
Story owns:
what happens
why it happens
what changes
what each character wants/believes/knows
what is planted/promised/paid off
what emotional progression is intended

Directing owns:
how the audience experiences the story event
performance emphasis
information reveal strategy in staging
rhythm of presentation

Cinematography owns:
camera / lens / composition / movement / lighting execution
```

## Decision

**ACCEPT.** Repo candidates are evaluated against these contracts, not the other way around.

---

# ROUND 2 — Broad Discovery Reviewer

## Independent question

Which repositories contain actual reusable narrative/research/evaluation mechanisms rather than only a "generate story" prompt?

## Candidate families inspected

### Hierarchical screenplay/narrative generation
- `google-deepmind/dramatron`
- `EdwardAThomson/StoryDaemon`
- `abdussamadbello/beatlume`
- `simon-benigeri/narrative-generation`
- `Open-Write/Open-Write`
- `lwhela12/AI-Screenwriting-Tool`

### Formal narrative planning / causality
- `sgware/sabre`
- `GAIR-NLP/MoPS`

### Research / evidence / perspective generation
- `assafelovic/gpt-researcher`
- `stanford-oval/storm`
- `machachlouei/evidence-graph`
- `langchain-ai/open_deep_research`

### Character / social intelligence / memory
- `sotopia-lab/sotopia`
- `StanfordHCI/genagents`
- `mem0ai/mem0`
- `letta-ai/letta-code`

### Craft / story-method Brain Packs
- `jackterror/writers-room-story-engine`
- `NeuraCerebra-AI/story-architect-skill`
- `bflandev/script-doctor`

## Finding R134-F01 — HIGH

Star count is a poor selector for Story Intelligence. Small repos contain highly relevant patterns that large generic agent frameworks do not.

## Finding R134-F02 — HIGH

"Screenwriting app" and "story intelligence" are not synonymous. Editor/formatting repos can inform UX but often do not own causality, emotional progression or story-state semantics.

## Decision

Shortlist by **capability evidence**, not popularity.

---

# ROUND 3 — License / Activity / Dependency Reviewer

## Independent question

Can the code legally and operationally enter a commercial/local-first Studio?

## License triage

### Reuse-friendly candidates

```text
Apache-2.0:
Dramatron
GPT Researcher
Open-Write
Mem0
Letta Code

MIT:
STORM
SOTOPIA
Evidence Graph
Writers Room Story Engine
Story Architect Skill
Script Doctor
AI-Screenwriting-Tool
GenAgents
```

### Pattern-only by default

```text
Sabre: GPL-3.0
StoryDaemon: no license detected
Beatlume: no license detected
narrative-generation: no license detected
MoPS: no license detected
```

## Finding R135-F01 — BLOCKING

A repo without a reusable license cannot be treated as a code donor merely because its source is public.

**Rule:** inspect → document concept → independently implement. Do not copy source.

## Finding R135-F02 — CRITICAL

GPL/AGPL code must not silently contaminate a closed-source/commercial V1. Sabre is therefore an algorithmic reference unless a compatible licensing decision is made later.

## Finding R135-F03 — HIGH

An MIT/Apache license does not automatically make a repo a good runtime dependency. Language/runtime/authority fit still matters.

## Decision

Add a two-axis decision:

```text
LEGAL REUSE ELIGIBILITY
×
ARCHITECTURAL INTEGRATION FITNESS
```

A candidate can be legally reusable but still be pattern-only for architectural reasons.

---

# ROUND 4 — Deep Code Reviewer

## Independent question

What does the code actually do?

## Dramatron

Inspected `colab/dramatron.ipynb`.

Observed hierarchy:

```text
storyline
→ title
→ characters
→ scenes
→ places
→ dialogs
```

`StoryGenerator.step()` generates each level from higher-level context. Dialogue generation consumes the current scene, place, character descriptions, plot element, previous beat summary and current beat. `rewrite()` records interventions/diffs at hierarchy levels.

### Keep
- top-down decomposition pattern;
- explicit intermediate story artifacts;
- human rewrite/intervention history.

### Do not keep as canonical engine
- storyline as a single textual source of truth;
- prompt prefix structures as canonical story state;
- lack of explicit causal/knowledge/emotional contracts.

**Decision:** `EXTRACT/PATTERN`.

---

## Sabre

Inspected README and planner/domain code.

Sabre models:
- typed entities and properties;
- state;
- actions with preconditions/effects;
- consenting characters;
- observing characters;
- author utility;
- per-character utility;
- beliefs and nested theory of mind;
- deterministic forward search.

This is one of the strongest donors for **causal action that makes sense to the acting character**, not prose generation.

### Keep conceptually

```text
action must be executable
AND advance some narrative objective
AND make sense from actor's belief state
```

### Do not import directly
GPL-3.0 + Java + symbolic problem-authoring burden.

**Decision:** `PATTERN-ONLY` for Character Intentionality + Causal StoryGraph.

---

## StoryDaemon

Inspected orchestration, multi-stage planner, plot outline, evaluator and selective revision modules.

Observed:

```text
plot beat
→ strategic scene intention
→ semantic context gathering
→ tactical plan
→ write
→ evaluate continuity/POV
→ tension evaluation/control
→ commit
→ fact/lore/entity updates
→ verify beat
→ rolling-horizon revision if divergence
```

Especially strong patterns:
- strategic vs tactical planning;
- relevant-context retrieval instead of full-context prompt dumping;
- pending beat registry and prerequisites;
- throughline/open-loop concepts;
- tension target and arc pressure;
- selective paragraph revision that preserves unaffected blocks;
- fact/lore extraction after commit.

Weaknesses found in inspected code:
- parts of continuity QA are heuristic;
- some error paths deliberately degrade rather than hard-fail;
- no reusable license detected.

**Decision:** one of the strongest **PATTERN-ONLY** donors.

---

## Beatlume

Inspected scene scaffold, relationship inference and analytics code.

Useful non-prompt algorithms:

```text
pacing velocity
flatline detection
whiplash detection
breathing-room detection
cubic-spline tension visualization
peak/valley detection
```

Relationship analysis also treats character pairs and shared scenes as structured inputs.

The scaffold graph itself is primarily an LLM-call wrapper, so it is not enough as a Story Engine.

**Decision:** `PATTERN-ONLY`; independently reimplement pacing/tension metrics.

---

## GPT Researcher

Inspected multi-agent orchestrator, reviewer/reviser and deep-research skill.

Observed:

```text
browser/research
→ planner
→ plan review
→ parallel sub-research
→ writer
→ fact checker
→ revise loop
→ publish
```

Deep research has breadth/depth/concurrency, query+researchGoal structure, context limits, source tracking and defensive parsing.

Reviewer/reviser separation is highly relevant to Story Critique:
- reviewer gives targeted feedback;
- reviser is asked to preserve other aspects;
- loops are bounded.

**Decision:** `ADAPT/EXTRACT` for Research Intelligence and bounded critique protocol.

---

## STORM

Inspected persona generator, knowledge curation and outline generation.

Strong pattern:

```text
topic
→ related-topic structural examples
→ multiple research personas/perspectives
→ persona-guided questions
→ query generation/retrieval
→ grounded answer
→ information table
→ draft outline
→ outline refined from learned information
```

This directly helps **Angle Lab** and **Research Intelligence**. It does not directly solve dramatic structure.

**Decision:** `EXTRACT/PATTERN`.

---

## Evidence Graph

Inspected graph schemas, skeptic, contradiction hunter and LangGraph workflow.

Strong concepts:
- atomic claims with source provenance;
- typed edges `SUPPORTS / CONTRADICTS / QUALIFIES / EXTENDS`;
- contradiction-directed research;
- source-monoculture detection;
- disconfirmation search;
- stability-based stopping.

This is materially stronger than "search then summarize" for research-heavy stories/documentaries.

**Decision:** `EXTRACT/PATTERN`; use canonical Studio evidence schemas, not repo schemas verbatim.

---

## Open-Write

Inspected README and critic-mode definitions.

Observed:

```text
Bible
→ voice experiments
→ structural editorial gate
→ architect plan
→ writer
→ 5 blinded critics
→ conditional cutter
→ editorial
→ disk verification
→ meta-critic
→ full manuscript adversarial reader
→ completion verification
```

State includes project facts, callback ledger, audience knowledge and timeline. Continuity critic decomposes narrative claims into sub-assumptions and cross-checks state. Meta-critic evaluates the critics for hollow passes and blind spots.

This is one of the best direct donors for **Critique Council, Setup/Payoff, Audience Knowledge and Completion Verification**.

**Decision:** `ADAPT/EXTRACT` licensed rubrics/tools, translated into typed Studio contracts.

---

## SOTOPIA

Inspected persistent profile and evaluator surfaces.

Character data includes personality/values, decision style, secrets, social goals and relationship types. Evaluators judge participants against goals using structured outputs.

This is useful for character interaction evaluation, but its social-simulation runtime should not replace screenplay state.

**Decision:** `EXTRACT/PATTERN`.

---

# ROUND 5 — Intelligence-vs-Prompt-Wrapper Reviewer

## Independent question

Which candidates have mechanisms beyond "put prose in a prompt and ask an LLM"?

## Classification

| Candidate | Mechanism depth | Evidence |
|---|---|---|
| Sabre | **Algorithmic / formal** | symbolic state, utility, belief, precondition/effect search |
| Evidence Graph | **Algorithmic + LLM hybrid** | claim graph, typed edges, stability, contradiction loop |
| GPT Researcher | **Orchestration + retrieval hybrid** | recursive breadth/depth, sources, bounded reviews |
| StoryDaemon | **Domain workflow hybrid** | persistent beats/memory/tension/rolling horizon/selective repair |
| Open-Write | **Procedure + verification hybrid** | blinded critics, state ledgers, manifest/completion gate |
| STORM | **Research workflow hybrid** | perspective/persona research + grounded outline refinement |
| SOTOPIA | **Simulation/evaluation hybrid** | goals/profiles/social environment/evaluators |
| Beatlume | **Mixed** | real pacing/tension algorithms + prompt-driven scaffold |
| Dramatron | **Hierarchical prompt system** | strong decomposition, weaker formal semantics |
| narrative-generation | **Research prototype** | emotion-conditioned models/context |
| Brain-pack repos | **Knowledge assets** | craft rubrics/methods, not runtime engines |

## Finding R137-F01 — CRITICAL

No LLM-generated numeric score should become story truth simply because a framework produces one.

## Finding R137-F02 — HIGH

The strongest solution is heterogeneous:
- formal/deterministic checks where possible;
- graph/state checks for causality/continuity;
- LLM judgment for semantic/artistic dimensions;
- independent critic evidence for subjective dimensions.

## Decision

Build a hybrid quality system, not an "LLM judge everything" system.

---

# ROUND 6 — Runnable / Test-Surface Reviewer

## Independent question

Which donors show enough executable/test structure to justify borrowing implementation patterns?

## Strong test surfaces

- GPT Researcher: broad tests/evals and benchmark assets.
- StoryDaemon: extensive unit/integration tests around beats, tension, contracts, entities, rolling horizon and repair.
- SOTOPIA: tests for environment, evaluators, storage, benchmark integration.
- Beatlume: backend tests, simulation tests and frontend E2E layout.
- Evidence Graph: focused graph tests and explicit baseline/ablation workflow.
- Open-Write: verification/lint/completion tools plus a shipped demo process.

## Weaker integration surfaces

- Dramatron: notebook-centered research code.
- narrative-generation: old experiment with model files/paths and limited production packaging.
- MoPS: research/notebook orientation.
- methodology/skill repos: intentionally data/rubric assets rather than executable engines.

## Important honesty constraint

A full install-and-run of every candidate was **not** performed because:
- candidates use different languages/models/API credentials;
- some are unlicensed and cannot become code donors anyway;
- a synthetic runtime "PASS" would not establish screenplay quality;
- pre-implementation phase should not turn into unrelated infrastructure certification.

This round therefore evaluates **runnable/test surface evidence**, not fictional runtime equivalence.

## Decision

Favor donor patterns with explicit tests/contracts, but require Studio-owned tests after extraction/porting.

---

# ROUND 7 — Quality Evidence / Benchmarkability Reviewer

## Independent question

Which repo's claims about quality are externally or internally testable, and what remains unproven?

## Evidence categories

### Dramatron
Has published human co-writing evaluation with playwrights/screenwriters. This supports usefulness as a co-writing hierarchy, **not** autonomous screenplay excellence.

### GPT Researcher
Maintains explicit research/evaluation assets and current benchmark work. This supports research subsystem reuse more than story quality.

### STORM / SOTOPIA
Research-oriented projects with evaluation methodology, useful for perspective research/social interaction, but not direct screenplay-quality proof.

### Evidence Graph
Ships baseline/ablation route and graph tests; useful for contradiction handling. Small project means broad production evidence remains limited.

### Open-Write
Ships a demo and explicitly documents limitations plus completion verification. Its honesty about autonomous lapses is valuable, but its creative quality still requires our own story benchmarks.

### StoryDaemon / Beatlume
Strong internal structures/tests but no comparable independent screenplay benchmark established in this audit.

## Finding R139-F01 — BLOCKING

A cross-repo "winner" cannot be truthfully declared from stars, README claims or incompatible demo outputs.

## Future implementation benchmark

After Story Intelligence core exists, run the same locked corpus across candidate policies/adapters:

```text
family drama
true crime/documentary
historical drama
romance
horror
business documentary
children/family story
science explainer
retention-aware YouTube documentary
cinematic short
```

Evaluate:
- premise strength;
- angle distinctiveness;
- thematic coherence;
- source specificity/provenance;
- character depth/motivation;
- conflict/stakes;
- causal coherence;
- emotional arc/rhythm;
- scene state change;
- dialogue/subtext;
- pacing/tension;
- setup/payoff;
- continuity;
- targeted rewrite quality.

## Decision

Benchmark is an **implementation acceptance task**, not a blocker to defining the architecture today.

---

# ROUND 8 — Integration-Fit Reviewer

## Independent question

Can a donor fit the Electron/local-first canonical-domain modular monolith without adding a second source of truth?

## Integration rules

### Allowed

```text
third-party algorithm/rubric
→ adapter/port
→ canonical input contract
→ canonical output contract
→ Studio persistence
```

### Forbidden

```text
Repo A state DB
↔ Repo B memory DB
↔ Repo C story JSON
↔ FlowKit scene state
↔ Studio DB
```

because authority becomes impossible to reason about.

## Language/runtime conclusion

Most strongest donors are Python. V1 should **not** add Python as a mandatory canonical runtime merely to reuse them.

Reuse modes:
1. Port small deterministic algorithms (e.g. pacing metrics) into Studio language.
2. Import licensed rubric/data assets as Brain Packs.
3. Reimplement patterns from unlicensed/GPL repos.
4. Allow an optional external Research Adapter later for heavyweight GPT Researcher-like research, without making it story authority.

## Finding R140-F01 — CRITICAL

"Reuse" must not mean "run five foreign agent frameworks inside Electron."

## Decision

No new mandatory story-runtime framework dependency is selected in V0.16.

---

# ROUND 9 — Authority-Conflict Reviewer

## Independent question

Where would donor systems conflict with canonical Studio ownership?

## Authority conflicts found

### Memory
Mem0/Letta/StoryDaemon can all persist memory. None may own locked story facts.

**Canonical rule:**

```text
SQLite Story Domain = authority
semantic/vector/agent memory = derived retrieval index
```

### Character state
SOTOPIA profiles, Sabre belief states and Open-Write character files overlap.

**Canonical rule:** a single `CharacterModelVersion + CharacterStateSnapshot + KnowledgeState` owns truth; donor schemas map into it.

### Scene/beat
Dramatron scene objects and StoryDaemon plot beats differ from our Story→Sequence→Scene→Beat model.

**Canonical rule:** donor scene/beat objects are import/analysis artifacts only.

### Research truth
GPT Researcher/STORM/Evidence Graph produce learned claims.

**Canonical rule:** research evidence is **source material**, not locked story fact until accepted/normalized according to project mode.

### Critic verdicts
Open-Write or LLM reviewer verdicts cannot directly lock script.

**Canonical rule:** critics emit `CritiqueFinding`; Story Quality Gate aggregates deterministic and semantic evidence; lock remains an explicit project transition.

## Decision

One responsibility → one canonical authority. All donor state is subordinate/derived.

---

# ROUND 10 — Adversarial / Devil's Advocate Reviewer

## Independent question

Assume the proposed hybrid architecture fails. What likely caused it?

## Failure attack 1 — Framework zoo

**Risk:** too many repos become dependencies.  
**Patch:** no mandatory repo runtime selected; donor extraction only.

## Failure attack 2 — License contamination

**Risk:** GPL/no-license code copied into product.  
**Patch:** source snapshot records license; pattern-only rule enforced.

## Failure attack 3 — Prompt inflation

**Risk:** every donor contributes a giant rubric and context explodes.  
**Patch:** structured contracts + resolver selects only relevant Brain Pack slices.

## Failure attack 4 — Story-by-score

**Risk:** optimization against tension/emotion metrics creates mechanical writing.  
**Patch:** metrics are diagnostics/policy signals, not story truth; blocking gates and qualitative critics remain.

## Failure attack 5 — Causal rigidity

**Risk:** Sabre-like formal logic makes stories predictable.  
**Patch:** use formal causality as validation/option generation, not as sole creative generator.

## Failure attack 6 — Research overwhelms drama

**Risk:** factual detail becomes exposition.  
**Patch:** separate Evidence → Story Material transformation; only material with dramatic/human function enters script planning.

## Failure attack 7 — Brain Pack dogma

**Risk:** one methodology (Hero's Journey/Truby/Pixar/etc.) becomes universal.  
**Patch:** Brain Packs are selectable policies, never domain authority.

## Failure attack 8 — Critic monoculture

**Risk:** same model writes and judges itself.  
**Patch:** blinded specialist critics, optional model diversity, meta-critic/hollow-review detection, evidence-linked findings.

## Failure attack 9 — Rewrite destroys good material

**Risk:** whole-scene/full-script regeneration fixes one defect but degrades voice/structure.  
**Patch:** targeted Story Repair with preserve/patch/invalidate/recheck and bounded scope.

## Failure attack 10 — Memory becomes fiction

**Risk:** vector memory retrieves stale/inferred facts as canon.  
**Patch:** canonical records carry version/status/provenance; retrieval output cannot self-promote to truth.

## Decision

All ten attack paths are addressed in the V0.16 architecture requirements.

---

# ROUND 11 — Composition Architecture Reviewer

## Independent question

Given all previous findings, what exact hybrid should be built?

## Proposed composition

```text
IDEA / TOPIC / SOURCE MATERIAL
        ↓
PREMISE LAB
  modular candidate synthesis (MoPS pattern)
  craft constraints (Brain Packs)
        ↓
ANGLE LAB
  STORM-style perspective generation
  research-gap / novelty analysis
        ↓
THEME SYSTEM
  theme hypothesis + moral/value tension
        ↓
RESEARCH INTELLIGENCE
  GPT Researcher breadth/depth pattern
  STORM persona questions
  EvidenceGraph atomic claim/contradiction/skeptic loop
        ↓
RESEARCH → STORY MATERIAL
  fact → human detail / conflict / setting / scene opportunity
        ↓
DYNAMIC BRAIN RESOLVER
  domain + genre + audience + format + platform packs
        ↓
CHARACTER PSYCHOLOGY + KNOWLEDGE STATE
  SOTOPIA-style values/goals/social evaluation
  Sabre-style intentionality/belief semantics
        ↓
CONFLICT / STAKES
        ↓
CAUSAL STORY GRAPH + STRUCTURE
  author objective + character reason + precondition/effect validation
  hierarchical Story→Sequence→Scene→Beat
        ↓
EMOTIONAL ARC
        +
EMOTIONAL RHYTHM / TENSION CURVE
        ↓
SCENE CONTRACTS
  START_STATE → OBJECTIVE → CONFLICT → TURN → END_STATE
        ↓
BEAT CONTRACTS
  intention → action → reaction → resistance/new info → micro-change
        ↓
DIALOGUE / SUBTEXT
  goal + tactic + relationship + knowledge asymmetry + unsaid intent
        ↓
DRAFT SCRIPT
        ↓
INDEPENDENT CRITIQUE COUNCIL
  structure / causality / character / emotion / dialogue / continuity /
  research / audience-retention / theme / devil's advocate
        ↓
TARGETED STORY REPAIR
  defect → root layer → preserve → patch → invalidate → recheck
        ↺
STORY QUALITY GATE
        ↓
SCRIPT LOCK
        ↓
DIRECTING → CINEMATOGRAPHY → SHOTS
```

## FlowKit relationship

FlowKit is not asked to become this Story Intelligence System.

```text
FlowKit Gold Core
= execution/reference/generation donor

Story Intelligence V0.16
= canonical upstream creative intelligence
```

## Decision

**ACCEPT composition candidate.**

---

# ROUND 12 — Final Decision / Freeze-Readiness Reviewer

## Independent question

Is the Story Intelligence design now detailed enough to enter final project consolidation without another open-ended repo-search cycle?

## Findings

### R144-F01 — PASS
All required story responsibilities have a canonical owner.

### R144-F02 — PASS
Every major module has a donor strategy: reusable code/pattern/brain pack/custom authority.

### R144-F03 — PASS
No unlicensed/GPL repository is required as product code.

### R144-F04 — PASS
No third-party memory/story database becomes canonical authority.

### R144-F05 — PASS
Story research has a provenance/contradiction model rather than raw summary injection.

### R144-F06 — PASS
Story quality includes hard blocking defects and cannot be averaged into a false PASS.

### R144-F07 — PASS
Scene and Beat semantics require state movement, preventing static exposition-only structure from passing silently.

### R144-F08 — PASS
Critique is independent/specialized and repair is targeted rather than full-regenerate by default.

### R144-F09 — OPEN-BY-DESIGN, NOT A DESIGN BLOCKER
A comparable creative benchmark has not yet been run. It belongs after the canonical Story Intelligence implementation exists.

### R144-F10 — OPEN-BY-DESIGN, NOT A DESIGN BLOCKER
Exact LLM/model choices remain runtime policy; Story contracts are model-neutral.

## Final decision

```text
STORY INTELLIGENCE REPO HARVEST = COMPLETE
12/12 INDEPENDENT ROUNDS = COMPLETE
NEW OPEN-ENDED REPO SEARCH = NOT REQUIRED BEFORE CODING
```

The next project phase is:

```text
V0.16 Story Intelligence
→ FINAL DESIGN CONSOLIDATION
→ resolve cross-document supersession
→ IMPLEMENTATION BASELINE FREEZE
→ dependency graph
→ task decomposition
→ TASK_QUEUE
→ implementation
```

Live creative benchmarking remains attached to implementation acceptance tasks rather than blocking the start of coding.

---

# Final donor policy

```text
KEEP
FlowKit Gold Core where already strong.

ADAPT / EXTRACT
GPT Researcher research/review patterns
STORM perspective research patterns
Evidence Graph contradiction/skeptic patterns
Open-Write critic/callback/completion assets
selected SOTOPIA social-profile/evaluation patterns
licensed craft Brain Packs

PATTERN-ONLY
Sabre
StoryDaemon
Beatlume
narrative-generation
MoPS
and any no-license candidate

OPTIONAL ADAPTER
Mem0 only for semantic/episodic retrieval if the built-in Studio retrieval layer proves insufficient.

DEFER
Letta-scale stateful agent runtime for V1.
```

# Core architectural law produced by this audit

> **Third-party repos may contribute algorithms, rubrics, evidence workflows, retrieval mechanisms and craft knowledge. They may not own canonical story truth, project state, character state, scene/beat identity, quality acceptance or script lock.**
