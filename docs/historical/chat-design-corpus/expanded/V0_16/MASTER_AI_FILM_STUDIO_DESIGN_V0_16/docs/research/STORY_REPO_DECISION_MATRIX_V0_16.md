# STORY_REPO_DECISION_MATRIX_V0_16.md
# Story Intelligence — Repo Donor Decision Matrix

**Status:** 12-round repo harvest decision candidate  
**Rule:** no third-party repo becomes canonical story authority.  
**Decision vocabulary:** `KEEP / ADAPT / EXTRACT / REWRITE / REPLACE / PATTERN-ONLY / BRAIN-PACK / DROP / DEFER`.

## Final module map

| Story module | Primary donor evidence | Decision | Integration rule |
|---|---|---|---|
| Premise / Idea Lab | MoPS; Writers Room; Dramatron | PATTERN + BRAIN PACK | Canonical custom module. Use modular candidate synthesis; do not import unlicensed MoPS code. |
| Angle Lab | STORM; GPT Researcher; Evidence Graph | EXTRACT/PATTERN | Generate competing perspectives/research questions; select by novelty, relevance, evidence potential. |
| Theme System | Open-Write; Story Architect; Writers Room | BRAIN PACK | Theme is explicit hypothesis/argument + character/value embodiment; selectable methodologies. |
| Research Intelligence | GPT Researcher; STORM; Evidence Graph | ADAPT + EXTRACT | Best reuse opportunity. Recursive research + persona questions + claim/contradiction graph. |
| Research → Story Material | GPT Researcher; STORM; Open-Write | CUSTOM | Transform facts into concrete human detail, tensions, scene opportunities; source provenance retained. |
| Dynamic Brain Resolver | Writers Room; Story Architect; Script Doctor; Open-Write | CUSTOM + BRAIN PACKS | Versioned data-driven packs; engine remains ours. |
| Character Psychology | SOTOPIA; Sabre; Open-Write; GenAgents | CUSTOM + PATTERN | Canonical character state/knowledge/values/goals; social/evaluative patterns borrowed. |
| Conflict / Stakes | Sabre; Writers Room; StoryDaemon | CUSTOM + PATTERN | Intentional action + opposition + stakes ladder; symbolic planner pattern not runtime dependency. |
| Structure / Causality | Sabre; Dramatron; StoryDaemon; Open-Write | CUSTOM HYBRID | Causal graph + hierarchical structure + rolling horizon; canonical StoryGraph owned by Studio. |
| Emotional Arc | StoryDaemon; narrative-generation; Open-Write | CUSTOM + PATTERN | Typed emotional progression tied to character/value change, not single emotion labels. |
| Emotional Rhythm | Beatlume; StoryDaemon | EXTRACT/PATTERN | Tension/relief curve analytics inform but never alone decide story quality. |
| Scene Engine | StoryDaemon; Beatlume; Dramatron | CUSTOM HYBRID | Scene contract requires start state→conflict→turn→end state; no-static-scene gate. |
| Beat Engine | StoryDaemon; Dramatron | CUSTOM HYBRID | Intention→action→reaction→resistance/new-info→micro-change. |
| Dialogue / Subtext | SOTOPIA; Open-Write; Dramatron | CUSTOM + PATTERN | Dialogue generated from goals, relationship, knowledge asymmetry, tactic and subtext; specialist critics. |
| Pacing / Tension | Beatlume; StoryDaemon | EXTRACT/PATTERN | Detect flatline, whiplash, breathing room, arc-pressure drift. |
| Setup / Payoff Ledger | Open-Write; StoryDaemon | ADAPT/PATTERN | Typed plant/remind/escalate/payoff/consequence ledger with unresolved-loop checks. |
| Continuity / Story Memory | Open-Write; StoryDaemon; Mem0 optional | CUSTOM AUTHORITY + OPTIONAL ADAPTER | SQLite canonical truth; semantic memory only retrieval support. |
| Independent Critique Council | Open-Write; GPT Researcher; Evidence Graph | ADAPT/EXTRACT | Blinded specialist critics + skeptic + bounded revise; findings need located evidence. |
| Targeted Story Repair | StoryDaemon; GPT Researcher; Open-Write | CUSTOM + PATTERN | Repair earliest responsible layer; preserve unaffected content; dependency invalidation. |
| Script Lock | Open-Write + Studio approval system | ADAPT/PATTERN | Manifest/verification + story quality gates + explicit human/project lock. |

