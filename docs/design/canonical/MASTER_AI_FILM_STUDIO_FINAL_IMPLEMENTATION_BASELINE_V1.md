# MASTER AI FILM STUDIO FINAL IMPLEMENTATION BASELINE V1

**STATUS:** FROZEN IMPLEMENTATION BASELINE V1 ? DESIGN AUTHORITY

**Authority statement:** This document is the frozen V1 implementation-design authority after FINAL_MASTER_INDEPENDENT_AUDIT_V4 returned BLOCKER=0 and MAJOR=0. Runtime implementation, benchmark, packaged-product and release evidence remain separate claim classes under ADR-0015 and the evidence-governance rules.

**Historical corpus:** evidence/lineage only. Historical files are immutable and are not runtime/design authority when a stronger accepted source exists.

**Source hierarchy:**

```text
Accepted ADR decision
> resolved canonical primary source
> required supporting source
> evidence / lineage source
> historical source
```

Generated/runtime artifacts never override canonical design authority.

**Current implementation warning:** the existing FlowKit repository is a React/Vite + FastAPI + SQLite + Chrome MV3/Flow execution system. The Electron topology defined here is a TARGET architecture and MUST NOT be described as already implemented.

**Consolidation method:**

```text
SOURCE SELECTION
→ DEDUPLICATION
→ SUPERSESSION RESOLUTION
→ TERMINOLOGY NORMALIZATION
→ AUTHORITY RESOLUTION
→ CONTRADICTION RESOLUTION
→ CANONICAL CONSOLIDATION
→ TRACEABILITY PRESERVATION
```

---

# 00. Executive Architecture Summary

The Studio is a local-first, canonical-domain, modular production system for converting a project intent into a versioned, traceable, QA-governed film/video production.

Canonical top-level flow:

```text
PROJECT
→ ACTIVE PRODUCTION PROFILE
→ STORY CORE
→ MACRO STORY BEAT
→ SEQUENCE
→ SCENE
→ SCENE DRAMATIC BEAT
→ AUDIENCE EXPERIENCE TARGET
→ SCRIPT LOCK
→ DIRECTING INTENT
→ SCENE SPATIAL DRAMATIC CONTRACT
→ BLOCKING PLAN
→ CINEMATOGRAPHY OBJECTIVE
→ SHOT LIST ITEM
→ SHOT ELIGIBILITY GATE
→ FULL SHOT SPEC
→ SHOT IR
→ PROVIDER COMPILATION
→ GENERATION JOB
→ ARTIFACT
→ QA
→ APPROVAL
→ CANONICAL STATE COMMIT
```

The system is not a giant prompt and not a provider wrapper. Structured canonical contracts own truth. Prompts, provider requests and generated artifacts are derivatives.

Target execution topology:

```text
Renderer
↓ narrow contextBridge
Electron Main / Host Security Broker
↓ typed IPC / MessagePort
Production Utility Process
├─ canonical domain/application
├─ SQLite repository
├─ orchestrator
├─ production compiler
├─ provider adapters
├─ QA / repair
└─ artifact store
```

Current FlowKit remains an execution/reference/provider compatibility donor behind anti-corruption adapters.

---

# 01. Design Principles

1. One responsibility has one canonical authority.
2. Canonical truth is structured, versioned, provider-neutral and traceable.
3. Historical recency alone does not confer authority.
4. Prompt prose is not canonical state.
5. Generated media is not approved truth.
6. State, references and artifacts are separate concepts.
7. Dramatic authority must precede camera realization.
8. Provider integration occurs through adapters/capability profiles.
9. Failures are localized to the earliest responsible semantic layer.
10. Repairs preserve accepted unaffected decisions.
11. Paid-provider ambiguity is not a normal retry.
12. Evidence class must match the claim being closed.
13. Runtime implementation evidence is distinct from design authority.
14. Progressive complexity is allowed: simple projects may auto-create minimal wrappers but still use the same canonical identities.
15. FlowKit strengths are retained without importing FlowKit operational schemas upward as canonical Studio truth.

16. Every canonical component contract MUST declare or explicitly mark not-applicable for: PURPOSE, CANONICAL DEFINITION, OWNER, AUTHORITY, INPUTS, OUTPUTS, IDENTITY, PARENT/CHILD, STATE OWNERSHIP, MUTABILITY, VERSIONING, PROVENANCE, PERSISTENCE, INVARIANTS, DEPENDENCIES, INVALIDATION, FAILURE MODES, QA/GATES, LEGACY FLOWKIT MAPPING and IMPLEMENTATION IMPLICATIONS.
17. A shortened prose section in this Master does not waive those contract fields. If a local section does not restate INVALIDATION, VERSIONING, PERSISTENCE or FAILURE semantics, the canonical dependency/version/state rules in sections 62-63 and the owning domain contract apply and implementation MUST make the field explicit.

---

# 02. Authority / Truth Hierarchy

Canonical authority order:

```text
Accepted ADR / Canonical invariant
> locked Story / State / Profile authority
> accepted parent domain entity
> accepted child domain entity
> derived manifest / plan
> FullShotSpec
> ShotIR
> provider-specific compiled request
> generated artifact
> telemetry/event record
```

Important separations:

- Provider success != canonical truth.
- Artifact READY != creative APPROVED.
- Event log != current-state authority.
- Parent image != semantic continuity authority.
- Prompt != ShotIR.
- ShotIR != FullShotSpec.
- Manifest != canonical entity.
- FlowKit operational Scene != cinematic Scene.

Operational current-state authority lives in canonical repository rows; append-only events remain audit/observability evidence.

---

# 03. Canonical Terminology

- **Project:** durable production container and top-level ownership scope.
- **BrainPack:** versioned reusable knowledge/policy definition.
- **Profile Resolver:** sole resolver of pack inheritance/composition/precedence/conflicts.
- **ActiveProductionProfile:** immutable effective policy snapshot pinned to project/run/version.
- **StoryCore:** accepted core story truth.
- **MacroStoryBeat:** macro structural dramatic movement.
- **Sequence:** dramatic progression container under a MacroStoryBeat.
- **Scene:** canonical cinematic scene identity.
- **SceneDramaticBeat:** intra-scene intention/action/reaction/resistance/change unit.
- **AudienceExperienceTarget:** viewer-effect/information/tension/expectation authority.
- **DirectingIntent:** performance/reveal/staging intention.
- **SceneSpatialDramaticContract:** canonical dramatic spatial constraints.
- **BlockingPlan:** actor/object movement and spatial execution.
- **CinematographyObjective:** visual-language translation of dramatic/directing authority.
- **ShotListManifest:** ordered collection/projection of ShotListItems.
- **ShotListItem:** origin of canonical shot_id and basic shot purpose.
- **FullShotSpec:** complete production realization of the same shot_id.
- **ShotIR:** provider-neutral executable representation derived from canonical inputs.
- **CompiledRequest:** provider-specific derivative request.
- **StateSnapshot:** approved semantic state authority.
- **ReferenceAsset:** versioned conditioning/evidence asset, not identity truth.
- **Artifact:** produced bytes/media plus lineage/metadata.
- **QAResult:** evidence-bound quality result.
- **RepairPlan:** typed preserve/patch/invalidate/recheck plan.

Deprecated canonical term: generic persistent **Beat**.

---

# 04. System Boundaries

Canonical Studio domains:

```text
Project/Profile
Story Intelligence
Directing/Spatial/Cinematography
Shot Planning/Realization
Entity/Reference/State/Continuity
Compiler
Provider/Generation
Orchestration/Persistence/Artifact
QA/Repair/Approval
Editorial/Audio/Export
Security/Observability/Recovery
```

Boundary law: provider/runtime concerns may depend on canonical contracts; canonical Story/Shot/State domains MUST NOT depend on FlowKit/Google/provider-specific schemas.

---

# 05. Target Runtime Topology

**CURRENT FLOWKIT — evidence/current-state only**

```text
React/Vite Dashboard
→ FastAPI
→ SQLite
→ Worker
→ FlowClient
→ Chrome Extension
→ flow.google.com
```

**TARGET STUDIO — design only, not implemented evidence**

```text
Renderer
↓ narrow contextBridge
Electron Main / Host Security Broker
↓ typed IPC / MessagePort
Production Utility Process
├─ application/domain services
├─ SQLite repository
├─ orchestrator / scheduler
├─ Production Compiler
├─ Provider Registry / Router / Adapters
├─ QA / Repair
└─ Artifact Store
```

Long-running provider/network work and durable orchestration live outside the Renderer. Main owns privileged host/security capabilities. Production Utility owns canonical repository access and the single logical SQLite writer.

---

# 06. Project / Topic Intelligence

**PURPOSE:** normalize project intent before niche/story resolution.

**CANONICAL DEFINITION / OWNER:** Project domain owns project identity; Topic Intelligence owns normalized topic/classification output.  
**AUTHORITY:** Project locks and accepted canonical facts outrank soft classification preferences.  
**INPUTS:** raw topic, project goals, format/platform/audience hints, factuality mode.  
**OUTPUTS:** normalized topic, weighted topic labels, ambiguity set, constraints.  
**IDENTITY:** project_id; topic_resolution_id/version.  
**STATE / MUTABILITY:** candidate until accepted; accepted version immutable.  
**VERSIONING / PROVENANCE:** every Topic resolution records topic-normalizer/classifier rule versions, project/bootstrap input versions and source evidence. A final ActiveProductionProfile is never a prerequisite for Topic Intelligence.  
**PERSISTENCE:** canonical repository.  
**INVARIANTS:** topic != niche; multi-label is allowed; no provider-specific field becomes project truth.  
**DEPENDENCIES:** Project Input / Project Intent, user constraints, language/locale, target duration/platform/format hints, existing materials and source evidence only. Topic Intelligence MUST NOT depend on Profile Resolver or ActiveProductionProfile.  
**INVALIDATION:** accepted topic change invalidates dependent niche/profile/story artifacts.  
**FAILURE MODES:** ambiguous labels, unsupported factuality class, missing provenance.  
**QA/GATE:** ambiguity must be explicit rather than silently guessed.  
**LEGACY FLOWKIT:** project/material/provider flags are compatibility inputs only.  
**IMPLEMENTATION:** typed TopicResolution contract plus resolver service.

### FM-002 exact field-label normalization

**CANONICAL DEFINITION:** Project / Topic Intelligence is the provider/model-neutral canonical contract/service boundary defined by this section; it owns no authority beyond the scope stated here.

**OWNER:** The owner named by this section for Project / Topic Intelligence; combined owner/definition wording above is preserved and this line makes ownership explicit.

**STATE:** Use the section-specific lifecycle above; approved/locked versions are explicit and historical/superseded/invalidated versions remain auditable.

**MUTABILITY:** Approved/locked versions are immutable; semantic change creates a successor version or new evidence record.

**VERSION:** Explicit artifact/output or rule/evaluator version bound to exact input/source versions.

**PROVENANCE:** Exact parent/source IDs+versions, profile/rule/evaluator version where applicable, source refs and revision/resolution reason.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.

**IMPLEMENTATION IMPLICATION:** Implement Project / Topic Intelligence as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose/provider state.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 07. Domain / Niche / Genre Resolution

**PURPOSE:** resolve domain/niche/genre/audience/format/platform/factuality context.

**OWNER / AUTHORITY:** Domain/Niche/Genre Resolution owns topic-derived classification only. BrainPack Registry owns pack definitions; Profile Resolver later owns pack selection/composition/precedence/conflict resolution and effective policy.  
**INPUTS:** normalized topic + project constraints + registry metadata.  
**OUTPUTS:** weighted domain/niche/genre/audience/format/platform/factuality classifications plus classification/ambiguity trace. It does not emit the final effective pack stack.  
**IDENTITY:** niche_resolution_id/version.  
**MUTABILITY:** immutable once pinned into ActiveProductionProfile.  
**PROVENANCE:** each selected/omitted pack has reason and evidence.  
**INVARIANTS:** unknown niche is explicit; hybrid niches are allowed; no single-label forced collapse.  
**INVALIDATION:** changed resolution invalidates only profile-dependent downstream artifacts.  
**FAILURE:** incompatible hard packs, unresolved ambiguity, missing registry version.  
**QA:** conflict trace must be inspectable.  
**FLOWKIT MAPPING:** none canonical; legacy material/style values can seed resolution.

### FM-002 explicit contract completion

**CANONICAL DEFINITION:** The provider/model-neutral Domain / Niche / Genre Resolution contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Domain / Niche / Genre Resolution.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**IMPLEMENTATION IMPLICATION:** Implement Domain / Niche / Genre Resolution as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**OWNER:** The owner named by this section for Domain / Niche / Genre Resolution; combined owner/definition wording above is preserved and this line makes ownership explicit.

**AUTHORITY:** Domain / Niche / Genre Resolution owns only its declared output/decision scope; locked accepted upstream authority outranks it and downstream stages cannot rewrite that authority.

**FAILURE MODES:** The section-specific failure cases above plus stale-version reuse, provenance loss, schema/invariant violation, or Domain / Niche / Genre Resolution taking authority owned by another canonical layer.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 08. Composable BrainPack Architecture

**OWNER:** BrainPack Registry.

**CANONICAL PACK FAMILIES:** Knowledge, Creative, Story, Production Style, Audience, Format, Platform, QA/Rubric and other typed packs.

**INPUTS:** pack definition/version/parents/applicability/rules/provenance.  
**OUTPUTS:** immutable versioned pack definition.  
**IDENTITY:** pack_id + pack_version.  
**STATE:** DRAFT / VALIDATED / FROZEN / DEPRECATED as registry lifecycle, separate from downstream artifact state.  
**MUTABILITY:** published versions immutable.  
**AUTHORITY:** pack owns reusable rule definition only; it does not own resolved effective project policy.  
**INVARIANTS:** one registry; StoryBrainPack is specialization, not parallel registry; donor content cannot directly become canonical runtime authority without adaptation/validation.  
**INVALIDATION:** new pack version alone does not mutate pinned profile; re-resolution creates new ActiveProductionProfile.  
**FAILURE:** cycles, incompatible hard constraints, provenance/license absence.  
**QA:** schema + compatibility + policy validation.  
**LEGACY:** prompt-policy snippets are import candidates, not canonical pack state.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Composable BrainPack Architecture as already specified by this section; it must not absorb adjacent authority.

**CANONICAL DEFINITION:** The provider/model-neutral Composable BrainPack Architecture contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Composable BrainPack Architecture.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**IMPLEMENTATION IMPLICATION:** Implement Composable BrainPack Architecture as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**FAILURE MODES:** The section-specific failure cases above plus stale-version reuse, provenance loss, schema/invariant violation, or Composable BrainPack Architecture taking authority owned by another canonical layer.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 09. Profile Resolver

**OWNER:** Profile Resolver service.

**PURPOSE:** resolve inheritance, composition, conflicts, precedence and project overrides exactly once.

**INPUTS:** normalized Topic + accepted domain/niche/genre/audience/format/platform/factuality classification + BrainPack Registry definitions + project locks/constraints + canonical facts/invariants + requested overrides.  
**OUTPUTS:** ActiveProductionProfile + ResolutionTrace.  
**AUTHORITY PRECEDENCE:**

```text
locked canonical facts/invariants
> hard constraints
> allowed project locks/overrides
> inherited pack policy
> soft preferences
> local downstream intent where allowed
```

**IDENTITY:** resolver_version + resolution_id.  
**INVARIANTS:** hard > soft; project override is allowlisted; lower layers cannot break higher authority.  
**PROVENANCE:** every effective field stores source pack/version, precedence, override source and resolution reason.  
**INVALIDATION:** delta of effective fields feeds dependency-aware invalidation.  
**FAILURE:** unresolved hard-hard conflict => profile resolution FAIL, not silent last-write-wins.

### FM-002 explicit contract completion

**CANONICAL DEFINITION:** The provider/model-neutral Profile Resolver contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**STATE:** N/A for service runtime state ? persisted Profile Resolver outputs/evidence are immutable for exact input versions and have explicit current/stale/disposition evidence where applicable.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Profile Resolver.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**QA / GATE:** Schema + semantic invariant + source-version/provenance checks; any section-specific hard gate remains authoritative and blocking findings cannot be averaged away.

**IMPLEMENTATION IMPLICATION:** Implement Profile Resolver as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**AUTHORITY:** Profile Resolver owns only its declared output/decision scope; locked accepted upstream authority outranks it and downstream stages cannot rewrite that authority.

**FAILURE MODES:** The section-specific failure cases above plus stale-version reuse, provenance loss, schema/invariant violation, or Profile Resolver taking authority owned by another canonical layer.



### FM2-004 ? Acyclic bootstrap / profile-resolution order

**BOOTSTRAP INPUTS:** raw Project Input / Project Intent and source-supported bootstrap context feed Topic Intelligence before any effective profile exists.

**CANONICAL ORDERING:**
PROJECT INPUT / PROJECT INTENT
? TOPIC INTELLIGENCE
? DOMAIN / NICHE / GENRE / AUDIENCE / FORMAT / PLATFORM / FACTUALITY RESOLUTION
? BRAINPACK CANDIDATE SELECTION / COMPOSITION INPUTS
? PROFILE RESOLVER
? ACTIVE PRODUCTION PROFILE
? DOWNSTREAM STORY / PRODUCTION

**CYCLE PROHIBITION:** Topic Intelligence and classification MUST NOT read a final ActiveProductionProfile that they are contributing to create. Profile Resolver consumes their versioned outputs. Downstream systems consume the pinned ActiveProductionProfile and MUST NOT independently re-resolve packs.

**INVALIDATION DIRECTION:** accepted Topic/classification change may cause a new profile resolution; a new profile version then invalidates only dependent downstream artifacts. It does not retroactively become an input to the historical Topic resolution that produced it.

---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 10. ActiveProductionProfile

**OWNER:** profile domain; generated only by Profile Resolver.

**DEFINITION:** immutable effective policy snapshot pinned to a project/run/version.

**INPUTS:** Profile Resolver output.  
**OUTPUTS:** profile_id/version referenced by all downstream artifacts.  
**IDENTITY:** profile_id + profile_version + resolver_version.  
**MUTABILITY:** immutable; changes create a new version.  
**PERSISTENCE:** canonical repository with resolution trace/hash.  
**INVARIANTS:** downstream stages MUST NOT independently re-resolve packs.  
**DEPENDENCIES:** Project/Topic/Niche/BrainPack resolution.  
**INVALIDATION:** profile change selectively invalidates dependent research/story/directing/shot/compiler/QA artifacts.  
**QA:** profile completeness, provenance and unresolved-conflict gate.  
**LEGACY:** legacy flags are translated before resolution, never read directly downstream.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of ActiveProductionProfile as already specified by this section; it must not absorb adjacent authority.

**AUTHORITY:** ActiveProductionProfile owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by ActiveProductionProfile.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or ActiveProductionProfile silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement ActiveProductionProfile as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**CANONICAL DEFINITION:** ActiveProductionProfile is the provider/model-neutral canonical contract/service boundary defined by this section; it owns no authority beyond the scope stated here.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 11. Idea

**PURPOSE:** capture project-level creative proposition without prematurely becoming script truth.

**OWNER:** Story Intelligence.  
**INPUTS:** project/topic/profile/research seed.  
**OUTPUTS:** IdeaContract candidates.  
**IDENTITY:** idea_id/version.  
**STATE:** DRAFT / ACCEPTED / SUPERSEDED.  
**INVARIANTS:** idea is not screenplay; acceptance requires intent/scope/context.  
**INVALIDATION:** accepted Idea change invalidates Logline/StoryCore descendants.  
**QA:** premise potential, distinctness, policy/factuality compatibility.

### FM-002 explicit contract completion

**CANONICAL DEFINITION:** The provider/model-neutral Idea contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**AUTHORITY:** Idea owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Idea.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Idea silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Idea as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 12. Logline

**OWNER:** Story Intelligence.  
**DEFINITION:** concise causal dramatic statement derived from accepted idea, not a replacement for StoryCore.  
**INPUTS:** accepted Idea + profile/research constraints.  
**OUTPUTS:** logline_id/version.  
**INVARIANTS:** must encode protagonist/drive/conflict/stakes appropriate to format where applicable.  
**MUTABILITY:** versioned; approved value feeds StoryCore.  
**FAILURE:** vague premise-only slogan, contradiction with locked fact, unsupported factual claim.  
**QA:** causal clarity and promise consistency.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Logline as already specified by this section; it must not absorb adjacent authority.

**AUTHORITY:** Logline owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** The section's canonical output ID/version; it never allocates an ID belonging to an upstream or downstream canonical entity.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Logline.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Logline outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**IMPLEMENTATION IMPLICATION:** Implement Logline as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**CANONICAL DEFINITION:** Logline is the provider/model-neutral canonical contract/service boundary defined by this section; it owns no authority beyond the scope stated here.

**FAILURE MODES:** The section-specific failure cases above plus stale-version reuse, provenance loss, schema/invariant violation, or Logline taking authority owned by another canonical layer.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 13. Premise

**OWNER:** Premise Lab / Story Intelligence.  
**AUTHORITY:** accepted premise is a StoryCore input, subordinate to locked factual/canonical constraints.  
**INPUTS:** idea/logline/research/profile.  
**OUTPUTS:** PremiseCandidate → accepted premise version.  
**IDENTITY:** premise_id/version.  
**INVARIANTS:** premise must support causal development, not merely topic restatement.  
**QA:** novelty/clarity/conflict potential/research dependency gate.  
**INVALIDATION:** premise revision invalidates affected angle/theme/structure/story descendants.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Premise as already specified by this section; it must not absorb adjacent authority.

**CANONICAL DEFINITION:** The provider/model-neutral Premise contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Premise.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Premise silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Premise as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 14. Angle

**OWNER:** Angle Lab.  
**DEFINITION:** chosen perspective/approach separating how the story is told from what the topic is.  
**INPUTS:** premise + research perspectives + audience/profile.  
**OUTPUTS:** accepted angle_id/version.  
**INVARIANTS:** angle cannot falsify canonical evidence/facts.  
**QA:** differentiation, relevance, audience promise, factuality compatibility.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Angle as already specified by this section; it must not absorb adjacent authority.

**AUTHORITY:** Angle owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** The section's canonical output ID/version; it never allocates an ID belonging to an upstream or downstream canonical entity.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Angle.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Angle outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Angle silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Angle as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**CANONICAL DEFINITION:** Angle is the provider/model-neutral canonical contract/service boundary defined by this section; it owns no authority beyond the scope stated here.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 15. Theme

**OWNER:** Theme System.  
**DEFINITION:** thematic question/claim/hypothesis governing meaning, not a dialogue slogan.  
**INPUTS:** premise/angle/character/conflict/research.  
**OUTPUTS:** ThemeHypothesis version.  
**INVARIANTS:** theme guides selection but cannot force characters/events to violate causal truth.  
**QA:** recurrence/integration without didactic repetition.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Theme as already specified by this section; it must not absorb adjacent authority.

**AUTHORITY:** Theme owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** The section's canonical output ID/version; it never allocates an ID belonging to an upstream or downstream canonical entity.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Theme.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Theme outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Theme silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Theme as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**CANONICAL DEFINITION:** Theme is the provider/model-neutral canonical contract/service boundary defined by this section; it owns no authority beyond the scope stated here.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 16. Research Intelligence

**OWNER:** Story Research subsystem; Studio canonical evidence contracts own truth.

**INPUTS:** research brief, factuality class, topic/niche/profile, questions/perspectives.  
**OUTPUTS:** EvidenceClaims, source/provenance links, contradictions, confidence/scope.  
**IDENTITY:** research_brief_id; evidence_claim_id/version.  
**AUTHORITY:** external sources support claims; donor research frameworks are adapters/patterns, never canonical story stores.  
**INVARIANTS:** unsupported/disputed claims retain status and attribution.  
**FAILURE:** fabricated source, lost provenance, conflating opinion with fact.  
**QA:** evidence completeness/contradiction/factuality gate.  
**LEGACY:** FlowKit fact-check skill may be donor input only.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Research Intelligence as already specified by this section; it must not absorb adjacent authority.

**CANONICAL DEFINITION:** The provider/model-neutral Research Intelligence contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Research Intelligence.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Research Intelligence outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**IMPLEMENTATION IMPLICATION:** Implement Research Intelligence as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**FAILURE MODES:** The section-specific failure cases above plus stale-version reuse, provenance loss, schema/invariant violation, or Research Intelligence taking authority owned by another canonical layer.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 17. Research → Story Material

**OWNER:** Research-to-Story Material Transformer.

**PURPOSE:** convert evidence into usable pressure, detail, constraints, scene material and questions without turning source prose into script truth.

**INPUTS:** accepted EvidenceClaims + profile + story needs.  
**OUTPUTS:** StoryMaterial records with source links and allowed transformations.  
**INVARIANTS:** material retains evidence provenance; adaptation cannot silently change factual status.  
**INVALIDATION:** evidence revision invalidates dependent material and story artifacts using it.  
**QA:** source trace, relevance, no unsupported synthesis.

### FM-002 explicit contract completion

**CANONICAL DEFINITION:** The provider/model-neutral Research → Story Material contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**AUTHORITY:** Research → Story Material owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** N/A for the service runtime ? persisted Research → Story Material outputs carry their own ID/version or exact target/version binding.

**STATE:** N/A for service runtime state ? persisted Research → Story Material outputs/evidence are immutable for exact input versions and have explicit current/stale/disposition evidence where applicable.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Research → Story Material.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Research → Story Material silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Research → Story Material as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 18. Character Psychology

**OWNER:** Character Psychology Engine / Story domain.

**INPUTS:** StoryCore, profile, evidence/material, relationship context.  
**OUTPUTS:** CharacterModelVersion containing desire/need/fear/secret/values/decision style and format-required psychology.  
**IDENTITY:** character_id + model_version.  
**STATE:** canonical dramatic character state is separate from visual Entity/Reference identity.  
**INVARIANTS:** actions must be intelligible from information/belief/value state unless randomness is intentional.  
**INVALIDATION:** psychology revision invalidates dependent dialogue/conflict/beat decisions.  
**QA:** motivation coherence, contradiction checks, arc consistency.  
**LEGACY:** FlowKit visual character Entity is not full dramatic Character authority.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Character Psychology as already specified by this section; it must not absorb adjacent authority.

**CANONICAL DEFINITION:** The provider/model-neutral Character Psychology contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**AUTHORITY:** Character Psychology owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Character Psychology.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Character Psychology silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Character Psychology as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 19. Relationship State

**OWNER:** Story domain.  
**DEFINITION:** versioned relationship truth between canonical dramatic characters/entities.  
**INPUTS:** prior RelationshipState + scene/beat changes.  
**OUTPUTS:** relationship_state_id/version and deltas.  
**INVARIANTS:** relationship claims trace to causes/events; no silent reset between scenes.  
**PERSISTENCE:** canonical state/version table.  
**QA:** continuity and causal-change validation.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Relationship State as already specified by this section; it must not absorb adjacent authority.

**AUTHORITY:** Relationship State owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** The section's canonical output ID/version; it never allocates an ID belonging to an upstream or downstream canonical entity.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Relationship State.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Relationship State outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Relationship State silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Relationship State as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**CANONICAL DEFINITION:** Relationship State is the provider/model-neutral canonical contract/service boundary defined by this section; it owns no authority beyond the scope stated here.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 20. Knowledge / Belief State

**OWNER:** Story domain.

**DEFINITION:** distinct tracks for objective knowledge, perceived knowledge, belief/misbelief and audience knowledge where needed.

**INPUTS:** evidence/story events/reveals.  
**OUTPUTS:** CharacterKnowledgeState / belief state versions.  
**INVARIANTS:** character may not act on information never acquired unless explicitly motivated by inference/guess; objective truth != belief.  
**INVALIDATION:** reveal/order change invalidates affected downstream dialogue/beat/continuity.  
**QA:** information chronology and contradiction checks.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Knowledge / Belief State as already specified by this section; it must not absorb adjacent authority.

**AUTHORITY:** Knowledge / Belief State owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** The section's canonical output ID/version; it never allocates an ID belonging to an upstream or downstream canonical entity.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Knowledge / Belief State.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Knowledge / Belief State silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Knowledge / Belief State as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**CANONICAL DEFINITION:** Knowledge / Belief State is the provider/model-neutral canonical contract/service boundary defined by this section; it owns no authority beyond the scope stated here.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 21. Conflict / Stakes

**OWNER:** Conflict & Stakes Engine.

**INPUTS:** StoryCore, characters, relationships, theme, profile.  
**OUTPUTS:** ConflictModel + StakesModel.  
**IDENTITY:** conflict_id/version, stakes_id/version.  
**INVARIANTS:** conflict must produce resistance/change potential; stakes escalation must fit genre/scale.  
**DEPENDENCIES:** feeds StoryGraph/MacroStoryBeat/Sequence/Scene.  
**QA:** causal pressure, escalation, personal/external consequences.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Conflict / Stakes as already specified by this section; it must not absorb adjacent authority.

**CANONICAL DEFINITION:** The provider/model-neutral Conflict / Stakes contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**AUTHORITY:** Conflict / Stakes owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Conflict / Stakes.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**INVALIDATION:** A changed accepted source version marks dependent Conflict / Stakes outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Conflict / Stakes silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Conflict / Stakes as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.


---



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 22. Causal StoryGraph

**OWNER:** Story Structure/Causality subsystem.

**DEFINITION:** canonical causal graph of events, decisions, revelations, reversals, setup/payoff and state changes.

**INPUTS:** exact StoryCore DRAFT version + conflict/stakes + character decisions + research constraints. StoryGraph construction MUST NOT require an already locked/frozen StoryCore.  
**OUTPUTS:** graph nodes/edges with causes/consequences.  
**INVARIANTS:** major change answers "because of what prior event/decision?"; sequence ordering cannot substitute for causality.  
**PERSISTENCE:** typed nodes/edges, versions/provenance.  
**QA:** orphan cause/effect, cycles where illegal, missing consequence, causality gaps.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Causal StoryGraph as already specified by this section; it must not absorb adjacent authority.

**AUTHORITY:** Causal StoryGraph owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** The section's canonical output ID/version; it never allocates an ID belonging to an upstream or downstream canonical entity.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Causal StoryGraph.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Causal StoryGraph outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Causal StoryGraph silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Causal StoryGraph as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**CANONICAL DEFINITION:** Causal StoryGraph is the provider/model-neutral canonical contract/service boundary defined by this section; it owns no authority beyond the scope stated here.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.



