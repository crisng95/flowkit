# PRE-MASTER CONTRADICTION REGISTER V1

## 0. Status

This register records live and historical contradictions before Master consolidation.

Rules:
- historical sources are not modified;
- proposed decisions are recommendations only;
- an item is RESOLVED only when an existing ADR/registry/review/evidence source already establishes the decision;
- an item is UNRESOLVED when the future Master must make the decision;
- BLOCKING means Master consolidation would create duplicate authority or unstable canonical IDs/contracts if the conflict is ignored.

## 1. Register

| ID | DOMAIN | SEVERITY | SOURCE A | SOURCE B | CONFLICT | PROPOSED CANONICAL DECISION | STATUS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PM-001 | PROCESS LIFECYCLE | HIGH | V0.3–V0.15 PROJECT_STATE/HANDOFF language that coding waits for L6/live gates | ADR-0015 | Older lifecycle wording requires most target/live evidence before feature coding; ADR-0015 says implementation/live acceptance normally follows implementation unless a pre-code spike can change architecture. | ADR-0015 governs. Pre-code requires coherent authority/contracts/task plan; subsystem live proofs become implementation/release acceptance unless architecture-changing. | RESOLVED |
| PM-002 | MATURITY L5/L6/L7 | HIGH | Historical maturity labels and L6 gate boards | V0.16 PROJECT_STATE + ADR-0011 + ADR-0015 | Historical documents can appear to imply that documentation/harness completion promotes maturity; V0.16 remains L5.5 and evidence classes prohibit that inference. | PROJECT_STATE is maturity authority. Preserve L5.5 historical state; do not infer L6/L7 from document count or harness readiness. | RESOLVED |
| PM-003 | PERSISTENCE | BLOCKING historical | direct/multiwriter assumptions and Windows Run-1 lane | ADR-0013 + PERSISTENCE_WRITE_OWNERSHIP_V0_14 + Run-2 PASS | Direct concurrent SQLite writers produced lock failures; earlier architecture did not guarantee single ownership. | V1 uses Production Utility with one logical SQLite write owner + bounded queue; Run-1 remains diagnostic history, Run-2 owns topology decision evidence. | RESOLVED |
| PM-004 | PROVIDER AMBIGUITY / RETRY | BLOCKING historical | generic retry/resubmit assumptions | ADR-0007 + PROVIDER_SUBMISSION_RECOVERY_ARCHITECTURE | Retrying after a network break can duplicate a paid job if provider accepted submission. | UNKNOWN_REMOTE_STATE / RECONCILING / AMBIGUOUS_HOLD; no blind resubmit without proven idempotency or negative reconciliation. | RESOLVED |
| PM-005 | CREDENTIAL OWNERSHIP / SECRET STORAGE | BLOCKING | V0.16 PROJECT_STATE lists secret storage as pending | ADR-0008 + SECURITY_MODEL + CREDENTIAL_BROKER_ARCHITECTURE | Authority precedence was ambiguous between stale pending state and detailed broker design. | HOST SECURITY BROKER is canonical credential authority; Electron Main + safeStorage owns long-lived secret, Production Utility receives short-lived scoped leases, Renderer never owns/reads long-lived secret, FlowKit auth/session behavior is compatibility-only. | **RESOLVED ? ADR-0016** |
| PM-006 | TOPIC / NICHE / BRAIN PACK / PROFILE | BLOCKING | V0.16 STORY_BRAIN_PACK_SPEC + Project/Story policy model | POST-NICHE Universal Niche & Composable Brain Architecture | Two registries/resolvers could create divergent effective policy. | BrainPack Registry owns reusable versioned packs; Profile Resolver uniquely owns inheritance/composition/conflict/precedence; immutable pinned ActiveProductionProfile is the only downstream effective-policy source; hard constraints and locked invariants outrank soft/project preferences; changes use dependency-aware invalidation. | **RESOLVED ? ADR-0017** |
| PM-007 | NARRATIVE EXPANSION / ARTIFACT IDENTITY | BLOCKING | V0.16 Story Architecture/Contracts with generic Beat | POST-LADDER | Planning manifests could become duplicate narrative truth and generic Beat was ambiguous. | Canonical identities are StoryCore ? MacroStoryBeat ? Sequence ? Scene ? SceneDramaticBeat. SceneListManifest references ordered Scene IDs; SceneBreakdownManifest projects SceneDramaticBeat IDs; StructureProfile owns budgets/policy only; no generic persistent Beat. | **RESOLVED ? ADR-0018** |
| PM-008 | BEAT / SCENE AUTHORITY | BLOCKING | V0.16 BeatContract and persistent generic Beat identity | POST-BEAT | Generic persistent Beat conflated macro structure and intra-scene dramatic movement. | MacroStoryBeat and SceneDramaticBeat are separate first-class identities; generic persistent Beat is prohibited. Bidirectional hierarchy trace is required through StoryCore/MacroStoryBeat/Sequence/Scene/SceneDramaticBeat. | **RESOLVED ? ADR-0018** |
| PM-009 | DIRECTING / SPATIAL / BLOCKING / CINEMATOGRAPHY | BLOCKING | V0.16 DirectingDecision + CinematographyDecision with blocking_json | POST-BEAT DirectingIntent + SceneSpatialDramaticContract + BlockingPlan + CinematographyObjective | Camera/blocking authority could self-originate or be split across multiple records. | Canonical chain: StoryCore ? MacroStoryBeat ? Sequence ? Scene ? SceneDramaticBeat ? AudienceExperienceTarget ? DirectingIntent ? SceneSpatialDramaticContract ? BlockingPlan ? CinematographyObjective ? ShotListItem. Immediate Shot narrative authority is SceneDramaticBeat. Camera/lens/angle/movement/focus/lighting/composition cannot self-author. | **RESOLVED ? ADR-0019** |
| PM-010 | SHOT LIST / FULL SHOT SPEC / SHOT IR | BLOCKING | V0.16 Shot identity + ShotSpecVersion + ShotIRVersion | POST-LADDER ShotListManifest/ShotExpansion and POST-BEAT FullShotSpec/ShotEligibility/ShotDecisionTrace | Multiple Shot/spec/IR artifacts risked parallel shot masters. | ShotListItem is the canonical shot_id origin inside ordered ShotListManifest; ShotEligibilityGate precedes realization; FullShotSpec realizes the same shot_id; legacy ShotSpec is deprecated/compatibility alias only; ShotIR has its own ir_id/version but always references shot_id and is provider-neutral; provider prompt/request are derivative only. | **RESOLVED ? ADR-0020** |
| PM-011 | FLOWKIT SCENE VS CANONICAL SCENE | HIGH | FlowKit operational Scene model | V0.16 FLOWKIT_STORY_REPLACEMENT_MAP + Story SceneContract | FlowKit Scene combines generation/media/prompt/chain state and conflicts with cinematic Scene semantics. | FlowKit operational Scene maps downstream to Shot/GenerationJob compatibility projection; cinematic Scene/SceneContract owns narrative authority. | RESOLVED |
| PM-012 | STORY VS GENERATION OWNERSHIP | HIGH | FlowKit project.story / prompt-led workflow | ADR-0014 + V0.16 Story Architecture + DATA_MODEL | Execution artifacts/prompts could become de facto story truth. | Studio-owned Story domain owns locked narrative truth. Generation consumes ScriptLock/Scene/Shot lineage; provider outputs cannot rewrite Story truth without explicit upstream revision. | RESOLVED |
| PM-013 | PROMPT VS COMPILER | HIGH | prompt/image_prompt/video_prompt historically treated as central inputs | V0.16 DATA_MODEL/API/DESIGN_DRAFT | Raw prose prompt can bypass structured shot/state/reference authority. | ShotSpec/FullShotSpec + state/reference resolution → ShotIR → compiler → provider-specific prompt/request. Prompt is compiled artifact only. | RESOLVED |
| PM-014 | COMPILER OWNERSHIP | MEDIUM | V0.16 DESIGN_DRAFT compiler sections + DATA_MODEL CompiledRequest + API contracts | No dedicated Compiler Architecture document; POST patches add upstream constraints | Compiler responsibility was distributed, risking drift in ownership/diagnostics/hash/invalidation. | Master section 64 defines one Production Compiler boundary: canonical pinned inputs -> ShotIR -> capability resolution -> provider-specific CompiledRequest; compiler owns lowering only and cannot own Story/Directing/State/Reference/Shot truth. | **RESOLVED IN MASTER CANDIDATE ?64 ? pending independent final audit/freeze** |
| PM-015 | ARTIFACT VS STATE TRUTH | HIGH | older artifact/status concepts and generated parent media | JOB_STATE_MODEL_V0_13 + DATA_MODEL + continuity decision D-005 | READY/generated artifacts can be confused with semantic/creative approval or continuity truth. | Artifact state describes materialization only. Creative acceptance is separate. Approved/locked StateSnapshot owns semantic continuity; artifacts are evidence/conditioning and only accepted artifacts may become default anchors. | RESOLVED |
| PM-016 | REFERENCE AUTHORITY | HIGH | FlowKit single current media_id/reference image | V0.16 EntityVersion/ReferenceAsset + resolver architecture | One current reference asset cannot express role/version/provenance/approval and risks becoming identity truth by accident. | Entity/EntityVersion owns identity state; versioned ReferenceAssets/roles are evidence/conditioning selected by resolver. Provider binding is compiled output, not canonical reference truth. | RESOLVED |
| PM-017 | CONTINUITY AUTHORITY | HIGH | parent-image inheritance / chain semantics | StateSnapshot D-005 + DATA_MODEL + STATIC_QA | Parent image can conflict with approved semantic state; historical FlowKit continuity was media-centric. | StateSnapshot = semantic authority; parent accepted artifact = conditioning/evidence. Conflict blocks propagation and triggers repair/replan instead of silently preferring pixels. | RESOLVED |
| PM-018 | QA PASS VS APPROVAL | HIGH | provider success / weighted score / artifact READY | ADR-0005 + JOB_STATE_MODEL_V0_13 + STATIC_QA | Generation success or a good average score can be mistaken for creative approval. | Provider success, artifact READY and creative APPROVED are separate. Blocking defect prevents PASS regardless of unrelated scores; human override is explicit/audited. | RESOLVED |
| PM-019 | REPAIR INVALIDATION | HIGH | heuristic prompt rewrite/full regeneration | TARGETED_REPAIR_ARCHITECTURE + Story repair + POST-NICHE profile invalidation | Repair can fix one dimension while invalidating unrelated accepted state or downstream outputs; profile changes add another invalidation source. | Use typed dependency graph. Repair declares preserve/patch/invalidate/recheck sets. Upstream accepted truth or profile-version changes invalidate only dependent artifacts/contracts. | RESOLVED for principle; implementation graph remains future work |
| PM-020 | SEQUENCE QA | MEDIUM | V0.16 REQUIREMENTS FR-026 / DESIGN_DRAFT Sequence QA | No dedicated Sequence QA contract; POST-LADDER/POST-BEAT add sequence/coverage gates | Sequence-level acceptance existed without one consolidated owner/dimension/evidence contract. | Master section 77 defines SequenceQA as cross-shot/cross-scene QA with explicit dimensions, evidence-bound findings and repair path; it does not replace StaticQA/VideoQA/ShotQA or become Story/Shot authority. | **RESOLVED IN MASTER CANDIDATE ?77 ? pending independent final audit/freeze** |
| PM-021 | V0.16 VS POST-NICHE PATCH | HIGH | V0.16 Story/Brain/project policy | POST-NICHE | Post patch added broader pack/profile authority. | Integrate post-Niche content under ADR-0017: one BrainPack Registry, one Profile Resolver, pinned ActiveProductionProfile. | RESOLVED ? ADR-0017 |
| PM-022 | V0.16 VS POST-LADDER PATCH | HIGH | V0.16 Story contracts | POST-LADDER | Patch adds explicit expansion artifacts. | Integrate as manifests/projections around canonical identities defined by ADR-0018; do not create duplicate Story/Sequence/Scene/Beat truth. | RESOLVED ? ADR-0018 |
| PM-023 | V0.16 VS POST-BEAT PATCH | BLOCKING | V0.16 Beat/Directing/Cinematography/Shot contracts | POST-BEAT | Patch changes beat terminology and visual authority chain. | Integrate according to ADR-0018 (narrative identities), ADR-0019 (dramatic-to-camera authority), and ADR-0020 (Shot identity/spec/IR). | RESOLVED ? ADR-0018 / ADR-0019 / ADR-0020 |