## Repo-level decision summary

| Repo | License | Decision | Runtime dependency? | Main value |
|---|---|---|---|---|
| `google-deepmind/dramatron` | Apache-2.0 | **EXTRACT/PATTERN** | NO | hierarchical logline→characters→scenes→places→dialogue; human rewrite/intervention history |
| `sgware/sabre` | GPL-3.0 | **PATTERN-ONLY** | NO | deterministic narrative planning; character utilities/intentionality |
| `EdwardAThomson/StoryDaemon` | NO LICENSE DETECTED | **PATTERN-ONLY** | NO | multi-stage strategic→semantic-context→tactical planning; plot beats/rolling horizon/throughline/open loops |
| `abdussamadbello/beatlume` | NO LICENSE DETECTED | **PATTERN-ONLY** | NO | scene scaffold and relationship graph; structured story/character/scene models |
| `simon-benigeri/narrative-generation` | NO LICENSE DETECTED | **PATTERN-ONLY** | NO | explicit emotions/character arc idea; narrative planner/context/dialogue separation |
| `sotopia-lab/sotopia` | MIT | **EXTRACT/PATTERN** | NO | persistent character profiles/values/decision style/secrets; agent goals and relationships |
| `assafelovic/gpt-researcher` | Apache-2.0 | **ADAPT/EXTRACT** | OPTIONAL; NOT CORE AUTHORITY | recursive breadth/depth research; parallel subresearch |
| `langchain-ai/open_deep_research` | MIT | **PATTERN-ONLY** | NO | supervisor/research graph; state/config contracts |
| `stanford-oval/storm` | MIT | **EXTRACT/PATTERN** | NO | perspective/persona generation; persona-guided questions |
| `machachlouei/evidence-graph` | MIT | **EXTRACT/PATTERN** | NO | atomic claim graph; typed supports/contradicts/qualifies/extends edges |
| `mem0ai/mem0` | Apache-2.0 | **OPTIONAL ADAPTER** | OPTIONAL | production-oriented long-term memory infrastructure; persistent semantic memory and retrieval |
| `StanfordHCI/genagents` | MIT | **PATTERN-ONLY** | NO | memory/reflection/behavior pattern for simulated persons |
| `letta-ai/letta-code` | Apache-2.0 | **DEFER/PATTERN** | NO V1 | stateful agent memory/identity runtime; TypeScript and current activity |
| `GAIR-NLP/MoPS` | NO LICENSE DETECTED | **PATTERN-ONLY** | NO | modular story premise synthesis; candidate module composition before premise integration |
| `Open-Write/Open-Write` | Apache-2.0 | **ADAPT/EXTRACT** | NO CORE RUNTIME; IMPORT RUBRICS/TOOLS | screenplay pipeline; story bible/state/callback/audience/timeline ledgers |
| `jackterror/writers-room-story-engine` | MIT | **ADAPT AS BRAIN PACK** | NO | premise/story spine/causal beat/character arc craft framework; modular AI-ready skill format |
| `NeuraCerebra-AI/story-architect-skill` | MIT | **ADAPT AS BRAIN PACK** | NO | Truby-like character web/moral argument/scene weave/dialogue framework |
| `bflandev/script-doctor` | MIT | **ADAPT AS BRAIN PACK** | NO | story bible approval; beat sheet acceptance |
| `lwhela12/AI-Screenwriting-Tool` | MIT | **UI/PATTERN** | NO | screenplay editor/beat board/outline UX; current TypeScript codebase |

## Non-negotiable license rule

```text
NO LICENSE / UNKNOWN LICENSE
→ inspect for learning
→ record architecture/pattern
→ independently reimplement
→ DO NOT copy source into product
```

```text
GPL / AGPL donor
→ no code incorporation into closed-source V1 unless licensing strategy explicitly accepts obligations
→ pattern-level study only by default
```

Apache/MIT donor code may be reused only with license/notice attribution and only behind canonical Studio contracts.