### FM2-005 ? StoryCore / StoryGraph acyclic construction rule

**ORDERING:** StoryGraph is constructed from one exact StoryCore DRAFT version. Its causal-validation result is evidence used by the later StoryCore lock transition.

**PARENT / CHILD OR REFERENCES:** StoryGraph references story_core_id + draft version and the exact Conflict/Stakes/Character/Research versions it analyzed.

**CYCLE PROHIBITION:** StoryGraph MUST NOT require StoryCoreLock/FROZEN_FOR_STRUCTURE as an input. It consumes a draft version; the lock transition occurs only after causal validation.

**INVALIDATION:** changing the StoryCore draft version invalidates StoryGraph and causal-validation evidence derived from the old draft.

---



### FM3-001 ? V3 local implementation surface completion

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 23. Story Core Lock

**OWNER:** Story Intelligence.

**DEFINITION:** lock transition for the same canonical StoryCore identity. It freezes a validated successor version sufficiently for structural expansion; it does not create a second StoryCore object.

**INPUTS:** one exact StoryCore DRAFT version assembled from accepted Idea/Logline/Premise/Angle/Theme/Research plus core goal/question, conflict and stakes; matching StoryGraph causal-validation evidence may gate the lock but is not part of the locked StoryCore identity.  
**OUTPUTS:** story_core_id/version + lock manifest.  
**MUTABILITY:** locked version immutable; revision creates successor.  
**INVARIANTS:** lock is not final ScriptLock; it protects core story truth while allowing controlled structural realization.  
**INVALIDATION:** revised StoryCore invalidates dependent MacroStoryBeat/Sequence/Scene/Script/directing/shot artifacts by dependency graph.  
**QA:** contradiction/factuality/causality/core-goal gate.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Story Core Lock as already specified by this section; it must not absorb adjacent authority.

**AUTHORITY:** Story Core Lock owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** The section's canonical output ID/version; it never allocates an ID belonging to an upstream or downstream canonical entity.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Story Core Lock.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Story Core Lock silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Story Core Lock as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**CANONICAL DEFINITION:** Story Core Lock is the provider/model-neutral canonical contract/service boundary defined by this section; it owns no authority beyond the scope stated here.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.



### FM2-005 ? Two-phase lifecycle of one StoryCore identity

**CANONICAL IDENTITY RULE:** story_core_id is stable logical identity. DRAFT and FROZEN_FOR_STRUCTURE / locked realizations are versions of that same StoryCore, not parallel StoryCore authorities.

**DRAFT INPUT FIELDS:** accepted Logline, Premise, Angle, Theme hypothesis, core character goal/question, core conflict, core stakes, factual/research anchors and other already-accepted StoryCore facts.

**ORDERING:**
StoryCore DRAFT version
? Causal StoryGraph construction
? causal / structural validation
? StoryCore lock transition
? FROZEN_FOR_STRUCTURE successor version
? MacroBeatSheet / MacroStoryBeat structural expansion.

**LOCK PRECONDITIONS:** exact draft version is identified; required core fields are present; matching StoryGraph validation has no unresolved blocking causal defect; factual/canonical hard constraints remain satisfied.

**VERSION:** locking emits an immutable successor version of the same story_core_id bound to the exact draft and validation provenance. It MUST NOT mutate an already accepted/locked version in place.

**REOPEN / REVISION:** there is no in-place unlock. An approved revision creates a successor DRAFT version from the locked predecessor, then repeats graph validation and lock.

**FAILURE PATH:** causal validation failure leaves the candidate draft unlocked and routes repair to the earliest responsible Story layer. Structural expansion is blocked.

**INVALIDATION:** successor draft or core-fact revision invalidates old StoryGraph/lock evidence and all dependent structural descendants according to ?63. Historical locked versions remain auditable.

---



### FM3-001 ? V3 local implementation surface completion

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 24. StructureProfile

**PURPOSE:** define structure/budget/count-range policy, never narrative truth.  
**OWNER:** Profile/Story Structure policy.  
**INPUTS:** ActiveProductionProfile, format, duration, genre/niche.  
**OUTPUTS:** structure_profile_id/version, target ranges for macro beats/sequences/scenes/beats/duration.  
**IDENTITY:** immutable versioned policy artifact.  
**INVARIANTS:** fixed counts are profiles, not universal laws; profile cannot overwrite accepted StoryCore facts.  
**INVALIDATION:** profile change invalidates planning/budget projections, not locked truth unless revision is explicitly accepted.  
**QA:** range plausibility, format compatibility, no false precision.  
**LEGACY:** replaces ad-hoc shot/scene count assumptions.

### FM-002 explicit contract completion

**CANONICAL DEFINITION:** The provider/model-neutral StructureProfile contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**AUTHORITY:** StructureProfile owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by StructureProfile.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or StructureProfile silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement StructureProfile as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
## 24A. MacroBeatSheet ? structural manifest/projection

**PURPOSE:** Order and budget canonical MacroStoryBeat references for one StoryCore/StructureProfile expansion.

**CANONICAL DEFINITION:** MacroBeatSheet is an ordered structural manifest/projection of canonical macro_story_beat_id references. It does not own the narrative truth carried by MacroStoryBeat.

**OWNER:** Story Structure planning/projection layer.

**AUTHORITY:** Projection/order/budget only; StoryCore and MacroStoryBeat versions remain narrative authority.

**INPUTS:** locked StoryCore, StructureProfile, canonical/planned MacroStoryBeat IDs/versions and runtime budget.

**OUTPUTS:** ordered MacroStoryBeat references, budget/projection status and gate evidence.

**IDENTITY:** macro_beat_sheet_id/version.

**REFERENCES:** story_core_id/version; structure_profile_id/version; ordered macro_story_beat_id/version refs.

**STATE:** DRAFT / REVIEWED / APPROVED / SUPERSEDED / INVALIDATED.

**MUTABILITY:** approved manifest version is immutable; reordering/rebudgeting creates a successor manifest and does not create new MacroStoryBeat identity.

**VERSION:** explicit manifest version independent from referenced MacroStoryBeat versions.

**PROVENANCE:** parent/source versions, planner/profile version, ordering/budget rationale and gate evidence.

**PERSISTENCE:** Story planning repository; entries persist references/order/budget metadata, not duplicate MacroStoryBeat truth.

**DEPENDENCIES:** StoryCore, StructureProfile and referenced MacroStoryBeat versions.

**INVALIDATION:** source/profile/referenced-beat revision invalidates affected projection; order-only revision invalidates only order-dependent consumers when narrative truth is unchanged.

**FAILURE MODES:** duplicate/missing/orphan beat ref, budget overflow, projection copied as competing beat truth.

**QA / GATE:** Macro Structure Gate plus reference-integrity, order/coverage and budget checks.

**IMPLEMENTATION IMPLICATION:** store manifest header + ordered reference rows; resolve semantic beat content through MacroStoryBeat IDs.

**INVARIANT:** MacroBeatSheet != MacroStoryBeat truth.





### FM3-001 ? V3 nested-contract implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
## 24B. DurationBudget ? versioned planning allocation contract

**PURPOSE:** Allocate target runtime across macro structure, sequences, scenes, SceneDramaticBeats and ShotBudget without becoming narrative truth.
**CANONICAL DEFINITION:** DurationBudget is the explicit versioned planning artifact required by the Narrative Expansion Ladder for runtime allocation. It constrains planning; StoryCore/MacroStoryBeat/Sequence/Scene/SceneDramaticBeat remain narrative authority.
**OWNER:** Story Structure / Budget Planning.
**AUTHORITY:** budget allocation and tolerance only. It cannot invent, delete or rewrite narrative facts to make arithmetic fit.
**INPUTS:** target runtime, format, genre/niche, platform, pacing profile, dialogue density, action density, StructureProfile and pinned ActiveProductionProfile.
**OUTPUTS:** total_seconds plus versioned allocations for macro beats, sequences, scenes, scene-dramatic beats/micro-beats and shot budget.
**IDENTITY:** duration_budget_id + version. This is planning-artifact identity, never narrative entity identity.
**STATE:** DRAFT / REVIEWED / APPROVED / SUPERSEDED / INVALIDATED.
**MUTABILITY:** approved budget versions are immutable; changed target/runtime/allocation creates a successor version.
**VERSION:** explicit DurationBudget version bound to exact StructureProfile, ActiveProductionProfile and bootstrap/runtime inputs.
**PROVENANCE:** target-runtime source, format/platform/profile versions, allocator/rule version, tolerance policy and rationale.
**PERSISTENCE:** Story planning repository as typed budget metadata; no duplicated narrative payload.
**PARENT / CHILD OR REFERENCES:** references StructureProfile/profile inputs and allocation targets by canonical IDs/versions where they already exist.
**DEPENDENCIES:** StructureProfile, ActiveProductionProfile and exact planning inputs.
**ORDERING:** produced before dependent Sequence/Scene/Shot budget gates; may be recomputed only from a new accepted input version.
**CONCURRENCY / TRANSACTION BOUNDARY:** pure planning computation; persistence uses canonical repository/write-owner rules and performs no provider/network side effect in the write transaction.
**INVALIDATION:** target runtime, StructureProfile, effective pacing/profile or allocation-rule change invalidates dependent budgets/plans, not locked narrative truth.
**FAILURE MODES:** BUDGET_RUNTIME_OVERFLOW, missing input provenance, inconsistent parent/child allocation, fixed-count assumption treated as universal truth.
**RECOVERY:** recompute a successor budget version from pinned inputs after the responsible source is repaired; never mutate accepted narrative truth.
**QA / GATE:** SUM(child budgets) must reconcile to parent budget within configured tolerance from the governing profile/policy.
**OBSERVABILITY:** emit budget/version, exact inputs, tolerance, rationale, exceptions and gate result.
**IMPLEMENTATION IMPLICATION:** implement as typed versioned planning artifact/service; never bury authoritative runtime allocation only in prompt prose.
**TESTABILITY:** deterministic budget fixtures, tolerance-boundary, recomputation and selective-invalidation tests.
**LEGACY FLOWKIT MAPPING:** N/A ? FlowKit has no canonical narrative DurationBudget authority.
# 25. MacroStoryBeat

**OWNER:** Story Structure.  
**AUTHORITY:** ADR-0018.  
**DEFINITION:** first-class macro structural dramatic movement; never a camera unit.  
**INPUTS:** StoryCore, StoryGraph, Conflict/Stakes, StructureProfile.  
**OUTPUTS:** macro_story_beat_id/version with dramatic change, cause, consequence, role.  
**PARENT/CHILD:** StoryCore → MacroStoryBeat → Sequence.  
**INVARIANTS:** MacroStoryBeat != SceneDramaticBeat; no camera/lens/light fields.  
**QA:** structural necessity, causal linkage, non-redundancy.  
**INVALIDATION:** change invalidates child Sequences and descendants.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of MacroStoryBeat as already specified by this section; it must not absorb adjacent authority.

**IDENTITY:** The section's canonical output ID/version; it never allocates an ID belonging to an upstream or downstream canonical entity.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by MacroStoryBeat.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or MacroStoryBeat silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement MacroStoryBeat as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**CANONICAL DEFINITION:** MacroStoryBeat is the provider/model-neutral canonical contract/service boundary defined by this section; it owns no authority beyond the scope stated here.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 26. Sequence

**OWNER:** Story Structure.  
**DEFINITION:** canonical dramatic progression container under one or more macro structural obligations.  
**IDENTITY:** sequence_id/version.  
**INPUTS:** MacroStoryBeat, StructureProfile.  
**OUTPUTS:** ordered Scene IDs, sequence objective/escalation/turn.  
**INVARIANTS:** Sequence is truth; SequencePlan is a planning artifact only.  
**QA:** progression, escalation, coverage of macro obligation.  
**INVALIDATION:** accepted Sequence revision invalidates affected Scenes/descendants.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Sequence as already specified by this section; it must not absorb adjacent authority.

**AUTHORITY:** Sequence owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Sequence.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Sequence silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Sequence as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
## 26A. SceneListManifest ? scene-order projection

**PURPOSE:** Order canonical Scene references within accepted Sequence expansion.

**CANONICAL DEFINITION:** SceneListManifest is an ordered manifest/projection of canonical scene_id references. It is not a second Scene store.

**OWNER:** Story Scene planning/projection layer.

**AUTHORITY:** Order/planning/budget projection only; canonical Scene contracts own Scene truth.

**INPUTS:** accepted Sequence versions, StructureProfile/SceneBudget and canonical/planned Scene IDs/versions.

**OUTPUTS:** ordered Scene references, duration budget/projection status and gate evidence.

**IDENTITY:** scene_list_manifest_id/version.

**REFERENCES:** sequence plan/version where used; sequence_id/version; ordered scene_id/version refs.

**STATE:** DRAFT / REVIEWED / APPROVED / SUPERSEDED / INVALIDATED.

**MUTABILITY:** approved manifest immutable; reorder/rebudget creates successor and never changes Scene identity by itself.

**VERSION:** manifest version independent from Scene versions.

**PROVENANCE:** Sequence/StructureProfile/profile/planner versions, order/budget rationale and evidence.

**PERSISTENCE:** Story planning repository; reference/order rows only, no duplicate Scene truth.

**DEPENDENCIES:** Sequence, StructureProfile/SceneBudget and referenced Scene versions.

**INVALIDATION:** Sequence/referenced-Scene/budget revision invalidates affected projection; order-only change does not rewrite Scene truth.

**FAILURE MODES:** dangling/duplicate Scene refs, budget drift, manifest-as-Scene shadow truth, uncaused ordering.

**QA / GATE:** Scene Function/ordering/causality/budget/reference-integrity checks.

**IMPLEMENTATION IMPLICATION:** persist ordered Scene references and resolve content from canonical Scene repository.

**INVARIANT:** SceneListManifest != Scene truth.





### FM3-001 ? V3 nested-contract implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
## 26B. SequencePlan ? planning/projection contract

**PURPOSE:** Turn an approved MacroBeatSheet/StructureProfile into an ordered, budgeted plan for canonical Sequence realization.
**CANONICAL DEFINITION:** SequencePlan is a versioned planning/projection artifact. It does not own Sequence narrative truth. Accepted Sequence entities are canonical under ADR-0018.
**OWNER:** Story Structure planning layer.
**AUTHORITY:** order, target count, runtime budget, causality-planning evidence and projection only; MacroStoryBeat and Sequence own narrative truth.
**INPUTS:** StructureProfile, MacroBeatSheet, canonical MacroStoryBeat IDs/versions, DurationBudget and pinned ActiveProductionProfile.
**OUTPUTS:** sequence_plan_id/version, ordered Sequence references/planning entries, target_count, runtime_budget_seconds and Sequence Causality Gate evidence.
**IDENTITY:** sequence_plan_id + version, as explicitly defined by the post-V0.16 source.
**STATE:** DRAFT / REVIEWED / APPROVED / SUPERSEDED / INVALIDATED.
**MUTABILITY:** approved SequencePlan version is immutable. Reorder/rebudget/replan creates a successor plan version.
**VERSION:** explicit SequencePlan version independent from canonical Sequence versions.
**PROVENANCE:** beat_sheet_id/version, StructureProfile, DurationBudget, profile/planner version, ordering/causality rationale and gate evidence.
**PERSISTENCE:** Story planning repository. Persist plan header/order/references/budget metadata; do not duplicate canonical Sequence truth.
**PARENT / CHILD OR REFERENCES:** parent = MacroBeatSheet/StructureProfile; children = canonical Sequence IDs/versions once accepted. A draft planning entry may exist before Sequence acceptance but MUST NOT be exposed as canonical sequence_id truth.
**DEPENDENCIES:** MacroBeatSheet, MacroStoryBeat versions, StructureProfile, DurationBudget and ActiveProductionProfile.
**ORDERING:** Macro Structure Gate must pass before SequencePlan approval; canonical Sequence realization/acceptance follows the plan; Scene planning follows accepted Sequence versions.
**CONCURRENCY / TRANSACTION BOUNDARY:** planning-only computation; accepted plan/version write is repository-serialized and has no provider side effect.
**INVALIDATION:** MacroBeatSheet/MacroStoryBeat/StructureProfile/DurationBudget/profile change invalidates affected plan and downstream Sequence/Scene projections according to ?63.
**FAILURE MODES:** SEQUENCE_NO_TURN, SEQUENCE_NO_ESCALATION, SEQUENCE_CAUSAL_GAP, dangling MacroStoryBeat ref, budget drift, or plan content treated as a second Sequence truth.
**RECOVERY:** revise the plan or earliest responsible upstream artifact, emit successor plan version and re-run Sequence Causality Gate.
**QA / GATE:** opening-state continuity, purpose, escalation, major turn, closing-state change, next-sequence causal enablement and setup/payoff preservation.
**OBSERVABILITY:** emit plan/version, parent refs, budget, planner/rule version and causal-gate findings.
**IMPLEMENTATION IMPLICATION:** model SequencePlan separately from Sequence entities; accepted plan entries resolve to canonical Sequence IDs rather than storing competing Sequence truth.
**TESTABILITY:** order/reference integrity, causality fixtures, budget reconciliation, plan-only mutation vs Sequence identity tests.
**LEGACY FLOWKIT MAPPING:** N/A ? FlowKit operational Scene/request structures do not own canonical Sequence planning.


## 26C. SceneBudget ? versioned planning range contract

**PURPOSE:** Allocate justified Scene count/duration ranges per Sequence without creating Scene identity or narrative content.
**CANONICAL DEFINITION:** SceneBudget is a versioned planning artifact derived from runtime/structure/profile constraints; canonical Scene remains owned by Story Scene Engine.
**OWNER:** Story Structure / Scene Planning.
**AUTHORITY:** count/duration range and rationale only; no Scene identity or Scene truth ownership.
**INPUTS:** DurationBudget, StructureProfile, SequencePlan/accepted Sequence versions, runtime, average-scene-duration assumptions, genre/format/pacing/dialogue density and pinned ActiveProductionProfile.
**OUTPUTS:** scene_budget_id/version, total_scene_target min/preferred/max, per_sequence allocations, average_scene_seconds ranges and rationale.
**IDENTITY:** scene_budget_id + version. This is planning-artifact identity, not scene_id.
**STATE:** DRAFT / REVIEWED / APPROVED / SUPERSEDED / INVALIDATED.
**MUTABILITY:** approved versions immutable; changed allocation/range creates successor.
**VERSION:** explicit SceneBudget version bound to DurationBudget/StructureProfile/SequencePlan/profile versions.
**PROVENANCE:** allocator/rule version, assumptions, source versions, rationale and approved exception if any.
**PERSISTENCE:** Story planning repository as budget metadata; no Scene semantic payload.
**PARENT / CHILD OR REFERENCES:** references DurationBudget/StructureProfile/SequencePlan and per-Sequence canonical IDs; SceneListManifest consumes budget but owns only Scene ordering/projection.
**DEPENDENCIES:** DurationBudget, StructureProfile, SequencePlan/Sequence versions and ActiveProductionProfile.
**ORDERING:** SceneBudget is resolved before SceneListManifest approval; Scene creation/acceptance remains in canonical Scene domain.
**CONCURRENCY / TRANSACTION BOUNDARY:** pure planning calculation; repository write only, no provider/network side effect.
**INVALIDATION:** parent budget/profile/sequence-plan changes invalidate affected SceneBudget and dependent SceneListManifest planning, not existing locked Scene truth unless revision is explicitly accepted.
**FAILURE MODES:** BUDGET_SCENE_OVERFLOW, unjustified range, missing per-sequence allocation, false precision, or SceneBudget allocating canonical scene_id.
**RECOVERY:** recalculate successor budget after parent repair/change; preserve unrelated canonical Scenes.
**QA / GATE:** range plausibility, parent duration reconciliation, per-sequence coverage and explicit rationale for out-of-profile exceptions.
**OBSERVABILITY:** emit budget/version, assumptions, parent refs, rationale and exception/gate evidence.
**IMPLEMENTATION IMPLICATION:** typed budget artifact consumed by Scene planning; scene_id allocation remains solely with canonical Scene creation.
**TESTABILITY:** range/budget fixtures, out-of-profile tests, no-scene-identity ownership test and selective invalidation tests.
**LEGACY FLOWKIT MAPPING:** N/A ? legacy FlowKit scene count is not canonical SceneBudget authority.
# 27. Scene

**OWNER:** Story Scene Engine.  
**AUTHORITY:** ADR-0018.  
**DEFINITION:** canonical cinematic scene identity with location/time/context/objective/change; not FlowKit operational Scene.  
**IDENTITY:** scene_id/version.  
**PARENT/CHILD:** Sequence → Scene → SceneDramaticBeat.  
**INPUTS:** Sequence, StoryGraph, character/relationship/knowledge state.  
**OUTPUTS:** SceneContract/scene truth.  
**INVARIANTS:** scene must justify existence; static/no-change scenes require explicit atmosphere/setup/comedy/etc. purpose.  
**QA:** objective, opposition, turn/change, state delta.  
**LEGACY FLOWKIT:** operational scene maps downstream to shot/generation compatibility projection only.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Scene as already specified by this section; it must not absorb adjacent authority.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Scene.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Scene outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Scene silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Scene as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
## 27A. SceneBreakdownManifest ? SceneDramaticBeat breakdown projection

**PURPOSE:** Project one canonical Scene into an ordered SceneDramaticBeat breakdown plus scene-level planning metadata.

**CANONICAL DEFINITION:** SceneBreakdownManifest references canonical scene_dramatic_beat_id values and stores breakdown/order/budget/planning metadata; SceneDramaticBeat remains dramatic truth.

**OWNER:** Story Scene breakdown/planning layer.

**AUTHORITY:** Projection/order/budget only; Scene and SceneDramaticBeat own narrative truth.

**INPUTS:** canonical Scene version, current state/obligations, profile/budget policy and canonical/planned SceneDramaticBeat IDs/versions.

**OUTPUTS:** ordered beat refs, opening/closing planning state refs, duration budget and gate evidence.

**IDENTITY:** scene_breakdown_manifest_id/version.

**REFERENCES:** scene_id/version; ordered scene_dramatic_beat_id/version refs; relevant state/setup-payoff refs.

**STATE:** DRAFT / REVIEWED / APPROVED / SUPERSEDED / INVALIDATED.

**MUTABILITY:** approved manifest immutable; breakdown/order change creates successor and cannot silently mutate Beat truth.

**VERSION:** independent breakdown-manifest version.

**PROVENANCE:** Scene/state/profile/planner versions, ordering/budget rationale and gate evidence.

**PERSISTENCE:** Story planning repository; no duplicated beat semantic payload as authority.

**DEPENDENCIES:** Scene, referenced SceneDramaticBeats, state/setup-payoff refs and profile/budget policy.

**INVALIDATION:** Scene/Beat/state/profile change invalidates affected projection; manifest-only presentation change does not create new SceneDramaticBeat identity.

**FAILURE MODES:** dangling/duplicate Beat refs, breakdown drift, opening/closing state mismatch, manifest-as-Beat shadow truth.

**QA / GATE:** Beat Movement/scene-compression/reference/budget checks.

**IMPLEMENTATION IMPLICATION:** persist breakdown header + ordered Beat references/planning metadata; resolve dramatic content from SceneDramaticBeat repository.

**INVARIANT:** SceneBreakdownManifest != SceneDramaticBeat truth.



### FM3-001 ? V3 nested-contract implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 28. SceneSpatialDramaticContract

**OWNER:** Directing/Spatial domain under ADR-0019.  
**PURPOSE:** bind dramatic geography before blocking/camera.  
**INPUTS:** Scene, SceneDramaticBeat set, location/world state.  
**OUTPUTS:** spatial_contract_id/version with zones, anchors, sightlines, entrances/exits, constraints.  
**INVARIANTS:** spatial facts cannot be invented by camera layer; contract must preserve canonical location/state.  
**INVALIDATION:** location/state/beat change invalidates dependent BlockingPlan/Cinematography/Shot realization.

### FM-002 explicit contract completion

**CANONICAL DEFINITION:** The provider/model-neutral SceneSpatialDramaticContract contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**AUTHORITY:** SceneSpatialDramaticContract owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** The section's canonical output ID/version; it never allocates an ID belonging to an upstream or downstream canonical entity.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by SceneSpatialDramaticContract.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or SceneSpatialDramaticContract silently taking authority owned by an adjacent canonical layer.

**QA / GATE:** Schema + semantic invariant + source-version/provenance checks; any section-specific hard gate remains authoritative and blocking findings cannot be averaged away.

**IMPLEMENTATION IMPLICATION:** Implement SceneSpatialDramaticContract as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 29. SceneDramaticBeat

**OWNER:** Story Scene Dramatic Beat Engine.  
**AUTHORITY:** ADR-0018; consumed by ADR-0019.  
**DEFINITION:** intra-scene objective/action/reaction/resistance/reveal/microchange unit.  
**IDENTITY:** scene_dramatic_beat_id/version.  
**PARENT/CHILD:** Scene → SceneDramaticBeat → AudienceExperienceTarget → Shot lineage.  
**INVARIANTS:** no generic persistent Beat; every canonical shot binds to a SceneDramaticBeat.  
**QA:** movement/change, cause/effect, no duplicate microbeat.  
**INVALIDATION:** change invalidates dependent directing/shot artifacts.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of SceneDramaticBeat as already specified by this section; it must not absorb adjacent authority.

**INPUTS:** Accepted upstream artifacts/versions declared by the section and the pinned ActiveProductionProfile where policy is consumed; no hidden provider prompt is an authority input.

**OUTPUTS:** The typed SceneDramaticBeat result/record described by this section, with exact source-version bindings.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by SceneDramaticBeat.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or SceneDramaticBeat silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement SceneDramaticBeat as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**CANONICAL DEFINITION:** SceneDramaticBeat is the provider/model-neutral canonical contract/service boundary defined by this section; it owns no authority beyond the scope stated here.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 30. AudienceExperienceTarget

**OWNER:** Directing intent layer.  
**DEFINITION:** intended viewer effect: feel/understand/fear/expect/doubt/notice.  
**INPUTS:** SceneDramaticBeat + inherited Scene/Sequence/MacroStoryBeat/StoryCore.  
**OUTPUTS:** audience_experience_target_id/version.  
**INVARIANTS:** must be traceable to dramatic function; not a generic "cinematic" style request.  
**HARD GATE:** NO AUDIENCE EXPERIENCE TARGET → NO CINEMATOGRAPHY DECISION.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of AudienceExperienceTarget as already specified by this section; it must not absorb adjacent authority.

**AUTHORITY:** AudienceExperienceTarget owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** The section's canonical output ID/version; it never allocates an ID belonging to an upstream or downstream canonical entity.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by AudienceExperienceTarget.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent AudienceExperienceTarget outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or AudienceExperienceTarget silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement AudienceExperienceTarget as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**CANONICAL DEFINITION:** AudienceExperienceTarget is the provider/model-neutral canonical contract/service boundary defined by this section; it owns no authority beyond the scope stated here.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 31. Emotional Arc

**OWNER:** Story Intelligence.  
**DEFINITION:** long-range character/story emotional trajectory.  
**INPUTS:** StoryCore, character psychology, macro structure.  
**OUTPUTS:** EmotionalArcPlan.  
**INVARIANTS:** arc != local rhythm; major shifts require causal events/decisions.  
**QA:** coherence, payoff, character plausibility.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Emotional Arc as already specified by this section; it must not absorb adjacent authority.

**AUTHORITY:** Emotional Arc owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** The section's canonical output ID/version; it never allocates an ID belonging to an upstream or downstream canonical entity.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Emotional Arc.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Emotional Arc outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Emotional Arc silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Emotional Arc as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**CANONICAL DEFINITION:** Emotional Arc is the provider/model-neutral canonical contract/service boundary defined by this section; it owns no authority beyond the scope stated here.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 32. Emotional Rhythm / Tension

**OWNER:** Story Rhythm/Tension analytics.  
**INPUTS:** Scene/SceneDramaticBeat progression, EmotionalArcPlan.  
**OUTPUTS:** EmotionalRhythmPoint/tension diagnostics.  
**AUTHORITY:** analytics diagnose; they do not rewrite story automatically.  
**FAILURE:** flatline, whiplash, repetitive escalation.  
**QA:** profile/genre-relative, not one universal score.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Emotional Rhythm / Tension as already specified by this section; it must not absorb adjacent authority.

**CANONICAL DEFINITION:** The provider/model-neutral Emotional Rhythm / Tension contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**IDENTITY:** N/A ? Emotional Rhythm / Tension is diagnostic/evidence for exact evaluated versions and creates no new narrative identity; persisted evidence uses its own evidence/evaluation record ID.

**STATE:** N/A for service runtime state ? persisted Emotional Rhythm / Tension outputs/evidence are immutable for exact input versions and have explicit current/stale/disposition evidence where applicable.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Emotional Rhythm / Tension.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist as QA/Story evidence when used for a gate/repair/audit; service process memory is not canonical truth.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Emotional Rhythm / Tension outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**IMPLEMENTATION IMPLICATION:** Implement Emotional Rhythm / Tension as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**FAILURE MODES:** The section-specific failure cases above plus stale-version reuse, provenance loss, schema/invariant violation, or Emotional Rhythm / Tension taking authority owned by another canonical layer.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 33. Dialogue / Subtext

**OWNER:** Dialogue Engine.  
**INPUTS:** SceneDramaticBeat, character psychology, knowledge/belief, relationship, audience target.  
**OUTPUTS:** DialogueIntent + screenplay dialogue realization.  
**INVARIANTS:** dialogue cannot reveal unknown knowledge accidentally; subtext must remain consistent with intent/state.  
**QA:** voice, naturalness, information discipline, subtext, repetition.  
**REPAIR:** line/exchange scope before scene rewrite when possible.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Dialogue / Subtext as already specified by this section; it must not absorb adjacent authority.

**CANONICAL DEFINITION:** The provider/model-neutral Dialogue / Subtext contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**AUTHORITY:** Dialogue / Subtext owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** The section's canonical output ID/version; it never allocates an ID belonging to an upstream or downstream canonical entity.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Dialogue / Subtext.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Dialogue / Subtext outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Dialogue / Subtext silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Dialogue / Subtext as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 34. Setup / Payoff

**OWNER:** Story Setup/Payoff Ledger.  
**IDENTITY:** setup_payoff_link_id/version.  
**INPUTS:** StoryGraph, scenes/beats, props/evidence/information.  
**OUTPUTS:** planted/developing/paid/intentionally-open/broken status.  
**INVARIANTS:** payoff traces to setup; broken links are QA findings.  
**INVALIDATION:** moved/deleted setup invalidates dependent payoff checks.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Setup / Payoff as already specified by this section; it must not absorb adjacent authority.

