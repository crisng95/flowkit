# FLOWKIT_STORY_REPLACEMENT_MAP_V0_16.md
# FlowKit Weak-Story Replacement Map V0.16

**Goal:** keep FlowKit where it is strong and prevent Story Intelligence from being forced into FlowKit's operational `Scene` model.

| Concern | FlowKit role | V0.16 action | New authority |
|---|---|---|---|
| Entity persistence/reference | strong donor | KEEP/ADAPT | Studio Entity/Reference canonical contract with FlowKit adapter |
| Reference chaining/parent conditioning | strong donor | KEEP/UPGRADE | Reference Resolver + State Engine |
| Queue/waves/dependencies/retry/resume | strong donor | KEEP/EXTEND | Orchestrator |
| Provider generation integration | strong donor | KEEP behind adapters | Provider Runtime |
| Operational Scene generation unit | useful runtime concept | RENAME/MAP only; never cinematic authority | Shot/GenerationJob mapping |
| Premise | weak/not canonical | REPLACE | Premise Lab |
| Angle | weak/not canonical | REPLACE | Angle Lab |
| Theme | weak/not canonical | REPLACE | Theme System |
| Deep research/evidence | missing/weak | REPLACE | Research Intelligence |
| Domain/genre brain | prompt-policy style | REPLACE | Dynamic Brain Resolver + Brain Packs |
| Character psychology | insufficient | REPLACE | Character Psychology Model |
| Character knowledge/beliefs | insufficient | REPLACE | Knowledge State |
| Conflict/stakes | insufficient | REPLACE | Conflict & Stakes Engine |
| Causal story structure | insufficient | REPLACE | StoryGraph + Structure Engine |
| Emotional arc/rhythm | insufficient | REPLACE | Emotional Arc + Rhythm Engines |
| Scene dramatic transition | overloaded with operational scene | REPLACE | SceneContract |
| Beat semantics | insufficient | REPLACE | BeatContract |
| Dialogue/subtext | prompt output | REPLACE | DialogueIntent + Dialogue Engine |
| Pacing/tension | limited | REPLACE/EXTEND | Rhythm/Tension Analytics |
| Setup/payoff | missing | REPLACE | SetupPayoff Ledger |
| Story continuity/knowledge | visual/execution continuity not enough | EXTEND | Story Memory + State Authority |
| Independent story critique | missing | REPLACE | Critique Council |
| Story targeted repair | missing | REPLACE | Story Repair |
| Script lock | missing as formal authority | REPLACE | ScriptLockManifest |

## Anti-corruption boundary

```text
CANONICAL STORY DOMAIN
Story / Sequence / Scene / Beat / Script Lock
        ↓
Directing / Shot planning
        ↓
Shot / Generation Job
        ↓
FlowKitAdapter
        ↓
FlowKit-derived queue/reference/generation machinery
```

FlowKit objects must not be imported upward as canonical Story entities.

## Mapping law

A cinematic `Scene` may compile to many `Shot`s; each `Shot` may produce one or more generation attempts. A FlowKit operational scene/request object therefore maps **downstream** to a generation job/shot attempt, not upward to the cinematic Scene authority.
