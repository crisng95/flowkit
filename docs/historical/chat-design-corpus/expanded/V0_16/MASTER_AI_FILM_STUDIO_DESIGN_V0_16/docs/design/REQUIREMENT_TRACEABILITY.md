# REQUIREMENT_TRACEABILITY.md
# Initial Requirement → Component → Data → Contract → Test → Acceptance Matrix V0.3

**Status:** INITIAL COMPLETE PASS  
**Purpose:** prevent core requirements from disappearing between design and implementation.

| Req | Component | Data | Contract | Minimum Test | Acceptance |
|---|---|---|---|---|---|
| FR-001 Multi-entry ingest | Ingest | SourceVersion | source import | parser fixture + invalid input | source version traceable |
| FR-002 Story causality | Story Engine | StoryVersion | story blueprint | story fixture semantic checks | objectives/causality represented |
| FR-003 Film Bible | Production Memory | FilmBibleVersion | film-bible | version/lock test | downstream consumes locked version |
| FR-004 Hierarchy | Narrative Domain | Sequence/Scene/Beat/Shot | entity schemas | FK/ref validation | no dangling hierarchy |
| FR-005 Beat | Narrative Domain | Beat | beat schema | valid/invalid beat | purpose/change explicit |
| FR-006 Shot | Shot Domain | Shot | shot schema | shot cross-ref | every shot binds beat |
| FR-007 8-Layer ShotSpec | Shot Domain | ShotSpecVersion | shot-spec | schema + semantic validation | provider input derived from spec |
| FR-008 Cinematography | Cinematography Engine | CinematographyDecision | cinematography decision | decision fixture/review | decision_basis present |
| FR-009 Entity Registry | Entity Service | Entity/EntityVersion | entity | version/ref tests | stable typed entity |
| FR-010 Reference Bible | Reference Service | ReferenceAsset | reference | view/version tests | approved refs immutable |
| FR-011 Resolver | Reference Resolver | binding result | reference-binding | provider-limit test | best allowed subset returned |
| FR-012 State Engine | State Engine | StateSnapshot | state-snapshot | propagation test | only approved state propagates |
| FR-013 Spatial Baseline | Spatial module | SpatialBaseline | spatial baseline | axis/landmark validation | geometry refs coherent |
| FR-014 Shot IR | Compiler Preflight | ShotIRVersion | shot-ir | provider-neutral schema test | no provider syntax in IR |
| FR-015 Static compiler | Compiler | CompiledRequest | static compile | golden fixture | locks preserved |
| FR-016 Motion compiler | Compiler | CompiledRequest | motion compile | start/action/end test | temporal delta explicit |
| FR-017 Capability registry | Provider Registry | ProviderProfile | provider-profile | capability mismatch test | unsupported request blocked/adapted |
| FR-018 Provider adapters | Provider Runtime | provider state | adapter contract | mock adapter contract test | normalized errors/results |
| FR-019 Durable jobs | Orchestrator | GenerationJob | job | restart test | in-flight state survives |
| FR-020 Dependency graph | Orchestrator | DependencyEdge | dependency | cycle/ordering tests | child waits for parent |
| FR-021 Waves | Scheduler | job/dependency | scheduling command | parallel/ordering integration | independent parallelism only |
| FR-022 Retry/timeout/cancel/resume | Orchestrator | Job/RecoveryEvent | job state | failure injection | bounded correct transitions |
| FR-023 Selective invalidation | Dependency/State | edges/artifacts | invalidation event | parent-change test | unrelated shots stay valid |
| FR-024 Static QA | QA | QAResult | qa-result | labeled artifact fixtures | blocking defects fail |
| FR-025 Video QA | QA | QAResult | qa-result | ffmpeg/semantic integration | state/motion checked |
| FR-026 Sequence QA | QA | QAResult | sequence review | sequence regression fixture | rhythm/continuity checked |
| FR-027 Targeted repair | Repair | RepairPlan | repair-plan | layer-failure fixture | passing layers preserved |
| FR-028 Lineage | Artifact/Lineage | all version refs | lineage | trace query test | artifact→story trace works |
| FR-029 Approval/lock | Domain services | statuses/versions | approve/lock command | illegal transition test | locked fact cannot silently mutate |
| FR-030 Restart safe | Backend recovery | jobs/stages | recovery | crash/restart E2E | exact resume/reconcile |
| FR-031 Editorial | Editorial | TimelineVersion | timeline/export | non-destructive edit test | source lineage retained |
| FR-032 3D previs | optional plugin | SpatialBaseline | previs | optional plugin contract | no core dependency |

