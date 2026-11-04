# FLOWKIT TO AI FILM STUDIO GAP MATRIX

## 0. Purpose

This matrix compares the implementation verified in the current FlowKit repository against the target AI Film Studio design vocabulary supplied for the DISCOVERY + DESIGN INGEST phase.

This is a design-gap document, not an implementation plan.

Restrictions:

- No feature tasks are created here.
- No code change is authorized by this document.
- No build/test result is claimed.
- “Absent” means no canonical runtime model/subsystem was found in the audited code, not that a skill document never mentions a related word.
- Existing procedural guidance in skills is distinguished from typed, persisted runtime architecture.

## 1. Comparison legend

Current-state labels:

- PRESENT — first-class runtime capability exists.
- PARTIAL — useful implementation exists but does not satisfy the target contract.
- PROCEDURAL — represented mainly as agent/skill instructions, not durable typed state.
- ABSENT — no canonical runtime subsystem found.

Gap size:

- FOUNDATIONAL — target requires a new domain boundary or canonical model.
- MAJOR — current implementation is useful but materially incomplete.
- MODERATE — mostly an extension/integration problem.
- SMALL — limited contract/persistence/policy additions.

Reuse disposition uses the same vocabulary as the current-state audit:
KEEP, KEEP + EXTEND, ADAPT, EXTRACT, REWRITE, REPLACE, DROP.

## 2. Executive comparison

FlowKit Current is strongest from reference media onward:

Entity/reference
→ image/video generation
→ queue/retry/resume
→ provider transport
→ video QA

The target Studio begins much earlier and requires explicit intelligence and state:

Topic/Niche Intelligence
→ Idea/Story Development
→ Dramatic Structure
→ Screenplay
→ Directing
→ Blocking/Cinematography
→ Shot Planning
→ State/Continuity/Reference Resolution
→ Shot IR/Compiler
→ Provider Routing
→ Orchestration
→ QA/Repair

The largest architectural gap is therefore not another generator integration. It is the missing canonical production-intelligence model between a raw project story string and the current Scene generation unit.

## 3. Topic and niche intelligence

| Target capability | FlowKit Current | Evidence / current behavior | Gap | Target requirement | Disposition |
| --- | --- | --- | --- | --- | --- |
| Topic Intelligence | ABSENT | No topic-intelligence domain/table/service found. Research skill is fact-check oriented. | FOUNDATIONAL | Structured topic signals, audience opportunity, relevance, constraints, evidence/provenance. | REPLACE |
| Niche Resolver | ABSENT | No niche model/resolver found. | FOUNDATIONAL | Resolve topic into market/content niche with rules, rationale and selected production strategy. | REPLACE |
| Composable Brain Pack | ABSENT / PROCEDURAL | skills/ contains reusable instructions, but there is no typed/versioned Brain Pack composition system. | FOUNDATIONAL | Versioned composable intelligence packs with declared inputs/outputs, authority and compatibility. | REPLACE; ingest useful skill knowledge |
| Active Production Profile | PARTIAL | project stores language/material/audio flags; providers.json stores video-review role; video stores orientation. | MAJOR | One canonical resolved profile covering genre, audience, format, style, runtime rules, brain packs, provider/cost/quality policy and locks. | ADAPT |

Key design consequence:

Current configuration is distributed across Project, Video, Material, models.json, providers.json, environment variables, skill instructions, and request fields. The Studio needs one authoritative ActiveProductionProfile that resolves these sources before story/shot compilation.

## 4. Idea and story-development intelligence

