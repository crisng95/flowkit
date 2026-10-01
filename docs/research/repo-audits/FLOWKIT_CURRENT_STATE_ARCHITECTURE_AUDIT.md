# FLOWKIT CURRENT STATE ARCHITECTURE AUDIT

## 0. Scope and evidence rule

This document records the repository state observed at HEAD d7977fd51b87d4da2a25a05b896f5cdac064e030 on branch main during the DISCOVERY / CURRENT STATE AUDIT phase.

Scope restrictions for this audit:

- No feature code was changed.
- No dependency was installed.
- No build was run.
- No test suite was executed.
- No commit was created.
- Findings below come from reading implementation code, schemas, API models, UI types, extension code, skills, and test source.
- A test file being present is evidence of test coverage intent/source coverage, not evidence that the current checkout passes that test.

Classification vocabulary:

- KEEP — retain largely as-is.
- KEEP + EXTEND — retain the implementation as a foundation and add capabilities around it.
- ADAPT — reuse substantial code but change boundaries/contracts/semantics.
- EXTRACT — pull a useful capability out of its current coupled location.
- REWRITE — replace the internal model/implementation while preserving selected behavior.
- REPLACE — current repository has no adequate runtime subsystem; introduce a new subsystem.
- DROP — remove from the target architecture.

## 1. Repository identity

- Workspace: D:\FlowKit-Studio-Upgrade
- Git root: D:/FlowKit-Studio-Upgrade
- Branch: main
- HEAD: d7977fd51b87d4da2a25a05b896f5cdac064e030
- Remote: origin = https://github.com/crisng95/flowkit.git
- Runtime status at audit start: tracked upstream code unchanged; governance files created locally are untracked.

## 2. Root structure and manifests

Observed root source/runtime areas:

- agent/ — Python FastAPI server, SQLite persistence, SDK/domain models, generation services, worker, QA/review services.
- extension/ — Chrome Manifest V3 browser bridge used to execute authenticated Google Flow requests in a signed-in browser tab.
- dashboard/ — React + TypeScript + Vite web dashboard.
- skills/ — procedural AI-agent workflow instructions and prompt/camera/pipeline guidance.
- tests/ — Python unit tests plus a Node-based MV3 extension bootstrap regression test.
- scripts/ and tools/ — operational helpers.
- docs/ — existing project documentation.

Observed manifests/configuration:

- setup.py
- requirements.txt
- requirements-dev.txt
- pytest.ini
- dashboard/package.json
- dashboard/package-lock.json
- dashboard/tsconfig.json
- dashboard/vite.config.ts
- agent/models.json
- agent/providers.json
- extension/manifest.json

There is no root src/ directory.

There is no Electron runtime. No BrowserWindow, ipcMain, ipcRenderer, contextBridge, main/preload Electron entrypoint, or Electron package dependency was found. The desktop-adjacent surfaces are a local FastAPI server, Chrome extension, and browser dashboard.

## 3. Actual runtime topology

The current runtime is a local production bridge around Google Flow:

1. FastAPI starts in agent/main.py.
2. SQLite is initialized through agent/db/schema.py.
3. OperationService is initialized with FlowClient plus SQLiteRepository.
4. A WebSocket server waits for Chrome extension connections.
5. WorkerController starts a persistent request-processing loop.
6. The Chrome MV3 extension connects to the local WebSocket server.
7. FlowClient asks the extension to execute Flow batchexecute RPCs in an authenticated flow.google.com browser context.
8. Request and generation state is stored in SQLite.
9. Dashboard clients receive request/worker events through a separate FastAPI WebSocket.
10. Media generation results are normalized and written back to entity/scene state.

High-level data flow:

Project / Entity / Scene records
→ Request rows
→ Worker prerequisite and priority selection
→ OperationService
→ FlowClient
→ Chrome extension
→ flow.google.com batchexecute
→ normalized result
→ result_handler
→ SQLite scene/entity/request state
→ dashboard events

