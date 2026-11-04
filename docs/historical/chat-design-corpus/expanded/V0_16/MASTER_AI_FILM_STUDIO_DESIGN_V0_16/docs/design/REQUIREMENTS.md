# REQUIREMENTS.md
# Initial Requirement Map — V0.1

**Status:** DRAFT  
**Current maturity:** L5.5 — Reviewed + Partial Hardening Evidence  
**Origin:** V0.1 requirement baseline; patched by later subsystem designs.  
**Notation:** MUST / SHOULD / COULD / WON'T

---

# 1. Functional Requirements

## FR-001 — Multi-entry ingest
**Priority:** MUST  
**Description:** Accept idea, outline, screenplay, or an existing structured project.  
**Input:** text/file/project state.  
**Output:** normalized source record.  
**Dependencies:** ingest adapters.  
**Failure cases:** unreadable file, unsupported format, partial extraction.  
**Acceptance:** source is versioned and traceable; unsupported content is reported without fabricating structure.

## FR-002 — Story causality model
**Priority:** MUST  
**Description:** Derive/maintain character objective, obstacle, causal chain, pressure changes, information flow, and payoff relationships.  
**Output:** story blueprint + unresolved gaps.  
**Acceptance:** major beats can explain why they exist and what changes.

## FR-003 — Film Bible
**Priority:** MUST  
**Description:** Persist project/world rules, characters, locations, timeline, visual DNA, and locked story facts.  
**Acceptance:** later stages consume versioned bible data instead of re-inventing facts.

## FR-004 — Narrative hierarchy
**Priority:** MUST  
**Description:** Canonical hierarchy:
`Story → Sequence → Scene → Beat → Shot`.  
**Acceptance:** every generated shot references a valid beat; every beat references scene; no dangling IDs.

## FR-005 — Beat contract
**Priority:** MUST  
**Fields:** summary, purpose, change, emotion/audience effect, information priority, state transition.  
**Acceptance:** beat is more specific than generic “advance story.”

## FR-006 — Shot contract
**Priority:** MUST  
**Description:** Shot is the generation unit.  
**Acceptance:** each shot contains duration, intent, state refs, cinematography decision, dependencies, and expected end state.

## FR-007 — 8-Layer ShotSpec
**Priority:** MUST  
**Layers:**
1. subject/identity;
2. state/wardrobe/props;
3. action/performance/emotion;
4. environment/blocking/space;
5. time/atmosphere;
6. camera/optics/composition;
7. lighting/color/style;
8. continuity/constraints.  
**Acceptance:** provider prompts are compiled from this contract.

## FR-008 — Cinematography decision engine
**Priority:** MUST  
**Description:** Choose visual grammar from narrative function + audience relation + blocking + information order.  
**Acceptance:** every major camera decision has a `decision_basis`.

## FR-009 — Entity Registry
**Priority:** MUST  
**Entities:** character/location/prop/visual asset/other typed entities.  
**Acceptance:** each entity has stable ID, type, version, description, reference state, and lifecycle.

## FR-010 — Reference Bible
**Priority:** MUST  
**Description:** Store canonical and variant reference views.  
**Acceptance:** reference roles and versions are explicit; approved refs cannot silently mutate.

## FR-011 — Reference Resolver
**Priority:** MUST  
**Description:** Select the minimal/best reference set per shot/provider.  
**Acceptance:** respects provider ref limit and assigns reference roles.

## FR-012 — State Engine
**Priority:** MUST  
**Description:** Persist story/visual state per shot.  
**State:** wardrobe, props, hair/makeup, injury, wetness, dirt, position, screen direction, weather, lighting sources, location, time.  
**Acceptance:** only approved end-state propagates.

## FR-013 — Spatial Baseline
**Priority:** SHOULD  
**Description:** Store location landmarks, entrances/exits, axes, marks, props, motivated lights.  
**Acceptance:** camera/blocking can be checked against same world state.

## FR-014 — Shot IR
**Priority:** MUST  
**Description:** Provider-neutral semantic intermediate representation between ShotSpec and provider requests.  
**Acceptance:** no provider-specific syntax is canonical story data.