| Target capability | FlowKit Current | Evidence / current behavior | Gap | Target requirement | Disposition |
| --- | --- | --- | --- | --- | --- |
| Idea | ABSENT | No typed Idea artifact. | FOUNDATIONAL | Versioned idea artifact with source, intent, audience promise and provenance. | REPLACE |
| Logline | ABSENT | Repository search found no canonical logline model/field. | FOUNDATIONAL | One-sentence dramatic contract derived from accepted idea/premise. | REPLACE |
| Premise | ABSENT | No runtime premise model/field found. | FOUNDATIONAL | Structured premise with protagonist, goal, opposition, stakes and dramatic engine. | REPLACE |
| Angle | ABSENT | No runtime angle artifact. | FOUNDATIONAL | Explicit treatment/point-of-view/content angle bound to audience/genre. | REPLACE |
| Theme | ABSENT | No runtime theme artifact. | FOUNDATIONAL | Theme statement plus thematic questions/oppositions and scene relevance. | REPLACE |
| Research Intelligence | PROCEDURAL | AGENTS and fk-research require research before scripting, but no structured research store was found in runtime schema. | MAJOR | Evidence objects, source quality, claims, contradictions, confidence, applicability and provenance. | REWRITE |
| Research → Story Material | ABSENT | No transformation artifact mapping facts/research to usable dramatic material. | FOUNDATIONAL | Selection/transformation layer: facts → story facts, constraints, motifs, events, props, dialogue evidence, exclusions. | REPLACE |

Current bottleneck:

Project.story is an optional TEXT string. That makes it impossible to know whether an eventual scene came from an idea, researched fact, premise decision, theme, or later improvisation.

## 5. Character and causal story model

| Target capability | FlowKit Current | Evidence / current behavior | Gap | Target requirement | Disposition |
| --- | --- | --- | --- | --- | --- |
| Character Psychology | ABSENT | character/entity record stores visual description and optional voice description, not dramatic psychology. | FOUNDATIONAL | Desire / Need / Fear / Wound / Secret / Lie / Value / Arc state. | REPLACE while linking existing Entity ID |
| Relationship | ABSENT | No relationship graph/table found. | FOUNDATIONAL | Typed character/entity relationships with dynamic state and history. | REPLACE |
| Knowledge | ABSENT | No per-character knowledge ledger. | FOUNDATIONAL | What each actor knows, source/time learned, confidence and reveal constraints. | REPLACE |
| Belief | ABSENT | No belief/misperception model. | FOUNDATIONAL | Belief state separated from objective truth and knowledge. | REPLACE |
| Conflict / Stakes | ABSENT | Only free story/scene prose can imply these. | FOUNDATIONAL | Explicit conflict engines, stakes, escalation, consequence and scene-level pressure. | REPLACE |
| Causal StoryGraph | ABSENT | Scene display_order and parent_scene_id are media-chain/order constructs, not story causality. | FOUNDATIONAL | Causal graph of events/decisions/reveals/setups/payoffs with prerequisites and consequences. | REPLACE |

Critical separation:

Existing Entity should remain the production identity anchor.
Character Psychology and dramatic state should attach to that identity, not be embedded into image prompts or visual descriptions.

## 6. Narrative hierarchy

| Target capability | FlowKit Current | Evidence / current behavior | Gap | Target requirement | Disposition |
| --- | --- | --- | --- | --- | --- |
| MacroStoryBeat | ABSENT | No runtime type/table. | FOUNDATIONAL | Structural beat with dramatic function, causal inputs/outputs and arc contribution. | REPLACE |
| Sequence | ABSENT | No sequence domain. Videos are containers, not narrative sequences. | FOUNDATIONAL | Sequence groups scenes around dramatic objective/escalation/turn. | REPLACE |
| Scene | PARTIAL / CONFLICTING | Current Scene is ordered render/generation unit with prompts/media state. | FOUNDATIONAL | Separate dramatic Scene contract from render Shot/RenderUnit. | ADAPT |
| SceneDramaticBeat | ABSENT | No runtime beat model. | FOUNDATIONAL | Within-scene beat progression, action/reaction/turn/value change. | REPLACE |
| AudienceExperienceTarget | ABSENT | No explicit audience emotion/knowledge/tension target per beat/scene. | FOUNDATIONAL | Expected audience question, emotion, information, anticipation and payoff. | REPLACE |

Required hierarchy:

Story
→ MacroStoryBeat
→ Sequence
→ Dramatic Scene
→ SceneDramaticBeat
→ Shot planning

Current hierarchy:

Project
→ Video
→ Scene
→ generation media

These cannot be treated as equivalent.

## 7. Screenplay realization and story QA