The runtime is therefore already a useful media-generation execution engine, but it is not yet an AI-native film-development system. Most pre-production story/directing intelligence exists only as procedural skill prose, not as typed, persisted production state.

## 4. Server/backend

### 4.1 FastAPI application

Primary path: agent/main.py

Actual inputs:
- HTTP API requests.
- Browser-extension WebSocket messages.
- Dashboard WebSocket connections.
- Environment/configuration values.

Actual outputs:
- CRUD/API responses.
- health/status responses.
- generation/review endpoints.
- WebSocket events.
- lifecycle startup/shutdown of DB, extension WS server, and worker.

Owned state:
- Process-local extension connection registry through FlowClient.
- Process-local dashboard EventBus subscribers.
- WorkerController lifecycle.

Dependencies:
- FastAPI, websockets, SQLite, SDK services, API routers, FlowClient, worker.

Assessment: KEEP + EXTEND.

Reason:
The server composition is clean enough to remain the application shell. Studio intelligence should be added as new domain/application modules rather than replacing the FastAPI bootstrap.

### 4.2 Browser transport bridge

Primary paths:
- extension/manifest.json
- extension/background.js
- extension/content.js
- extension/injected.js
- agent/services/flow_client.py
- agent/services/flow_batch.py

Actual input:
- normalized media-generation operations from the server.
- signed-in Flow browser session.
- project/media IDs, prompts, model family/options.
- CAPTCHA requests for generation calls.

Actual output:
- raw batchexecute payloads or narrowed response fragments.
- generated media IDs and signed media URLs.
- operation handles/status.

Owned state:
- extension WebSocket lifecycle.
- browser storage/connection metrics.
- Flow tab/session context.
- FlowClient pending futures and operation lookup caches.

Dependencies:
- Chrome MV3 APIs.
- flow.google.com page session.
- reCAPTCHA Enterprise.
- current captured Flow RPC contracts.

Assessment: KEEP + EXTEND.

Strength:
It isolates browser-authenticated transport from the rest of the application and reshapes current Flow payloads into stable downstream structures.

Weakness:
It is provider-specific and wire-contract-specific. Target Studio should not let Flow transport semantics leak into Story, Shot IR, Compiler, or Orchestrator domains.

## 5. Database and application state

### 5.1 SQLite persistence

Primary paths:
- agent/db/schema.py
- agent/db/crud.py
- agent/sdk/persistence/base.py
- agent/sdk/persistence/sqlite_repository.py

Current durable tables observed:

- project
- character
- material
- project_character
- video
- scene
- request

Important current state:

project:
- name, description, story string, language, material, audio flags, tier, status.

character:
- generic entity record despite the class/table name.
- entity_type supports character, location, creature, visual_asset, generic_troop, faction.
- description, image_prompt, voice_description, reference_image_url, media_id.

scene:
- prompt/image_prompt/video_prompt.
- entity-name list.
- parent_scene_id and chain_type.
- per-orientation image/video/upscale media IDs, URLs and statuses.
- transition_prompt.
- narrator_text.
- trim/duration.

request:
- generation operation type/status.
- links to project/video/scene/entity.
- external operation request_id.
- media/output/error.
- retry_count and next_retry_at fields.

Additional state:
- agent/api/active_project.py persists the selected project in agent/active_project.json with atomic temp-file replacement.
- FlowClient keeps non-durable connection and operation lookup caches.
- WorkerController keeps in-memory deferral/backoff maps.

Assessment: ADAPT.

Strength:
The repository abstraction and normalized CRUD boundary are reusable. SQLite is adequate as a local durable execution store.

Weakness:
The domain schema is far too coarse for Studio. There are no durable records for story development, story graph, beats, screenplay, directing intent, blocking, shots, shot IR, continuity ledger, decision trace, critique artifact, repair plan, authority/lock state, or provider capability resolution.

Studio conflict:
Current scene row simultaneously acts as narrative unit, prompt holder, render unit, media-state holder, and continuity-chain node. That conflation must not become the Studio canonical model.

## 6. Subsystem audit and classification