---

# Non-functional Traceability

| Req | Control / Component | Test |
|---|---|---|
| NFR-001 provider independence | ShotIR + adapter boundary | import/dependency architecture test |
| NFR-002 durable state | SQLite repository | crash/restart |
| NFR-003 idempotency | GenerationJob/idempotency | duplicate submit injection |
| NFR-004 deterministic validation | Zod/JSON Schema + semantic validator | invalid fixture suite |
| NFR-005 recoverability | Recovery Coordinator | crash point matrix |
| NFR-006 observability | events/logs/metrics | event presence/redaction |
| NFR-007 one authority | module boundary rules | architecture dependency test |
| NFR-008 extensibility | ProviderAdapter | add mock provider without domain edits |
| NFR-009 long-form scale | DB + incremental loading | 300-shot benchmark |
| NFR-010 testability | mock providers/repos | offline integration suite |
| SEC-001 secrets | Security Broker | secret persistence/log scan |
| SEC-002 credential isolation | Main safeStorage broker | renderer cannot access secret |
| SEC-003 log redaction | logging | token/cookie fixture |
| SEC-004 path traversal | File broker | traversal/symlink tests |
| SEC-005 plugin permissions | future plugin host | permission denial tests |
| SEC-006 data-only import | importers | malicious payload fixtures |
| REL-001 completion≠acceptance | Job vs QA state | state transition test |
| REL-002 ambiguous timeout | Recovery/Provider | timeout-after-submit injection |
| REL-003 parent invalidation | dependency graph | selective invalidation test |
| REL-004 migration | migration manager | upgrade/rollback/backup test |
| REL-005 corrupt metadata | artifact reconciler | corruption fixture |


# Provider Ambiguity Traceability Addendum

| Req | Component | Data | Contract | Test | Acceptance |
|---|---|---|---|---|---|
| REL-006 no blind ambiguous resubmit | Orchestrator + Provider Adapter | GenerationJob + RecoveryProfile | submit/reconcile | response-loss fault injection | no automatic duplicate |
| REL-007 provider recovery evidence | Provider Registry | RecoveryProfile | provider-profile | adapter evidence fixture/live proof | policy reflects verified provider capability |


# Credential Broker Traceability Addendum

| Req | Component | Data | Contract | Test | Acceptance |
|---|---|---|---|---|---|
| SEC-007 renderer cannot retrieve secret | Main Security Broker | credential metadata | renderer credential API | renderer secret-call negative test | no secret method/result |
| SEC-008 credential use is scoped | Main Broker | lease metadata | credential lease | wrong provider/operation/utility tests | unauthorized use denied |
| SEC-009 lease lifecycle | Main Broker | credential version/session | lease | expiry/replay/crash/rotation | stale/replayed lease denied |
| SEC-010 project export excludes vault | Export + Broker | credential ID only | export manifest | canary scan | no plaintext/encrypted vault payload |
| SEC-011 secret redaction | Logging | structured log | redaction policy | canary log scan | no canary in sink |


# Performance / Admission Traceability Addendum

| Req | Component | Data | Contract | Test | Acceptance |
|---|---|---|---|---|---|
| PERF-001 provider-safe concurrency | Scheduler | ProviderProfile + active counts | admission policy | flat vs hierarchical simulation | no configured cap violation |
| PERF-002 project fairness | Scheduler | queued jobs | scheduling policy | multi-project synthetic load | no persistent starvation under equal priority |
| PERF-003 budget admission | Scheduler/Cost | estimate/actual cost | budget policy | hard-budget simulation | new submissions block at hard budget |
| REL-008 migration startup gate | Recovery/Migration | migration state | startup contract | interrupted migration harness | scheduler blocked until compatible/completed |


# Evidence Governance Traceability Addendum