**CANONICAL DEFINITION:** The provider/model-neutral Setup / Payoff contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**AUTHORITY:** Setup / Payoff owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Setup / Payoff.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Setup / Payoff silently taking authority owned by an adjacent canonical layer.

**QA / GATE:** Schema + semantic invariant + source-version/provenance checks; any section-specific hard gate remains authoritative and blocking findings cannot be averaged away.

**IMPLEMENTATION IMPLICATION:** Implement Setup / Payoff as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 35. Screenplay Realization

**OWNER:** Screenplay Realization stage.  
**PURPOSE:** render accepted canonical story structure into screenplay scene content without creating a new contradictory story master.  
**INPUTS:** StoryCore hierarchy, Scene/SceneDramaticBeat, DialogueIntent, setup/payoff, profile.  
**OUTPUTS:** versioned screenplay scenes.  
**INVARIANTS:** realization may add non-canonical texture only where allowed; it cannot alter locked facts/causality silently.  
**QA:** scene intent fidelity, dialogue/subtext, continuity, pacing.

### FM-002 explicit contract completion

**CANONICAL DEFINITION:** The provider/model-neutral Screenplay Realization contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**AUTHORITY:** Screenplay Realization owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** N/A for the service runtime ? persisted Screenplay Realization outputs carry their own ID/version or exact target/version binding.

**STATE:** N/A for service runtime state ? persisted Screenplay Realization outputs/evidence are immutable for exact input versions and have explicit current/stale/disposition evidence where applicable.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Screenplay Realization.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Screenplay Realization outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Screenplay Realization silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Screenplay Realization as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 36. Full Screenplay

**OWNER:** Story/Screenplay domain.  
**DEFINITION:** assembled versioned screenplay artifact referencing canonical Scene IDs and realization versions.  
**IDENTITY:** screenplay_id/version.  
**MUTABILITY:** immutable versions; edits create successor.  
**QA:** full-draft critique across causality, character, rhythm, setup/payoff, continuity, retention/audience experience.  
**PERSISTENCE:** canonical metadata + text artifact/provenance.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Full Screenplay as already specified by this section; it must not absorb adjacent authority.

**AUTHORITY:** Full Screenplay owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**INPUTS:** Accepted upstream artifacts/versions declared by the section and the pinned ActiveProductionProfile where policy is consumed; no hidden provider prompt is an authority input.

**OUTPUTS:** The typed Full Screenplay result/record described by this section, with exact source-version bindings.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Full Screenplay.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Full Screenplay outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Full Screenplay silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Full Screenplay as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**CANONICAL DEFINITION:** Full Screenplay is the provider/model-neutral canonical contract/service boundary defined by this section; it owns no authority beyond the scope stated here.

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 37. Story Critique

**OWNER:** Independent Critique Council.  
**INPUTS:** screenplay + structured story contracts + evidence.  
**OUTPUTS:** CritiqueFinding with location, evidence, responsible layer, severity.  
**INVARIANTS:** writer/generator is not sole judge; subjective disagreement is not automatically BLOCKING.  
**QA:** critic role isolation, evidence-linked finding, meta-critique where needed.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Story Critique as already specified by this section; it must not absorb adjacent authority.

**CANONICAL DEFINITION:** The provider/model-neutral Story Critique contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**AUTHORITY:** Story Critique owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** N/A ? Story Critique is diagnostic/evidence for exact evaluated versions and creates no new narrative identity; persisted evidence uses its own evidence/evaluation record ID.

**STATE:** N/A for service runtime state ? persisted Story Critique outputs/evidence are immutable for exact input versions and have explicit current/stale/disposition evidence where applicable.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Story Critique.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist as QA/Story evidence when used for a gate/repair/audit; service process memory is not canonical truth.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Story Critique outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Story Critique silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Story Critique as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 38. Root-Cause Localization

**OWNER:** QA/Repair diagnosis layer.  
**PURPOSE:** map defect to earliest responsible semantic layer.  
**INPUTS:** findings + lineage.  
**OUTPUTS:** root_cause_owner, preserve set, invalidation scope candidate.  
**INVARIANTS:** visible defect location != responsible layer.  
**FAILURE:** always blaming prompt/provider, or escalating too far upstream.

### FM-002 explicit contract completion

**CANONICAL DEFINITION:** The provider/model-neutral Root-Cause Localization contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**AUTHORITY:** Root-Cause Localization owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** N/A ? Root-Cause Localization is diagnostic/evidence for exact evaluated versions and creates no new narrative identity; persisted evidence uses its own evidence/evaluation record ID.

**STATE:** N/A for service runtime state ? persisted Root-Cause Localization outputs/evidence are immutable for exact input versions and have explicit current/stale/disposition evidence where applicable.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Root-Cause Localization.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist as QA/Story evidence when used for a gate/repair/audit; service process memory is not canonical truth.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Root-Cause Localization outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**QA / GATE:** Schema + semantic invariant + source-version/provenance checks; any section-specific hard gate remains authoritative and blocking findings cannot be averaged away.

**IMPLEMENTATION IMPLICATION:** Implement Root-Cause Localization as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**FAILURE MODES:** The section-specific failure cases above plus stale-version reuse, provenance loss, schema/invariant violation, or Root-Cause Localization taking authority owned by another canonical layer.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 39. Targeted Story Repair

**OWNER:** Story Repair.  
**INPUTS:** root cause + accepted preserve obligations + dependency graph.  
**OUTPUTS:** StoryRepairPlan.  
**MODES:** line/exchange, SceneDramaticBeat, Scene, Sequence, CharacterModel, research package, structure, premise/angle as justified.  
**INVARIANTS:** preserve unaffected accepted truth; regression-check explicit obligations.  
**INVALIDATION:** only dependent artifacts.  
**QA:** original defect removed, preserve obligations unchanged, no new blocking defect.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Targeted Story Repair as already specified by this section; it must not absorb adjacent authority.

**CANONICAL DEFINITION:** The provider/model-neutral Targeted Story Repair contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**AUTHORITY:** Targeted Story Repair owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** N/A for the service runtime ? persisted Targeted Story Repair outputs carry their own ID/version or exact target/version binding.

**STATE:** N/A for service runtime state ? persisted Targeted Story Repair outputs/evidence are immutable for exact input versions and have explicit current/stale/disposition evidence where applicable.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Targeted Story Repair.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Targeted Story Repair silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Targeted Story Repair as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 40. Story Quality Gate

**OWNER:** Story QA.  
**INPUTS:** structured story + screenplay + critique evidence.  
**OUTPUTS:** StoryQualityResult PASS/WARN/FAIL/NEEDS_HUMAN_REVIEW as contract permits.  
**INVARIANTS:** blocking weakness cannot be averaged away by strong prose.  
**HARD GATES:** factual contradiction, causality break, identity/state contradiction, missing critical payoff where required.  
**APPROVAL:** PASS does not itself equal ScriptLock; lock is explicit.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Story Quality Gate as already specified by this section; it must not absorb adjacent authority.

**CANONICAL DEFINITION:** The provider/model-neutral Story Quality Gate contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**AUTHORITY:** Story Quality Gate owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**IDENTITY:** N/A ? Story Quality Gate is diagnostic/evidence for exact evaluated versions and creates no new narrative identity; persisted evidence uses its own evidence/evaluation record ID.

**STATE:** N/A for service runtime state ? persisted Story Quality Gate outputs/evidence are immutable for exact input versions and have explicit current/stale/disposition evidence where applicable.

**MUTABILITY:** Approved/locked versions are immutable; any semantic change creates a successor version or new evidence record rather than silent in-place mutation.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Story Quality Gate.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist as QA/Story evidence when used for a gate/repair/audit; service process memory is not canonical truth.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Story Quality Gate outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Story Quality Gate silently taking authority owned by an adjacent canonical layer.

**IMPLEMENTATION IMPLICATION:** Implement Story Quality Gate as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.

### FM-002 exact field-label normalization

**QA / GATE:** Apply the section-specific QA/hard checks above plus schema, exact-source-version and provenance validation; blocking findings cannot be averaged away.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 41. Script Lock

**OWNER:** Story domain.  
**IDENTITY:** ScriptLockManifest + locked screenplay/story versions.  
**INPUTS:** Story Quality Gate pass + explicit approval policy.  
**OUTPUTS:** locked version references/hashes.  
**MUTABILITY:** immutable; upstream revision creates new lock version and invalidates downstream dependencies.  
**INVARIANTS:** Directing/Cinematography bind exact locked script/story versions.

### FM-002 explicit contract completion

**PURPOSE:** Define the scoped canonical responsibility of Script Lock as already specified by this section; it must not absorb adjacent authority.

**CANONICAL DEFINITION:** The provider/model-neutral Script Lock contract or service boundary described in this section; persisted creative outputs follow the canonical contract rule for ID/version/status/provenance/source versions unless a stricter section contract applies.

**AUTHORITY:** Script Lock owns only its declared output/decision scope; locked canonical facts and accepted upstream versions outrank it, and downstream stages cannot rewrite upstream truth.

**STATE:** DRAFT / REVIEW / APPROVED / LOCKED / SUPERSEDED / INVALIDATED as applicable to the artifact; section-specific states/statuses override this general creative lifecycle.

**VERSION:** Explicit output/artifact or rule/evaluator version bound to the exact source versions consumed by Script Lock.

**PROVENANCE:** Exact parent/source IDs and versions, pinned profile/rule/evaluator version where applicable, actor/source refs and revision/resolution reason.

**PERSISTENCE:** Persist typed canonical metadata/output in the repository owned by the section; derived text/provider payloads do not replace the canonical record.

**DEPENDENCIES:** The explicit INPUTS and accepted parent authority named in this section; dependency edges are version-aware and auditable.

**INVALIDATION:** A changed accepted source version marks dependent Script Lock outputs/evidence stale or invalid according to dependency edges; unrelated accepted truth is preserved.

**FAILURE MODES:** Schema/invariant/provenance/authority violation, stale input-version reuse, or Script Lock silently taking authority owned by an adjacent canonical layer.

**QA / GATE:** Schema + semantic invariant + source-version/provenance checks; any section-specific hard gate remains authoritative and blocking findings cannot be averaged away.

**IMPLEMENTATION IMPLICATION:** Implement Script Lock as a typed contract/service/repository boundary with exact source-version bindings; do not collapse it into prompt prose or provider state.



### FM3-001 ? V3 local implementation surface completion

**ORDERING:** This boundary runs only after the required INPUTS declared in this section are available at the exact accepted/current versions required by its local gates; downstream consumers may treat its OUTPUTS as current only after this boundary's own validation/acceptance rules succeed.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic evaluation may run concurrently for independent entity/version scopes. Durable canonical writes, accepted/current-pointer changes and coordination mutations use the owning repository plus optimistic revision/CAS and the one-logical-writer rule where SQLite applies. No provider/network side effect occurs inside a canonical DB transaction.

**RECOVERY:** If inputs are stale/invalid or local evaluation fails, retain prior accepted/history evidence, repair the earliest responsible source, emit/recompute a successor result for the corrected exact versions, and propagate only dependency-reachable invalidation through ?63; do not silently mutate accepted upstream truth.

**OBSERVABILITY:** Emit structured correlation with exact input/output IDs and versions, rule/profile/evaluator version where applicable, gate/decision result, failure reason and provenance. Telemetry/logs are evidence only, never canonical truth, and secrets are redacted.

**TESTABILITY:** Provide provider-neutral contract/schema, authority/invariant, exact-version/stale-input, ordering/gate, selective-invalidation and failure/recovery fixtures for this boundary; use deterministic fixtures where the boundary is deterministic.
# 42. DirectingIntent

**OWNER:** Directing domain under ADR-0019.  
**INPUTS:** ScriptLock, SceneDramaticBeat, AudienceExperienceTarget, character/performance state.  
**OUTPUTS:** directing_intent_id/version.  
**AUTHORITY:** performance/reveal/staging intention.  
**INVARIANTS:** cannot invent narrative facts; no final shot design without directing authority.  
**QA:** beat/audience alignment, performance motivation, reveal timing.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make DirectingIntent
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** DirectingIntent
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**IDENTITY:** directing_intent_id + version, per ADR-0019.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After ScriptLock + SceneDramaticBeat + AudienceExperienceTarget; before spatial/blocking/cinematography/Shot finalization.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement DirectingIntent
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 43. BlockingPlan

**OWNER:** Directing/Blocking domain.  
**INPUTS:** DirectingIntent + SceneSpatialDramaticContract + state.  
**OUTPUTS:** blocking_plan_id/version: actor/object positions, movement, timing, interactions.  
**INVARIANTS:** blocking owns spatial execution; cinematography observes/translates it rather than rewriting it.  
**INVALIDATION:** change invalidates dependent camera/composition/shot realization.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make BlockingPlan
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** BlockingPlan
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** blocking_plan_id + version, per ADR-0019.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After DirectingIntent + SceneSpatialDramaticContract + current State; before final CinematographyObjective/Shot design.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement BlockingPlan
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 44. CinematographyObjective

**OWNER:** Cinematography domain.  
**INPUTS:** AudienceExperienceTarget, DirectingIntent, SpatialContract, BlockingPlan, profile.  
**OUTPUTS:** cinematography_objective_id/version.  
**DEFINITION:** visual-language objective, not a list of camera settings and not narrative authority.  
**INVARIANTS:** camera size/angle/lens/movement/focus/light/composition cannot self-origin.  
**QA:** each major visual decision has decision basis.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make CinematographyObjective
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** cinematography_objective_id + version, per ADR-0019.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After AudienceExperienceTarget + DirectingIntent + spatial/blocking authority; before ShotListItem/FullShotSpec realization.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement CinematographyObjective
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 45. Coverage Strategy

**OWNER:** Cinematography/Shot Planning.  
**INPUTS:** SceneDramaticBeat set, blocking, cinematography objectives, duration/profile.  
**OUTPUTS:** CoverageStrategy with required functions/angles/continuity needs.  
**INVARIANTS:** coverage serves dramatic/editing need, not shot-count inflation.  
**QA:** sufficiency, redundancy, screen-direction/spatial coherence.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Coverage Strategy
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Coverage Strategy
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** coverage_strategy_id + version as planning-artifact identity; it is not Shot or narrative identity.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After SceneDramaticBeat/directing/blocking/cinematography context; before ShotBudget/ShotExpansion and final coverage gates.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Coverage Strategy
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 46. Shot Budget

**OWNER:** Shot Planning.  
**INPUTS:** Sequence/Scene duration budgets, CoverageStrategy, StructureProfile.  
**OUTPUTS:** shot count/duration ranges and rationale.  
**INVARIANTS:** budgets are policy/planning constraints, not narrative truth.  
**FAILURE:** fixed universal shot count or false precision.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Shot Budget
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Shot Budget
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** shot_budget_id + version as planning-artifact identity; it is not Shot identity.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After duration/profile/coverage inputs; before ShotExpansion/ShotListManifest approval.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Shot Budget
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 47. ShotListManifest

**OWNER:** Shot Planning under ADR-0020.  
**DEFINITION:** ordered collection/projection of ShotListItem references.  
**IDENTITY:** shot_list_manifest_id/version.  
**INVARIANTS:** manifest does not duplicate Shot truth; reorder/versioning is separate from shot identity.  
**PERSISTENCE:** manifest entries reference canonical shot_id.




### FM3-001 ? ShotListManifest parent-contract completion

**PURPOSE:** Persist the ordered, versioned projection of existing canonical ShotListItem references for an accepted planning scope without creating or duplicating Shot truth.

**CANONICAL DEFINITION:** ShotListManifest is a projection/ordering artifact over canonical ShotListItem identities. It never allocates a second shot_id and never stores an alternate authoritative Shot payload.

**AUTHORITY:** Ordering/projection/coverage-manifest authority only. ShotListItem owns canonical Shot identity and its own semantic fields; upstream SceneDramaticBeat/directing/cinematography authority remains unchanged.

**INPUTS:** Existing ShotListItem shot_id values and the exact ShotListItem versions/derivation evidence being ordered, plus the accepted parent Scene/Sequence/ShotExpansion planning scope and applicable coverage/budget constraints.

**OUTPUTS:** shot_list_manifest_id/version, ordered ShotListItem references, ordering/coverage metadata, and gate/provenance evidence.

**STATE:** DRAFT / REVIEWED / APPROVED / SUPERSEDED / INVALIDATED. Manifest lifecycle is separate from ShotListItem lifecycle.

**MUTABILITY:** An approved manifest version is immutable. Reordering, membership change or coverage-plan change creates a successor manifest version; it does not mutate shot_id or ShotListItem truth in place.

**VERSION:** Manifest version is independent from referenced ShotListItem versions and binds the exact member shot_id/version set it projects.

**PROVENANCE:** Parent Scene/Sequence/SceneDramaticBeat scope, ShotExpansion/planner rule version, exact member ShotListItem IDs/versions, coverage/budget inputs, ordering rationale, actor/source and gate evidence.

**DEPENDENCIES:** Exact referenced ShotListItem versions plus the accepted parent planning/coverage/budget versions that determine manifest membership/order.

**ORDERING:** Canonical ShotListItem identities exist before manifest approval. FullShotSpec/ShotIR realization may consume the manifest only after required Shot eligibility/ordering gates for the referenced versions are current.

**CONCURRENCY / TRANSACTION BOUNDARY:** Ordering/coverage calculation may run concurrently for independent planning scopes; manifest/version writes and accepted/current-pointer changes are repository-serialized under optimistic revision/CAS and one-logical-writer rules where SQLite applies. No provider/network side effect occurs in the DB transaction.

**INVALIDATION:** Member ShotListItem supersession, accepted parent planning/coverage/budget change, or manifest membership/order change invalidates only the affected manifest version and dependency-reachable consumers. It never rewrites unrelated ShotListItems.

**FAILURE MODES:** dangling ShotListItem reference, duplicate shot_id entry, stale member version, missing required coverage member, order inconsistent with accepted parent constraints, or manifest payload copied as competing Shot truth.

**RECOVERY:** Rebuild a successor manifest from current canonical ShotListItem references and repaired parent planning inputs; preserve historical manifest versions and never create replacement Shot identity as a repair shortcut.

**QA / GATE:** reference integrity, no duplicate shot_id, exact-version membership, required coverage/order checks, no orphan entries, and proof that the manifest contains references/projection metadata rather than a shadow Shot authority.

**OBSERVABILITY:** Emit manifest ID/version, ordered shot_id/version refs, parent scope/version, planner/rule version, membership/order changes, gate outcome and rejection/failure reasons.

**IMPLEMENTATION IMPLICATION:** Persist a manifest header plus ordered canonical ShotListItem references. Resolve Shot semantics from the ShotListItem repository; never duplicate canonical Shot payload into the manifest.

**TESTABILITY:** single-shot-identity, duplicate/dangling member, reorder-successor, stale-member, coverage/order, selective-invalidation and restart/readback fixtures.

**LEGACY FLOWKIT MAPPING:** Legacy FlowKit operational Scene/render ordering may be imported only as compatibility evidence or mapping input; it cannot become canonical ShotListManifest/Shot truth without explicit canonical ShotListItem mapping.

## 47A. ShotExpansion ? SceneDramaticBeat to ShotListItem derivation contract

**PURPOSE:** Expand accepted dramatic units into the minimum justified set of ShotListItems for dramatic/coverage execution.
**CANONICAL DEFINITION:** ShotExpansion is a planning transformation stage. It does not own a second Shot entity and does not allocate parallel canonical Shot identity outside ShotListItem.
**OWNER:** Shot Planning.
**AUTHORITY:** derives ShotListItems from SceneDramaticBeat + directing/cinematography/coverage/budget authority; cannot invent narrative purpose or camera authority.
**INPUTS:** ScriptLock, SceneDramaticBeat IDs/versions, DirectingIntent, BlockingPlan, CinematographyObjective, CoverageStrategy, ShotBudget/DurationBudget and pinned ActiveProductionProfile.
**OUTPUTS:** ShotListManifest plus ShotListItem candidates/accepted items; canonical shot_id originates only at ShotListItem under ADR-0020.
**IDENTITY:** N/A ? ShotExpansion is transformation/service boundary, not persistent Shot identity; execution correlation IDs are operational evidence only.
**STATE:** N/A ? service has no independent canonical domain state; output ShotListItem/Manifest and gate evidence own lifecycle.
**MUTABILITY:** N/A for service; output versions are immutable under owning contracts.
**VERSION:** shot-expansion rule/planner version is recorded in output provenance; it is not Shot identity/version.
**PROVENANCE:** exact SceneDramaticBeat, ScriptLock, directing/blocking/cinematography, coverage, budget, profile and planner-rule versions.
**PERSISTENCE:** no independent truth store; persist output ShotListManifest/ShotListItems and derivation/decision evidence.
**PARENT / CHILD OR REFERENCES:** SceneDramaticBeat ? ShotExpansion derivation ? one or more ShotListItems; each item retains parent_scene_dramatic_beat_id.
**DEPENDENCIES:** declared inputs plus NarrativeTrace and relevant State/Reference constraints where required for eligibility planning.
**ORDERING:** no ShotExpansion before SceneDramaticBeat, AudienceExperienceTarget, Directing/Blocking and Cinematography authority are ready; eligibility follows ShotListItem creation.
**CONCURRENCY / TRANSACTION BOUNDARY:** planning may compute independently by eligible beat/scene, but canonical ShotListItem identity allocation/manifest write is repository-serialized; no provider submission.
**INVALIDATION:** parent beat/directing/blocking/cinematography/coverage/budget/profile change invalidates affected expansion outputs and downstream spec/IR, not unrelated shots.
**FAILURE MODES:** SHOT_NO_NARRATIVE_FUNCTION, SHOT_NOT_BOUND_TO_BEAT, SHOT_MISSING_REQUIRED_COVERAGE, duplicate shot without purpose, random Scene?N shots, or second shot identity.
**RECOVERY:** replan only affected beat/coverage scope or escalate upstream; never repair by creating parallel shot master.
**QA / GATE:** every shot has narrative function, SceneDramaticBeat binding, coverage role, duration/budget fit and non-redundant reason before eligibility.
**OBSERVABILITY:** emit input versions, planner version, output shot_ids and rejection/redundancy reasons.
**IMPLEMENTATION IMPLICATION:** typed planning service calling canonical ShotListItem creation boundary; never persist independent ShotExpansion-owned Shot truth.
**TESTABILITY:** beat?shot mapping, duplicate/redundancy, budget/coverage and single-shot-identity tests.
**LEGACY FLOWKIT MAPPING:** legacy FlowKit Scene/render rows may become compatibility execution targets after canonical ShotListItem exists; they do not own expansion.

# 48. ShotListItem

**OWNER:** Shot Planning; origin of canonical Shot identity.  
**IDENTITY:** shot_id.  
**REQUIRED:** parent_scene_dramatic_beat_id, dramatic_function, coverage_function, reason_for_exist, duration_budget, basic_shot_intent.  
**PARENT:** immediate narrative authority = SceneDramaticBeat; inherited context = Scene/Sequence/MacroStoryBeat/StoryCore.  
**INVARIANTS:** NO SCENE DRAMATIC BEAT → NO SHOT; no orphan shot; shot identity is stable across spec/IR revisions.  
**QA:** function/coverage/traceability/redundancy.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make ShotListItem
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** ShotListItem
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed ShotListItem
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**STATE:** PLANNED / ELIGIBLE / REJECTED from the accepted ShotListItem source; production realization/QA state remains separate.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After valid SceneDramaticBeat/directing/coverage planning; before ShotEligibilityGate.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement ShotListItem
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 49. ShotEligibilityGate

**OWNER:** Shot Planning/Preflight under ADR-0020.

**PURPOSE:** Persist the eligibility verdict/evidence that authorizes detailed realization of an existing canonical ShotListItem.

**CANONICAL DEFINITION:** ShotEligibilityGate is a versioned gate-evidence record for one existing shot_id. It is not Shot identity, FullShotSpec or ShotIR.

**IDENTITY:** shot_eligibility_gate_id + version; always references canonical shot_id.

**INPUTS:** ShotListItem plus exact dramatic/directing/spatial/cinematography/state/reference/profile/provider-neutral feasibility input versions.

**EVALUATED INPUT BINDING:** gate record stores evaluated IDs/versions/hashes plus rule/profile version.

**OUTPUTS:** ELIGIBLE or REJECTED plus blocking reasons/findings and evidence/provenance.

**PROVENANCE:** evaluator/rule version, exact source IDs/versions, profile version, evidence refs and timestamp.

**PERSISTENCE:** Shot/preflight repository as immutable gate evidence.

**MUTABILITY / VERSIONING:** a gate result is immutable for its evaluated inputs. Re-evaluation emits a new gate version/evidence record.

**RE-EVALUATION / INVALIDATION:** any dependency/source/profile/reference/state/ShotListItem version change invalidates prior eligibility for new realization use; stale gate evidence remains historical and cannot authorize a new FullShotSpec.

**INVARIANTS:**
- ShotEligibilityGate != ShotListItem.
- ShotEligibilityGate != FullShotSpec.
- ShotEligibilityGate != ShotIR.
- gate never creates or reallocates shot_id.
- NO ELIGIBILITY PASS -> NO FULL SHOT SPEC.

**FAILURE MODES:** state break, impossible spatial relation, duplicate shot, missing coverage, duration violation, stale gate evidence, missing evaluated-version lineage.

**QA / GATE:** reference integrity + exact-version binding + all blocking eligibility checks.

**IMPLEMENTATION IMPLICATION:** FullShotSpec creation must carry a current eligible shot_eligibility_gate_id/version; repository rejects stale/mismatched gate evidence.

**REPAIR:** replan shot or escalate upstream; never force compile.



### FM2-003 ? Local contract completeness

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**STATE:** Gate evidence is immutable per evaluated inputs; result = ELIGIBLE or REJECTED. A stale prior version remains historical and cannot authorize realization.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After ShotListItem exists and required upstream versions are resolved; before FullShotSpec.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 50. FullShotSpec

**OWNER:** Shot Realization under ADR-0020.  
**IDENTITY:** full_shot_spec_id/version referencing existing shot_id.  
**INPUTS:** eligible ShotListItem + upstream dramatic/directing/cinematography/state/profile.  
**OUTPUTS:** complete provider-neutral production realization.  
**MUTABILITY:** immutable versions for same shot_id.  
**INVARIANTS:** FullShotSpec does not create a new shot_id or another Shot identity; it always realizes an existing ShotListItem shot_id. Legacy generic ShotSpec has no independent authority.  
**PROVENANCE:** exact parent IDs/versions + decision bases.  
**FAILURE:** missing function/trace, self-originating camera, state/reference ambiguity.  
**QA:** FullShotSpec contract validation before ShotIR.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make FullShotSpec
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** FullShotSpec
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After current eligible ShotEligibilityGate; before StaticKeyframeSpec/MotionDeltaSpec/ShotIR.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement FullShotSpec
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 51. ShotDecisionTrace

**OWNER:** Shot Planning/Explainability.  
**INPUTS:** all authority chain references.  
**OUTPUTS:** trace from each major shot decision to SceneDramaticBeat/Audience/Directing/Blocking/Cinematography/constraints.  
**INVARIANTS:** "cinematic" alone is never sufficient reason.  
**PERSISTENCE:** immutable trace record per spec version.  
**QA:** required justification questions all resolvable.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make ShotDecisionTrace
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** ShotDecisionTrace
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** shot_decision_trace_id + version bound to full_shot_spec_id/version and shot_id; trace identity is evidence identity, not Shot identity.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Created with/for a FullShotSpec decision set before compile/generation acceptance; used by QA/repair explainability.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement ShotDecisionTrace
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 52. L1-L12 Shot System

**SOURCE-NORMALIZATION DECISION:** the consolidated corpus explicitly defines **eight canonical semantic Shot layers (L1–L8)**. No authoritative source defines additional semantic L9–L12. Therefore this Master MUST NOT invent L9–L12 as new semantic truth layers merely to satisfy a label.

Canonical semantic layers:

```text
L1 SUBJECT
L2 STATE / WARDROBE
L3 ACTION / PERFORMANCE
L4 ENVIRONMENT
L5 TIME / ATMOSPHERE
L6 CAMERA
L7 LIGHTING / STYLE
L8 CONTINUITY
```

Each field carries authority class:

```text
FIXED
INHERITED
VARIABLE
```

and provenance.

For compatibility with the requested "L1-L12" heading, the technical realization after L8 is represented by **four downstream stages, not four invented semantic layers**:

```text
T9  Static Keyframe Spec
T10 Motion Delta Spec
T11 ShotIR
T12 Provider Compilation
```

These T9–T12 labels are pipeline-stage aliases only and MUST NOT be persisted or documented as canonical semantic L9–L12 unless a future accepted ADR explicitly defines such layers.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make L1-L12 Shot System
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** L1-L12 Shot System
 is the cross-cutting policy/governance boundary defined by this section; it does not become Story/Shot/State/Profile truth.

**OWNER:** Shot Contract / Schema governance

**AUTHORITY:** Policy/enforcement authority only; no narrative, Shot, State or Profile truth ownership.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed L1-L12 Shot System
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** N/A ? this section defines a semantic-layer taxonomy, not a separately persisted domain object. Persisted fields live inside FullShotSpec/StaticKeyframeSpec/MotionDeltaSpec/ShotIR.

**STATE:** N/A ? taxonomy has no runtime lifecycle.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** N/A for the policy/boundary itself ? persist only the governed outputs, decisions/evidence, mappings or test artifacts in their owning repositories; this section creates no shadow truth store.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Semantic L1-L8 are resolved inside shot realization before T9/T10/T11/T12 technical lowering.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement as explicit policy/contract/evidence boundary, not as hidden prompt convention and not as a new canonical truth store.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 53. Static Keyframe Spec

**OWNER:** Shot Realization.  
**DEFINITION:** observable starting/keyframe state for one shot.  
**INPUTS:** FullShotSpec + resolved State + References.  
**OUTPUTS:** StaticKeyframeSpec linked to shot_id/spec version.  
**INVARIANTS:** captures state, composition and visible performance at keyframe; no temporal delta masquerading as static truth.  
**QA:** identity/state/reference/camera/light/continuity checks.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Static Keyframe Spec
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** static_keyframe_spec_id + version referencing canonical shot_id/full_shot_spec_id.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After FullShotSpec + resolved State/References; before still-image/Static compilation.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Static Keyframe Spec
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 54. Motion Delta Spec