## 6.1 ENTITY — KEEP + EXTEND

Primary paths:
- agent/db/schema.py
- agent/models/character.py
- agent/sdk/models/character.py
- agent/api/characters.py
- agent/api/projects.py
- agent/sdk/services/media_resolver.py

Actual input:
- name.
- entity_type.
- visual description.
- optional voice description.
- optional reference URL/media ID.

Actual output:
- persisted entity record.
- slug.
- generated image_prompt/profile.
- reference media ID and URL.

Owned state:
- visual identity seed/profile.
- entity type.
- one current reference image/media ID.

Dependencies:
- Material registry.
- SQLiteRepository.
- Flow generation/upload.

Strengths:
- A single record already represents more than characters.
- Project↔entity many-to-many linking exists.
- slug/display-name lookup works for reference resolution.
- reference media lifecycle is integrated.

Weaknesses/missing:
- Class/table naming remains character-centric.
- No canonical identity version.
- No wardrobe/state variants.
- No relationship graph.
- No psychology/desire/need/fear/secret.
- No temporal state.
- No knowledge/belief state.
- No prop ownership/state.
- No reference bundle/version/authority.

Reuse:
Keep IDs, entity linking, reference-media integration, and generic entity-type idea. Extend into a formal Studio Entity system rather than cloning a second unrelated entity store.

## 6.2 REFERENCE — KEEP + EXTEND

Primary paths:
- agent/sdk/services/operations.py
- agent/sdk/services/media_resolver.py
- agent/services/flow_client.py
- agent/services/flow_batch.py
- agent/sdk/services/result_handler.py

Actual input:
- entity image prompt or existing reference URL.
- project ID.
- scene entity-name set.
- existing source media for edit.

Actual output:
- Flow media UUID.
- signed image URL.
- imageInputs/reference inputs for scene generation.

Owned state:
- character.media_id.
- character.reference_image_url.
- scene image media IDs.
- provider-side media identity.

Dependencies:
- Flow upload/generation.
- UUID extraction.
- project entity mapping.

Strengths:
- Missing refs block scene generation instead of silently degrading.
- UUID recovery/upload fallback exists.
- base-image and reference-image wire types are distinct.
- edit operations can combine base image with identity refs.

Weaknesses/missing:
- Only one current reference media ID per entity.
- No reference role taxonomy.
- No canonical reference sheet.
- No versioning, provenance, quality score, approval state, or validity window.
- No shot-specific reference selection trace.
- No immutable lock/reference contract.

Studio conflict:
The target requires references as explicit production assets selected by a resolver/compiler, not an implicit list derived only from character_names.

## 6.3 CONTINUITY — REWRITE

Reusable implementation to extract:
- parent_scene_id chain.
- ROOT / CONTINUATION / INSERT.
- source/base-image edit behavior.
- result cascade from image to video/upscale.
- parent end-frame updates.
- media re-upload recovery.

Primary paths:
- agent/services/scene_chain.py
- agent/sdk/services/operations.py
- agent/sdk/services/result_handler.py
- agent/models/scene.py
- agent/db/schema.py

Actual current continuity:
- image/media continuity.
- parent-child scene linkage.
- end-frame/start-frame bridging.
- entity reference reuse.

Missing:
- character physical state.
- wardrobe state.
- location/world state.
- prop state.
- injuries/damage.
- time/weather/light state.
- relationship/knowledge/belief state.
- causal continuity.
- continuity constraints at shot boundaries.
- continuity validation before compile/generation.

Verified contract inconsistency requiring design resolution:
- generate_scene_video treats the scene end_scene_media_id as an end-image input.
- result_handler updates the parent end_scene_media_id using the generated child image media ID.
- scene_chain.create_continuation_scene has a path that initializes a child's end_scene_media_id from the parent video media ID.
These semantics are not one coherent contract and should be separated into explicit fields/contracts in the target architecture.

Reason for REWRITE:
Media chaining should survive as an execution utility, but it cannot be the canonical Studio continuity model.