## FR-015 — Static compiler
**Priority:** MUST  
**Description:** Compile Shot IR into still-image request + reference bindings.  
**Acceptance:** cannot bypass project/entity/state locks.

## FR-016 — Motion compiler
**Priority:** MUST  
**Description:** Compile approved static + action/camera/environment deltas into temporal request.  
**Acceptance:** static state and temporal change are separate.

## FR-017 — Provider capability registry
**Priority:** MUST  
**Description:** Version provider/model support for refs, ratios, duration, resolution, generation modes.  
**Acceptance:** unsupported capability blocks or adapts explicitly.

## FR-018 — Provider adapters
**Priority:** MUST  
**Description:** Uniform adapter boundary for Flow/Veo/WAN/Seedance/Kling/etc.  
**Acceptance:** provider transport failures use stable error taxonomy.

## FR-019 — Durable generation jobs
**Priority:** MUST  
**Fields:** request, shot, provider, status, attempt, idempotency, dependency IDs, provider job ID, cost, error, artifacts.  
**Acceptance:** restart cannot lose submitted job state.

## FR-020 — Dependency graph
**Priority:** MUST  
**Edge types:** ROOT, CONTINUATION, INSERT, BRANCH.  
**Acceptance:** child jobs do not execute before required parent artifacts are approved.

## FR-021 — Wave execution
**Priority:** MUST  
**Description:** independent nodes parallelize; dependent nodes wait.  
**Acceptance:** dependency correctness preserved under concurrency.

## FR-022 — Retry/timeout/cancel/resume
**Priority:** MUST  
**Acceptance:** each provider call has explicit retryability, timeout, cancellation and resume semantics.

## FR-023 — Selective invalidation
**Priority:** MUST  
**Description:** changes invalidate only affected descendants/artifacts.  
**Acceptance:** unrelated approved shots remain valid.

## FR-024 — Static QA
**Priority:** MUST  
**Dimensions:** technical, identity, state, props, location, camera, composition, lighting/style, continuity, narrative intent.  
**Acceptance:** generation success is not acceptance.

## FR-025 — Video QA
**Priority:** MUST  
**Dimensions:** character consistency, prompt adherence, motion quality, temporal coherence, composition, state transition, narrative intent.  
**Acceptance:** start/end state compliance is checked.

## FR-026 — Sequence QA
**Priority:** MUST for long-form; SHOULD for short-form  
**Description:** check rhythm, information order, shot-size repetition, continuity, progression, monotony.  
**Acceptance:** a sequence can fail even if all shots individually pass.

## FR-027 — Targeted Repair
**Priority:** MUST  
**Description:** map defect to earliest responsible layer, preserve accepted layers, regenerate only affected artifacts.  
**Acceptance:** RepairPlan records preserve/patch/invalidate/recheck.

## FR-028 — Artifact lineage
**Priority:** MUST  
**Trace:** artifact → generation attempt → compiled request → Shot IR → ShotSpec → beat → scene → sequence → story version + refs/state/compiler/provider versions.  
**Acceptance:** every accepted artifact is traceable.

## FR-029 — Approval/lock workflow
**Priority:** MUST  
**States:** draft/review/approved/locked/revision-required.  
**Acceptance:** locked facts cannot silently change.

## FR-030 — Restart-safe workflow
**Priority:** MUST  
**Acceptance:** app/server restart resumes exact incomplete stage/job.

## FR-031 — Editorial handoff
**Priority:** SHOULD  
**Description:** non-destructive selected takes, in/out points, audio tracks, export manifest.  
**Acceptance:** accepted generation artifacts can be assembled/exported without destroying lineage.

## FR-032 — Optional 3D previs
**Priority:** COULD  
**Use when:** action/spatial complexity requires it.  
**WON'T:** make 3D mandatory for every shot.

---

# 2. Non-functional Requirements

## NFR-001 — Provider independence
Canonical domain must not import provider-specific semantics.

## NFR-002 — Durable state
Critical production state MUST be persisted; chat or RAM cannot be authoritative.

## NFR-003 — Idempotency
Duplicate submission MUST not unintentionally create duplicate paid jobs.

## NFR-004 — Deterministic validation
Schema and cross-reference validation MUST occur before paid generation.