**OWNER:** Shot Realization.  
**DEFINITION:** temporal change from approved start/static state.  
**INPUTS:** FullShotSpec + StaticKeyframeSpec + action/blocking/movement.  
**OUTPUTS:** MotionDeltaSpec.  
**INVARIANTS:** 1 Shot = 1 Static Keyframe Spec + 1 Motion Delta Spec conceptually; motion cannot redefine start state silently.  
**QA:** temporal feasibility, action continuity, movement motivation.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Motion Delta Spec
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** motion_delta_spec_id + version referencing canonical shot_id/full_shot_spec_id and approved start/static version.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After FullShotSpec + approved/current StaticKeyframeSpec/start state; before motion/video compilation.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Motion Delta Spec
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 55. Shot IR

**OWNER:** Compiler-facing canonical execution representation under ADR-0020.  
**IDENTITY:** ir_id/version + canonical shot_id.  
**INPUTS:** FullShotSpec + resolved canonical State + resolved References + pinned ActiveProductionProfile + provider-neutral execution constraints + compiler rules.  
**OUTPUTS:** provider-neutral executable representation.  
**INVARIANTS:** ShotIR != FullShotSpec; contains no provider-specific syntax as canonical intent; always references canonical shot_id/source versions.  
**MUTABILITY:** immutable versions.  
**INVALIDATION:** source/profile/compiler semantic changes create new IR.  
**QA:** schema/semantic/preflight validation.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Shot IR
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Shot IR
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After FullShotSpec + State + References + ActiveProductionProfile + compiler rules; before provider capability/routing/lowering.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Shot IR
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 56. Entity System

**FLOWKIT DECISION:** KEEP + EXTEND.  
**OWNER:** Canonical Entity Registry.  
**DEFINITION:** persistent identity for characters/locations/props/production assets; dramatic Character state remains Story-owned.  
**IDENTITY:** entity_id + entity_version.  
**OUTPUTS:** typed entity metadata/versions/links.  
**INVARIANTS:** reference media is not identity truth.  
**LEGACY:** adapt FlowKit generic entity/media strengths through anti-corruption interface.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Entity System
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Entity identity exists before Reference binding and downstream Shot/State consumers may bind it.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Entity System
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.
# 57. Reference System

**FLOWKIT DECISION:** KEEP + EXTEND.  
**OWNER:** Reference Registry/Resolver.  
**INPUTS:** EntityVersion, approved reference assets, roles, provider capabilities.  
**OUTPUTS:** resolved reference bindings.  
**IDENTITY:** reference_asset_id/version/hash + role.  
**INVARIANTS:** resolver selects subset; do not upload every reference blindly; references are evidence/conditioning, not semantic state authority.  
**QA:** provenance, approval, compatibility, identity coverage.

### FM-005 Reference version invalidation

**VERSION / MUTABILITY:** approved ReferenceAsset versions are immutable; replacement/role/content change creates a new reference version/hash.

**INVALIDATION RULE:** ReferenceVersion change performs dependency lookup against consumers bound to the old version/hash, emits durable InvalidationRecord entries, marks affected descendants stale/invalid, and requires recompute/regeneration/re-QA according to each dependency edge. Unrelated descendants are preserved.

**PERSISTENCE / RESTART:** reference-to-consumer version bindings and resulting invalidation records are durable; an in-memory-only stale flag is insufficient.

**FAILURE MODE:** new reference bytes/version becoming current without invalidating consumers that bind the previous reference version/hash.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Reference System
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Reference System
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Approved/current Reference versions resolve before dependent ShotIR/compiled generation; changed versions invalidate consumers first.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Reference System
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 58. Canonical State Model

**OWNER:** State Engine.  
**DEFINITION:** semantic world/entity/continuity state independent from generated pixels.  
**INPUTS:** accepted Story/Scene/Shot outcomes, approved changes.  
**OUTPUTS:** typed state snapshots/deltas.  
**INVARIANTS:** parent image != state truth; generated artifact != approved state.  
**PERSISTENCE:** versioned canonical state records.  
**QA:** schema, timeline, identity, relationship, prop/location invariants.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Canonical State Model
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** N/A ? Canonical State Model is a domain/service authority; persisted state identity is StateSnapshot state_snapshot_id/version.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Canonical semantic State is resolved/versioned before downstream continuity/shot compilation consumes it.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Canonical State Model
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 59. Continuity Ledger

**FLOWKIT DECISION:** REWRITE semantic authority while retaining useful chaining execution patterns.  
**OWNER:** Continuity Engine.  
**INPUTS:** canonical StateSnapshots + reference bindings + approved artifacts + dependency lineage.  
**OUTPUTS:** continuity constraints/findings/propagation links.  
**INVARIANTS:** semantic continuity is state-based; visual parent may condition but cannot override state.  
**INVALIDATION:** upstream approved-state change invalidates affected dependent shots.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Continuity Ledger
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Continuity Ledger
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** continuity_ledger_id + version as continuity-evidence/constraint identity; semantic world truth remains StateSnapshot.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After StateSnapshot/reference/artifact lineage exists; before downstream continuity constraints/propagation are accepted.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Continuity Ledger
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 60. State Snapshot

**OWNER:** State Engine.  
**IDENTITY:** state_snapshot_id/version.  
**INPUTS:** prior approved state + accepted canonical change.  
**OUTPUTS:** immutable snapshot.  
**AUTHORITY:** only APPROVED/LOCKED snapshots may become downstream semantic continuity authority.  
**PROVENANCE:** responsible shot/scene/story change + approval evidence.  
**QA:** transition validity, no impossible jumps.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make State Snapshot
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** State Snapshot
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Candidate transition is validated/approved before it becomes downstream continuity authority.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement State Snapshot
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 61. Approved End State

**OWNER:** Approval workflow owns approval evidence; State Engine owns canonical StateSnapshot truth.

**PURPOSE:** Designate which immutable/versioned StateSnapshot is approved for downstream propagation after QA/approval.

**CANONICAL DEFINITION:** ApprovedEndState is NOT an independent world-state truth object. It is an approval-qualified designation/reference to an immutable canonical StateSnapshot version.

Conceptual persisted designation:

ApprovedEndStateDesignation:
- approved_state_snapshot_id -> StateSnapshot state_snapshot_id/version
- approval_record_id
- shot_id / source outcome ref
- approval provenance

The canonical state payload remains only in the referenced StateSnapshot version. The designation MUST NOT copy that payload into a second truth store.

**IDENTITY:** semantic state identity/version = referenced state_snapshot_id/version; approval_record_id identifies approval evidence/designation only.

**INPUTS:** candidate end-state StateSnapshot + artifact/QA evidence + canonical shot expected end-state + approval policy.

**OUTPUTS:** approval designation making the referenced StateSnapshot eligible as downstream continuity authority.

**STATE / APPROVAL RELATIONSHIP:** only an APPROVED/LOCKED referenced snapshot may propagate. Provider success and QA execution alone do not create the designation.

**MUTABILITY / VERSIONING:** approved StateSnapshot is immutable. Revocation/supersession creates explicit approval history and/or a successor StateSnapshot/designation; it never rewrites prior state bytes.

**PROVENANCE:** approval_record_id carries actor/policy/reason/time/evidence and exact shot/artifact/QA/source versions.

**PERSISTENCE:** State repository stores StateSnapshot once; approval record stores the designation/reference and provenance.

**DOWNSTREAM PROPAGATION:** descendants bind the approved state_snapshot_id/version; they do not consume duplicated state from ApprovedEndState.

**INVALIDATION:** revocation, superseding StateSnapshot, or accepted state correction triggers dependency-aware invalidation of descendants bound to obsolete snapshot/designation.

**FAILURE CASES:** shadow duplicate state payload, approval without current QA/policy evidence, designation to nonexistent/non-approved snapshot, stale snapshot propagation.

**HARD GATE:** NO QA APPROVAL -> NO CANONICAL STATE COMMIT.

**IMPLEMENTATION IMPLICATION:** model ApprovedEndState as an approval/reference role around StateSnapshot, never as another mutable state table containing canonical world truth.



### FM2-003 ? Local contract completeness

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**STATE:** approval designation lifecycle is represented by approval/supersession/revocation history; canonical state lifecycle remains on StateSnapshot.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After QA + explicit approval of exact candidate StateSnapshot; before descendant continuity consumption.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 62. Versioning

Canonical mutable concepts use immutable versions plus active pointers/locks where needed.

Rules:
- IDs identify logical entities; version IDs identify immutable realizations.
- optimistic revision guards protect mutable pointers/status.
- accepted/locked versions are never edited in place.
- supersession preserves history.
- provider/profile/compiler/evidence versions are bound into lineage.
- historical failure evidence is retained even after successor PASS evidence.




### FM3-001 ? Versioning parent-contract completion

**PURPOSE:** Define the cross-cutting rule that separates logical identity, immutable semantic versions, mutable current pointers/status/revisions and retained historical evidence across canonical domains.

**CANONICAL DEFINITION:** Versioning is a governance/persistence policy boundary, not a second domain entity or truth store. Each owning domain keeps its canonical identity/state; this policy defines how versions, supersession, current pointers and revision guards behave.

**OWNER:** Canonical persistence/versioning governance together with each domain repository owner for its governed records.

**AUTHORITY:** Owns version/supersession/current-pointer/revision semantics only. It cannot invent Story, Shot, State, Profile, Job or provider truth and cannot override stricter local lifecycle rules.

**INPUTS:** Canonical entity/artifact identities, immutable content versions, owning-domain lifecycle rules, dependency edges, current-pointer/status records, repository revision/CAS metadata and provenance.

**OUTPUTS:** Immutable version records, supersession links, current/accepted/locked pointer or status updates where the owning contract permits them, revision evidence and version-bound lineage.

**IDENTITY:** N/A ? Versioning is a cross-cutting policy/service boundary. Governed domain objects retain their own logical IDs and version IDs.

**STATE:** N/A ? Versioning has no independent domain lifecycle. Governed artifacts/coordination records retain the states defined by their owning contracts.

**MUTABILITY:** Accepted/locked semantic content versions are immutable. Mutable current pointers, lifecycle statuses, leases and coordination state may change only when the owning contract explicitly permits it, through its authorized transition rules plus optimistic revision/CAS/one-writer discipline. Historical versions and transition evidence are retained.

**VERSION:** Versioning-policy/rule version is recorded when policy behavior affects persisted evidence; domain version identity remains owned by the governed component.

**PROVENANCE:** Record logical ID, immutable version ID/content hash where applicable, predecessor/supersession link, exact source versions, actor/reason, policy/rule version, revision/CAS evidence and timestamp.

**PERSISTENCE:** Owning repositories persist immutable versions separately from mutable current-pointer/status/revision coordination where applicable. No provider/network call is executed inside the DB transaction.

**DEPENDENCIES:** Owning-domain identity/lifecycle contracts, DependencyGraph/?63 invalidation rules, repository revision rules and stricter component-specific version semantics.

**ORDERING:** Create/validate a successor immutable version before switching an accepted/current pointer. Validate authorized state/status transitions before coordination mutation. Supersession/invalidation evidence is durable before downstream work treats the new version/pointer as current.

**CONCURRENCY / TRANSACTION BOUNDARY:** One logical SQLite writer serializes durable writes where SQLite is used; optimistic revision/CAS protects mutable pointers/status/coordination rows; immutable version inserts are append-only. Remote/provider side effects remain outside DB transactions.

**INVALIDATION:** Accepted source-version or governing-policy changes trigger only dependency-reachable invalidation through ?63; historical versions remain auditable and unrelated accepted versions remain valid.

**FAILURE MODES:** in-place edit of accepted semantic content, lost supersession history, stale pointer overwrite, CAS bypass, coordination mutation without authorized transition, version/provenance mismatch, or provider output replacing canonical version truth.

**RECOVERY:** Reconstruct current pointers/status from durable version/transition evidence, reconcile CAS/revision conflicts, preserve immutable history, and emit corrective successor/status transitions rather than rewriting accepted historical bytes.

**QA / GATE:** immutable-version integrity, supersession chain, pointer/version consistency, legal mutable-transition ownership, CAS conflict handling, provenance completeness and selective-invalidation checks.

**OBSERVABILITY:** Emit logical ID, old/new version or old/new status/pointer, revision/CAS outcome, actor/reason, policy version and correlation ID; telemetry is evidence only.

**IMPLEMENTATION IMPLICATION:** Model immutable semantic versions separately from mutable coordination/current-pointer state. Do not apply the immutable-content rule blindly to scheduler/provider/invalidation status fields whose owning contracts explicitly require legal in-place coordination transitions.

**TESTABILITY:** immutable-history, successor-version, pointer-switch, stale-CAS rejection, legal/illegal coordination mutation, restart reconstruction, supersession and selective-invalidation fixtures.

**LEGACY FLOWKIT MAPPING:** Legacy mutable rows are adapted only after classifying which fields are immutable semantic content versus mutable coordination/status; migration must not infer a second canonical identity.

## 62A. NarrativeTrace ? bidirectional lineage/provenance contract

**PURPOSE:** Make every narrative-expansion child explain canonical ancestry and allow top-down/bottom-up traversal.
**CANONICAL DEFINITION:** NarrativeTrace is a lineage/provenance structure over canonical artifacts. It does not own or duplicate narrative truth.
**OWNER:** Lineage / Traceability service; canonical domain owners remain authoritative for referenced objects.
**AUTHORITY:** trace relationships/provenance only; cannot rewrite StoryCore, MacroStoryBeat, Sequence, Scene, SceneDramaticBeat or Shot truth.
**INPUTS:** exact artifact IDs/versions, parent_ids, root idea/story lineage, dramatic purpose, inherited constraints, local changes and source_versions.
**OUTPUTS:** versioned trace records supporting StoryCore ? MacroStoryBeat ? Sequence ? Scene ? SceneDramaticBeat ? Shot traversal and reverse traversal.
**IDENTITY:** composite trace identity = traced artifact_id + artifact_type + trace_version; no new narrative entity identity.
**STATE:** CURRENT / SUPERSEDED / INVALIDATED as trace-evidence lifecycle; never narrative artifact state.
**MUTABILITY:** emitted trace versions are immutable; changed lineage/provenance creates successor trace_version.
**VERSION:** explicit trace_version bound to exact referenced source versions.
**PROVENANCE:** source_versions plus resolver/planner/compiler/evaluator versions relevant to traced edges.
**PERSISTENCE:** lineage repository / canonical metadata store; references only, not duplicated canonical payload.
**PARENT / CHILD OR REFERENCES:** parent_ids plus reverse child indexes over canonical IDs. Mandatory canonical narrative chain supports parent?children and child?parent traversal.
**DEPENDENCIES:** referenced artifact identities/versions and DependencyGraph edges.
**ORDERING:** a derived canonical artifact cannot be accepted without valid trace to required parent/root authority.
**CONCURRENCY / TRANSACTION BOUNDARY:** trace metadata commits with or immediately after owning canonical version under repository transaction rules; no provider side effect.
**INVALIDATION:** source-version supersession invalidates affected current trace pointers and descendants according to ?63; historical trace remains auditable.
**FAILURE MODES:** TRACE_ORPHAN_ARTIFACT, TRACE_MISSING_PARENT, TRACE_CYCLE, stale source_versions or contradictory parent lineage.
**RECOVERY:** repair lineage metadata when canonical parents exist; if canonical parent is missing/invalid, escalate to responsible upstream layer rather than fabricate ancestry.
**QA / GATE:** top-down traversal, bottom-up why-exists traversal, orphan detection and cycle detection.
**OBSERVABILITY:** trace queries/events include artifact/version, parent edge, source versions and validation finding.
**IMPLEMENTATION IMPLICATION:** maintain typed lineage edges/indexes; do not reconstruct canonical ancestry from prompt text.
**TESTABILITY:** orphan/cycle/missing-parent fixtures, bidirectional traversal and exact-version provenance tests.
**LEGACY FLOWKIT MAPPING:** legacy IDs may be external lineage references only; they do not replace canonical narrative IDs.

# 63. Dependency Invalidation

**OWNER:** Dependency Graph owns dependency truth; application invalidation service owns computation; Production Utility repository boundary owns durable write serialization.

**PURPOSE:** Convert accepted source-version changes into a durable, replayable minimal invalidation set.

**RULE:** dependency-aware selective invalidation; never full-regenerate by default and never rely on a transient in-memory stale flag as the only record.

## Canonical InvalidationRecord

Fields:
- invalidation_id
- cause
- source_object_id
- source_version_old
- source_version_new
- affected_object_id
- affected_object_version
- dependency_edge_id/type
- dependency_reason
- scope
- status
- created_at
- provenance
- repair_or_recompute_requirement
- resolved_at optional
- resolution_record_id optional
- dedupe_key

**AUTHORITY:** InvalidationRecord records consequences of DependencyGraph/version truth; it does NOT own or invent dependency edges.

**STATUS:** record has explicit unresolved/required vs resolved/cleared lifecycle while preserving historical cause. Domain artifacts keep their own lifecycle/state.

**TRANSACTION OWNERSHIP:** dependency lookup may be computed outside a DB transaction; durable creation/status mutation of InvalidationRecord entries is submitted through the one logical SQLite write owner. No provider/network call occurs inside that transaction.

**IDEMPOTENCY / DEDUPLICATION:** deterministic dedupe_key derives from cause + source old/new versions + affected object/version + dependency edge. Replaying the same accepted change MUST NOT create semantically duplicate active invalidation records.

**RESTART / REPLAY:** startup recovery reloads unresolved invalidation records and dependency bindings, reconciles affected-object stale/valid markers, then schedules required recompute/regenerate/re-QA work. Resolved historical records remain auditable.

**AUDITABILITY:** every record traces cause, source old/new versions, dependency reason, affected version, provenance and resolution.

**REFERENCE VERSION RULE:**

ReferenceVersion change
-> dependency lookup
-> durable InvalidationRecord(s)
-> affected descendants stale/invalid
-> recompute / regenerate / re-QA as required

**OTHER REQUIRED TRIGGERS:** Profile effective-policy changes, Story/Scene/Beat revisions, approved StateSnapshot changes, ShotListItem/FullShotSpec changes and compiler-semantic changes use the same durable mechanism according to declared dependency edges.

Examples:
- Profile dialogue rule change -> dialogue/voice/related QA, not unrelated references.
- SceneDramaticBeat change -> directing/camera/shot descendants.
- BlockingPlan change -> camera/composition/shot realization.
- FullShotSpec change -> ShotIR/provider derivatives.
- approved StateSnapshot change -> continuity-dependent descendants.
- ReferenceAsset version/hash change -> bound ShotIR/compiled/generation/QA descendants as declared by dependency edges.

**FAILURE MODES:** missing edge, duplicate active record, stale record incorrectly cleared, in-memory-only invalidation, over-broad full reset, lost source-version provenance.

**QA / GATE:** graph reachability/selectivity tests, restart/replay idempotency, duplicate-record test and preserved-unrelated-descendant test.

Repair and replan always use explicit preserve/patch/invalidate/recheck sets.



### FM2-003 ? Local contract completeness

**CANONICAL DEFINITION:** Dependency Invalidation
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed Dependency Invalidation
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** N/A for the invalidation service boundary; each persisted InvalidationRecord has invalidation_id and source/affected version identity.

**STATE:** InvalidationRecord lifecycle = unresolved/required versus resolved/cleared while historical cause is retained.

**MUTABILITY:** InvalidationRecord identity, source old/new version binding, affected-object identity and original cause/scope evidence are immutable after creation. Its lifecycle/status field is mutable only through the owning invalidation service from unresolved/required to resolved/cleared (or the exact locally defined equivalent) under one-logical-writer + optimistic revision/CAS rules. Every status change retains durable audit history; changing cause/scope requires a new record rather than rewriting historical cause.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After an accepted source-version change and before affected dependent work is admitted as current.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Dependency Invalidation
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 64. Production Compiler

**PM-014 RESOLUTION — CANONICAL DECISION IN THIS MASTER**

There is exactly one **Production Compiler boundary**.

```text
FullShotSpec
+ Canonical State Snapshot
+ Resolved References
+ ActiveProductionProfile
+ Provider-neutral execution constraints
        ↓
PRODUCTION COMPILER
        ↓
ShotIR
        ↓
Provider Capability Resolution
        ↓
Provider-specific Compiled Request
```

**PURPOSE:** deterministic lowering of canonical shot realization into executable provider-neutral IR and provider-specific derivative requests.

**OWNER:** Production Compiler component.  
**AUTHORITY:** compiler owns compilation semantics only; it does not own Story, Directing, State, Reference or Shot truth.  
**INPUTS:** exact pinned FullShotSpec, StateSnapshot, Reference bindings, ActiveProductionProfile, compiler version, provider-neutral constraints.  
**OUTPUTS:** ShotIR + diagnostics + compile provenance; then provider-specific CompiledRequest through capability lowering.  
**IDENTITY:** compiler_version; ir_id/version; compiled_request_id/version/hash.  
**MUTABILITY:** outputs immutable; recompilation creates successor.  
**VERSIONING:** compiler rule change is explicit and bound in provenance.  
**PROVENANCE:** every emitted provider field traces to source canonical field/default/capability rule.  
**PERSISTENCE:** IR and request metadata/hashes are durable; secret-bearing ephemeral values are excluded/redacted.  
**INVARIANTS:**
- prompt string concatenation != compiler;
- provider adapter cannot invent canonical intent;
- compiler cannot mutate upstream authority;
- same pinned canonical inputs + same compiler rules/capability profile produce the same semantic compiled result, excluding provider/runtime nondeterministic IDs;
- provider-specific request is derivative.
**INVALIDATION:** changes in any pinned input/compiler/capability profile invalidate dependent IR/request only as required.  
**FAILURE MODES:** unsupported capability, contradictory constraints, missing source binding, provider lowering loss, nondeterministic rule drift.  
**QA/GATES:** schema validation, semantic invariant validation, capability preflight, provenance completeness, deterministic fixture tests.  
**LEGACY FLOWKIT:** prompt construction is wrapped as compatibility lowering, never canonical compiler authority.  
**IMPLEMENTATION:** one compiler service/port; adapters consume CompiledRequest rather than Story/FullShotSpec directly.

**PM-014 STATUS: RESOLVED IN MASTER.**



### FM2-003 ? Local contract completeness

**CANONICAL DEFINITION:** Production Compiler
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**STATE:** N/A ? compiler service has no independent domain state; immutable IR/request outputs own versions.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After resolved FullShotSpec/State/References/Profile; before provider routing/adapter execution.

**CONCURRENCY / TRANSACTION BOUNDARY:** Compiler work may parallelize by independent Shot; IR/request metadata commit follows repository rules. Provider/network calls are outside compiler and outside DB transactions.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.
# 65. Provider Capability Model

**OWNER:** Provider Capability Registry.  
**IDENTITY:** provider + surface + region + model_family + model_version + profile_version.  
**INPUTS:** evidence-versioned capability/limits/cost/recovery facts.  
**OUTPUTS:** ProviderProfile.  
**INVARIANTS:** no timeless brand-level quota/price/capability constants; unsupported facts are UNKNOWN, not guessed.  
**PERSISTENCE:** versioned profiles with evidence refs/verified_at.  
**INVALIDATION:** new evidence/profile version triggers routing/recompile consideration, not mutation of historical jobs.  
**QA:** schema, evidence provenance, expiry/freshness policy.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Provider Capability Model
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Provider Capability Model
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** ProviderProfile evidence exists before routing/admission/compile lowering that depends on it.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Provider Capability Model
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 66. Provider Router

**OWNER:** Provider Routing service.  
**INPUTS:** ShotIR requirements, ProviderProfiles, project/profile policy, budget, availability, recovery capability.  
**OUTPUTS:** selected provider/profile + rationale.  
**AUTHORITY:** may choose execution target; cannot change canonical shot intent.  
**INVARIANTS:** degradation requires explicit allowed policy; unsupported feature cannot be silently dropped.  
**FAILURE:** no eligible provider → planning/repair/escalation, not hidden fallback.  
**QA:** capability match, cost/budget/admission, evidence freshness.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Provider Router
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Provider Router
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**IDENTITY:** N/A ? Provider Router is a decision service; persisted routing evidence binds selected ProviderProfile/version and job/run correlation.

**STATE:** N/A ? router service has no independent canonical state; routing decision/evidence is immutable for evaluated inputs.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After ShotIR requirements + ProviderProfiles + project policy; before provider adapter execution.

**CONCURRENCY / TRANSACTION BOUNDARY:** Routing evaluation is side-effect-free and may run concurrently for independent jobs; route-evidence persistence uses repository revision rules and no provider call.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Provider Router
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 67. Provider Adapter Boundary

**OWNER:** provider-specific adapter.  
**INPUTS:** provider-specific CompiledRequest + scoped credential/session authorization.  
**OUTPUTS:** submission result, remote identifiers, status/artifact metadata.  
**INVARIANTS:** adapter owns transport dialect only; no canonical Story/Shot/State edits.  
**LEGACY FLOWKIT:** FlowKit/Chrome-extension/Flow integration becomes one compatibility adapter path.  
**SECURITY:** credential use follows ADR-0016.  
**FAILURE:** transport errors classified before retry/resubmit.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Provider Adapter Boundary
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Provider Adapter Boundary
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** N/A ? Provider Adapter is a transport service; persisted identity lives in GenerationJob submission attempt/provider remote IDs.

**STATE:** N/A ? adapter service state is represented by the Provider Submission axis on GenerationJob.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After routing/capability lowering yields provider-specific CompiledRequest; immediately before/through remote transport side effects.

**CONCURRENCY / TRANSACTION BOUNDARY:** Remote calls run outside DB transactions. Submission identity/state is durably recorded before/around the side-effect boundary; adapter state updates follow GenerationJob transition/CAS rules.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**RECOVERY:** Classify transport outcome first; reconcile UNKNOWN_REMOTE_STATE before resubmit; NO RETRY WITHOUT PROOF.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Provider Adapter Boundary
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.
# 68. Generation Job Model

**OWNER:** Orchestrator owns GenerationJob aggregate; each state axis has a separate transition owner.

**IDENTITY:** generation_job_id + submission_attempt identity + expected input fingerprint.

**INPUTS:** ShotIR/CompiledRequest/provider profile.

**OUTPUTS:** durable execution state, remote job lineage and Artifact candidates.

A GenerationJob stores four orthogonal persisted state axes. The old generic status field is deprecated as canonical authority and MUST NOT replace these fields.

## Scheduler state

Exact enum:
- QUEUED
- WAITING_DEPENDENCY
- WAITING_CAPACITY
- CLAIMED
- RUNNING
- WAITING_RECOVERY
- TERMINAL

**TRANSITION OWNER:** Scheduler / Recovery Coordinator.

**LEGAL TRANSITION CONSTRAINTS:** work starts at QUEUED; dependency/capacity gates may hold work in WAITING_DEPENDENCY / WAITING_CAPACITY; admitted work is CLAIMED then RUNNING; ambiguous remote recovery uses WAITING_RECOVERY; TERMINAL means scheduler work is no longer actively runnable for that job. Recovery may return WAITING_RECOVERY work to active coordination only when persisted reconciliation evidence permits it.

## Provider submission state

Exact enum:
- NOT_SUBMITTED
- SUBMITTING
- SUBMITTED
- POLLING
- UNKNOWN_REMOTE_STATE
- RECONCILING
- AMBIGUOUS_HOLD
- REMOTE_SUCCEEDED
- REMOTE_FAILED
- CANCEL_REQUESTED
- REMOTE_CANCELED

**TRANSITION OWNER:** Provider Adapter / Orchestrator.

**SOURCE-BACKED LEGAL PATHS:**
- NOT_SUBMITTED -> SUBMITTING -> SUBMITTED -> POLLING.
- POLLING -> REMOTE_SUCCEEDED or REMOTE_FAILED.
- SUBMITTING with missing/uncertain remote handle -> UNKNOWN_REMOTE_STATE -> RECONCILING.
- RECONCILING -> SUBMITTED/POLLING when a handle is recovered.
- RECONCILING -> NOT_SUBMITTED only when absence/no-side-effect crossing is proven for safe retry.
- RECONCILING -> AMBIGUOUS_HOLD when ambiguity remains.
- active submitted/polling operation -> CANCEL_REQUESTED -> REMOTE_CANCELED only on provider-confirmed cancellation.

CANCEL_REQUESTED is local intent, not remote cancellation proof.

**REMOTE TERMINAL MEANING:** REMOTE_SUCCEEDED / REMOTE_FAILED / REMOTE_CANCELED are provider-terminal evidence states. AMBIGUOUS_HOLD is a safety hold, not proof of remote terminality.

## Artifact materialization state

Exact enum:
- NONE
- STAGING
- READY
- STALE_RESULT
- QUARANTINED
- MISSING
- CORRUPT
- ARCHIVED

**TRANSITION OWNER:** Artifact Store / Reconciler.

**LEGAL TRANSITION CONSTRAINTS:** materialization proceeds NONE -> STAGING -> READY when bytes validate. Input/dependency fingerprint mismatch produces STALE_RESULT and MUST NOT activate/propagate. Reconciliation/integrity policy may mark materialized history QUARANTINED, MISSING, CORRUPT or ARCHIVED. APPROVED/REJECTED are forbidden on this axis.

## Creative acceptance state

Exact enum:
- NOT_APPLICABLE
- PENDING_QA
- QA_RUNNING
- QA_ERROR
- QA_FAILED
- REPAIR_PENDING
- NEEDS_HUMAN_REVIEW
- APPROVED
- LOCKED
- REJECTED

**TRANSITION OWNER:** QA / Repair / Human-or-policy Approval.

**LEGAL TRANSITION CONSTRAINTS:** QA is entered only when an eligible artifact exists; PENDING_QA -> QA_RUNNING -> QA_ERROR | QA_FAILED | NEEDS_HUMAN_REVIEW | APPROVED | REJECTED according to evaluator/policy evidence. QA_FAILED may enter REPAIR_PENDING and a repaired candidate enters a new PENDING_QA evaluation. APPROVED may become LOCKED through explicit lock policy. Evaluator infrastructure failure is QA_ERROR, not QA_FAILED.

## Cross-axis validity / invalid-transition handling