## 6.4 STORY — REWRITE

Primary current locations:
- project.story string in schema/models.
- skills/fk-create-project.md.
- skills/fk-research.md.
- procedural instructions in other skills.

Actual input:
- user-provided story/brief text.
- research gathered procedurally by an agent.

Actual output:
- one unstructured project.story value.
- manually/agent-authored scenes and prompts.

Owned durable state:
- only the story string.

Strength:
The system accepts a story and has procedural research guidance.

Missing:
- Idea.
- Logline.
- Premise.
- Angle.
- Theme.
- Character psychology.
- conflict/stakes.
- causal story graph.
- setup/payoff/reveal ledgers.
- macro beats/sequences.
- screenplay realization.
- script versions/locks.
- critique and targeted story repair.

Reason for REWRITE:
The target needs a first-class story domain, not additional prose conventions around project.story.

## 6.5 SCENE — ADAPT

Primary paths:
- agent/db/schema.py
- agent/models/scene.py
- agent/sdk/models/scene.py
- agent/api/scenes.py

Actual input:
- prompt.
- optional image_prompt/video_prompt/transition_prompt.
- entity names.
- chain linkage.
- display order.

Actual output:
- persisted renderable unit.
- image/video/upscale state for vertical/horizontal orientation.
- narration/trim data.

Owned state:
- both semantic prompt state and generation/media state.

Strengths:
- mutable via PATCH.
- ordered.
- supports insertion.
- supports parent chain.
- owns production media status.

Weakness:
It conflates dramatic scene, visual setup, shot, and generation job target.

Target adaptation:
Keep the current render/media scene concept only as a legacy execution projection or migrate it toward Shot/RenderUnit. Introduce a separate dramatic Scene entity with SceneDramaticBeat and directing contracts.

## 6.6 BEAT — REPLACE

Evidence:
- No MacroStoryBeat runtime type/table.
- No SceneDramaticBeat runtime type/table.
- Searching the repository finds only informal use of the word beat in skill prose, such as emotional beats.

Current I/O/state:
None as a runtime subsystem.

Target need:
- macro story beats.
- scene dramatic beats.
- beat purpose/turn/value change.
- causality and dependencies.
- audience target.
- beat→shot decomposition.

Reason for REPLACE:
There is no existing canonical beat model to extend.

## 6.7 SHOT — REPLACE

Evidence:
- No Shot table/model/domain object.
- Shot terminology exists in skills/fk-camera-guide.md and creative workflow prose.
- INSERT scenes are used as a practical way to create alternate camera views, but they remain Scene records.

Current input/output:
Camera and shot choices are encoded as free text inside prompt/video_prompt.

Missing:
- Shot List.
- ShotEligibilityGate.
- Full Shot Spec.
- lens/framing/angle/movement fields.
- subject/action/blocking bindings.
- continuity inputs/outputs.
- shot duration intent.
- ShotDecisionTrace.
- static vs motion prompt separation as typed output.
- Shot IR.

Reason for REPLACE:
A formal Shot domain must be introduced; current camera prose can be ingested as guidance/reference data.

## 6.8 PROMPT — REWRITE

Primary paths:
- agent/api/projects.py
- agent/materials.py
- agent/sdk/services/operations.py
- skills/fk-camera-guide.md
- skills/fk-create-project.md

Actual current prompt composition:
- entity image prompts are string-built from description + material + composition + lighting.
- scene creation prepends material.scene_prefix.
- continuation image prompts receive a generic hard-coded transformation instruction.
- video prompts are augmented with detected dialogue voice context, audio restrictions, and a hard-coded Negative clause.
- skill files tell the AI agent how to write camera/action text.

Strength:
There are useful production rules and a clear separation between entity ref prompts and scene actions.

Weakness:
This is string concatenation and procedural authoring, not a compiler.

Missing:
- typed prompt inputs.
- layer authority.
- FIXED / INHERITED / VARIABLE resolution.
- Shot IR.
- deterministic compile stages.
- provider-specific lowering.
- conflict resolution.
- provenance.
- compile diagnostics.
- decision trace.
- immutable compiled artifact/hash.