## NFR-005 — Recoverability
After crash/restart, no accepted decision or submitted provider job should be lost.

## NFR-006 — Observability
Every job and stage SHOULD expose status, timing, retries, errors, cost, lineage.

## NFR-007 — Maintainability
One responsibility must have one authority. Duplicate story/camera/prompt masters are prohibited.

## NFR-008 — Extensibility
Adding a provider SHOULD not require changing Story/Beat/Shot domain schemas.

## NFR-009 — Long-form scale
Architecture MUST support hundreds of shots without loading entire project state into one prompt/context.

## NFR-010 — Testability
Core state transitions and contracts MUST be testable without real providers.

---


## NFR-011 — Evidence provenance
**Priority:** MUST  
Every maturity-critical proof must be stored as an identifiable evidence artifact with explicit supported claims, limitations, environment and integrity hash.

## NFR-012 — Evidence-class gate closure
**Priority:** MUST  
A design gate must not close from an evidence class weaker than the class required by that gate.

---

# 3. Security Requirements

## SEC-001
Secrets MUST NOT be persisted in project files or prompts.

## SEC-002
Provider credentials MUST be isolated behind adapter/config boundaries.

## SEC-003
Logs MUST redact secrets/tokens/cookies.

## SEC-004
Filesystem imports MUST defend against path traversal.

## SEC-005
Plugin/provider adapters MUST have explicit permission boundaries.

## SEC-006
External reference/project import MUST not automatically execute embedded commands/scripts.

---

## SEC-007 — Renderer secret denial
**Priority:** MUST  
Renderer must not expose an API that returns decrypted provider credentials.

## SEC-008 — Scoped credential use
**Priority:** MUST  
Credential use must be authorized by trusted caller identity, provider, operation and credential version.

## SEC-009 — Credential lease lifecycle
**Priority:** MUST  
Ephemeral credential leases must be bounded by TTL/single-use/session/version rules and revoked on utility-process exit where applicable.

## SEC-010 — Project export excludes credential vault
**Priority:** MUST  
Project backup/export contains credential references only, not the machine/user credential vault.

## SEC-011 — Secret redaction invariant
**Priority:** MUST  
Secrets must be redacted before all durable log/telemetry sinks, including debug mode.

---

# 4. Reliability Requirements

## REL-001
Technical completion and creative acceptance are separate states.

## REL-002
Unknown provider result after timeout MUST reconcile by provider job ID before resubmitting.

## REL-003
Parent artifact mutation MUST trigger selective descendant invalidation.

## REL-004
Database/state migration MUST be versioned and reversible or backed up.

## REL-005
Corrupt artifact metadata MUST not silently convert into accepted state.

---

## REL-006 — Ambiguous remote submit
**Priority:** MUST  
A side-effecting remote generation with uncertain acceptance must not be automatically resubmitted without provider-specific proof of safety.

## REL-007 — Provider recovery evidence
**Priority:** MUST  
Every shipping provider surface must have a versioned recovery profile describing handle retention, reconciliation methods, idempotency evidence and ambiguous-resubmit policy.

## REL-008 — Migration startup gate
**Priority:** MUST  
Scheduler/generation writes must remain disabled while schema migration is incomplete or the schema version is unsupported.

---


## REL-009 — Orthogonal job state authority
**Priority:** MUST  
Scheduler ownership, provider submission/recovery, artifact materialization and creative acceptance must be persisted as distinct state axes; approval semantics must not be duplicated into artifact materialization state.

---

## REL-010 — Single SQLite write ownership
**Priority:** MUST  
For the V1 local SQLite runtime, all mutating database commands must pass through one logical write owner / bounded write queue inside the Production Utility Process; provider-generation slots must not each own an independent SQLite writer connection.

---

# 5. Performance Requirements — Initial Assumptions

**ASSUMPTION P-001:** target operation is local-first/hybrid with multiple remote generation providers.

**ASSUMPTION P-002:** execution should eventually support up to 12 concurrent independent generation slots, subject to provider limits.

**ASSUMPTION P-003:** generation latency dominates local CPU work; orchestration must favor async I/O and provider-specific backpressure.