## 2. Conflict counts

For state gating, PM-001 through PM-020 are counted as unique decision conflicts. PM-021..PM-023 remain trace rows and are not double-counted.

- Unique decision conflicts tracked: **20**.
- Resolved/principle-set conflicts: **20**.
- Unresolved unique conflicts: **0**.
- Blocking unresolved conflicts: **0**.
- Non-blocking unresolved conflicts: **0**.
- Additional V0.16-vs-post-patch trace rows PM-021..PM-023: **RESOLVED** by ADR-0017 through ADR-0020.

The two unresolved non-blocking items are:
- PM-014 ? Compiler responsibility consolidation.
- PM-020 ? Sequence QA contract consolidation.

## 3. Blocking set after accepted ADRs

**NONE.**

Resolved blocker mapping:

1. PM-005 ? ADR-0016 ? Credential Authority.
2. PM-006 ? ADR-0017 ? BrainPack / ActiveProductionProfile Authority.
3. PM-007 ? ADR-0018 ? Narrative Artifact Identity.
4. PM-008 ? ADR-0018 ? no generic persistent Beat; MacroStoryBeat / SceneDramaticBeat split.
5. PM-009 ? ADR-0019 ? Dramatic-to-Camera Authority.
6. PM-010 ? ADR-0020 ? Shot Identity / FullShotSpec / ShotIR Boundary.

## 4. Gate decision

Blocking authority conflicts are now zero.

PRE-MASTER MASTER CONSOLIDATION GATE = **READY**

This does not create the Master and does not authorize feature implementation by itself.

The next step may consolidate accepted canonical sources into the Master implementation baseline, while carrying PM-014 and PM-020 as non-blocking consolidation work.


## 5. Master candidate consolidation resolution

After MASTER_AI_FILM_STUDIO_FINAL_IMPLEMENTATION_BASELINE_V1.md and
MASTER_CONSOLIDATION_SELF_AUDIT_V1.md:

- PM-014 = RESOLVED IN MASTER CANDIDATE ?64.
- PM-020 = RESOLVED IN MASTER CANDIDATE ?77.
- unresolved conflicts = 0.
- blocking conflicts = 0.

These resolutions remain candidate-baseline decisions until the required independent final Master audit and freeze.