Reason for REWRITE:
Preserve useful prompt rules as compiler policies, but replace ad-hoc string assembly as the canonical prompt-generation architecture.

## 6.9 GENERATION — KEEP + EXTEND

Primary paths:
- agent/sdk/services/operations.py
- agent/services/flow_client.py
- agent/services/flow_batch.py
- agent/services/omni_flash.py
- agent/sdk/services/result_handler.py
- agent/api/flow.py

Actual input:
- prompts.
- project ID.
- source/base/reference media.
- orientation.
- model family/mode/duration/resolution for supported direct endpoints.

Actual output:
- media ID.
- URL.
- operation/workflow descriptors.
- normalized GenerationResult.
- updated scene/entity media state.

Strengths:
- current Flow batchexecute transport is isolated.
- image base/ref inputs are explicit at wire level.
- polling is normalized.
- multiple Omni modes are implemented.
- failures are surfaced rather than silently treated as success.
- result application cascades downstream invalidation.

Weakness:
Generation is still coupled to legacy Scene and Character models and does not consume a provider-neutral Shot IR/CompiledGenerationPlan.

Target:
Keep the transport/execution primitives; add provider-neutral generation contracts above them.

## 6.10 PROVIDER — ADAPT

Current provider concepts are split:

Generation providers:
- FlowClient / flow_batch.
- Omni Flash service.
- Veo paths within Flow.

QA model providers:
- agent/services/cli_providers.py.
- agent/providers.json.
- role video_review supports Claude/Codex/agy model/effort selection.

Strengths:
- CLI QA role resolution is already configurable.
- Flow/Omni capabilities are represented in code and models.json.
- unsupported migrated Flow features fail explicitly.

Weaknesses:
- no unified provider capability registry.
- no provider-neutral request contract.
- no router that selects based on shot requirements.
- generation and QA provider selection use different mechanisms.
- fallback/degradation decisions are service flags/endpoint choices, not compiled policy.
- no durable provider decision trace.

Target:
Adapt current adapters behind a ProviderRouter + CapabilityRegistry + provider-specific compiler/lowering layer.

## 6.11 QUEUE — KEEP + EXTEND

Primary paths:
- agent/worker/processor.py
- agent/api/requests.py
- agent/db/crud.py
- agent/sdk/services/queue.py

Actual input:
- request row with type, target IDs, orientation.

Actual output:
- PENDING / PROCESSING / COMPLETED / FAILED transitions.
- persisted result/error.
- dashboard events.

Owned state:
- durable request status/retry_count/external operation ID.
- process-local active/deferred/backoff maps.

Strengths:
- priority by operation dependency class.
- server-side concurrency limit.
- cooldown gate.
- prerequisite deferral.
- duplicate active request suppression.
- batch status.
- generation skip/idempotence behavior.

Missing:
- generic dependency DAG.
- job graph derived from Shot IR.
- durable dependency edges.
- production-stage artifact lineage.
- job lease/ownership.
- richer scheduling policy.
- per-provider concurrency/cost budget.
- deterministic resume cursor over a production plan.

Target:
Retain worker mechanics but lift them under a Studio Orchestrator that schedules explicit production-plan nodes.

## 6.12 RETRY — KEEP + EXTEND

Primary path: agent/worker/processor.py

Verified behavior:
- general bounded retry.
- exponential delay up to a cap.
- CAPTCHA-specific retry policy.
- extension disconnect retry without increment.
- not-found media recovery by re-upload.
- unsupported/configuration failures fail without pointless retry.
- Flow image transport also has a bounded transient retry for a captured error code.

Strength:
Failure classes are distinguished rather than blindly retried.

Weakness:
Some backoff/deferral timing is held in process memory even though request schema contains next_retry_at.
Repair retry and transport retry are not separated into explicit policies/artifacts.

Target:
Keep transport resilience, persist retry policy/next-attempt state, and separate technical retry from creative repair.