Source-validated tuples:
- VALID: scheduler=WAITING_RECOVERY, provider=AMBIGUOUS_HOLD, artifact=NONE, creative=NOT_APPLICABLE.
- VALID: scheduler=TERMINAL, provider=REMOTE_SUCCEEDED, artifact=READY, creative=QA_FAILED.
- VALID: scheduler=TERMINAL, provider=REMOTE_SUCCEEDED, artifact=STALE_RESULT, creative=REJECTED.
- VALID: scheduler=TERMINAL, provider=REMOTE_SUCCEEDED, artifact=MISSING, creative=APPROVED.
- INVALID: scheduler=TERMINAL with provider=POLLING.
- INVALID: provider=NOT_SUBMITTED with artifact=READY and creative=PENDING_QA.
- INVALID: artifact=NONE with creative=QA_RUNNING.

Each subsystem may update only its own axis. Cross-axis changes are coordinated by application services; no module silently rewrites another axis. Any state tuple/transition not permitted by typed state invariants is rejected and recorded rather than coerced.

## Recovery / persistence / observability

- All four axes are persisted on GenerationJob with immutable input identity/provider-operation lineage.
- Startup scans non-terminal scheduler/provider states and reconciles UNKNOWN_REMOTE_STATE / SUBMITTED / POLLING before scheduler admission resumes.
- UNKNOWN_REMOTE_STATE -> RECONCILING -> AMBIGUOUS_HOLD remains mandatory when remote acceptance cannot be proven.
- NO RETRY WITHOUT PROOF applies to ambiguous paid submission.
- Observability emits the four axes separately; UI summary status is derived and never persistence authority.
- WAITING_RECOVERY, QA_ERROR and STALE_RESULT remain first-class and MUST NOT be collapsed away.

**INVARIANTS:** expected source versions/hashes are pinned; stale late result cannot auto-approve; artifact state never carries creative approval semantics.

**PERSISTENCE:** durable before/around side-effect boundaries; generic status is non-authoritative compatibility/UI projection only.

**EVIDENCE LIMIT:** JOB_STATE_MODEL_V0_13 is model-checked design evidence, not runtime orchestrator proof.



### FM2-002 ? Closed machine-checkable transition contract

**CANONICAL DEFINITION:** The four V0.13 axes remain independent. The transition rows below are the closed legal transition relation for V1 design consolidation. They normalize only source-backed states/flows from JOB_STATE_MODEL_V0_13, ADR-0012, Failure/Recovery, Static QA and Persistence. No new state is introduced.

**GLOBAL TRANSITION RULES:**
- Initial tuple = scheduler QUEUED; provider NOT_SUBMITTED; artifact NONE; creative NOT_APPLICABLE.
- A transition is legal only when a row below matches FROM_STATE + EVENT/COMMAND + GUARD and the named TRANSITION_OWNER performs the update.
- Any state transition not listed below is ILLEGAL/UNSUPPORTED and MUST be rejected without mutating that axis.
- Every accepted transition persists from-state, to-state, command/event, guard evidence, actor/owner, timestamp, correlation_id and optimistic revision/CAS evidence through the one logical write owner.
- Restart restores the last durable axis values; recovery may move them only through rows explicitly marked as recovery transitions.
- Cross-axis invariant validation runs before commit. No subsystem silently writes another subsystem's axis.
- A timeout/transport exception is never sufficient evidence for a new SUBMIT attempt.
- NO RETRY WITHOUT PROOF remains hard authority.

#### Scheduler axis

**INITIAL STATE:** QUEUED.  
**TERMINAL STATE:** TERMINAL.  
**TRANSIENT STATES:** CLAIMED, RUNNING.  
**RECOVERABLE/HOLD STATES:** WAITING_DEPENDENCY, WAITING_CAPACITY, WAITING_RECOVERY.

| FROM_STATE | EVENT / COMMAND | GUARD | TO_STATE | TRANSITION_OWNER | SIDE EFFECT | PERSISTENCE REQUIREMENT | ILLEGAL TRANSITION BEHAVIOR | RECOVERY BEHAVIOR | OBSERVABLE EVIDENCE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QUEUED | EVALUATE_DEPENDENCIES | required dependency not ready | WAITING_DEPENDENCY | Scheduler | none | persist reason + dependency refs | reject any direct RUNNING mutation | re-evaluate on dependency change/startup | dependency IDs/versions + hold reason |
| QUEUED | EVALUATE_ADMISSION | dependencies ready; capacity/resource/provider/budget gate not ready | WAITING_CAPACITY | Scheduler | none | persist admission gate snapshot | reject direct RUNNING mutation | re-evaluate on gate/resource change | gate snapshot + reason |
| QUEUED | CLAIM | all admission/dependency gates satisfied; atomic lease/revision claim succeeds | CLAIMED | Scheduler | acquire worker lease only | atomic state+lease+revision commit before work | failed CAS leaves QUEUED | stale/expired claim is reconciled | worker/lease/revision evidence |
| WAITING_DEPENDENCY | DEPENDENCIES_READY | all required dependencies now valid/current | QUEUED | Scheduler | none | persist readiness evidence | remain held if any dependency stale | startup recomputes readiness | dependency readiness result |
| WAITING_CAPACITY | CAPACITY_AVAILABLE | admission/resource/budget gates now permit retry of admission | QUEUED | Scheduler | none | persist changed gate evidence | remain held if gate still closed | startup re-evaluates gates | provider/model/resource gate evidence |
| CLAIMED | START_WORK | valid lease + unchanged expected input fingerprint | RUNNING | Scheduler / Worker coordinator | begin local orchestration work | persist RUNNING before side-effecting stage proceeds | reject if lease/input stale | stale claim routes to WAITING_RECOVERY | lease + input fingerprint |
| CLAIMED | LEASE_OR_RESTART_RECOVERY | lease expired/lost or restart prevents safe direct continuation | WAITING_RECOVERY | Recovery Coordinator | stop active execution | persist recovery cause before reassignment | no blind requeue | reconcile provider/job lineage first | lease expiry/restart evidence |
| RUNNING | REMOTE_OR_LEASE_RECOVERY_REQUIRED | ambiguous remote state, lost lease, or restart requires reconciliation | WAITING_RECOVERY | Recovery Coordinator | stop normal runnable path | persist recovery cause + provider lineage | no direct QUEUED blind retry | reconcile under provider recovery rules | remote/lease ambiguity evidence |
| WAITING_RECOVERY | RECOVERY_PROVEN_SAFE_TO_REQUEUE | provider absence/no-side-effect or same-job idempotency safety proven and dependencies still valid | QUEUED | Recovery Coordinator | none | persist proof allowing requeue | proofless requeue rejected | subsequent normal admission applies | reconciliation proof/idempotency evidence |
| WAITING_RECOVERY | RECOVERY_RESUMES_ACTIVE_WORK | existing remote/local work recovered and active coordination resumes | RUNNING | Recovery Coordinator | resume polling/materialization/coordination only | persist recovered handle/lease evidence | cannot create new remote job without proof | continue same operation lineage | recovered remote handle/lease |
| RUNNING | SCHEDULER_WORK_COMPLETE | local scheduler/orchestrator has no further runnable work and provider/local outcome permits closure | TERMINAL | Scheduler | release lease | persist terminal reason + final axis tuple | TERMINAL cannot become RUNNING in place | successor/retry requires explicit new attempt/job policy | terminal reason + final tuple |
| WAITING_RECOVERY | RECOVERY_RESOLVED_TERMINAL | reconciliation establishes terminal provider/local outcome and no runnable recovery work remains | TERMINAL | Recovery Coordinator / Scheduler | release recovery hold | persist reconciliation result | terminal state immutable for this attempt | new work requires successor attempt/policy | reconciliation evidence |
| QUEUED | CANCEL_BEFORE_SIDE_EFFECT | user/policy cancels before provider side-effect boundary | TERMINAL | Scheduler | no provider call | persist cancellation proof/provider=NOT_SUBMITTED | cancellation after submit must use provider cancel path | N/A | actor/policy + no-submit evidence |
| WAITING_DEPENDENCY | CANCEL_BEFORE_SIDE_EFFECT | provider still NOT_SUBMITTED | TERMINAL | Scheduler | no provider call | persist cancellation proof | same | N/A | actor/policy + no-submit evidence |
| WAITING_CAPACITY | CANCEL_BEFORE_SIDE_EFFECT | provider still NOT_SUBMITTED | TERMINAL | Scheduler | no provider call | persist cancellation proof | same | N/A | actor/policy + no-submit evidence |

#### Provider submission axis

**INITIAL STATE:** NOT_SUBMITTED.  
**TERMINAL EVIDENCE STATES:** REMOTE_SUCCEEDED, REMOTE_FAILED, REMOTE_CANCELED.  
**TRANSIENT STATES:** SUBMITTING, SUBMITTED, POLLING, RECONCILING, CANCEL_REQUESTED.  
**SAFETY HOLD:** UNKNOWN_REMOTE_STATE, AMBIGUOUS_HOLD.

| FROM_STATE | EVENT / COMMAND | GUARD | TO_STATE | TRANSITION_OWNER | SIDE EFFECT | PERSISTENCE REQUIREMENT | ILLEGAL TRANSITION BEHAVIOR | RECOVERY BEHAVIOR | OBSERVABLE EVIDENCE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NOT_SUBMITTED | SUBMIT | durable submission identity/correlation/idempotency data written; scheduler RUNNING/valid | SUBMITTING | Provider Adapter / Orchestrator | one remote submission attempt may cross side-effect boundary | persist SUBMITTING + attempt identity before network call | reject submit if durable identity absent | crash without durable remote handle becomes UNKNOWN_REMOTE_STATE | attempt/correlation/idempotency evidence |
| SUBMITTING | ACCEPTED_HANDLE | provider acceptance/handle is confirmed | SUBMITTED | Provider Adapter / Orchestrator | none beyond already-issued request | persist provider_job_id/accepted evidence immediately | no synthetic handle | restart scans SUBMITTED | remote handle/receipt |
| SUBMITTING | ACCEPTANCE_AMBIGUOUS | response lost/crash/timeout means side-effect may have crossed boundary | UNKNOWN_REMOTE_STATE | Provider Adapter / Recovery | none; MUST NOT submit again | persist ambiguity evidence | SUBMITTING?NOT_SUBMITTED without proof rejected | begin reconciliation | transport/crash evidence + attempt identity |
| SUBMITTED | START_POLL | durable remote handle exists | POLLING | Provider Adapter / Orchestrator | provider status query | persist polling/revision as policy requires | polling without handle rejected | startup may reconcile same handle | provider_job_id + poll correlation |
| SUBMITTED | RECOVERY_SCAN | restart/liveness uncertainty requires provider reconciliation | RECONCILING | Recovery Coordinator / Adapter | lookup existing operation only | persist reconciliation start | no new submit | reconcile existing handle | startup/recovery evidence |
| POLLING | REMOTE_SUCCESS | provider supplies terminal success evidence | REMOTE_SUCCEEDED | Provider Adapter | stop polling; materialization may begin on artifact axis | persist terminal remote evidence | cannot infer from local timeout | terminal history immutable | provider terminal payload/hash/IDs |
| POLLING | REMOTE_FAILURE | provider supplies terminal failure evidence | REMOTE_FAILED | Provider Adapter | stop polling | persist typed remote failure | cannot collapse ambiguity into failure | terminal history immutable | provider failure code/evidence |
| POLLING | RECOVERY_SCAN | poll timeout/not-found/restart requires reconciliation rather than inference | RECONCILING | Recovery Coordinator / Adapter | lookup existing operation only | persist reason/last-known handle | no blind submit | reconcile by provider profile | poll/timeout/not-found evidence |
| UNKNOWN_REMOTE_STATE | BEGIN_RECONCILE | durable attempt identity exists | RECONCILING | Recovery Coordinator / Adapter | provider lookup/idempotency/history only | persist transition + recovery profile version | no submit command permitted | execute source-backed lookup priority | recovery profile + lookup request evidence |
| RECONCILING | RECOVERED_HANDLE | existing accepted operation proven and handle recovered | SUBMITTED | Recovery Coordinator / Adapter | none | persist recovered handle/source | cannot allocate new remote operation | then poll same operation | recovered handle evidence |
| RECONCILING | RECOVERED_ACTIVE_POLL | existing operation and pollable handle proven | POLLING | Recovery Coordinator / Adapter | resume polling existing operation | persist recovered handle/state | no submit | continue same remote lineage | lookup result |
| RECONCILING | PROVEN_ABSENT | provider/transport evidence proves request did not create remote side effect, or server idempotency guarantees same-job behavior | NOT_SUBMITTED | Recovery Coordinator | none | persist proof authorizing safe retry eligibility | absent proof makes transition illegal | scheduler may requeue under its own row | PROVEN_NOT_SUBMITTED/idempotency evidence |
| RECONCILING | STILL_AMBIGUOUS | reconciliation cannot prove accepted operation or absence | AMBIGUOUS_HOLD | Recovery Coordinator | none | persist ambiguity hold + evidence | no retry/resubmit | later reconciliation may be requested | lookup attempts + unresolved evidence |
| AMBIGUOUS_HOLD | RECONCILE_AGAIN | new evidence/manual policy requests another lookup; no submit | RECONCILING | Recovery Coordinator | provider lookup only | persist reason/evidence delta | direct SUBMITTING illegal | continue reconciliation | new evidence / operator action |
| SUBMITTED | REQUEST_CANCEL | provider profile supports/accepts cancel request | CANCEL_REQUESTED | Provider Adapter / Orchestrator | send bounded cancel request for existing handle | persist local cancel intent before/with call | CANCEL_REQUESTED is not cancellation proof | reconcile if response ambiguous | actor/policy + remote handle |
| POLLING | REQUEST_CANCEL | existing remote handle; cancel policy allows | CANCEL_REQUESTED | Provider Adapter / Orchestrator | send cancel request | persist intent | same | reconcile if needed | cancel request correlation |
| CANCEL_REQUESTED | CANCEL_CONFIRMED | provider explicitly confirms remote cancellation | REMOTE_CANCELED | Provider Adapter | stop normal poll | persist provider confirmation | local intent alone cannot enter REMOTE_CANCELED | terminal history immutable | provider cancel receipt |
| CANCEL_REQUESTED | REMOTE_SUCCESS_WON_RACE | provider terminal success is observed despite cancel intent | REMOTE_SUCCEEDED | Provider Adapter | late result enters artifact/stale/cancel policy | persist terminal evidence + cancel history | cannot rewrite as REMOTE_CANCELED | artifact policy decides quarantine/stale | provider success + cancel lineage |
| CANCEL_REQUESTED | REMOTE_FAILURE_WON_RACE | provider terminal failure observed | REMOTE_FAILED | Provider Adapter | stop cancel/poll path | persist terminal evidence + cancel history | cannot rewrite as REMOTE_CANCELED | terminal history immutable | provider failure + cancel lineage |

**ABSOLUTE ILLEGAL PATH:** TIMEOUT / CONNECTION BREAK / CRASH AFTER POSSIBLE SUBMIT ? SUBMITTING is forbidden unless reconciliation first reaches PROVEN_ABSENT/NOT_SUBMITTED or verified server idempotency proves same-job behavior.

#### Artifact materialization axis

**INITIAL STATE:** NONE.  
**USABLE STATE:** READY.  
**TRANSIENT STATE:** STAGING.  
**NON-USABLE/HOLD STATES:** STALE_RESULT, QUARANTINED, MISSING, CORRUPT.  
**RETENTION TERMINAL:** ARCHIVED.

| FROM_STATE | EVENT / COMMAND | GUARD | TO_STATE | TRANSITION_OWNER | SIDE EFFECT | PERSISTENCE REQUIREMENT | ILLEGAL TRANSITION BEHAVIOR | RECOVERY BEHAVIOR | OBSERVABLE EVIDENCE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NONE | BEGIN_MATERIALIZE | provider/local result is eligible for artifact ingest | STAGING | Artifact Store | create staging bytes/path | persist artifact identity/staging lineage before final promotion | no direct READY without staged integrity path | startup reconciles staging | staging path + attempt/job refs |
| NONE | DISCOVER_ORPHAN | startup finds final bytes without trusted DB lineage | QUARANTINED | Artifact Reconciler | isolate/register evidence only | persist quarantine reason/hash/path | cannot promote automatically | manual/policy lineage reconciliation | hash/path/origin evidence |
| STAGING | MATERIALIZE_VALID | bytes complete; checksum/type/durability and metadata validation pass | READY | Artifact Store / Reconciler | atomic finalization + metadata commit | persist hash/size/path/lineage atomically per policy | validation failure blocks READY | startup verifies final/DB consistency | hash/size/media validation |
| STAGING | INPUT_BECAME_STALE | expected input/dependency fingerprint differs from pinned job input | STALE_RESULT | Artifact Store / Reconciler | retain candidate but never activate | persist stale reason + old/new fingerprints | cannot become READY current output | archive/inspect only or regenerate successor | fingerprint mismatch |
| STAGING | INTEGRITY_FAILED | bytes/hash/decoder integrity fails | CORRUPT | Artifact Reconciler | isolate corrupt bytes | persist corruption evidence | cannot enter creative QA | re-materialize under explicit recovery | checksum/decoder evidence |
| STAGING | LINEAGE_UNTRUSTED | artifact cannot be safely bound to expected job/source | QUARANTINED | Artifact Reconciler | isolate candidate | persist lineage finding | no approval/propagation | resolve lineage or archive | lineage mismatch |
| READY | DEPENDENCY_OR_INPUT_INVALIDATED | dependency/current expected fingerprint changes | STALE_RESULT | Artifact Reconciler / Invalidation service | active/current pointer removed as applicable | persist invalidation/stale record | stale artifact cannot remain active canonical candidate | regenerate/recompute successor | InvalidationRecord + fingerprint evidence |
| READY | FILE_MISSING | startup/reconciler cannot find expected bytes | MISSING | Artifact Reconciler | none | persist missing finding without erasing creative history | cannot silently recreate authority | re-download/recover when lineage permits | missing-path reconciliation evidence |
| READY | INTEGRITY_FAILED | stored bytes no longer match hash/decoder constraints | CORRUPT | Artifact Reconciler | quarantine from use | persist integrity finding | cannot remain usable | restore/re-download/new version | checksum/integrity evidence |
| READY | ARCHIVE | retention/supersession policy authorizes archive | ARCHIVED | Artifact Store | move/mark retention location/state | persist archive manifest | archived artifact not active | restore only through explicit retention/recovery policy | retention/manifest evidence |
| STALE_RESULT | ARCHIVE | retention policy | ARCHIVED | Artifact Store | archive stale candidate | persist archive lineage | cannot return to READY in place | regenerate successor if needed | stale + archive evidence |
| QUARANTINED | ARCHIVE | policy decides candidate cannot be trusted/promoted | ARCHIVED | Artifact Store / Reconciler | archive/quarantine retention | persist disposition | no READY promotion without a separately validated recovery record | create/restore validated successor if appropriate | disposition evidence |
| MISSING | RECOVER_BYTES | authoritative lineage exists and re-download/restore is permitted | STAGING | Artifact Reconciler | recover bytes to staging | persist recovery attempt | cannot jump directly to READY | validate through STAGING path | recovery source + lineage |
| CORRUPT | RECOVER_BYTES | authoritative lineage exists and replacement bytes are permitted | STAGING | Artifact Reconciler | re-materialize to staging | persist recovery attempt | corrupt bytes never treated as READY | validate through STAGING path | corruption + recovery source |

#### Creative acceptance axis

**INITIAL STATE:** NOT_APPLICABLE.  
**TRANSIENT STATES:** PENDING_QA, QA_RUNNING.  
**RECOVERABLE STATES:** QA_ERROR, QA_FAILED, REPAIR_PENDING, NEEDS_HUMAN_REVIEW.  
**ACCEPTED STATE:** APPROVED.  
**TERMINAL/POLICY-END STATES:** LOCKED, REJECTED.  
Approval semantics never live in Artifact Materialization.

| FROM_STATE | EVENT / COMMAND | GUARD | TO_STATE | TRANSITION_OWNER | SIDE EFFECT | PERSISTENCE REQUIREMENT | ILLEGAL TRANSITION BEHAVIOR | RECOVERY BEHAVIOR | OBSERVABLE EVIDENCE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NOT_APPLICABLE | QUEUE_QA | artifact is READY/current and creative QA applies | PENDING_QA | QA Orchestrator | enqueue evaluator work only | persist artifact/spec/state/reference versions being evaluated | reject if artifact NONE/STALE/MISSING/CORRUPT | materialize/repair first | evaluated-version fingerprint |
| PENDING_QA | START_QA | evaluator lease/rule version valid | QA_RUNNING | QA Orchestrator | run evaluator/sensors | persist evaluator/rule/dataset versions | stale input blocks run | requeue with current versions | evaluator lease + input fingerprint |
| QA_RUNNING | EVALUATOR_ERROR | reviewer/sensor infrastructure failed; no artifact-quality judgment | QA_ERROR | QA subsystem | stop/record evaluator failure | persist evaluator error separately from artifact defect | MUST NOT become QA_FAILED merely from tool failure | retry/fallback evaluator | typed evaluator error |
| QA_RUNNING | ARTIFACT_QA_FAILED | blocking creative/technical defect found | QA_FAILED | QA subsystem | create QA findings | persist evidence-bound defects/severity | cannot approve same evidence | enter repair planning | QA findings/evidence |
| QA_RUNNING | REVIEW_REQUIRED | policy/confidence/sensor disagreement requires human review | NEEDS_HUMAN_REVIEW | QA subsystem | create review task | persist reasons/evidence | no auto approval when policy requires human | human/policy disposition | disagreement/confidence evidence |
| QA_RUNNING | QA_PASS_AND_AUTO_APPROVE | all blocking gates pass and authorized approval policy explicitly permits automatic approval | APPROVED | QA + authorized Approval policy | artifact becomes eligible for state-commit workflow, not state truth by itself | persist QA result + separate approval evidence | provider success alone cannot trigger | revoke/supersede only through explicit approval history/new version | QA pass + approval policy/actor evidence |
| QA_RUNNING | EXPLICIT_REJECT | evaluator/policy produces final rejection rather than repair | REJECTED | QA / Approval policy | block propagation | persist rejection evidence | cannot later mutate to APPROVED without new evaluation/version | new/repaired candidate starts new QA path | rejection reason/evidence |
| QA_ERROR | RETRY_EVALUATOR | retry/fallback sensor/evaluator selected; source artifact still current | PENDING_QA | QA Orchestrator | enqueue evaluator retry only | persist retry/fallback lineage | cannot map QA_ERROR to QA_FAILED without artifact defect evidence | alternate/retried evaluator | prior error + retry policy |
| QA_FAILED | PLAN_REPAIR | failure is repairable and repair policy accepts scope | REPAIR_PENDING | Repair subsystem | create RepairPlan only | persist preserve/patch/invalidate/recheck sets | no direct APPROVED | repair then new PENDING_QA | QA finding + RepairPlan |
| REPAIR_PENDING | REPAIRED_CANDIDATE_READY | repaired/successor candidate is materialized READY and exact versions are bound | PENDING_QA | Repair + QA Orchestrator | enqueue fresh QA | persist successor/repaired lineage | prior QA PASS/FAIL cannot be reused as current verdict | re-QA from pinned inputs | repaired artifact/version |
| NEEDS_HUMAN_REVIEW | HUMAN_APPROVE | authorized human/policy review accepts exact candidate | APPROVED | Human / Approval workflow | candidate eligible for state commit | persist actor/reason/time/evidence | stale candidate blocks approval | re-review current successor | approval record |
| NEEDS_HUMAN_REVIEW | HUMAN_REJECT | authorized reviewer rejects exact candidate | REJECTED | Human / Approval workflow | block propagation | persist rejection evidence | no silent reopen | new/repaired candidate required | rejection record |
| NEEDS_HUMAN_REVIEW | HUMAN_REQUEST_REPAIR | reviewer identifies repairable localized defect | REPAIR_PENDING | Human / Repair workflow | create/authorize RepairPlan | persist reason/scope | no direct mutation of accepted state | repair then re-QA | review + RepairPlan |
| APPROVED | LOCK | explicit lock policy/authorized actor freezes accepted version | LOCKED | Approval workflow | prevents in-place semantic mutation | persist lock record | LOCKED has no in-place unlock transition | revision creates successor artifact/version | lock actor/policy/reason |

### Cross-axis transition commit / concurrency rules

1. The one logical SQLite write owner serializes durable state mutation.
2. Each axis update uses optimistic revision/CAS on the mutable coordination row; failed CAS reloads and revalidates guards.
3. Provider/network calls do not occur inside DB transactions.
4. Side-effect boundary metadata is durably written before/around remote submission as defined by Persistence/Recovery.
5. A multi-axis application command validates the full target tuple before commit, then writes only through authorized axis transitions.
6. Startup recovery scans non-terminal scheduler/provider states, expired leases, artifact staging/final paths and QA work before normal scheduler admission.
7. Event/log/UI status is derived evidence only; it cannot override the four durable axes.
8. Historical transition evidence is retained after successor states.

### Machine-check contract expectation

An implementation transition validator MUST be generated from or semantically equivalent to the closed rows above. Required tests:
- every declared state is reachable from the initial state or a source-backed recovery fixture;
- every transition target is a declared state;
- any unspecified transition is rejected;
- valid/invalid cross-axis fixtures from JOB_STATE_MODEL_CHECK_V0_13 remain valid/invalid;
- WAITING_RECOVERY + AMBIGUOUS_HOLD is valid;
- TERMINAL + POLLING is rejected;
- NOT_SUBMITTED + READY/PENDING_QA is rejected;
- artifact NONE + QA_RUNNING is rejected;
- QA_ERROR never means artifact QA failure;
- STALE_RESULT never auto-activates;
- timeout/connection break never reaches SUBMITTING again without PROVEN_ABSENT/idempotency proof.


### FM2-003 ? Local contract completeness

**PURPOSE:** Make Generation Job Model
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**STATE:** Four independent persisted axes defined by the exact V0.13 transition contract in this section.

**MUTABILITY:** GenerationJob identity, pinned input fingerprint, compiled-request identity, provider correlation/idempotency data once issued, and historical transition evidence are immutable. The four coordination axes plus lease/revision fields are mutable only through the closed legal transition rows in this section under one-logical-writer + optimistic revision/CAS. Every accepted transition retains durable from/to/event/guard/owner evidence; semantic input change creates a successor job/input version rather than rewriting pinned history.

**COORDINATION HISTORY RULE:** Current coordination state may mutate only by legal transition; the durable transition/event history is append-only evidence. This rule is the intended specialization of ?62 Versioning for GenerationJob.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After compiled execution inputs are pinned; axes evolve through the closed transition contract until durable terminal/recovery conditions.

**CONCURRENCY / TRANSACTION BOUNDARY:** One logical SQLite writer + optimistic revision/CAS governs mutable coordination rows; worker leases bound concurrent ownership; provider/network work is outside DB transactions.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** Restore durable state, reconcile leases/provider ambiguity/artifacts, then resume only through the closed transition/recovery rules; never blind-resubmit uncertain paid work.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Generation Job Model
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 69. Queue / DAG

**FLOWKIT DECISION:** KEEP + EXTEND.

**OWNER:** Orchestrator/Scheduler.  
**INPUTS:** ProductionRun/PlanNode/GenerationJob dependencies, provider/resource/budget gates.  
**OUTPUTS:** admitted ready work.  
**ORDERING:** priority class + project fairness + oldest-ready.  
**ADMISSION:** global + provider + model + operation + local-resource + dependency readiness + budget.  
**INVARIANTS:** bounded queues/backpressure; no execution before dependencies/gates satisfied.  
**PERSISTENCE:** DAG/checkpoint state restart-safe.  
**LEGACY:** reuse FlowKit queue/wave/dependency strengths behind canonical job model.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Queue / DAG
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Queue / DAG
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** N/A ? Scheduler/Queue service itself has no domain identity; persisted DAG/job nodes retain their own IDs/versions.

**STATE:** Queue/scheduler coordination state is represented by GenerationJob scheduler_state plus durable DAG/checkpoint readiness.

**MUTABILITY:** Accepted DAG topology/dependency definition for a planned version is immutable; a semantic topology change creates a successor plan/DAG version. Readiness/checkpoint/lease/admission and GenerationJob scheduler coordination fields are mutable only through their owning scheduler/job transition rules under one-logical-writer + optimistic revision/CAS, with transition history retained.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**CONCURRENCY / TRANSACTION BOUNDARY:** One logical SQLite writer + optimistic revision/CAS governs mutable coordination rows; worker leases bound concurrent ownership; provider/network work is outside DB transactions.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** Restore durable state, reconcile leases/provider ambiguity/artifacts, then resume only through the closed transition/recovery rules; never blind-resubmit uncertain paid work.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Queue / DAG
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.
# 70. Retry / Resume

**FLOWKIT DECISION:** KEEP + EXTEND.

**OWNER:** Orchestrator/Recovery policy.  
**INPUTS:** typed failure classification + provider recovery capability + persisted job state.  
**OUTPUTS:** retry/resume/reconcile/hold decision.  
**INVARIANTS:** retry != repair; restart resumes from durable state; ambiguous paid submission is excluded from generic retry.  
**FAILURE:** unbounded retry, duplicate paid job, lost lease.  
**QA:** fault-injection/model state tests.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Retry / Resume
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Retry / Resume
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** N/A ? Retry/Resume is a policy/service boundary; RecoveryEvent/attempt/job identities carry persistence identity.

**STATE:** N/A ? policy/service has no independent state; it acts on persisted Job/RecoveryEvent states.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Only after typed failure/recovery classification; ambiguity reconciliation precedes any resubmit.

**CONCURRENCY / TRANSACTION BOUNDARY:** One logical SQLite writer + optimistic revision/CAS governs mutable coordination rows; worker leases bound concurrent ownership; provider/network work is outside DB transactions.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**RECOVERY:** Restore durable state, reconcile leases/provider ambiguity/artifacts, then resume only through the closed transition/recovery rules; never blind-resubmit uncertain paid work.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Retry / Resume
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 71. Ambiguous Remote State

**OWNER:** Provider Recovery architecture.

Canonical states:

```text
SUBMITTING
→ UNKNOWN_REMOTE_STATE
→ RECONCILING
→ AMBIGUOUS_HOLD
```

**RULE:** NO RETRY WITHOUT PROOF.

Resubmit is permitted only when:
- provider idempotency proves same-job behavior; or
- reconciliation proves absence; or
- transport evidence proves request never crossed side-effect boundary.

Current evidence: architecture + local fault injection exists; live paid-provider crash proof remains later acceptance evidence, not a design blocker.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Ambiguous Remote State
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Ambiguous Remote State
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed Ambiguous Remote State
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** N/A ? AmbiguousRemoteState is a typed provider/job state pattern, not a separate canonical entity.