| Target capability | FlowKit Current | Evidence / current behavior | Gap | Target requirement | Disposition |
| --- | --- | --- | --- | --- | --- |
| Screenplay Realization | ABSENT | narrator_text and scene prompt are not a screenplay model. | FOUNDATIONAL | Scene headings/action/dialogue/subtext/turns mapped from locked dramatic structure. | REPLACE |
| Critique | PARTIAL | video reviewer critiques rendered video; no story/screenplay critique subsystem. | FOUNDATIONAL | Stage-specific critique against story requirements, structure, causality, dialogue, repetition, retention and genre grammar. | KEEP video QA + REPLACE story critique |
| Targeted Story Repair | ABSENT | Current repair guidance targets rendered media prompts, not story artifacts. | FOUNDATIONAL | Repair plan scoped to specific failed story requirement without uncontrolled rewrite. | REPLACE |
| Script Lock | ABSENT | No version/authority lock for screenplay. | FOUNDATIONAL | Immutable accepted screenplay/version boundary required before downstream directing. | REPLACE |

Important distinction:

Current REVIEW stage is a rendered-video quality review.
Target Critique must begin before expensive generation and operate on story/screenplay/directing/shot artifacts as well.

## 8. Directing and cinematography

| Target capability | FlowKit Current | Evidence / current behavior | Gap | Target requirement | Disposition |
| --- | --- | --- | --- | --- | --- |
| DirectingIntent | PROCEDURAL | Camera/action advice exists in skills but no persisted directing-intent artifact. | FOUNDATIONAL | Why the scene should feel/play a certain way; power, point of view, reveal strategy, rhythm, actor focus. | REPLACE; ingest skill rules |
| SceneSpatialDramaticContract | ABSENT | Location entity and free prompts exist, but no spatial dramatic model. | FOUNDATIONAL | Space zones, entrances/exits, geography, sightlines, screen direction, power positions, constraints. | REPLACE |
| BlockingPlan | ABSENT | Blocking is expressed only in authored prose prompts when present. | FOUNDATIONAL | Actor/object positions, movement beats, marks, interaction and continuity constraints. | REPLACE |
| CinematographyObjective | PROCEDURAL | fk-camera-guide describes shot types/angles/movement/lighting, but not a resolved per-scene objective. | MAJOR | Scene-level visual strategy tied to dramatic intent before selecting shots. | REWRITE using camera guide as donor knowledge |

Reusable donor:
skills/fk-camera-guide.md is valuable production knowledge, but it must become policies/taxonomy consumed by planning rather than remain the sole source of camera decisions.

## 9. Shot system

| Target capability | FlowKit Current | Evidence / current behavior | Gap | Target requirement | Disposition |
| --- | --- | --- | --- | --- | --- |
| Shot List | ABSENT | INSERT scenes and camera prose imitate multiple angles, but no Shot collection exists. | FOUNDATIONAL | Ordered shots derived from beat/blocking/cinematography objectives. | REPLACE |
| ShotEligibilityGate | ABSENT | No formal check decides whether a proposed shot is valid/necessary/generatable. | FOUNDATIONAL | Gate for narrative necessity, continuity, reference availability, provider feasibility and redundancy. | REPLACE |
| Full Shot Spec | ABSENT | Prompt text contains some framing/action/camera details, not typed complete shot state. | FOUNDATIONAL | Full structured shot contract: purpose, beat, framing, lens, angle, movement, blocking, composition, lighting, environment, entities, state, refs, duration, transitions, audio intent. | REPLACE |
| ShotDecisionTrace | ABSENT | No persisted reason for why a shot/camera choice was selected. | FOUNDATIONAL | Inputs considered, decision rules, alternatives/rejections and final rationale/provenance. | REPLACE |

The existing Scene should not simply be renamed Shot without migration design. It owns media statuses, narration, chain state and other legacy responsibilities that should become execution projections/artifacts.

## 10. Entity, Reference, State and Continuity