## 6.13 RESUME — KEEP + EXTEND

Primary paths:
- agent/worker/processor.py
- agent/sdk/services/operations.py
- request table.

Verified behavior:
- stale PROCESSING rows reset to PENDING on worker startup.
- external operation ID is persisted in request.request_id for video generation.
- an already-submitted operation is re-polled rather than resubmitted.
- GENERATE requests can skip already completed downstream state.

Strength:
This prevents duplicate paid renders in important cases and gives the current queue practical restart behavior.

Weakness:
- not a full persisted workflow checkpoint model.
- some provider lookup caches are in memory.
- deferred/backoff maps are in memory.
- skill-level pipeline stage progress is not a durable orchestration graph.
- QA/repair cycle state is not persisted.

Target:
Keep request-level resume primitives and add durable ProductionRun / PlanNode / Attempt / Artifact lineage.

## 6.14 PERSISTENCE — ADAPT

See Section 5.

Why ADAPT rather than rewrite:
The Repository abstraction, SQLite local-first model, migration approach, and normalized row/domain conversion are useful. The schema and domain objects must be expanded substantially, but the persistence boundary itself is worth keeping.

Required additions for Studio:
- concept/artifact versioning.
- authority/lock records.
- story hierarchy.
- directing contracts.
- shot hierarchy.
- state/continuity ledgers.
- reference versions/bundles.
- compiled IR.
- provider decisions.
- QA artifacts.
- repair plans and attempts.
- production-run DAG and lineage.

## 6.15 QA — KEEP + EXTEND

Primary paths:
- agent/services/video_reviewer.py
- agent/models/review.py
- agent/api/reviews.py
- agent/services/cli_providers.py

Actual input:
- completed scene video.
- scene prompt context.
- entity refs.
- review mode/orientation.
- selected QA provider role.

Actual output:
- dimensions: character_consistency, prompt_adherence, motion_quality, visual_fidelity, temporal_coherence, composition.
- structured errors with severity.
- usable segments.
- overall score/verdict.
- textual fix guide.

Strengths:
- extracts/analyzes actual frames.
- refuses completely missing dimension output instead of fabricating a plausible score.
- critical errors influence scoring.
- provider role is pinned for a whole review.
- supports SDK or CLI analysis path.

Weaknesses:
- review results are returned, not durably modeled as QA artifacts.
- QA is mostly rendered-video QA, not story/script/directing/shot/compiler QA.
- no requirement-to-evidence trace.
- no gate artifact/lock integration.

Target:
Keep video QA engine and extend into stage-specific QA with persisted findings and explicit gates.

## 6.16 REPAIR — REWRITE

Current implementation is split:
- video_reviewer._fix_guide produces textual guidance.
- skills/fk-review-video.md and skills/fk-pipeline.md describe how an AI agent should patch prompts and regenerate.

Actual runtime output:
- guidance string only.
- no durable RepairPlan.
- no automatic targeted patch execution in reviewer backend.
- no persisted before/after evidence or repair lineage.

Strength:
Useful error taxonomy and practical fix heuristics exist.

Weakness:
Repair is procedural, external, and non-deterministic.

Target:
Create TargetedRepairPlan with source QA finding, target artifact, permitted mutation scope, patch decision, attempt number, result evidence, and acceptance gate.

## 7. Storyboard / Scene / Shot reality

Current repository does not have a separate storyboard domain.

The practical visual planning model is:

Project
→ Video
→ ordered Scene rows
→ prompt / image_prompt / video_prompt
→ image media
→ video media
→ optional upscale

Visual continuity and alternative angles are expressed through:
- ROOT / CONTINUATION / INSERT.
- parent_scene_id.
- image editing from a parent.
- transition_prompt.
- skill instructions for camera/shot language.

Therefore the current Scene is effectively a mixed unit containing pieces of:
- dramatic scene,
- storyboard card,
- shot,
- render request target,
- media artifact status.

That mixed role is the central modeling conflict with the target Studio hierarchy.