| Req | Component | Data | Contract | Test | Acceptance |
|---|---|---|---|---|---|
| NFR-011 evidence provenance | Evidence Ledger | evidence entry + SHA-256 | evidence schema | ledger integrity verification | changed/missing evidence fails integrity |
| NFR-012 evidence-class gate closure | Gate Evaluator | gate rules + evidence classes | gate rules JSON | gate verifier | weak evidence cannot close stronger gate |
| REL-009 orthogonal job state authority | Orchestrator/Artifact/QA | four state axes | job state contract | model reachability/scenario test | no approval duplication; ambiguity has recovery state |


# Windows Persistence Evidence Addendum

| Req | Component | Data | Contract | Test | Acceptance |
|---|---|---|---|---|---|
| REL-010 single SQLite write ownership | Production Utility / Repository | write queue + DB connection | persistence command contract | Windows V2 12-producer single-writer spike | 3000/3000, 0 writer/producer errors, integrity ok |

# Story Intelligence V0.16 Traceability Addendum

| Req | Component | Data | Contract | Minimum Test | Acceptance |
|---|---|---|---|---|---|
| FR-033 premise | Premise Lab | PremiseCandidate | story-premise | candidate/anti-topic fixtures | selected premise has pressure/stakes |
| FR-034 angle | Angle Lab | AngleCandidate | story-angle | multi-angle fixture | lens/question/advantage explicit |
| FR-035 theme | Theme System | ThemeHypothesis | theme | choice/consequence fixture | theme embodied, not only stated |
| FR-036 research | Research Intelligence | ResearchBrief/EvidenceClaim/Edge | research evidence | source/contradiction fixture | provenance + unresolved gaps retained |
| FR-037 story material | Material Transformer | StoryMaterial | story-material | evidence→scene-material fixtures | story function + provenance present |
| FR-038 Brain resolver | Brain Resolver | BrainPack/BrainResolution | brain policy | conflict/precedence tests | locked canon cannot be overridden |
| FR-039 character psychology | Character Engine | CharacterModelVersion | character model | motivation/voice fixtures | major action has intelligible basis |
| FR-040 knowledge/relationship | Character State | KnowledgeState/RelationshipState | character-state | knowledge-leak tests | no unsupported knowledge dependency |
| FR-041 conflict/stakes | Conflict Engine | ConflictModel/StakesModel | conflict | escalation fixtures | pressure/stakes progression explicit |
| FR-042 causal graph | Structure Engine | StoryGraph | story-graph | missing-edge/cycle/causal fixtures | major nodes have causal rationale |
| FR-043 emotional arc | Emotion Engine | EmotionalArcPlan | emotion-arc | arc-turn fixture | emotional turns caused/consequential |
| FR-044 rhythm/tension | Rhythm Engine | EmotionalRhythmPoint | rhythm | flatline/whiplash fixtures | diagnostics generated, not authority |
| FR-045 scene change | Scene Engine | SceneContract | scene | static-scene fixture | key change or accepted exception |
| FR-046 beat microchange | Beat Engine | BeatContract | beat-v2 | repeated-tactic fixtures | micro-change explicit |
| FR-047 dialogue/subtext | Dialogue Engine | DialogueIntent | dialogue-intent | knowledge/voice/subtext fixtures | line respects intent/knowledge |
| FR-048 setup/payoff | Story Ledger | SetupPayoffLink | setup-payoff | plant/payoff/orphan fixtures | critical promises accounted for |
| FR-049 critique council | Story QA | CritiqueFinding | critic result | blinded critic/hollow pass fixture | located evidence + severity |
| FR-050 quality gate | Story QA | StoryQualityResult | story-quality | blocking-vs-average adversarial tests | blocking cannot average away |
| FR-051 story repair | Story Repair | StoryRepairPlan | story-repair | root-layer/selective rewrite fixtures | preserve/patch/invalidate/recheck |
| FR-052 script lock | Story Lock | ScriptLockManifest | script-lock | unresolved-blocker/hash tests | locked version explicit/immutable |

| Req | Control / Component | Test |
|---|---|---|
| NFR-013 donor isolation | dependency/license boundary | forbidden donor import/license scan + architecture test |
| NFR-014 Brain Packs | Brain Registry/Resolver | add new genre pack without engine fork |
| NFR-015 critique independence | Critique Orchestrator | blinded-role + provenance + hollow-pass tests |
| NFR-016 factual provenance | Research/Story Material/Lock | claim→material→script trace + contested-claim fixture |