| Target capability | FlowKit Current | Evidence / current behavior | Gap | Target requirement | Disposition |
| --- | --- | --- | --- | --- | --- |
| Entity | PRESENT / PARTIAL | Generic entity_type in character table; project links; description/ref media. | MAJOR | Generalize naming/contracts; attach dramatic identity/state/reference authorities. | KEEP + EXTEND |
| Reference | PRESENT / PARTIAL | One current ref URL/media ID; UUID/upload/recovery; scene reference resolution. | MAJOR | Versioned ReferenceAsset/ReferenceBundle, roles, provenance, approval, lock, quality, applicability and resolver trace. | KEEP + EXTEND |
| State | PARTIAL | Project/media/request state exists; active_project.json; no narrative/world state. | FOUNDATIONAL | State snapshots/deltas for character, wardrobe, prop, world, time, weather, knowledge, belief and relationships. | ADAPT execution state + REPLACE narrative state |
| Continuity | PARTIAL | parent chains, base-image edits, end-frame links, shared entity refs and cascade. | FOUNDATIONAL | Explicit continuity constraints and state transition ledger independent from media chaining. | REWRITE |

Critical rule for target design:

REFERENCE answers “what canonical evidence should generation see?”
STATE answers “what is true at this point in the story?”
CONTINUITY answers “what must remain/transition consistently across boundaries?”

Those must not be collapsed into one media ID or one parent_scene_id.

## 11. Shot IR and compiler

| Target capability | FlowKit Current | Evidence / current behavior | Gap | Target requirement | Disposition |
| --- | --- | --- | --- | --- | --- |
| Shot IR | ABSENT | No provider-neutral intermediate representation. | FOUNDATIONAL | Canonical resolved shot truth after authority/state/reference resolution and before provider lowering. | REPLACE |
| Compiler | ABSENT / PARTIAL INGREDIENTS | String concatenation in entity profile builder, material prefixes, continuation helper and video prompt builder. | FOUNDATIONAL | Deterministic multi-stage compiler with validation, conflict resolution, diagnostics, provenance and provider lowering. | REWRITE |

Existing ingredients to extract into compiler policies:
- Material style prefix/instruction.
- reference composition policy.
- reference resolver.
- continuation transformation rule where still appropriate.
- voice-context injection.
- audio policy.
- negative-output policy.
- provider wire payload builders.

Required compiler stages conceptually:

Full Shot Spec
+ Active Production Profile
+ Entity truth
+ State snapshot
+ Continuity constraints
+ Reference selection
→ Shot IR
→ validation
→ provider capability match
→ provider-specific compiled static-image prompt / motion prompt / generation options
→ immutable compilation artifact + decision trace

Current FlowKit jumps from free-text Scene fields to provider request construction.

## 12. Provider Router

| Target capability | FlowKit Current | Evidence / current behavior | Gap | Target requirement | Disposition |
| --- | --- | --- | --- | --- | --- |
| Provider Router | PARTIAL | Direct Flow endpoints choose model_family veo/omni_flash; review has separate role resolver for Claude/Codex/agy. | MAJOR | One capability-aware router over generation and analysis providers with constraints, quality/cost/speed policy, fallback semantics and durable decision trace. | ADAPT |

Current useful provider assets:
- FlowClient transport.
- flow_batch wire builders.
- Omni Flash service.
- models.json capability/model data.
- CLI provider role resolution.

Missing:
- canonical ProviderCapability.
- compile-time feasibility.
- requirements→provider match.
- provider score/selection rationale.
- explicit degradation policy artifact.
- per-provider queue limits and cost budget.
- normalized provider option schema.

## 13. Orchestrator

| Target capability | FlowKit Current | Evidence / current behavior | Gap | Target requirement | Disposition |
| --- | --- | --- | --- | --- | --- |
| Orchestrator | PARTIAL / STRONG EXECUTION CORE | Worker processes durable Request rows with dependencies inferred by type; skills describe larger production pipeline. | MAJOR | Persisted production DAG over artifacts/stages with explicit dependencies, gates, attempts, resume checkpoints and provider resource policy. | KEEP + EXTEND |

Current strengths:
- durable request rows.
- prerequisite deferral.
- concurrency/cooldown.
- type priorities.
- duplicate suppression.
- result state.
- retry.
- operation re-poll.
- stale processing recovery.

Missing:
- production plan node model.
- dependency edges.
- stage gate artifact dependencies.
- compile artifact identity.
- QA→repair→recompile edges.
- run/version ownership.
- deterministic “what is next?” from persisted plan rather than skill-level procedure.

## 14. QA