## 8. Prompt/compiler reality

There is no Studio prompt compiler.

Verified current mechanisms:
- Material preset adds scene/style strings.
- entity profile builder composes a reference prompt.
- continuation helper prepends transformation text.
- video prompt builder detects dialogue verbs and may append voice descriptors.
- project flags control audio restrictions.
- negative text is appended if absent.
- provider wire builders convert final text/media IDs into Flow RPC payloads.

These are useful compiler ingredients, but there is no intermediate representation and no explicit authority resolver.

Recommended reuse boundary:
- EXTRACT material/style policy.
- EXTRACT audio/negative policy.
- EXTRACT reference-resolution logic.
- KEEP provider wire builders below the compiler.
- REWRITE the layer above those pieces as Shot IR → Provider Compilation.

## 9. Provider integration reality

Generation:
- Flow batchexecute is the current authenticated transport.
- image generation/edit/upload/image upscale are implemented.
- Veo plain image-to-video is implemented.
- current Veo start+end, R2V, and video upscale are explicitly unsupported on the new batch path unless degraded behavior is enabled where possible.
- Omni Flash has current batch implementations for text-to-video, first-frame, first+last, and reference-to-video for supported durations/resolutions.

QA:
- video review has a role-based CLI provider abstraction with Claude/Codex/agy.

Architecture implication:
Provider integration code is valuable, but the current application has several provider entry points rather than one provider-neutral routing layer.

## 10. Queue / orchestration reality

Two orchestration layers currently coexist:

Runtime worker:
- durable request rows.
- priorities.
- prerequisites.
- concurrency/cooldown.
- retry/resume.
- result application.

Skill-level pipeline:
- procedural instructions for REFS → IMAGES → VIDEOS → REVIEW → optional UPSCALE/TTS/DOWNLOAD/CONCAT.
- procedural review/regen loops.

The runtime worker is code.
The broader production pipeline is mainly agent instruction.

Target Studio requires the latter to become explicit, persisted orchestration state instead of relying on an agent to remember stage transitions.

## 11. Tests — source audit only

Observed Python test functions by file:

- test_cli_providers.py: 75
- test_flow_batch.py: 53
- test_flow_batch_golden.py: 4
- test_flow_client_batch.py: 44
- test_models.py: 25
- test_omni_flash.py: 19
- test_operations.py: 19
- test_parsing.py: 31
- test_processor.py: 12
- test_result_handler.py: 14
- test_setup.py: 10
- test_video_reviewer.py: 17

Total observed pytest test functions: 323.

Additional:
- tests/extension_mv3_bootstrap.test.cjs is a standalone Node regression test for MV3 cold-start hydration/socket behavior.

Coverage themes verified from source:
- batchexecute envelope and wire positions.
- image/base/reference inputs.
- Flow transport response shaping and failures.
- Omni modes.
- operation polling and non-resubmission.
- entity/reference generation.
- queue wrappers.
- parsing/UUID recovery.
- worker retry/failure handling.
- result cascade.
- generated AGENTS behavior.
- video reviewer integrity and provider role pinning.
- extension bootstrap lifecycle.

Not evidenced by current test source:
- Story domain because it does not exist.
- Beat/Shot domain because they do not exist.
- continuity ledger because it does not exist.
- Shot IR/compiler because they do not exist.
- persisted QA/repair lineage because it does not exist.
- end-to-end Studio architecture because it does not exist.

No tests were run in this phase, so this audit makes no passing-status claim.

## 12. Strongest reusable foundations

1. Browser-authenticated Flow transport boundary.
2. batchexecute wire adapter and response normalization.
3. entity-to-reference media lifecycle.
4. SQLite repository abstraction.
5. durable generation request records.
6. worker prerequisite/priority/concurrency mechanics.
7. technical retry/recovery.
8. operation-ID resume behavior.
9. result cascade.
10. video frame QA and structured error model.
11. dashboard live request-state visualization.
12. procedural camera/prompt knowledge in skills as donor material for formal policies.