**OPEN:** concrete target throughput, RAM/GPU budgets, disk retention, and provider rate limits are not yet frozen.

---

## PERF-001 — Provider-safe hierarchical admission
**Priority:** MUST  
Scheduler admission must respect applicable global, provider, model, operation and local-resource limits.

## PERF-002 — Multi-project fairness
**Priority:** SHOULD  
Equal-priority ready work from one large project should not indefinitely starve other projects.

## PERF-003 — Budget admission
**Priority:** SHOULD  
Configured hard budgets must block new paid submissions before the side effect occurs; already-running work follows provider cancellation semantics.

---

# 6. UX Requirements

## UX-001
UI should expose narrative tree: Sequence → Scene → Beat → Shot.

## UX-002
User should not be forced to fill every canonical field manually; agent proposes, user approves/edits/locks.

## UX-003
Shot workspace should show:
- intent;
- cinematography;
- 8 layers;
- refs;
- state;
- static;
- motion;
- QA;
- repair history.

## UX-004
Failure messages must name responsible layer and actionable next step.

---

# 7. Data Requirements

Persistent data must include at minimum:

```text
projects
story_versions
sequences
scenes
beats
shots
shot_specs
shot_ir_versions
entities
entity_versions
reference_assets
state_snapshots
spatial_baselines
cinematography_decisions
compiled_requests
generation_jobs
artifacts
qa_results
repair_plans
dependency_edges
timelines
export_manifests
```

---

# 8. Integration Requirements

- screenplay import adapters;
- provider adapters;
- optional evaluation/metric engine;
- optional 3D previs;
- editorial export formats;
- future plugin boundary.

---

# 9. Deployment Requirements — Not Frozen

Candidate deployment:
- desktop/local-first UI;
- local durable database;
- local orchestration process;
- remote provider APIs;
- optional local model adapters.

Final decision requires security, update, packaging, and recovery review.

---

# 6. Story Intelligence Requirements — V0.16 Addendum

## FR-033 — Premise Lab
**Priority:** MUST  
Generate/compare structured premise candidates from modular character/situation/pressure/stakes/theme inputs.  
**Acceptance:** a selected premise expresses dramatic pressure, consequential stakes and transformation/question potential; a topic-only statement cannot pass as a premise.

## FR-034 — Angle Lab
**Priority:** MUST  
Generate and compare distinct narrative lenses for the same source topic/premise.  
**Acceptance:** selected angle records focal lens, central question, information advantage, emotional access, research/visual potential and risks.

## FR-035 — Theme System
**Priority:** MUST  
Represent thematic question/value tension/working argument/counterargument without requiring didactic dialogue.  
**Acceptance:** theme is traceable to character choices/consequences and can remain intentionally ambiguous.

## FR-036 — Research Intelligence
**Priority:** MUST when project research mode requires it  
Plan perspective-aware research, preserve sources, extract atomic claims, surface contradiction/qualification and record unresolved gaps.  
**Acceptance:** a factual story claim can trace to evidence or explicit unresolved status; contradictions are not silently erased.

## FR-037 — Research-to-Story-Material Transformation
**Priority:** MUST for research-backed projects  
Transform accepted evidence into concrete human detail, conflict sources, setting/prop detail, character pressure and scene opportunities while preserving provenance.  
**Acceptance:** raw facts do not enter screenplay planning without a stated story function when research mode is active.

## FR-038 — Dynamic Brain Resolver
**Priority:** MUST  
Resolve versioned Domain/Genre/Audience/Format/Platform/Craft Brain Packs into effective policy for a project.  
**Acceptance:** packs are data-driven/advisory and cannot override locked project facts; conflicts are explicitly resolved.

## FR-039 — Character Psychology Model
**Priority:** MUST for character-led narrative  
Represent want, need, fear, values, contradictions, defenses, secrets, tactics, voice registers and arc hypothesis at appropriate depth.  
**Acceptance:** major character decisions can reference intelligible motivation rather than plot convenience alone.

## FR-040 — Character Knowledge & Relationship State
**Priority:** MUST  
Track what characters know/believe/suspect/misunderstand/hide and current relationship pressure/state.  
**Acceptance:** dialogue/action cannot depend on knowledge a character has not acquired unless explicitly justified.