| Target capability | FlowKit Current | Evidence / current behavior | Gap | Target requirement | Disposition |
| --- | --- | --- | --- | --- | --- |
| QA | PARTIAL / STRONG VIDEO QA | video_reviewer performs actual frame analysis and structured scoring/errors. | MAJOR | Multi-stage QA: research, story, screenplay, directing, shot, continuity, compile, generated image/video, final assembly; persist evidence. | KEEP + EXTEND |

Current rendered-video dimensions:
- character consistency.
- prompt adherence.
- motion quality.
- visual fidelity.
- temporal coherence.
- composition.

Needed QA architecture:
- Requirement.
- Check.
- Finding.
- Severity.
- Evidence.
- Target artifact/version.
- Gate result.
- Repair eligibility.
- reviewer/provider identity.
- persisted timestamp/version.

No QA result should be equivalent to a generic prose comment.

## 15. Repair

| Target capability | FlowKit Current | Evidence / current behavior | Gap | Target requirement | Disposition |
| --- | --- | --- | --- | --- | --- |
| Repair | PROCEDURAL / PARTIAL | reviewer creates fix_guide; skills instruct prompt patches/regeneration loops. | FOUNDATIONAL | Targeted repair engine with explicit scope, allowed mutations, failed requirement, before/after artifacts, attempt history and re-verification. | REWRITE |

Current useful assets:
- known error taxonomy.
- severity parsing.
- practical prompt remediation hints.
- REGENERATE operations.
- cascade invalidation.

Missing:
- repair-plan model.
- repair planner.
- scoped patch contract.
- durable attempt chain.
- automatic invalidation of dependent compiled artifacts based on semantic dependency.
- re-QA gate record.

## 16. Target authority gaps

The target Studio will need a clear authority ordering that FlowKit does not currently model.

Examples requiring an Authority Map:

1. Canonical Entity identity vs scene-local description.
2. Canonical Reference vs state-specific variant.
3. Project/Production Profile style vs Scene directing choice.
4. Dramatic Scene intent vs Shot composition choice.
5. Continuity lock vs provider optimization.
6. Full Shot Spec vs provider-specific prompt constraints.
7. Script Lock vs downstream repair.
8. QA finding vs allowed repair scope.
9. User lock vs automated resolver/repair.

Current FlowKit resolves many such conflicts implicitly by string order, field preference, or procedural instruction. The target must make precedence explicit and inspectable.

## 17. Canonical target pipeline implied by the gap analysis

This is not yet an implementation task list. It is the conceptual dependency chain the canonical design documents need to validate.

Topic Intelligence
→ Niche Resolver
→ Brain Pack composition
→ Active Production Profile
→ Idea
→ Logline
→ Premise
→ Angle
→ Theme
→ Research Intelligence
→ Research-to-Story Material
→ Character Psychology / Relationships / Knowledge / Belief
→ Conflict / Stakes
→ Causal StoryGraph
→ MacroStoryBeat
→ Sequence
→ Dramatic Scene
→ SceneDramaticBeat
→ AudienceExperienceTarget
→ Screenplay Realization
→ Story Critique / Targeted Story Repair
→ Script Lock
→ DirectingIntent
→ SceneSpatialDramaticContract
→ BlockingPlan
→ CinematographyObjective
→ Shot List
→ ShotEligibilityGate
→ Full Shot Spec
→ Entity/State/Continuity/Reference resolution
→ Shot IR
→ Compiler
→ Provider Router
→ Orchestrator
→ Generation
→ QA
→ Targeted Repair
→ recompile/regenerate/re-QA as required

## 18. What should remain below the Studio boundary

The following current FlowKit assets should remain execution infrastructure rather than become story authority:

- Flow batchexecute envelopes.
- CAPTCHA/browser bridge details.
- signed URL refresh.
- Flow operation polling.
- image/media UUID recovery.
- request retry mechanics.
- media result parsing.
- video frame extraction.
- provider subprocess invocation.

Story/directing/shot decisions should not know these transport details.

## 19. What current FlowKit concepts should not become target canonical concepts

1. character table name should not define the whole target Entity ontology.
2. project.story should not become the screenplay source of truth.
3. Scene should not remain both dramatic scene and shot/render unit.
4. parent_scene_id should not become the continuity ledger.
5. character_names should not be the only reference-selection contract.
6. prompt text should not be the Shot Spec.
7. material prefix concatenation should not be the compiler.
8. Request rows alone should not be the production DAG.
9. video review score should not be the only QA gate.
10. fix_guide prose should not be the Repair Plan.