## 13. Largest weaknesses / missing architecture

1. No formal story-development domain.
2. No StoryGraph / causal graph.
3. No MacroStoryBeat / Sequence / SceneDramaticBeat hierarchy.
4. No separate dramatic Scene versus render Shot.
5. No Shot model, shot eligibility gate, full shot spec, or decision trace.
6. No persistent directing/blocking/cinematography contracts.
7. No narrative/world state and continuity ledger.
8. Reference assets are single-current-value rather than versioned authority-bound bundles.
9. No Shot IR.
10. No deterministic prompt compiler or layer resolver.
11. No unified generation Provider Router/capability registry.
12. No persisted full production-plan DAG.
13. QA is render-video focused and non-persistent.
14. Repair is guidance/manual orchestration rather than a durable targeted-repair subsystem.
15. Current Scene object owns too many responsibilities.

## 14. Current subsystem disposition

| Subsystem | Classification | Core decision |
| --- | --- | --- |
| ENTITY | KEEP + EXTEND | Keep identity/link/reference foundation; add full Studio entity/state semantics. |
| REFERENCE | KEEP + EXTEND | Keep media lifecycle; add versioned reference assets, roles, locks and selection trace. |
| CONTINUITY | REWRITE | Preserve media-chain utilities but replace continuity semantics with explicit state/ledger contracts. |
| STORY | REWRITE | Replace single story string/procedural prose with structured story domain. |
| SCENE | ADAPT | Separate dramatic Scene from current render/media unit. |
| BEAT | REPLACE | Introduce first-class macro and scene beat models. |
| SHOT | REPLACE | Introduce first-class shot domain and shot planning. |
| PROMPT | REWRITE | Replace ad-hoc string assembly with Shot IR + deterministic compiler; keep useful policies. |
| GENERATION | KEEP + EXTEND | Keep current execution adapters and normalization beneath new contracts. |
| PROVIDER | ADAPT | Unify Flow/Omni/QA adapters behind capability-aware routing. |
| QUEUE | KEEP + EXTEND | Retain worker mechanics; schedule a persisted production DAG. |
| RETRY | KEEP + EXTEND | Retain technical retry; persist timing/policy and separate from creative repair. |
| RESUME | KEEP + EXTEND | Retain request/op resume; add run/node/artifact checkpoints. |
| PERSISTENCE | ADAPT | Keep repository/local SQLite foundation; expand schema/domain considerably. |
| QA | KEEP + EXTEND | Retain real rendered-video QA; add stage QA, persistence and gates. |
| REPAIR | REWRITE | Convert textual/manual repair into targeted, persisted repair plans and evidence. |

## 15. Architecture boundary recommended for the target Studio

Do not replace the whole FlowKit repository.

Preserve the execution substrate and put the Studio intelligence above it.

Recommended conceptual layers:

Studio Intelligence
- Niche / Topic / Brain Pack / Production Profile
- Story Development
- Story Graph / Beats / Screenplay
- Directing / Spatial / Blocking / Cinematography
- Shot Planning
- State / Continuity / References

Compilation
- Shot IR
- authority resolution
- provider-neutral generation plan
- provider-specific compiler/lowering

Execution
- Provider Router
- existing Flow/Omni adapters
- existing request worker expanded into Orchestrator
- persistence/artifact lineage

Quality
- current video reviewer as one QA adapter
- stage-specific QA
- targeted repair
- lock/release gates

This boundary maximizes reuse of the parts FlowKit already does well without forcing a film-studio ontology into the current overloaded Scene record.

## 16. Discovery conclusion

FlowKit is already a credible local media-execution and Google Flow integration substrate.

It is not yet a complete AI Film Studio architecture because story intelligence, directing state, shot planning, continuity semantics, compiler architecture, and durable QA/repair governance are not first-class runtime systems.

The correct next phase is not feature implementation. The next phase is to import the canonical target design documents, establish an authority map, resolve terminology and ownership, then derive contracts/dependencies before any implementation task is opened.