**STATE:** Provider-state values are SUBMITTING / UNKNOWN_REMOTE_STATE / RECONCILING / AMBIGUOUS_HOLD and related exact V0.13 provider states; no separate state store.

**MUTABILITY:** AmbiguousRemoteState has no separate mutable truth store. The owning GenerationJob provider_state is mutable only through the closed Provider Submission transition rows under one-logical-writer + optimistic revision/CAS. Submission identity, remote correlation/idempotency keys and reconciliation evidence already observed are retained as immutable history and are never overwritten to manufacture retry proof.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After ambiguous/uncertain provider evidence and before any retry/resubmit decision.

**CONCURRENCY / TRANSACTION BOUNDARY:** One logical SQLite writer + optimistic revision/CAS governs mutable coordination rows; worker leases bound concurrent ownership; provider/network work is outside DB transactions.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** Restore durable state, reconcile leases/provider ambiguity/artifacts, then resume only through the closed transition/recovery rules; never blind-resubmit uncertain paid work.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Ambiguous Remote State
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 72. Persistence

**OWNER:** Production Utility repository boundary.  
**DECISION:** SQLite operational store for V1 local-first target.

Canonical settings/directions:

```text
SQLite WAL
synchronous=FULL
foreign_keys=ON
one logical writer
bounded write command queue
separate reads under repository policy
short transactions
no provider/network calls inside DB transaction
artifact bytes outside DB
```

**CONCURRENCY:** write ownership serialization is primary correctness mechanism.  
**VERSIONING:** optimistic revisions + immutable creative versions.  
**RECOVERY:** startup reconciliation, migrations, backup/restore, schema compatibility gate.  
**EVIDENCE:** Windows Run-1 FAIL retained; Run-2 intended single-writer target lane PASS; this proves scoped persistence topology behavior, not full-product validation.  
**INVALIDATION:** stale input fingerprint prevents late result from overwriting newer decisions.

### FM-005 invalidation durability

InvalidationRecord and source/affected version bindings are canonical operational metadata persisted through the same one-logical-writer command queue. Restart recovery reloads unresolved invalidations before dependent work is admitted. No transient-only invalidation flag is sufficient.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Persistence
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed Persistence
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** N/A ? Persistence is an infrastructure boundary; records retain their domain identities and schema/migration versions.

**STATE:** N/A ? infrastructure service has no domain state; DB/schema/migration/repository records carry explicit states/versions.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Cross-cutting persistence surrounds all durable authority transitions; remote/network calls remain outside DB transactions.

**CONCURRENCY / TRANSACTION BOUNDARY:** Exactly one logical SQLite write owner with bounded write queue, short transactions, WAL/FULL/foreign_keys=ON; no provider/network call inside a DB transaction.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Persistence
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 73. Artifact Lifecycle

**OWNER:** Artifact Store + repository metadata.

**IDENTITY:** artifact_id/version/content hash + generation lineage.  
**STATES:** materialization state is separate from QA/creative approval.  
**WRITE:** staged bytes → integrity/hash → durable metadata commit → reconciliation.  
**INVARIANTS:** Artifact READY != APPROVED; corrupt/missing/stale result cannot become continuity authority.  
**PERSISTENCE:** DB owns metadata; artifact store owns bytes.  
**QA:** technical integrity precedes creative QA.  
**RETENTION:** superseded artifacts governed by retention policy; lineage retained.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Artifact Lifecycle
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Artifact Lifecycle
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed Artifact Lifecycle
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After provider/local bytes exist; integrity/materialization reaches READY before creative QA.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Artifact Lifecycle
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 74. Static QA

**OWNER:** Static QA subsystem.  
**INPUTS:** actual generated image + canonical expectations from ShotIR/FullShotSpec/State/References.  
**DIMENSIONS:** technical integrity, identity, state/wardrobe, props/assets, environment, action/performance, camera/composition, lighting/style, continuity, narrative intent.  
**OUTPUTS:** evidence-bound findings/verdict.  
**INVARIANTS:** inspect actual artifact; blocking identity/state/story failure cannot be averaged away.  
**EVIDENCE LIMIT:** policy spike supports blocking-gate logic; real vision calibration remains acceptance work.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Static QA
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Static QA
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** qa_result_id + version/evaluator-rule version bound to exact image/artifact and expectation versions.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After current READY static artifact + expectations exist; before approval/state commit.

**CONCURRENCY / TRANSACTION BOUNDARY:** Evaluators/planners may run concurrently on independent immutable inputs; verdict/repair evidence commits against exact versions using repository revision rules; no provider side effect in QA transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** Evaluator/tool failure becomes QA_ERROR/review evidence and may retry/fallback; artifact defect routes to localization/repair and mandatory re-QA.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Static QA
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 75. Video / Motion QA

**OWNER:** Motion/Video QA.  
**INPUTS:** actual generated video + MotionDeltaSpec + FullShotSpec + continuity/state expectations.  
**CHECKS:** temporal action, identity drift, state/prop/location drift, camera motion, duration, speech/action sync where applicable, end-state observability, technical integrity.  
**OUTPUTS:** findings with time ranges/evidence.  
**INVARIANTS:** provider success does not imply motion QA pass.  
**LEGACY:** FlowKit reviewer is KEEP + EXTEND donor, not full canonical QA authority.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Video / Motion QA
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Video / Motion QA
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** qa_result_id + version/evaluator-rule version bound to exact video/artifact and MotionDeltaSpec/FullShotSpec versions.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After current READY motion artifact + MotionDeltaSpec expectations exist; before approval/state commit.

**CONCURRENCY / TRANSACTION BOUNDARY:** Evaluators/planners may run concurrently on independent immutable inputs; verdict/repair evidence commits against exact versions using repository revision rules; no provider side effect in QA transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** Evaluator/tool failure becomes QA_ERROR/review evidence and may retry/fallback; artifact defect routes to localization/repair and mandatory re-QA.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Video / Motion QA
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.
# 76. Continuity QA

**OWNER:** Continuity QA.  
**INPUTS:** canonical StateSnapshots, Reference bindings, adjacent approved artifacts, Scene/Shot lineage.  
**CHECKS:** identity, wardrobe, props, location/world, time/light, spatial, action, relationship/knowledge where observable.  
**OUTPUTS:** continuity findings and responsible layer candidate.  
**INVARIANTS:** visual similarity cannot override canonical state contradiction.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Continuity QA
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Continuity QA
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** qa_result_id + version/evaluator-rule version bound to exact StateSnapshot/Reference/adjacent artifact versions.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After current artifact/state/reference lineage exists; before continuity approval/propagation.

**CONCURRENCY / TRANSACTION BOUNDARY:** Evaluators/planners may run concurrently on independent immutable inputs; verdict/repair evidence commits against exact versions using repository revision rules; no provider side effect in QA transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** Evaluator/tool failure becomes QA_ERROR/review evidence and may retry/fallback; artifact defect routes to localization/repair and mandatory re-QA.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Continuity QA
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 77. Sequence QA

**PM-020 RESOLUTION — CANONICAL DECISION IN THIS MASTER**

SequenceQA is a **cross-shot / cross-scene quality layer**. It does not replace StaticQA, VideoQA or ShotQA and it is not a second Story/Shot authority.

**OWNER:** Sequence QA component.  
**IDENTITY:** sequence_qa_result_id/version bound to exact Sequence/Scene/Shot/artifact versions.  
**INPUTS:** accepted/QA'd shot artifacts, canonical Sequence/Scene/State/Story lineage, editorial ordering where applicable.  
**OUTPUTS:** cross-boundary defects/findings/gate verdict.

Minimum dimensions:

- narrative continuity;
- character continuity;
- wardrobe/prop continuity;
- location/world continuity;
- time/lighting continuity;
- spatial continuity;
- action continuity;
- visual rhythm;
- shot redundancy;
- coverage sufficiency;
- transition coherence;
- emotional progression;
- setup/payoff continuity;
- approved end-state propagation.

**INVARIANTS:**
- individual shot PASS does not guarantee Sequence PASS;
- SequenceQA findings cannot rewrite Story/Shot truth directly;
- evidence is localized to spans/transitions/shots/scenes;
- blocking cross-sequence defect can prevent sequence approval.

Repair route:

```text
DEFECT
→ ROOT CAUSE
→ RESPONSIBLE LAYER
→ MINIMUM REPAIR SCOPE
→ DEPENDENCY INVALIDATION
→ RE-GENERATE / RE-REALIZE
→ RE-QA
```

**PM-020 STATUS: RESOLVED IN MASTER.**



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Sequence QA
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Sequence QA
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After shot-level QA evidence exists for sequence members; before sequence-level approval/editorial release.

**CONCURRENCY / TRANSACTION BOUNDARY:** Evaluators/planners may run concurrently on independent immutable inputs; verdict/repair evidence commits against exact versions using repository revision rules; no provider side effect in QA transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** Evaluator/tool failure becomes QA_ERROR/review evidence and may retry/fallback; artifact defect routes to localization/repair and mandatory re-QA.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Sequence QA
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 78. Defect Localization

**OWNER:** QA diagnosis.  
**INPUTS:** Static/Motion/Continuity/Sequence findings + lineage.  
**OUTPUTS:** typed defect code, earliest responsible owner/layer, evidence, confidence.  
**INVARIANTS:** defect manifestation layer is not automatically repair layer.  
**QA:** localization must be explainable and regression-testable.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Defect Localization
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Defect Localization
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** N/A ? localization is diagnostic evidence; persisted finding/evaluation ID is evidence identity and cannot become domain truth.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After QA findings; before RepairPlan scope is accepted.

**CONCURRENCY / TRANSACTION BOUNDARY:** Evaluators/planners may run concurrently on independent immutable inputs; verdict/repair evidence commits against exact versions using repository revision rules; no provider side effect in QA transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Defect Localization
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 79. Targeted Production Repair

**FLOWKIT DECISION:** REWRITE canonical repair semantics while retaining useful regeneration mechanics.

**OWNER:** Production Repair subsystem.  
**MODES:** PATCH_IN_PLACE, REGENERATE_FROM_ANCHOR, REPLAN_SHOT, ESCALATE_UPSTREAM.  
**INPUTS:** localized defect + preserve obligations + dependency graph + cost/provider constraints.  
**OUTPUTS:** RepairPlan with preserve/patch/invalidate/recheck.  
**INVARIANTS:** do not append vague prompt suffix as canonical repair output; unchanged accepted dimensions must be regression-checked.  
**EVIDENCE LIMIT:** deterministic planner spike supports policy/invalidation behavior, not real generative repair success.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Targeted Production Repair
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Targeted Production Repair
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** repair_plan_id + version/evidence lineage; repair plan is not repaired artifact identity.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After defect localization and dependency analysis; before recompute/regenerate and mandatory re-QA.

**CONCURRENCY / TRANSACTION BOUNDARY:** Evaluators/planners may run concurrently on independent immutable inputs; verdict/repair evidence commits against exact versions using repository revision rules; no provider side effect in QA transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** Apply preserve/patch/invalidate/recheck plan; repeated failure escalates to earlier responsible layer; every repaired successor is re-QA'd.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Targeted Production Repair
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 80. Approval / State Commit

**OWNER:** Approval workflow + State Engine.

```text
QA PASS
→ explicit approval policy/human or authorized automatic approval
→ artifact acceptance
→ approved end-state derivation
→ canonical state commit
```

**HARD RULE:** NO QA APPROVAL → NO CANONICAL STATE COMMIT.  
**INVARIANTS:** technical completion, QA state, user approval and production lock are separate.  
**AUDIT:** approval/override carries actor/policy/reason/time/version.

### FM-007 state-commit identity lock

State commit writes/approves a canonical StateSnapshot version, then records the ApprovedEndStateDesignation referencing that exact snapshot. The designation contains approval lineage only and MUST NOT duplicate canonical state payload. Descendants consume state_snapshot_id/version.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Approval / State Commit
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Approval / State Commit
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed Approval / State Commit
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** approval_record_id plus referenced artifact/state_snapshot IDs/versions; StateSnapshot remains state identity.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After QA PASS + authorized approval; before canonical state propagation/commit becomes current.

**CONCURRENCY / TRANSACTION BOUNDARY:** Approval/state-current-pointer commit is serialized through repository ownership and validates exact QA/artifact/state versions atomically as designed; no provider call in transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Approval / State Commit
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 81. Editorial

**OWNER:** Editorial domain.  
**INPUTS:** approved shot artifacts + Script/Sequence/Scene lineage + timing/coverage.  
**OUTPUTS:** editorial timeline/version and edit decisions.  
**AUTHORITY:** may omit/reorder/select material under policy; cannot silently rewrite canonical Story truth.  
**LINEAGE:** omitted shots retain status/history.  
**QA:** continuity/rhythm/coverage after edit.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Editorial
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Editorial
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**IDENTITY:** timeline_id/version or editorial_timeline_id/version as editorial derivative identity; source Shot/Story identities are referenced, not replaced.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After approved Shot artifacts/lineage; before final Export.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Editorial
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 82. Audio

**OWNER:** Audio domain.  
**INPUTS:** locked screenplay/dialogue/narration/music policy + approved timing/edit.  
**OUTPUTS:** voice/music/SFX/mix artifacts with lineage.  
**INVARIANTS:** audio generation does not become Story authority; voice identity/reference rules are explicit.  
**QA:** sync, intelligibility, continuity, loudness/format, rights/provenance as applicable.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Audio
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Audio
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** audio_artifact_id/version/hash plus voice/music/SFX/mix lineage; Story/Character identity is referenced.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After locked screenplay/dialogue and approved timing/edit inputs; before final mix/export.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Audio
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 83. Export

**OWNER:** Export/Packaging application service.  
**INPUTS:** approved editorial/audio/artifacts + target format profile.  
**OUTPUTS:** deliverable + export manifest/hashes.  
**INVARIANTS:** export never mutates canonical source state; secrets/project-internal vault data excluded.  
**QA:** media integrity, dimensions/codecs, required tracks/metadata, manifest completeness.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Export
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Export
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** export_manifest_id/version/hash plus deliverable content hash; export is derivative identity only.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** After approved Editorial/Audio/artifacts; produces final derivative deliverable.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Export
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 84. Security

**OWNER:** Security architecture; credential subdomain governed by ADR-0016.

**CURRENT VS TARGET:** current FlowKit is React/Vite + FastAPI + SQLite + Chrome MV3/Flow execution. The following Electron configuration is TARGET architecture only and MUST NOT be described as already implemented.

## Target Electron renderer hardening baseline

- nodeIntegration = false
- contextIsolation = true
- sandbox = true
- webSecurity = true
- allowRunningInsecureContent = false
- no experimental Blink features
- restrict navigation/new windows
- validate IPC sender
- restrict external URL opening
- prefer custom app protocol over file://
- current supported Electron release

**RENDERER TRUST:** Renderer is low-privilege/untrusted for OS privileges, secrets, arbitrary filesystem and process execution.

**CONTEXT BRIDGE:** expose narrow capability-scoped methods only. No generic channel-invoke bridge, raw ipcRenderer, fs, child_process, generic shell bridge, unrestricted filesystem bridge or secret accessor is exposed.

**IPC:** typed/allowlisted channels/capabilities. Every privileged handler validates sender/origin/frame, request schema and project/session authorization; it performs one bounded capability, returns versioned response data and redacts privileged error detail.

**NAVIGATION / WINDOWS / EXTERNAL URLS:** restrict navigation and new-window creation; external URL opening follows explicit allowlist/policy and never grants privileged renderer context.

**REMOTE CONTENT POLICY:** privileged renderer surfaces do not load arbitrary remote content with Node/OS capability. Imported/external content is data-only by default.

**CSP TARGET CANDIDATE:** default-src self; script-src self; style-src self with the source-documented inline-style exception if required by the chosen UI stack; img/media restricted to self/data/blob as appropriate; connect-src restricted to explicit provider/local endpoints; object-src none; base-uri none; frame-ancestors none. Exact CSP is tightened during implementation without weakening the source security boundary.

**FILESYSTEM / PROCESS:** privileged filesystem operations are brokered against authorized roots; archive paths are validated; project/import content never gains generic shell execution.

**SECRETS:** Renderer never receives long-lived plaintext secrets. Electron Main / Host Security Broker owns safeStorage access. Production Utility receives only authorized short-lived scoped credential leases.

**NETWORK:** SSRF/network controls, TLS verification, explicit endpoint policy and bounded redirects/timeouts apply at privileged fetch boundaries.

**LOGGING / REDACTION:** Authorization/Cookie/API/OAuth/session/vault payloads are secret and excluded/redacted from logs/exports.

**SUPPLY CHAIN:** dependency/license/integrity review required before implementation adoption.

**EVIDENCE LIMIT:** target design only; packaged Electron/Windows enforcement remains implementation/release evidence, not claimed here.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Security
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Security
 is the cross-cutting policy/governance boundary defined by this section; it does not become Story/Shot/State/Profile truth.

**AUTHORITY:** Policy/enforcement authority only; no narrative, Shot, State or Profile truth ownership.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed Security
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** N/A ? Security is cross-cutting policy/enforcement authority, not a domain entity.

**STATE:** N/A ? security policy is enforced by process/IPC/broker boundaries; security findings/evidence carry status separately.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** N/A for the policy/boundary itself ? persist only the governed outputs, decisions/evidence, mappings or test artifacts in their owning repositories; this section creates no shadow truth store.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Cross-cutting and precondition to every privileged Renderer/Main/Utility/file/network/secret operation.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement as explicit policy/contract/evidence boundary, not as hidden prompt convention and not as a new canonical truth store.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 85. Credential Broker

**OWNER:** HOST SECURITY BROKER abstraction — ADR-0016.

Target topology:

```text
Electron Main + safeStorage
= long-lived secret owner

Production Utility
= short-lived scoped lease consumer

Renderer
= no long-lived secret access

FlowKit auth/session
= compatibility adapter only
```

**IDENTITY:** credential_id/version; lease_id with utility/provider/operation/version/correlation scope.  
**INVARIANTS:** project files store credential IDs/metadata only; logs/export never contain long-lived secrets; rotation invalidates stale leases.  
**EVIDENCE LIMIT:** architecture/local simulation exists; packaged target-Windows safeStorage proof remains implementation/release evidence.

### FM-004 explicit target security lock

ADR-0016 credential ownership composes with ?84 hardening: Electron Main/Host Security Broker owns long-lived safeStorage secrets; Renderer never receives them; Production Utility receives only scoped short-lived leases. Current FlowKit authentication/session behavior remains compatibility-only and does not prove target Electron controls are implemented.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Credential Broker
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Credential Broker
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed Credential Broker
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**STATE:** Credential metadata/lease lifecycle is version/expiry/revocation based; plaintext secret is never Renderer state.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Before any provider operation requiring a secret; lease issuance follows authorization and expires/revokes independently.

**CONCURRENCY / TRANSACTION BOUNDARY:** Host Security Broker serializes credential version/lease authorization; secret use is scoped/short-lived. DB stores metadata/IDs only and never wraps network calls in secret-state transactions.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** Deny/expire/revoke unsafe lease, re-establish broker/safeStorage availability, rotate credential version if required; Renderer never receives fallback plaintext.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Credential Broker
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 86. Observability

**OWNER:** Observability component.  
**LAYERS:** durable operational events + structured logs + metrics/tracing.  
**IDENTITY:** correlation IDs across project/run/job/provider/artifact/QA/repair.  
**INVARIANTS:** event log is audit evidence, not current-state authority; secrets redacted; OpenTelemetry is optional export adapter, not canonical event store.  
**OUTPUTS:** health/dashboard/metrics/evidence links.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Observability
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Observability
 is the cross-cutting policy/governance boundary defined by this section; it does not become Story/Shot/State/Profile truth.

**AUTHORITY:** Policy/enforcement authority only; no narrative, Shot, State or Profile truth ownership.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**STATE:** N/A ? observability records evidence/events; event status does not become current-state authority.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Cross-cutting; evidence emitted at authoritative transitions but never precedes/causes authority merely by being logged.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement as explicit policy/contract/evidence boundary, not as hidden prompt convention and not as a new canonical truth store.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 87. Error Model

**OWNER:** shared contract/application layer.  
**CLASSES:** validation, invariant, dependency, security, persistence, provider transport, provider ambiguity, artifact integrity, QA, repair, migration, cancellation.  
**OUTPUT:** typed error code + retryability + responsible boundary + evidence + user-safe message.  
**INVARIANTS:** generic "FAILED" cannot erase provider ambiguity or QA distinctions; secrets never embedded.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Error Model
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Error Model
 is the cross-cutting policy/governance boundary defined by this section; it does not become Story/Shot/State/Profile truth.

**AUTHORITY:** Policy/enforcement authority only; no narrative, Shot, State or Profile truth ownership.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**IDENTITY:** N/A ? Error Model defines typed error/defect contracts; each error/finding instance carries evidence/correlation identity, not domain identity.

**STATE:** N/A ? error taxonomy has no lifecycle; individual error/finding instances are immutable evidence tied to source versions.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Error/defect classification follows detection and precedes retry/repair/recovery routing.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement as explicit policy/contract/evidence boundary, not as hidden prompt convention and not as a new canonical truth store.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.


## 87A. Canonical Narrative Expansion Defect Registry

**PURPOSE:** Restore the exact REQUIRED NEW DEFECT CODES from NARRATIVE_EXPANSION_LADDER_PATCH_V1_FINAL.md and bind them to deterministic QA/repair/test routing.

**CANONICAL DEFINITION:** This registry defines stable defect-code identity/meaning for Narrative Expansion. A defect code is not an exception class, UI message, model prose, domain entity or canonical truth.

**OWNER:** QA / Defect Localization registry governance; detectors remain owned by the stage named per row.

**AUTHORITY:** exact code spelling comes from the accepted post-V0.16 source. ADR-0018/0019/0020 terminology controls interpretation where old code text says Beat/Shot.

**VERSION:** registry_version is explicit in implementation/evidence. Code spelling/meaning cannot silently drift; changed semantics require registry-version migration/review.

**PERSISTENCE:** QAResult/CritiqueFinding/DefectLocalization evidence persists code + detector/rule version + exact affected artifact/version + disposition + evidence.

**ORDERING / REPAIR CHAIN:** DEFECT ? ROOT CAUSE ? RESPONSIBLE LAYER ? MINIMUM REPAIR SCOPE ? INVALIDATION ? RECOMPUTE / REGENERATE ? RE-QA.

**SEVERITY / BLOCKING RULE:** the source declares required codes but does not assign one immutable severity/blocking class to every code. Therefore the registry records POLICY_BOUND rather than inventing fixed severity. A versioned QA/gate policy MUST emit explicit severity and blocking disposition for every finding instance.

**SHOT_NOT_BOUND_TO_BEAT NORMALIZATION:** code spelling is preserved exactly for source fidelity; canonical meaning is ?ShotListItem missing parent SceneDramaticBeat binding? because generic persistent Beat authority is prohibited by ADR-0018.