## 20. Migration/reuse map

### Reuse directly or with extension

- FastAPI application shell.
- SQLite repository abstraction.
- Entity ID/link foundation.
- reference upload/media-ID lifecycle.
- Flow/Omni transport adapters.
- operation polling.
- result normalization.
- request queue.
- technical retry/recovery.
- operation resume.
- dashboard live event path.
- video reviewer.
- error taxonomy.

### Extract knowledge/policies from current implementation

- material/style rules.
- camera vocabulary and camera-guide heuristics.
- continuation/root heuristics.
- video audio/voice/negative prompt rules.
- entity reference composition rules.
- repair hints.
- provider wire/capability facts.

### Introduce as new canonical Studio domains

- Topic/Niche intelligence.
- Brain Packs.
- Active Production Profile.
- Story development artifacts.
- Character psychology and relation/knowledge/belief state.
- StoryGraph.
- narrative hierarchy.
- screenplay.
- directing/spatial/blocking/cinematography.
- shots.
- continuity ledger.
- versioned reference system.
- Shot IR.
- compiler.
- provider capability router.
- production DAG.
- cross-stage QA.
- targeted repair.
- locks/authority/version lineage.

## 21. Gap summary by architectural layer

### Intelligence layer — FOUNDATIONAL gap
FlowKit begins with user/agent-created story and scenes. The target needs explicit topic, niche, brain pack, story and research intelligence.

### Narrative layer — FOUNDATIONAL gap
There is no canonical story graph, beat hierarchy or screenplay model.

### Directing layer — FOUNDATIONAL gap
Camera knowledge exists as prose; directing contracts, blocking and cinematography objectives do not.

### Shot layer — FOUNDATIONAL gap
No formal shot model, gate, spec, decision trace or IR exists.

### Continuity layer — FOUNDATIONAL gap
Media chaining exists, but narrative state and continuity constraints do not.

### Compiler layer — FOUNDATIONAL gap
Useful prompt-building ingredients exist, but no deterministic compiler/IR architecture exists.

### Execution layer — MODERATE gap
This is FlowKit’s strongest area. Existing transport, queue, retry and resume code should be reused behind stronger orchestration/provider contracts.

### QA/Repair layer — MAJOR gap
Rendered video QA is substantive; persisted multi-stage QA and targeted repair are not yet present.

## 22. Design decisions that canonical documents must settle before implementation

1. Exact ownership boundaries between Project, ProductionProfile, StoryProject and ProductionRun.
2. Canonical hierarchy and IDs for Story → Beat → Sequence → Scene → SceneBeat → Shot.
3. Whether existing Video is a deliverable/timeline container or maps to another target concept.
4. Migration role of current Scene.
5. Entity taxonomy and relation to dramatic character state.
6. State snapshot/delta model.
7. continuity constraint types and evaluation timing.
8. ReferenceAsset/ReferenceBundle versioning and selection rules.
9. FIXED / INHERITED / VARIABLE authority model.
10. Shot IR schema.
11. compiler stages and immutable artifacts.
12. ProviderCapability schema and routing policy.
13. Orchestrator DAG/node/attempt/artifact contracts.
14. QA finding/evidence/gate contracts.
15. targeted repair scope and invalidation rules.
16. lock/version/authority precedence.
17. backward compatibility path for current FlowKit API/dashboard/skills.

## 23. Conclusion

The gap is asymmetric.

FlowKit already has substantial execution value:
- references,
- generation adapters,
- durable requests,
- retries,
- resume behavior,
- media persistence,
- video QA.

The target Studio is missing mostly above that layer:
- intelligence,
- story causality,
- dramatic hierarchy,
- directing,
- shots,
- narrative state/continuity,
- IR/compiler,
- durable QA/repair governance.

Therefore the correct design strategy is to build a canonical Studio intelligence and compilation architecture above the existing execution substrate, while carefully adapting the current Scene/persistence/provider boundaries rather than rewriting FlowKit wholesale.

The next design action is to import the canonical design documents and build an Authority Map that decides which document/contract owns each concept before implementation tasks are created.