## FR-041 — Conflict & Stakes Model
**Priority:** MUST  
Represent incompatible objectives, opposition forces, leverage, escalation and practical/relational/identity/irreversible stakes as applicable.  
**Acceptance:** major turns identify what became harder, riskier or unavailable.

## FR-042 — Causal StoryGraph
**Priority:** MUST  
Maintain events/decisions/revelations/reversals/setups/payoffs/state changes with typed causal/motivational edges.  
**Acceptance:** major beats answer why-now/why-this-character/what-changes/what-it-enables; unexplained causal gaps are surfaced.

## FR-043 — Emotional Arc
**Priority:** MUST for narrative formats where emotion is a target  
Maintain long-horizon emotional/value-state progression separately from local tension.  
**Acceptance:** major emotional turns have a story cause and an observable consequence.

## FR-044 — Emotional Rhythm / Tension
**Priority:** MUST for narrative formats where pacing is material  
Represent local intensity/tension/release and detect candidate flatlines, whiplash, missing breathing room and repeated emotional function.  
**Acceptance:** numeric curves remain advisory and cannot override causal/scene defects.

## FR-045 — Scene State-Change Contract
**Priority:** MUST  
A Scene owns start state, objective, opposition, escalation, turn, key change, audience effect and end state.  
**Acceptance:** `START_STATE != END_STATE` on at least one meaningful dramatic dimension, unless an explicit accepted static-scene exception exists.

## FR-046 — Beat Microchange Contract
**Priority:** MUST  
A Beat records intention → action/tactic → reaction → resistance/new information → micro-change.  
**Acceptance:** consecutive beats cannot silently repeat identical tactic/effect without intentional justification.

## FR-047 — Dialogue / Subtext Intent
**Priority:** MUST for dialogue scenes  
Dialogue generation consumes objectives, relationship state, knowledge asymmetry, tactic, voice register and hidden/surface intent.  
**Acceptance:** spoken lines cannot violate knowledge constraints; subtext is available where dramatically appropriate but not forced universally.

## FR-048 — Setup / Payoff Ledger
**Priority:** MUST  
Track plants/promises/questions/objects/skills/motifs through reinforcement/escalation/payoff/consequence or intentional openness.  
**Acceptance:** critical promised setups cannot disappear accidentally; payoff can trace to setup lineage.

## FR-049 — Independent Critique Council
**Priority:** MUST  
Run specialized, separable critique roles for relevant dimensions rather than one monolithic self-review.  
**Acceptance:** findings include location/evidence/severity/root-layer hypothesis; hollow PASS outputs are detectable.

## FR-050 — Story Quality Gate
**Priority:** MUST  
Combine deterministic checks, specialist semantic critique, blocking severity and advisory balanced scores.  
**Acceptance:** BLOCKING story defects cannot be averaged into PASS by stronger unrelated dimensions.

## FR-051 — Targeted Story Repair
**Priority:** MUST  
Diagnose earliest responsible story layer and repair minimal scope while preserving accepted content.  
**Acceptance:** repair plan records preserve/patch/invalidate/recheck; repeated local failure escalates upstream.

## FR-052 — Script Lock Manifest
**Priority:** MUST  
Lock a specific screenplay/story version only after required Story Quality and research/continuity/setup-payoff gates are satisfied/accepted.  
**Acceptance:** lock writes version/hash/critique/evidence snapshots and downstream Directing binds to that version.

## NFR-013 — Third-party donor isolation
Third-party story repositories MUST enter through license review + adapter/port/pattern boundary; no donor may become competing canonical story authority.

## NFR-014 — Data-driven Brain Packs
Domain/genre/audience/format/platform/craft specialization SHOULD be versioned data/policy where practical rather than forked engine code.

## NFR-015 — Critique independence
Critical creative acceptance SHOULD support blinded/specialized review and MUST distinguish writer output from reviewer evidence; same-model self-signoff is weaker evidence than independent/diverse review.

## NFR-016 — Evidence-grounded factual storytelling
For research-backed modes, factual propositions MUST retain provenance/status/uncertainty through research→story-material→script stages; retrieval or LLM synthesis cannot self-promote to locked fact.