| CODE | OWNER / DETECTOR | STAGE | TRIGGER CONDITION | SEVERITY CLASS | AFFECTED ARTIFACT | ROOT-CAUSE LAYER | BLOCKING / NON-BLOCKING SEMANTICS | REPAIR TARGET | MINIMUM REPAIR SCOPE | INVALIDATION EXPECTATION | RECHECK / QA REQUIREMENT |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LOGLINE_NO_FOCAL_SUBJECT | Logline Gate / Story QA | Logline | required logline semantic element or specificity is absent | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | Logline version | Logline / Story Intelligence | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | Logline | affected Logline version only, then descendants if accepted meaning changes | accepted Logline change invalidates StoryCore/expansion descendants through ?63 | re-run Logline gate + NarrativeTrace |
| LOGLINE_NO_GOAL_OR_CENTRAL_QUESTION | Logline Gate / Story QA | Logline | required logline semantic element or specificity is absent | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | Logline version | Logline / Story Intelligence | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | Logline | affected Logline version only, then descendants if accepted meaning changes | accepted Logline change invalidates StoryCore/expansion descendants through ?63 | re-run Logline gate + NarrativeTrace |
| LOGLINE_NO_OPPOSITION | Logline Gate / Story QA | Logline | required logline semantic element or specificity is absent | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | Logline version | Logline / Story Intelligence | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | Logline | affected Logline version only, then descendants if accepted meaning changes | accepted Logline change invalidates StoryCore/expansion descendants through ?63 | re-run Logline gate + NarrativeTrace |
| LOGLINE_NO_STAKES | Logline Gate / Story QA | Logline | required logline semantic element or specificity is absent | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | Logline version | Logline / Story Intelligence | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | Logline | affected Logline version only, then descendants if accepted meaning changes | accepted Logline change invalidates StoryCore/expansion descendants through ?63 | re-run Logline gate + NarrativeTrace |
| LOGLINE_GENERIC | Logline Gate / Story QA | Logline | required logline semantic element or specificity is absent | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | Logline version | Logline / Story Intelligence | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | Logline | affected Logline version only, then descendants if accepted meaning changes | accepted Logline change invalidates StoryCore/expansion descendants through ?63 | re-run Logline gate + NarrativeTrace |
| MACRO_BEAT_NO_FUNCTION | Macro Structure Gate / Story Structure | MacroStoryBeat | dramatic_function is missing or cannot justify the beat | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | MacroStoryBeat / MacroBeatSheet projection | MacroStoryBeat / Story Structure | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | MacroStoryBeat or earliest responsible StoryCore cause | affected beat plus only causally dependent structural descendants | revised MacroStoryBeat invalidates dependent Sequence/Scene projections through ?63 | re-run Macro Structure Gate + collapse/causality checks |
| MACRO_BEAT_NO_STATE_CHANGE | Macro Structure Gate / Story Structure | MacroStoryBeat | required macro movement has no defensible state/change consequence | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | MacroStoryBeat / MacroBeatSheet projection | MacroStoryBeat / Story Structure | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | MacroStoryBeat or earliest responsible StoryCore cause | affected beat plus only causally dependent structural descendants | revised MacroStoryBeat invalidates dependent Sequence/Scene projections through ?63 | re-run Macro Structure Gate + collapse/causality checks |
| MACRO_BEAT_CAUSAL_GAP | Macro Structure Gate / Story Structure | MacroStoryBeat | macro beat lacks required causal enablement/rationale | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | MacroStoryBeat / MacroBeatSheet projection | MacroStoryBeat / Story Structure | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | MacroStoryBeat or earliest responsible StoryCore cause | affected beat plus only causally dependent structural descendants | revised MacroStoryBeat invalidates dependent Sequence/Scene projections through ?63 | re-run Macro Structure Gate + collapse/causality checks |
| SEQUENCE_NO_TURN | Sequence Causality Gate / Story Structure | SequencePlan / Sequence | Sequence has no major turn | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | SequencePlan + canonical Sequence | Sequence / Story Structure | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | SequencePlan/Sequence or earliest upstream MacroStoryBeat cause | affected Sequence branch only unless upstream cause requires wider repair | accepted Sequence change invalidates dependent Scene/Beat/shot descendants through ?63 | re-run Sequence Causality Gate + NarrativeTrace |
| SEQUENCE_NO_ESCALATION | Sequence Causality Gate / Story Structure | SequencePlan / Sequence | Sequence lacks required escalation | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | SequencePlan + canonical Sequence | Sequence / Story Structure | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | SequencePlan/Sequence or earliest upstream MacroStoryBeat cause | affected Sequence branch only unless upstream cause requires wider repair | accepted Sequence change invalidates dependent Scene/Beat/shot descendants through ?63 | re-run Sequence Causality Gate + NarrativeTrace |
| SEQUENCE_CAUSAL_GAP | Sequence Causality Gate / Story Structure | SequencePlan / Sequence | opening/closing/next-sequence causal chain is not supported | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | SequencePlan + canonical Sequence | Sequence / Story Structure | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | SequencePlan/Sequence or earliest upstream MacroStoryBeat cause | affected Sequence branch only unless upstream cause requires wider repair | accepted Sequence change invalidates dependent Scene/Beat/shot descendants through ?63 | re-run Sequence Causality Gate + NarrativeTrace |
| SCENE_NO_FUNCTION | Scene Function Gate / Story Scene QA | Scene | scene contract violates the named condition: Scene cannot justify narrative/dramatic existence | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | canonical Scene / SceneListManifest projection | Scene / Story Scene Engine | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | Scene or earliest Sequence/Macro cause | affected Scene and dependent SceneDramaticBeat/directing/shot branch | Scene revision invalidates dependent beat/directing/shot artifacts through ?63 | re-run Scene Function Gate + state/causality trace |
| SCENE_NO_CONFLICT | Scene Function Gate / Story Scene QA | Scene | scene contract violates the named condition: Scene requires conflict/opposition under profile but has none | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | canonical Scene / SceneListManifest projection | Scene / Story Scene Engine | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | Scene or earliest Sequence/Macro cause | affected Scene and dependent SceneDramaticBeat/directing/shot branch | Scene revision invalidates dependent beat/directing/shot artifacts through ?63 | re-run Scene Function Gate + state/causality trace |
| SCENE_NO_TURN | Scene Function Gate / Story Scene QA | Scene | scene contract violates the named condition: Scene lacks expected turn/change | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | canonical Scene / SceneListManifest projection | Scene / Story Scene Engine | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | Scene or earliest Sequence/Macro cause | affected Scene and dependent SceneDramaticBeat/directing/shot branch | Scene revision invalidates dependent beat/directing/shot artifacts through ?63 | re-run Scene Function Gate + state/causality trace |
| SCENE_NO_STATE_CHANGE | Scene Function Gate / Story Scene QA | Scene | scene contract violates the named condition: Scene has neither state change nor explicit accepted exception purpose | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | canonical Scene / SceneListManifest projection | Scene / Story Scene Engine | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | Scene or earliest Sequence/Macro cause | affected Scene and dependent SceneDramaticBeat/directing/shot branch | Scene revision invalidates dependent beat/directing/shot artifacts through ?63 | re-run Scene Function Gate + state/causality trace |
| MICRO_BEAT_NO_INTENTION | Beat Movement Gate / Story Scene Dramatic Beat QA | SceneDramaticBeat | SceneDramaticBeat lacks intention | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | SceneDramaticBeat / SceneBreakdownManifest projection | SceneDramaticBeat | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | SceneDramaticBeat or earliest responsible Scene cause | affected beat and its directing/shot descendants | Beat revision invalidates audience/directing/blocking/cinematography/shot descendants | re-run Beat Movement Gate + downstream trace |
| MICRO_BEAT_NO_ACTION | Beat Movement Gate / Story Scene Dramatic Beat QA | SceneDramaticBeat | SceneDramaticBeat lacks action/tactic | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | SceneDramaticBeat / SceneBreakdownManifest projection | SceneDramaticBeat | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | SceneDramaticBeat or earliest responsible Scene cause | affected beat and its directing/shot descendants | Beat revision invalidates audience/directing/blocking/cinematography/shot descendants | re-run Beat Movement Gate + downstream trace |
| MICRO_BEAT_NO_REACTION | Beat Movement Gate / Story Scene Dramatic Beat QA | SceneDramaticBeat | SceneDramaticBeat lacks reaction/resistance/new information where required | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | SceneDramaticBeat / SceneBreakdownManifest projection | SceneDramaticBeat | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | SceneDramaticBeat or earliest responsible Scene cause | affected beat and its directing/shot descendants | Beat revision invalidates audience/directing/blocking/cinematography/shot descendants | re-run Beat Movement Gate + downstream trace |
| MICRO_BEAT_NO_CHANGE | Beat Movement Gate / Story Scene Dramatic Beat QA | SceneDramaticBeat | SceneDramaticBeat lacks micro-change | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | SceneDramaticBeat / SceneBreakdownManifest projection | SceneDramaticBeat | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | SceneDramaticBeat or earliest responsible Scene cause | affected beat and its directing/shot descendants | Beat revision invalidates audience/directing/blocking/cinematography/shot descendants | re-run Beat Movement Gate + downstream trace |
| SCREENPLAY_REALIZATION_DRIFT | Screenplay Realization / Story QA | Screenplay Realization | screenplay scene draft fails to realize accepted Scene/Beat/character/knowledge/dialogue constraints | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | Screenplay scene draft/version | Screenplay Realization | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | affected screenplay realization or earliest violated upstream source | affected screenplay scene(s) only unless upstream source is wrong | accepted screenplay correction invalidates ScriptLock/directing/shot descendants that consumed old version | re-run screenplay realization checks + Story Quality Gate |
| SHOT_NO_NARRATIVE_FUNCTION | ShotExpansion / Shot Coverage / ShotEligibilityGate | Shot planning | ShotListItem lacks traceable dramatic_function/reason_for_exist | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | ShotListItem / ShotListManifest | Shot Planning | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | ShotExpansion/ShotListItem or earliest directing/coverage cause | affected ShotListItem/coverage set only; never create a parallel shot identity | Shot planning change invalidates FullShotSpec/ShotIR/provider derivatives for affected shot_ids | re-run coverage + ShotEligibilityGate + ShotDecisionTrace |
| SHOT_NOT_BOUND_TO_BEAT | ShotExpansion / Shot Coverage / ShotEligibilityGate | Shot planning | ShotListItem lacks canonical parent_scene_dramatic_beat_id; legacy code name 'BEAT' means SceneDramaticBeat under ADR-0018 | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | ShotListItem / ShotListManifest | Shot Planning | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | ShotExpansion/ShotListItem or earliest directing/coverage cause | affected ShotListItem/coverage set only; never create a parallel shot identity | Shot planning change invalidates FullShotSpec/ShotIR/provider derivatives for affected shot_ids | re-run coverage + ShotEligibilityGate + ShotDecisionTrace |
| SHOT_MISSING_REQUIRED_COVERAGE | ShotExpansion / Shot Coverage / ShotEligibilityGate | Shot planning | required coverage function is absent | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | ShotListItem / ShotListManifest | Shot Planning | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | ShotExpansion/ShotListItem or earliest directing/coverage cause | affected ShotListItem/coverage set only; never create a parallel shot identity | Shot planning change invalidates FullShotSpec/ShotIR/provider derivatives for affected shot_ids | re-run coverage + ShotEligibilityGate + ShotDecisionTrace |
| BUDGET_RUNTIME_OVERFLOW | DurationBudget validator | Budget Planning | child/runtime allocations exceed configured parent tolerance/profile | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | DurationBudget | DurationBudget | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | DurationBudget or governing Structure/Profile input | affected budget allocation branch | new accepted budget invalidates dependent Sequence/Scene/Shot planning only | re-run budget reconciliation and downstream range gates |
| BUDGET_SCENE_OVERFLOW | SceneBudget validator | Scene planning budget | scene count/duration exceeds accepted range without approved rationale | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | SceneBudget / SceneListManifest | SceneBudget | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | SceneBudget/SequencePlan | affected Sequence scene-planning branch | new SceneBudget invalidates dependent SceneListManifest planning | re-run SceneBudget range + Scene Function planning checks |
| BUDGET_SHOT_OVERFLOW | ShotBudget validator | Shot planning budget | shot count/duration exceeds accepted range without approved rationale | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | ShotBudget / ShotListManifest | ShotBudget | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | ShotBudget/CoverageStrategy | affected Scene/Sequence shot-planning branch | new ShotBudget invalidates affected ShotExpansion/ShotList planning | re-run ShotBudget + coverage/eligibility checks |
| EXPANSION_LOGLINE_DRIFT | Expansion Drift / Collapse validator | Narrative expansion | child expansion fails reverse-compression/realization of its accepted parent function at LOGLINE | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | child expansion artifact and parent trace | earliest divergent expansion layer | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | earliest child layer whose content diverges from parent authority | minimum divergent branch only; escalate upstream only when parent authority itself is defective | repair creates successor child versions and invalidates only their descendants | re-run collapse test + layer gate + bidirectional NarrativeTrace |
| EXPANSION_MACRO_BEAT_DRIFT | Expansion Drift / Collapse validator | Narrative expansion | child expansion fails reverse-compression/realization of its accepted parent function at MACRO BEAT | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | child expansion artifact and parent trace | earliest divergent expansion layer | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | earliest child layer whose content diverges from parent authority | minimum divergent branch only; escalate upstream only when parent authority itself is defective | repair creates successor child versions and invalidates only their descendants | re-run collapse test + layer gate + bidirectional NarrativeTrace |
| EXPANSION_SEQUENCE_DRIFT | Expansion Drift / Collapse validator | Narrative expansion | child expansion fails reverse-compression/realization of its accepted parent function at SEQUENCE | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | child expansion artifact and parent trace | earliest divergent expansion layer | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | earliest child layer whose content diverges from parent authority | minimum divergent branch only; escalate upstream only when parent authority itself is defective | repair creates successor child versions and invalidates only their descendants | re-run collapse test + layer gate + bidirectional NarrativeTrace |
| EXPANSION_SCENE_DRIFT | Expansion Drift / Collapse validator | Narrative expansion | child expansion fails reverse-compression/realization of its accepted parent function at SCENE | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | child expansion artifact and parent trace | earliest divergent expansion layer | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | earliest child layer whose content diverges from parent authority | minimum divergent branch only; escalate upstream only when parent authority itself is defective | repair creates successor child versions and invalidates only their descendants | re-run collapse test + layer gate + bidirectional NarrativeTrace |
| EXPANSION_MICRO_BEAT_DRIFT | Expansion Drift / Collapse validator | Narrative expansion | child expansion fails reverse-compression/realization of its accepted parent function at MICRO BEAT | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | child expansion artifact and parent trace | earliest divergent expansion layer | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | earliest child layer whose content diverges from parent authority | minimum divergent branch only; escalate upstream only when parent authority itself is defective | repair creates successor child versions and invalidates only their descendants | re-run collapse test + layer gate + bidirectional NarrativeTrace |
| EXPANSION_SCREENPLAY_DRIFT | Expansion Drift / Collapse validator | Narrative expansion | child expansion fails reverse-compression/realization of its accepted parent function at SCREENPLAY | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | child expansion artifact and parent trace | earliest divergent expansion layer | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | earliest child layer whose content diverges from parent authority | minimum divergent branch only; escalate upstream only when parent authority itself is defective | repair creates successor child versions and invalidates only their descendants | re-run collapse test + layer gate + bidirectional NarrativeTrace |
| EXPANSION_SHOT_DRIFT | Expansion Drift / Collapse validator | Narrative expansion | child expansion fails reverse-compression/realization of its accepted parent function at SHOT | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | child expansion artifact and parent trace | earliest divergent expansion layer | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | earliest child layer whose content diverges from parent authority | minimum divergent branch only; escalate upstream only when parent authority itself is defective | repair creates successor child versions and invalidates only their descendants | re-run collapse test + layer gate + bidirectional NarrativeTrace |
| TRACE_ORPHAN_ARTIFACT | NarrativeTrace validator | Traceability | derived artifact has no valid required canonical ancestry | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | NarrativeTrace / referenced artifact lineage | Lineage / Traceability | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | trace metadata if canonical parents exist; otherwise escalate to missing/invalid parent owner | trace record/edges only unless canonical parent repair is required | lineage repair invalidates only consumers whose ancestry/version binding changed | re-run orphan/missing-parent/cycle + top-down/bottom-up traversal checks |
| TRACE_MISSING_PARENT | NarrativeTrace validator | Traceability | declared required parent reference is absent/unresolvable | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | NarrativeTrace / referenced artifact lineage | Lineage / Traceability | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | trace metadata if canonical parents exist; otherwise escalate to missing/invalid parent owner | trace record/edges only unless canonical parent repair is required | lineage repair invalidates only consumers whose ancestry/version binding changed | re-run orphan/missing-parent/cycle + top-down/bottom-up traversal checks |
| TRACE_CYCLE | NarrativeTrace validator | Traceability | NarrativeTrace contains a cycle where canonical hierarchy requires acyclic ancestry | POLICY_BOUND ? source fixes the code, not one immutable severity; versioned QA/gate policy assigns severity without changing code | NarrativeTrace / referenced artifact lineage | Lineage / Traceability | POLICY_BOUND ? evaluator/gate records blocking or non-blocking disposition explicitly; code text alone is not the disposition | trace metadata if canonical parents exist; otherwise escalate to missing/invalid parent owner | trace record/edges only unless canonical parent repair is required | lineage repair invalidates only consumers whose ancestry/version binding changed | re-run orphan/missing-parent/cycle + top-down/bottom-up traversal checks |

**REGISTRY INVARIANTS:**
- Exactly the 36 source-required Narrative Expansion codes above are restored in this registry.
- Free-text explanation supplements but never replaces code identity.
- Same code + different severity/disposition remains the same defect type under a different policy context.
- Repair does not rewrite upstream authority merely because a downstream symptom is observed.
- Every repaired finding is rechecked by its owning gate and all invalidated downstream gates.
- Historical finding/code/evidence remains auditable after successor repair PASS.

# 88. Recovery

**OWNER:** Recovery Coordinator/Orchestrator.  
**INPUTS:** persisted job/state/artifact/migration state.  
**OUTPUTS:** resume/reconcile/quarantine/retry/hold actions.  
**INVARIANTS:** restart loses no accepted decision or submitted paid-job lineage; ambiguous side effect reconciles before resubmit; stale results are retained/quarantined, never auto-applied.  
**QA:** crash-point/fault-injection scenarios.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Recovery
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Recovery
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** N/A ? Recovery Coordinator is a service; RecoveryEvent/checkpoint/job/artifact identities carry durable recovery evidence.

**STATE:** N/A ? coordinator service state is represented by the durable job/artifact/migration/recovery records it reconciles.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Startup/mid-run recovery reconciles durable state before scheduler normal admission resumes.

**CONCURRENCY / TRANSACTION BOUNDARY:** Recovery coordinates leases/jobs/artifacts before scheduler admission; durable mutations use one-writer/CAS rules and remote reconciliation calls occur outside DB transactions.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** Restore durable state, reconcile leases/provider ambiguity/artifacts, then resume only through the closed transition/recovery rules; never blind-resubmit uncertain paid work.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Recovery
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 89. Backup / Migration

**OWNER:** Persistence/Migration subsystem.  
**INPUTS:** schema/app version + DB + immutable referenced artifacts + in-flight provider state.  
**OUTPUTS:** migration state, backup manifest, restore result.  
**INVARIANTS:** update cannot destroy paid-job reconciliation ability; transformative/destructive migration is resumable/rollback-aware; newer unsupported schema blocks unsafe writes.  
**SECURITY:** backup excludes credential vault/plaintext secret.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Backup / Migration
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Backup / Migration
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**IDENTITY:** migration_run_id/checkpoint + schema/app version; backup_manifest_id/hash for backup identity.

**STATE:** N/A ? source does not define a separate fixed state enum for this component; accepted output lifecycle is represented by immutable versions plus explicit approval/supersession/invalidation evidence under ?62/?63/?80.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Compatibility/migration/backup gate completes before unsafe writes against incompatible schema and before release.

**CONCURRENCY / TRANSACTION BOUNDARY:** Migration/restore obtains exclusive compatibility/write gate as required; transformations are checkpointed/short-transaction bounded and provider jobs remain reconcilable.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** Use startup reconciliation, migration checkpoints and verified backup/restore; corruption or incompatible schema blocks unsafe writes rather than destructive auto-fix.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Backup / Migration
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 90. FlowKit Legacy Anti-Corruption Boundary

FlowKit remains useful but cannot own canonical Studio concepts.

Disposition:

```text
ENTITY       = KEEP + EXTEND
REFERENCE    = KEEP + EXTEND
CONTINUITY   = REWRITE
STORY        = REWRITE
SCENE        = ADAPT
BEAT         = REPLACE
SHOT         = REPLACE
PROMPT       = REWRITE
GENERATION   = KEEP + EXTEND
PROVIDER     = ADAPT
QUEUE        = KEEP + EXTEND
RETRY        = KEEP + EXTEND
RESUME       = KEEP + EXTEND
PERSISTENCE  = ADAPT
QA           = KEEP + EXTEND
REPAIR       = REWRITE
```

Anti-corruption law:
- FlowKit operational Scene object never becomes cinematic Scene authority.
- FlowKit prompt fields are compatibility inputs/compiled outputs only.
- FlowKit entity/reference/media lifecycle can back adapters but canonical IDs/contracts remain Studio-owned.
- FlowKit provider/session mechanisms are compatibility implementations behind canonical provider/security ports.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make FlowKit Legacy Anti-Corruption Boundary
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** FlowKit Legacy Anti-Corruption Boundary
 is the cross-cutting policy/governance boundary defined by this section; it does not become Story/Shot/State/Profile truth.

**OWNER:** Legacy Integration / Anti-Corruption layer

**AUTHORITY:** Policy/enforcement authority only; no narrative, Shot, State or Profile truth ownership.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed FlowKit Legacy Anti-Corruption Boundary
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** N/A ? anti-corruption boundary is a service/architecture boundary, not a domain entity.

**STATE:** N/A ? architecture boundary has no domain lifecycle.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** N/A for the policy/boundary itself ? persist only the governed outputs, decisions/evidence, mappings or test artifacts in their owning repositories; this section creates no shadow truth store.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Legacy data crosses anti-corruption adapters before entering canonical Studio domains.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Changes create a new policy/mapping/evidence version and invalidate only claims/consumers that depended on the superseded version; canonical domain truth is not silently mutated.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement as explicit policy/contract/evidence boundary, not as hidden prompt convention and not as a new canonical truth store.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** This section is itself the explicit legacy/adaptation boundary; mappings remain compatibility/import concerns and never elevate FlowKit operational schemas into canonical Studio truth.
# 91. FlowKit Current → Canonical Mapping

| Current FlowKit concept | Canonical target mapping |
| --- | --- |
| Project.story text | Story import/seed only; not StoryCore authority |
| Entity | Entity adapter → canonical Entity/EntityVersion |
| entity media_id/reference | ReferenceAsset/binding compatibility projection |
| operational Scene | Shot/GenerationJob compatibility projection; never canonical Scene |
| scene prompt/video_prompt | compiled/legacy derivative; never canonical FullShotSpec/ShotIR |
| scene chain/parent media | conditioning lineage; semantic continuity from StateSnapshot |
| request queue | Orchestrator/GenerationJob adapter |
| Flow/Omni generation | Provider Adapter |
| retry/re-poll | Recovery primitive under typed canonical policy |
| video reviewer | Video QA donor/adapter |
| SQLite current schema | migration source only; canonical schema follows Master contracts |



### FM2-003 ? Local contract completeness

**PURPOSE:** Make FlowKit Current → Canonical Mapping
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** FlowKit Current → Canonical Mapping
 is the cross-cutting policy/governance boundary defined by this section; it does not become Story/Shot/State/Profile truth.

**OWNER:** Architecture + Migration mapping authority

**AUTHORITY:** Policy/enforcement authority only; no narrative, Shot, State or Profile truth ownership.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed FlowKit Current → Canonical Mapping
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** N/A ? mapping specification is architecture/migration policy; mapping evidence references source and target IDs.

**STATE:** N/A ? mapping policy has no domain lifecycle.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** N/A for the policy/boundary itself ? persist only the governed outputs, decisions/evidence, mappings or test artifacts in their owning repositories; this section creates no shadow truth store.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Mapping is evaluated during import/migration/adaptation before legacy semantics can populate canonical records.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Changes create a new policy/mapping/evidence version and invalidate only claims/consumers that depended on the superseded version; canonical domain truth is not silently mutated.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement as explicit policy/contract/evidence boundary, not as hidden prompt convention and not as a new canonical truth store.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** This section is itself the explicit legacy/adaptation boundary; mappings remain compatibility/import concerns and never elevate FlowKit operational schemas into canonical Studio truth.
# 92. Persistence Migration Strategy

1. Inventory existing FlowKit project/entity/scene/request/media rows.
2. Introduce canonical IDs/version tables without mutating historical source.
3. Migrate/import Projects and Entities through validators.
4. Map legacy operational Scene records to compatibility Shot/GenerationJob lineage only where meaning is provable.
5. Do not infer cinematic SceneDramaticBeat/FullShotSpec from prompt prose without explicit migration review.
6. Preserve media/provider remote IDs as external lineage.
7. Establish one logical writer and canonical repository boundary.
8. Create migration journal/checkpoints and backup before transformation.
9. Retain source identifiers for audit/reconciliation.
10. Unknown/ambiguous mappings become import findings, not fabricated canonical truth.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Persistence Migration Strategy
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Persistence Migration Strategy
 is the provider/model-neutral canonical component boundary defined by this section and owns only the output/decision scope stated locally.

**OWNER:** Persistence / Migration subsystem

**AUTHORITY:** Owns only its declared output/decision scope; accepted upstream authority and locked invariants outrank it, and downstream/provider derivatives cannot rewrite it.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed Persistence Migration Strategy
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** migration_run_id/checkpoint + source/target schema versions; no new creative identity.

**STATE:** Migration state is explicit checkpoint/progress/blocked/completed evidence under migration policy; creative state is untouched.

**MUTABILITY:** Accepted/persisted versions are immutable; semantic change creates a successor version or a new evidence record and never silently rewrites a locked version.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Backup/checkpoint/schema compatibility precedes transformative migration; migration/reconciliation precedes normal scheduler admission.

**CONCURRENCY / TRANSACTION BOUNDARY:** Migration/restore obtains exclusive compatibility/write gate as required; transformations are checkpointed/short-transaction bounded and provider jobs remain reconcilable.

**INVALIDATION:** Any accepted upstream/profile/rule/version change invalidates only dependent derived outputs through ?63; unaffected accepted artifacts remain valid.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** Use startup reconciliation, migration checkpoints and verified backup/restore; corruption or incompatible schema blocks unsafe writes rather than destructive auto-fix.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement Persistence Migration Strategy
 behind a typed contract/service/repository port with exact version bindings and no provider-specific leakage into upstream canonical truth.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** This section is itself the explicit legacy/adaptation boundary; mappings remain compatibility/import concerns and never elevate FlowKit operational schemas into canonical Studio truth.
# 93. UI / Dashboard Adaptation Boundary

**CURRENT UI:** React/Vite dashboard attached to FastAPI/FlowKit concepts.

**TARGET UI:** Renderer consumes view models/use-cases through narrow typed bridge.  
**RULE:** UI is never canonical authority; forms edit commands/drafts, repository/application layer commits accepted versions.  
**REQUIRED VIEWS:** authority/provenance, profile resolution, story hierarchy, shot trace, state/reference, job/QA/repair, ambiguity/recovery, evidence status.  
**LEGACY:** existing dashboard may inform UX but must not force canonical domain to retain old Scene/request schemas.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make UI / Dashboard Adaptation Boundary
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** UI / Dashboard Adaptation Boundary
 is the cross-cutting policy/governance boundary defined by this section; it does not become Story/Shot/State/Profile truth.

**OWNER:** Renderer/Application boundary

**AUTHORITY:** Policy/enforcement authority only; no narrative, Shot, State or Profile truth ownership.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed UI / Dashboard Adaptation Boundary
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** N/A ? UI/Application bridge is a presentation/application boundary; it cannot allocate canonical domain identity.

**STATE:** N/A ? UI view state is non-authoritative and cannot replace repository state.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** N/A for the policy/boundary itself ? persist only the governed outputs, decisions/evidence, mappings or test artifacts in their owning repositories; this section creates no shadow truth store.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Renderer reads view models and issues typed commands only after canonical application authorization; UI never writes repository truth directly.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Changes create a new policy/mapping/evidence version and invalidate only claims/consumers that depended on the superseded version; canonical domain truth is not silently mutated.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement as explicit policy/contract/evidence boundary, not as hidden prompt convention and not as a new canonical truth store.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.
# 94. Testing Strategy

Design target only; tests have not been executed for this Master.

Required layers:
- contract/schema tests;
- semantic invariant tests;
- domain service unit tests;
- repository/concurrency tests;
- compiler determinism/golden fixtures;
- provider adapter contract tests;
- orchestration model/fault tests;
- security boundary tests;
- QA/repair fixture tests;
- migration/backup/recovery tests;
- anti-corruption mapping tests;
- end-to-end acceptance against representative projects.

No real-provider dependency is required for core canonical-domain unit tests.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Testing Strategy
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Testing Strategy
 is the cross-cutting policy/governance boundary defined by this section; it does not become Story/Shot/State/Profile truth.

**OWNER:** Test / Evidence governance

**AUTHORITY:** Policy/enforcement authority only; no narrative, Shot, State or Profile truth ownership.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed Testing Strategy
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** N/A ? Testing Strategy is evidence/governance policy; test cases/results have test/evidence IDs outside canonical production truth.

**STATE:** N/A ? testing strategy itself has no production lifecycle.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** N/A for the policy/boundary itself ? persist only the governed outputs, decisions/evidence, mappings or test artifacts in their owning repositories; this section creates no shadow truth store.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Contract/invariant tests are derived after design contracts and run before evidence gates that claim implementation correctness.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Changes create a new policy/mapping/evidence version and invalidate only claims/consumers that depended on the superseded version; canonical domain truth is not silently mutated.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement as explicit policy/contract/evidence boundary, not as hidden prompt convention and not as a new canonical truth store.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 95. Benchmark Strategy

Benchmarks are evidence instruments, not design authority.

Required benchmark families:
- metadata/repository throughput;
- 300-shot scheduling/admission;
- artifact ingest/reconciliation;
- compiler throughput/determinism;
- Static/Motion/Sequence QA;
- repair scope/effectiveness;
- crash/recovery;
- provider cost/latency under evidence-versioned profiles;
- UI responsiveness for long-form projects.

Synthetic/local benchmark cannot close a live/target gate requiring stronger evidence class.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Benchmark Strategy
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Benchmark Strategy
 is the cross-cutting policy/governance boundary defined by this section; it does not become Story/Shot/State/Profile truth.

**OWNER:** Benchmark / Evidence governance

**AUTHORITY:** Policy/enforcement authority only; no narrative, Shot, State or Profile truth ownership.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed Benchmark Strategy
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** benchmark_result_id/evidence_id + benchmark/profile/tool version; benchmark evidence is not domain truth.

**STATE:** N/A ? benchmark strategy itself has no production lifecycle.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Benchmarks run only with declared profile/tool/evidence versions before performance/cost claims or release gates.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Changes create a new policy/mapping/evidence version and invalidate only claims/consumers that depended on the superseded version; canonical domain truth is not silently mutated.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement as explicit policy/contract/evidence boundary, not as hidden prompt convention and not as a new canonical truth store.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 96. Calibration Strategy

QA thresholds/models require calibrated datasets and versioned policy.

Calibration records:
- dataset/version/provenance;
- dimension labels and blocking cases;
- inter-reviewer disagreement;
- false-negative/false-positive measures where meaningful;
- model/reviewer version;
- threshold/rubric version.

Static QA policy proof is not vision calibration. Repair planner policy proof is not generative repair efficacy proof.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Calibration Strategy
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Calibration Strategy
 is the cross-cutting policy/governance boundary defined by this section; it does not become Story/Shot/State/Profile truth.

**OWNER:** QA Calibration governance

**AUTHORITY:** Policy/enforcement authority only; no narrative, Shot, State or Profile truth ownership.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed Calibration Strategy
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** calibration_record_id/version bound to dataset/rubric/model/reviewer versions.

**STATE:** Calibration records are versioned evidence; accepted/superseded policy versions remain auditable.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Calibration precedes use of QA thresholds/models as acceptance authority.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Changes create a new policy/mapping/evidence version and invalidate only claims/consumers that depended on the superseded version; canonical domain truth is not silently mutated.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement as explicit policy/contract/evidence boundary, not as hidden prompt convention and not as a new canonical truth store.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 97. Product Acceptance

Product acceptance requires more than design completion.

Acceptance dimensions:
- canonical authority/invariants preserved;
- target topology implemented securely;
- migration/recovery demonstrated;
- real provider adapters obey ambiguity rules;
- QA calibrated at required evidence class;
- repair efficacy evaluated;
- representative performance/cost measured;
- user workflow/UX acceptance;
- export integrity.

This Master candidate alone does not satisfy product acceptance.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Product Acceptance
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Product Acceptance
 is the cross-cutting policy/governance boundary defined by this section; it does not become Story/Shot/State/Profile truth.

**OWNER:** Product Acceptance governance

**AUTHORITY:** Policy/enforcement authority only; no narrative, Shot, State or Profile truth ownership.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed Product Acceptance
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** acceptance_record_id/version or gate-evidence identity; it references product evidence and never becomes Story/Shot/State truth.

**STATE:** Acceptance record = NOT_EVALUATED / BLOCKED / ACCEPTED only if implementation defines those governance statuses; production-domain states remain unchanged.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Product acceptance evaluates accumulated implementation/runtime evidence after component/release prerequisites; Master text alone cannot satisfy it.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Changes create a new policy/mapping/evidence version and invalidate only claims/consumers that depended on the superseded version; canonical domain truth is not silently mutated.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement as explicit policy/contract/evidence boundary, not as hidden prompt convention and not as a new canonical truth store.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 98. Release Gates

At minimum:
1. implementation baseline frozen after independent audit;
2. dependency/license/security gate;
3. canonical contract/invariant test gate;
4. persistence/migration/recovery gate;
5. packaged Electron security/credential gate;
6. provider adapter/live ambiguity gate per supported surface;
7. QA calibration/benchmark gate;
8. repair benchmark gate;
9. performance/cost gate;
10. representative E2E/product acceptance gate;
11. evidence ledger integrity/gate-class verification.

Gate status must cite evidence IDs/classes; documentation existence is not proof.



### FM2-003 ? Local contract completeness

**PURPOSE:** Make Release Gates
 an explicit local boundary so its responsibility, lifecycle and failure behavior are implementable without shifting adjacent canonical authority.

**CANONICAL DEFINITION:** Release Gates
 is the cross-cutting policy/governance boundary defined by this section; it does not become Story/Shot/State/Profile truth.

**OWNER:** Release Governance

**AUTHORITY:** Policy/enforcement authority only; no narrative, Shot, State or Profile truth ownership.

**INPUTS:** Exact upstream canonical IDs/versions, profile/policy and evidence explicitly required by this section; free-form prompt/provider output cannot substitute for required canonical input.

**OUTPUTS:** Typed Release Gates
 decision/artifact/evidence described by this section, with exact source-version bindings; outputs do not absorb adjacent truth ownership.

**IDENTITY:** release_gate_result_id/version/evidence refs; release decision identity is governance evidence only.

**STATE:** Gate results are OPEN / PASS / FAIL only as evidence/governance status; they do not rewrite domain states.

**MUTABILITY:** N/A for the service/policy object itself ? behavior changes require a new rule/policy/tool version where they affect persisted evidence; governed domain records keep their own mutability rules.

**VERSION:** The component/output binds its explicit identity/version when defined above; otherwise the responsible rule/service/evaluator version is recorded in provenance. N/A as a separate domain version only where IDENTITY explicitly says the boundary is not a domain object.

**PROVENANCE:** Persist exact upstream IDs/versions, pinned ActiveProductionProfile where applicable, rule/service/evaluator version, actor/source/evidence refs and decision/revision reason.

**PERSISTENCE:** Persist canonical output/evidence metadata through the owning repository and one-logical-writer rules where SQLite is involved; provider payload/log text never replaces the canonical record.

**PARENT / CHILD OR REFERENCES:** References exact upstream canonical IDs/versions and exposes only declared downstream output references; it MUST NOT copy parent truth into a competing authority.

**DEPENDENCIES:** The declared INPUTS plus applicable ActiveProductionProfile/State/Reference/dependency edges; all dependency bindings are version-aware and auditable.

**ORDERING:** Release gates evaluate last; a gate may close only with evidence class matching the claim.

**CONCURRENCY / TRANSACTION BOUNDARY:** Deterministic/domain work may run in parallel only across independent dependency scopes; canonical version/current-pointer writes use repository ownership/optimistic revision rules. No provider/network side effect occurs inside the canonical DB transaction.

**INVALIDATION:** Changes create a new policy/mapping/evidence version and invalidate only claims/consumers that depended on the superseded version; canonical domain truth is not silently mutated.

**FAILURE MODES:** Missing/stale required input, schema/invariant violation, authority leakage, provenance loss, contradictory version binding, or the section-specific failure already named above.

**RECOVERY:** On stale/invalid input or failed local evaluation, do not mutate accepted upstream truth; repair the earliest responsible source, create/recompute a successor derived version, re-run declared gates and apply dependency invalidation.

**QA / GATE:** Schema + exact-version/provenance + local semantic invariant checks; any hard gate named by this section remains blocking and cannot be averaged away.

**OBSERVABILITY:** Emit structured correlation plus exact input/output IDs/versions, rule/evaluator version, decision/failure reason and provenance; telemetry/event logs are evidence only and secrets are redacted.

**IMPLEMENTATION IMPLICATION:** Implement as explicit policy/contract/evidence boundary, not as hidden prompt convention and not as a new canonical truth store.

**TESTABILITY:** Contract/schema, authority/invariant, stale-version, invalidation and failure-path fixtures must prove the local boundary; downstream/provider mocks cannot replace stronger evidence gates where required.

**LEGACY FLOWKIT MAPPING:** N/A ? no direct legacy FlowKit canonical authority. Any reuse/import is mediated by ?90-?93 anti-corruption/migration/UI boundaries.
# 99. Canonical Invariants

```text
NO MACRO STRUCTURE
→ NO SEQUENCE EXPANSION

NO SEQUENCE
→ NO SCENE EXPANSION

NO SCENE
→ NO SCENE DRAMATIC BEAT

NO SCENE DRAMATIC BEAT
→ NO SHOT

NO AUDIENCE EXPERIENCE TARGET
→ NO CINEMATOGRAPHY DECISION

NO DIRECTING / BLOCKING
→ NO FINAL SHOT DESIGN

NO TRACEABLE SHOT FUNCTION
→ NO FULL SHOT SPEC

NO SHOT ELIGIBILITY PASS
→ NO FULL SHOT SPEC

NO QA APPROVAL
→ NO CANONICAL STATE COMMIT

PROVIDER SUCCESS
!= CANONICAL TRUTH

GENERATED ARTIFACT
!= APPROVED STATE

PROVIDER PROMPT
!= SHOT IR

SHOT IR
!= FULL SHOT SPEC

SHOT LIST ITEM
!= FULL SHOT SPEC

MACRO STORY BEAT
!= SCENE DRAMATIC BEAT

CANONICAL SCENE
!= FLOWKIT LEGACY SCENE
```

Additional invariants:
- one BrainPack Registry;
- one Profile Resolver;
- downstream reads pinned ActiveProductionProfile;
- one canonical shot_id origin at ShotListItem;
- camera cannot self-author;
- StateSnapshot is semantic continuity authority;
- provider prompt/request and generated artifact are derivatives;
- current-state row != event log;
- retry != repair;
- ambiguous paid submission is reconciled before resubmit.

### FM repair invariants

- MacroBeatSheet != MacroStoryBeat truth.
- SceneListManifest != Scene truth.
- SceneBreakdownManifest != SceneDramaticBeat truth.
- ApprovedEndStateDesignation != StateSnapshot payload; canonical world truth remains the referenced StateSnapshot version.
- InvalidationRecord != DependencyGraph truth; it records the consequence of an accepted dependency/version change.
- ShotEligibilityGate != Shot identity; canonical shot_id still originates only at ShotListItem.
- stale ShotEligibilityGate evidence cannot authorize FullShotSpec.
- ReferenceVersion change enters durable dependency invalidation before affected descendants are treated as current.

# 100. Open Non-Blocking Decisions

PM-014 and PM-020 are resolved in this Master.

Pre-Master authority contradictions were resolved before consolidation. FINAL_MASTER_INDEPENDENT_AUDIT_V4 independently re-audited the repaired Master and returned BLOCKER=0, MAJOR=0, MINOR=0, NOTE=0 with post-audit byte-integrity confirmation. The V1 Master is therefore frozen as the implementation-design baseline; the items below remain implementation/detail decisions, not unresolved canonical-authority conflicts.

Items that remain **implementation/detail decisions**, not canonical-authority conflicts:
- exact TypeScript module/package layout;
- exact IPC serialization mechanics within accepted typed-contract boundary;
- exact SQLite schema/DDL/index tuning derived from contracts;
- exact provider/model profile values, which remain evidence-versioned;
- exact QA model/vendor/calibrated thresholds;
- exact packaging/updater vendor/tooling;
- exact artifact retention periods;
- UI presentation details;
- whether future accepted ADR defines semantic L9–L12. Until then only L1–L8 are canonical semantic layers and T9–T12 are downstream technical stages.

These must not silently alter the canonical decisions above.

# 101. Source Provenance / Supersession Appendix

## 101.1 Directly consolidated source classes

This Master directly consolidates **56 unique source documents**:

- 27 Required Primary Sources from CANONICAL_MERGE_CANDIDATE_SET_V1;
- 17 Required Supporting Sources;
- 3 post-V0.16 patch documents;
- 9 evidence/provenance documents needed to preserve claim boundaries.

Evidence/provenance set used:
1. WINDOWS_PERSISTENCE_RUN1_ANALYSIS_V0_14.md
2. WINDOWS_PERSISTENCE_RUN1_EVIDENCE_REVIEW_V0_14.md
3. WINDOWS_PERSISTENCE_RUN2_ANALYSIS_V0_15.md
4. PROVIDER_AMBIGUITY_PROOF_V0_5.md
5. CREDENTIAL_BROKER_PROOF_V0_6.md
6. EVIDENCE_LEDGER_V0_13.md
7. STORY_12_ROUND_INDEPENDENT_AUDIT_V0_16.md
8. STATIC_QA_POLICY_SPIKE_EVIDENCE_V0_7.md
9. TARGETED_REPAIR_PLANNER_SPIKE_EVIDENCE_V0_7.md

## 101.2 Primary ADR authority

Highest consolidation authority includes:
- historical ADR-0013 — one SQLite writer;
- ADR-0014 — Studio-owned Story Intelligence / donor boundary;
- ADR-0015 — design freeze vs implementation evidence;
- ADR-0016 — credential authority;
- ADR-0017 — BrainPack/Profile authority;
- ADR-0018 — narrative identity;
- ADR-0019 — dramatic-to-camera authority;
- ADR-0020 — Shot identity/spec/IR boundary.

Earlier ADR-0001→0012 remain lineage/support where not superseded.

## 101.3 Major section provenance

| Master area | Primary source | ADR authority | Supporting/post source | Superseded/historical semantics excluded |
| --- | --- | --- | --- | --- |
| Project/Niche/Brain/Profile | POST-NICHE + V0.16 Story Brain sources | ADR-0017 | V0.16 Story Architecture | parallel pack registries; unrestricted override |
| Story Intelligence | V0.16 Story Architecture/Contracts/QA | ADR-0014/0018 | POST-LADDER | generic V0.1 Story Engine; generic persistent Beat |
| Narrative hierarchy | POST-LADDER/POST-BEAT | ADR-0018 | V0.16 Story | generic Beat identity; manifest-as-truth |
| Directing/Cinematography | POST-BEAT + V0.16 data/requirements | ADR-0019 | Hybrid/FlowKit lineage only | self-originating camera; opaque blocking ownership |
| Shot system | POST-BEAT + V0.16 data/API | ADR-0020 | POST-LADDER | independent legacy ShotSpec authority; prompt-as-master |
| State/Reference | V0.16 DATA/StaticQA/decision registry | D-005 lineage | FlowKit donor evidence | parent image as semantic authority |
| Compiler | V0.16 DESIGN_DRAFT/DATA/API + ADR-0020 inputs | resolved in Master §64 | provider profiles | string concatenation as compiler; adapter invents intent |
| Provider/Recovery | Provider recovery/API/profile sources | ADR-0007/0010 | FlowKit execution donor | blind resubmit; brand-level timeless facts |
| Persistence | Persistence Architecture/Write Ownership | ADR-0013 | Windows Run-1/Run-2 evidence | direct multiwriter production topology |
| QA/Repair | StaticQA/Repair/StoryQA | ADR-0005/0006 | policy spikes | weighted-average acceptance; full-regenerate-as-repair |
| Sequence QA | requirements + post patches | resolved in Master §77 | Story/continuity/state sources | per-shot-only quality model |
| Security/Credential | Security/Credential sources | ADR-0016 | ADR-0004/0008 lineage | Renderer/Utility/FlowKit as long-lived secret authority |
| Evidence/release | Evidence policy/ledger | ADR-0011/0015 | readiness/review logs | harness/document existence as product proof |

## 101.4 Sources intentionally NOT merged as current authority

At least **12 superseded semantic families** identified by the pre-Master candidate set are excluded as current authority, including:
- JOB_STATE_MODEL_V0_10 current semantics;
- generic V0.1 Story Engine where conflicting;
- stale DESIGN_DRAFT subsystem sections;
- direct-multiwriter SQLite topology;
- blanket all-live-gates-before-code lifecycle;
- generic one-field job status;
- brand-level provider facts;
- weighted-average-only QA acceptance;
- blind ambiguous resubmit;
- parent image as semantic continuity authority;
- prompt prose as canonical generation intent;
- FlowKit operational Scene as cinematic Scene authority.

Also skipped as direct Master authority:
- MASTER_STUDIO_OPTIMAL_HYBRID_ARCHITECTURE_V1_FROZEN.md;
- FLOWKIT_INDEPENDENT_MULTI_ROUND_PRODUCTION_AUDIT_2026-09-20.md;
- byte-identical historical copies of already-selected logical documents.

They remain lineage/evidence sources only.

## 101.5 Current-vs-target claim discipline

Persistence Run-2 scoped target-runtime evidence may be cited for its tested SQLite topology lane only.

Provider ambiguity proof remains partial/local fault-injection until live supported-provider evidence exists.

Credential broker proof remains architecture/local simulation, not packaged Electron safeStorage proof.

Static QA spike proves policy behavior, not vision calibration.

Repair planner spike proves deterministic preserve/invalidation policy, not real model repair success.

V0.16 Story audit proves design/donor review depth, not screenplay-quality runtime benchmark.

## 101.6 FM-001 through FM-008 repair traceability

| Audit finding | Source authority | Master repair area | Requirement lineage | QA/Test expectation |
| --- | --- | --- | --- | --- |
| FM-001 | ADR-0018 + POST-LADDER | ??24A, 26A, 27A | FR-055, FR-059, FR-060 | manifests reference canonical IDs; zero shadow truth |
| FM-002 | Story canonical contracts + POST-LADDER ?1 | component-local completion in ??06-41 | FR-033?052 plus FR-053?061 as applicable | every component exposes explicit lifecycle/version/invalidation/failure/gate semantics |
| FM-003 | ADR-0012 + JOB_STATE_MODEL_V0_13 + model-check evidence | ?68 | FR-019, REL-009 | exact enums, owner isolation, valid/invalid state scenarios, ambiguity safety |
| FM-004 | SECURITY_MODEL ??1-5 + ADR-0016 | ??84-85 | SEC-001?011 | target Electron hardening/IPC/secret-boundary negative tests |
| FM-005 | POST-LADDER ??44-45 + ADR-0017/0020 | ??57,63,72 | FR-023, NFR-019 | durable selective invalidation, restart replay, idempotent dedupe, ReferenceVersion trigger |
| FM-006 | POST-LADDER ??79,85-86 | ?102.1 | FR-053?065, NFR-017?019 | zero missing IDs and no semantic duplicate/renumber |
| FM-007 | DATA_MODEL StateSnapshot + FR-012 + POST-NICHE approval rule | ??61,80 | FR-012, FR-029 | designation never duplicates state payload; only approved snapshot propagates |
| FM-008 | ADR-0020 + POST-BEAT eligibility gate | ?49 | FR-006/007/014 lineage | current gate version required; stale/mismatched eligibility evidence rejected |



### 101.7 Audit V2 repair provenance

This baseline was repaired after FINAL_MASTER_INDEPENDENT_AUDIT_V2 for FM2-001 through FM2-008, independently audited by V3, repaired for FM3-001/FM3-002, and independently re-audited by FINAL_MASTER_INDEPENDENT_AUDIT_V4. V4 returned BLOCKER=0, MAJOR=0, MINOR=0, NOTE=0. That PASS authorizes design freeze only; it is not runtime implementation, packaged-product or release evidence.
### 101.8 Independent Audit V4 freeze provenance

- FINAL_MASTER_REPAIR_FM3_001_FM3_002_V1 repaired the last V3 MAJOR findings.
- FINAL_MASTER_INDEPENDENT_AUDIT_V4 independently audited Master SHA 6122c46bd03ef1470a0e8231bef38486f4378005f1ee82ca5d7c9fa5c0fdfe11.
- V4 verdict: BLOCKER=0, MAJOR=0, MINOR=0, NOTE=0, PASS.
- Post-audit Master SHA remained identical to the audited SHA before this status-only freeze mutation.
- This freeze changes governance/status provenance only; canonical owners, identities, state machines, hard gates, requirements and contracts are unchanged.
- A frozen-baseline verification audit is required on the post-freeze SHA before implementation task decomposition begins.

# 102. Requirement → Component Traceability

The historical requirement set remains traceable, but terminology is normalized by accepted ADRs.

| Requirement family | Canonical component(s) | Contract/data | Persistence/interface | QA/Test | Acceptance |
| --- | --- | --- | --- | --- | --- |
| FR-001 ingest | Project/import boundary | import manifest | application/import port | malformed/adversarial import | validated canonical candidates |
| FR-002 causality | Causal StoryGraph | graph nodes/edges | Story repository | orphan/cycle/causality fixtures | causal gate |
| FR-003 Film Bible | Entity/Reference/State/Profile | versioned assets/state | canonical repo | identity/state fixtures | approved refs/state |
| FR-004 narrative hierarchy | StoryCore→MacroStoryBeat→Sequence→Scene→SceneDramaticBeat | ADR-0018 contracts | Story repo | hierarchy/invariant tests | zero generic Beat |
| FR-005 historical Beat | SceneDramaticBeat + MacroStoryBeat | normalized split | Story repo | migration semantic tests | no ambiguous Beat |
| FR-006 shot contract | ShotListItem/FullShotSpec | ADR-0020 | Shot repo | trace/identity tests | one shot_id origin |
| FR-007 8-layer ShotSpec | FullShotSpec semantic L1–L8 | spec contract | Shot repo | layer/provenance tests | complete valid spec |
| FR-008 cinematography | CinematographyObjective | ADR-0019 | directing/cine repo | decision-basis tests | no camera bypass |
| FR-009 Entity Registry | Entity | EntityVersion | entity repo | identity/version tests | stable canonical IDs |
| FR-010 Reference Bible | Reference Registry | ReferenceAsset/version/role | reference repo | provenance/approval tests | approved versioned references |
| FR-011 Reference Resolver | Reference Resolver | resolved bindings | resolver port | capability/selection tests | minimal valid provider bindings |
| FR-012 State Engine | StateSnapshot | state/delta | state repo | transition tests | approved state authority |
| FR-013 Spatial Baseline | SceneSpatialDramaticContract/BlockingPlan | spatial contracts | directing repo | spatial continuity | valid geography |
| FR-014 Shot IR | ShotIR | provider-neutral IR | compiler interface | semantic/preflight | valid IR |
| FR-015 Static compiler | Production Compiler | StaticKeyframeSpec/ShotIR/CompiledRequest | compiler port | determinism/golden | traceable static request |
| FR-016 Motion compiler | Production Compiler | MotionDeltaSpec/ShotIR/CompiledRequest | compiler port | determinism/golden | traceable motion request |
| FR-017 provider capability | Capability Registry/Router | ProviderProfile | registry/router ports | profile/routing tests | capability-safe selection |
| FR-018 provider adapters | Provider Adapter Boundary | CompiledRequest/submit result | adapter ports | contract/fault tests | provider-safe execution |
| FR-019 durable jobs | GenerationJob | orthogonal states | job repo | crash/restart | no lost side-effect lineage |
| FR-020 dependencies | Queue/DAG/Invalidation | DependencyEdge | orchestrator repo | graph tests | minimal valid recompute |
| FR-021 waves | Scheduler | admission policy | orchestrator | fairness/backpressure | bounded execution |
| FR-022 retry/resume | Recovery | typed failure/state | orchestrator/provider ports | fault tests | safe recovery |
| FR-023 invalidation | Dependency Invalidation | stale edges/reasons | canonical repo | selective invalidation | no unnecessary reset |
| FR-024 Static QA | Static QA | findings/result | QA repo | calibration fixtures | blocking gate |
| FR-025 Video QA | Motion QA | time-bound findings | QA repo | motion fixtures | artifact verdict |
| FR-026 Sequence QA | Sequence QA §77 | sequence findings/result | QA repo | cross-shot/scene fixtures | sequence gate |
| FR-027 repair | Targeted Production Repair | RepairPlan | repair repo | preserve/regression | minimal repair |
| FR-028 lineage | Artifact Lifecycle/Trace | hashes/IDs | artifact repo | lineage audit | bidirectional trace |
| FR-029 approval | Approval/State Commit | approval/lock | canonical repo | transition tests | explicit commit |
| FR-030 restart safety | Persistence/Recovery | checkpoints/state | SQLite/artifact store | crash scenarios | resumable |
| FR-031 editorial | Editorial | timeline/edit manifest | editorial repo | continuity/export tests | approved edit |
| SEC requirements | Security/Credential | broker/lease/redaction | Main/Utility IPC | security tests | no secret leakage |
| REL requirements | Persistence/Recovery/Job state | orthogonal states | repositories | fault/model tests | durable safe state |
| PERF requirements | Admission/Benchmarks | policy/profiles | scheduler metrics | representative benchmark | measured gate |
| NFR authority/testability | all canonical boundaries | typed contracts | ports/repos | architecture/contract tests | no duplicate authority |


| FR-032 optional 3D previs | Optional Previs adapter | derived previs contract | optional adapter/artifact store | adapter/visualization tests | no canonical authority leakage |
| FR-033 Premise Lab | Premise | PremiseCandidate | Story repo/service | premise fixtures/critique | accepted premise |
| FR-034 Angle Lab | Angle | AngleCandidate | Story repo/service | differentiation/factuality | accepted angle |
| FR-035 Theme System | Theme | ThemeHypothesis | Story repo/service | integration/repetition | accepted theme |
| FR-036 Research Intelligence | Research Intelligence | ResearchBrief/EvidenceClaim | research ports/repo | provenance/contradiction tests | evidence-grounded package |
| FR-037 Research?Story Material | Story Material Transformer | StoryMaterial | Story repo | source-trace fixtures | no unsupported synthesis |
| FR-038 Dynamic Brain Resolver | BrainPack Registry/Profile Resolver | pack/profile/ResolutionTrace | profile repo/resolver port | precedence/conflict tests | pinned ActiveProductionProfile |
| FR-039 Character Psychology | Character Psychology | CharacterModelVersion | Story repo | motivation/arc tests | coherent model |
| FR-040 Knowledge/Relationship | Knowledge/Belief + Relationship State | state versions | Story repo | chronology/continuity tests | valid state transitions |
| FR-041 Conflict/Stakes | Conflict & Stakes | ConflictModel/StakesModel | Story repo | pressure/escalation fixtures | viable conflict/stakes |
| FR-042 Causal StoryGraph | Causal StoryGraph | graph nodes/edges | Story repo | causality/orphan tests | causal gate |
| FR-043 Emotional Arc | Emotional Arc | EmotionalArcPlan | Story repo | arc coherence tests | accepted arc |
| FR-044 Rhythm/Tension | Emotional Rhythm/Tension | EmotionalRhythmPoint | Story analytics/repo | flatline/whiplash fixtures | diagnostics without authority theft |
| FR-045 Scene State-Change | Scene | Scene contract/state delta | Story repo | static-scene/change tests | justified scene |
| FR-046 historical Beat Microchange | SceneDramaticBeat | scene_dramatic_beat contract | Story repo | microchange tests | no generic Beat authority |
| FR-047 Dialogue/Subtext | Dialogue Engine | DialogueIntent | Story repo | voice/knowledge/subtext tests | accepted realization |
| FR-048 Setup/Payoff | Setup/Payoff Ledger | SetupPayoffLink | Story repo | broken-link tests | valid payoff state |
| FR-049 Critique Council | Story Critique | CritiqueFinding | QA/story repo | role-isolation/meta-critique | evidence-linked findings |
| FR-050 Story Quality Gate | Story Quality Gate | StoryQualityResult | QA/story repo | blocking-gate fixtures | explicit verdict |
| FR-051 Story Repair | Targeted Story Repair | StoryRepairPlan | repair/story repo | preserve/regression tests | localized repair |
| FR-052 Script Lock | Script Lock | ScriptLockManifest | Story repo | lock/version tests | immutable accepted script lock |
| NFR-001 provider independence | Compiler/Provider boundary | ShotIR/ProviderProfile | ports/adapters | provider-contract tests | no provider semantics in canonical domain |
| NFR-002 durable state | Persistence/State/Jobs | versioned rows/checkpoints | SQLite/artifact store | crash/restart | durable truth |
| NFR-003 idempotency | Provider Recovery/Jobs | submission identity | adapter/orchestrator | duplicate-submit faults | no accidental paid duplicate |
| NFR-004 deterministic validation | Contracts/Compiler | schemas/invariants | validators | deterministic fixtures | repeatable validation |
| NFR-005 recoverability | Recovery | persisted recovery state | orchestrator/repo | crash/fault tests | safe resume/reconcile |
| NFR-006 observability | Observability | events/logs/metrics | observability ports | correlation/redaction | traceable operations |
| NFR-007 maintainability | module boundaries | ports/contracts | package boundaries | architecture tests | one owner per responsibility |
| NFR-008 extensibility | registries/adapters | typed extension contracts | plugin/provider ports | compatibility tests | extension without authority leakage |
| NFR-009 long-form scale | Queue/DAG/incremental QA | dependency/admission contracts | orchestrator/repo | 300-shot benchmark | bounded scalable workflow |
| NFR-010 testability | all canonical components | provider-neutral contracts | dependency-injected ports | unit/contract fixtures | core tests without live provider |
| NFR-011 evidence provenance | Evidence Governance | evidence entry/hash | evidence ledger | hash/integrity audit | claims cite evidence |
| NFR-012 evidence-class closure | Evidence Governance | gate rules | evidence verifier | class-mismatch tests | no weak-evidence closure |
| NFR-013 donor isolation | Donor/Anti-Corruption Boundary | adapter/import contracts | ports | dependency/license tests | donor never canonical authority |
| NFR-014 data-driven Brain Packs | BrainPack Registry | pack schemas | registry repo | version/compatibility tests | reusable versioned policy |
| NFR-015 critique independence | Critique Council | CritiqueFinding | QA/story repo | role isolation tests | generator not sole judge |
| NFR-016 factual storytelling | Research Intelligence | EvidenceClaim/StoryMaterial | research/story repo | claim-source audits | factuality/provenance preserved |
| SEC-001 | Security | privileged-boundary contract | Main/Renderer | boundary tests | no renderer privilege escalation |
| SEC-002 | Security | credential isolation contract | Main/Utility | secret-boundary tests | no project-secret authority leakage |
| SEC-003 | Security | log redaction contract | logging layer | secret-scan tests | secret-safe logs |
| SEC-004 | Security | filesystem/import contract | import boundary | path traversal tests | safe import |
| SEC-005 | Security | plugin/provider permission contract | extension ports | permission tests | bounded adapters/plugins |
| SEC-006 | Security | external-source trust contract | import/research boundary | data-only/adversarial tests | no embedded execution |
| SEC-007 | Credential Broker | renderer-denial contract | contextBridge/Main | secret-denial tests | Renderer never receives long-lived secret |
| SEC-008 | Credential Broker | scoped lease | Main?Utility IPC | scope tests | least-privilege credential use |
| SEC-009 | Credential Broker | lease lifecycle | Main/Utility | expiry/rotation/crash tests | stale lease rejected |
| SEC-010 | Export/Security | export manifest | exporter | vault-exclusion test | no credential vault in project export |
| SEC-011 | Observability/Security | redaction rules | logging layer | secret scanning | no secret leakage |
| REL-001 | Persistence | durable transaction contract | SQLite | crash fixtures | committed state durable |
| REL-002 | Artifact Lifecycle | staged artifact commit | artifact store/repo | crash consistency tests | no half-committed artifact authority |
| REL-003 | Generation Job/State | stale-input fingerprint | job repo | late-result tests | stale result not auto-applied |
| REL-004 | Recovery | worker/job lease contract | orchestrator/repo | lease/crash tests | safe reclaim/resume |
| REL-005 | Cancellation/Recovery | cancel/late-result policy | orchestrator/provider | cancellation race tests | deterministic late-result handling |
| REL-006 | Ambiguous Remote State | provider submission states | orchestrator/adapter | ambiguity fault injection | no blind resubmit |
| REL-007 | Provider Recovery | reconciliation evidence | adapter | capability-class tests | evidence-backed retry safety |
| REL-008 | Migration | migration startup gate | migration service | interrupted migration tests | safe startup/resume |
| REL-009 | Generation Job Model | four orthogonal axes | job repo | model reachability/scenarios | no state conflation |
| REL-010 | Persistence | single writer command queue | repository | Windows concurrency lane | serialized canonical writes |
| PERF-001 | Scheduler | hierarchical admission | orchestrator | cap/backpressure benchmark | provider-safe admission |
| PERF-002 | Scheduler | fairness policy | orchestrator | multi-project fairness | no starvation |
| PERF-003 | Scheduler/Budget | budget gate | orchestrator/cost records | cost-admission tests | budget-safe execution |
| UX-001 | Renderer/View Models | project/workflow view contract | contextBridge/application ports | workflow checks | understandable state |
| UX-002 | Renderer/View Models | authority/provenance view | contextBridge/application ports | traceability UX checks | explainable decisions |
| UX-003 | Renderer/View Models | recovery/QA/repair views | contextBridge/application ports | failure-path UX checks | actionable recovery |
| UX-004 | Renderer/View Models | progressive-complexity view | contextBridge/application ports | simple/advanced workflow checks | UI hides complexity without changing contracts |


Bidirectional narrative trace is mandatory:

```text
Shot
→ SceneDramaticBeat
→ Scene
→ Sequence
→ MacroStoryBeat
→ StoryCore
```

and parent → children traversal is also required.

No canonical component may be orphaned from requirement, owner, contract/persistence/interface and QA/acceptance lineage.

---

## Consolidation Status

- PM-014 Compiler responsibility: **RESOLVED IN MASTER §64**.
- PM-020 Sequence QA: **RESOLVED IN MASTER §77**.
- Known unresolved canonical authority conflicts after consolidation: **0**.
- Known blocking conflicts after consolidation: **0**.
- This document is **FROZEN IMPLEMENTATION BASELINE V1 ? DESIGN AUTHORITY**.
- FINAL_MASTER_INDEPENDENT_AUDIT_V4 = **PASS** with BLOCKER=0 and MAJOR=0; design freeze gate is satisfied.

## 102.1 Post-V0.16 requirement IDs allocated by FM-006

Existing requirement IDs are not renumbered. These IDs own obligations introduced by the accepted Narrative Expansion/authority patches that were not already fully represented by a stable requirement identity.

| Requirement ID | Source authority | Canonical component | Contract / persistence-interface | QA/Test expectation | Acceptance condition |
| --- | --- | --- | --- | --- | --- |
| FR-053 | POST-LADDER ??5-7 | Logline | LoglineContract / Story repo | Logline blocking-defect fixtures | first-class versioned Logline passes Logline Gate |
| FR-054 | POST-LADDER ??3,8 | StructureProfile | StructureProfile / policy repo | count-range/profile tests | budgets/ranges are profile-driven, never universal fixed truth |
| FR-055 | POST-LADDER ??9,50 + ADR-0018 | MacroBeatSheet | manifest + MacroStoryBeat refs / Story planning repo | reference/order/compression/budget tests | ordered projection exists without duplicate Beat truth |
| FR-056 | POST-LADDER ??11,41-43 | SequencePlan (?26B) | Sequence planning projection / Story planning repo | causality/order/trace tests | plan traces to canonical Sequence/MacroStoryBeat without becoming Sequence truth |
| FR-057 | POST-LADDER ?12 | DurationBudget (?24B) | DurationBudget / Story planning repo | parent-child budget tolerance tests | child duration budgets reconcile to parent within configured tolerance |
| FR-058 | POST-LADDER ?13 | SceneBudget (?26C) | SceneBudget / Story planning repo | range/duration/profile tests | scene count/duration remains a justified range |
| FR-059 | POST-LADDER ??14-15 + ADR-0018 | SceneListManifest | manifest of Scene refs / Story planning repo | dangling/duplicate/order/causality tests | ordered Scene projection exists with no Scene shadow truth |
| FR-060 | POST-LADDER ??16-19 + ADR-0018 | SceneBreakdownManifest | manifest of SceneDramaticBeat refs / Story planning repo | beat movement/state/budget/reference tests | breakdown references canonical Beat IDs and owns no Beat truth |
| FR-061 | POST-LADDER ??20-24 | Screenplay Realization | ScreenplayScene / screenplay repo | realization-drift/knowledge/setup-payoff tests | realization preserves accepted upstream truth |
| FR-062 | POST-LADDER ??41-45 | NarrativeTrace (?62A) | NarrativeTrace + lineage refs / lineage repo | top-down/bottom-up/orphan/cycle tests | every expansion child traces to parent/root and every Shot explains why it exists |
| FR-063 | POST-LADDER ??34-35 | ShotBudget | ShotBudget / preproduction planning repo | runtime/ASL/profile budget tests | shot-count range has explicit rationale |
| FR-064 | POST-LADDER ??33,74 | ShotExpansion (?47A) | shot expansion planner output / preproduction service | Beat-to-Shot mapping/redundancy tests | dramatic units expand to justified ShotListItems |
| FR-065 | POST-LADDER ??36-38 + ADR-0020 | ShotListManifest | ordered ShotListItem refs / Shot repo | identity/coverage/order tests | manifest orders one canonical shot_id origin without duplicate Shot truth |
| NFR-017 | POST-LADDER ??41-43 | Narrative traceability | lineage IDs/source versions / lineage repo | deterministic top-down/bottom-up trace tests | same accepted versions yield complete deterministic lineage |
| NFR-018 | POST-LADDER ??46,66 | Approved creative versions | immutable versions / canonical repositories | mutation/successor-version tests | approved artifacts never silently mutate in place |
| NFR-019 | POST-LADDER ??44-45 + ADR-0017/0020 | Dependency Invalidation | InvalidationRecord + dependency bindings / canonical repo | selective/restart/idempotency tests | changed version invalidates dependency-reachable descendants with durable provenance |

**DUPLICATE RULE:** older adjacent requirements such as FR-023 or FR-028 keep their historical scope; the IDs above own only the newly explicit post-V0.16 artifact/constraint semantics and do not redefine old IDs.

### Post-repair candidate status

This Master is **FROZEN IMPLEMENTATION BASELINE V1 ? DESIGN AUTHORITY** after FINAL_MASTER_INDEPENDENT_AUDIT_V4 PASS (BLOCKER=0, MAJOR=0). The freeze governs implementation design; it does not claim feature implementation, packaged runtime validation or release readiness.

