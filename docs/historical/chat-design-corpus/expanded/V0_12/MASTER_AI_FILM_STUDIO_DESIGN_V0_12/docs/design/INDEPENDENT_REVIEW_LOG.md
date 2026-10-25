# INDEPENDENT_REVIEW_LOG.md
# Independent Review Log — Draft V0.1

The reviewers below are treated as independent roles. Each round restarts from the design problem rather than assuming the previous round was correct.

---

# ROUND 1 — Product Completeness Reviewer

**Scope reviewed:** Project Vision, Requirements, Architecture Draft.  
**Question:** Can the system actually cover idea→film without hidden gaps?

## Findings

### HIGH — R1-F01
There is no explicit distinction between *rough screenplay* and *production script lock*.  
**Impact:** downstream shot planning may bind to prose still undergoing structural revision.  
**Recommendation:** add separate states `ROUGH_SCRIPT`, `REVIEWED_SCRIPT`, `LOCKED_SCRIPT`.  
**Decision:** ACCEPT.

### HIGH — R1-F02
Audio/narration/dialogue are mentioned late but not yet represented as first-class production data.  
**Impact:** lip-sync/dialogue timing and shot duration may diverge.  
**Recommendation:** add Audio Bible + dialogue timing contract before final shot lock for applicable projects.  
**Decision:** ACCEPT.

### MEDIUM — R1-F03
Project formats (film/short/vertical/explainer/documentary) are not formalized.  
**Impact:** rhythm and hierarchy defaults may be wrong.  
**Recommendation:** add `ProductionFormatProfile` as policy input, not domain authority.  
**Decision:** ACCEPT.

**Design patch:** architecture must include Script Lock Gate, Audio/Dialogue state, Production Format Profile.

**Residual risk:** story quality remains partly model/judgment dependent.

---

# ROUND 2 — Architecture Reviewer

**Scope:** component boundaries and authority.  
**Question:** Where is coupling likely to force a rewrite?

## Findings

### CRITICAL — R2-F01
If FlowKit database objects are imported directly into canonical domain, provider/runtime concerns will leak upward.  
**Impact:** architecture becomes FlowKit-centric again.  
**Recommendation:** anti-corruption adapter boundary around FlowKit concepts.  
**Decision:** ACCEPT.

### HIGH — R2-F02
Story Engine and Directing Engine boundaries can overlap on scene purpose and rhythm.  
**Recommendation:** Story owns *what changes and why*; Directing owns *what audience experiences and how the scene is staged*.  
**Decision:** ACCEPT.

### MEDIUM — R2-F03
Reference Resolver and Provider Compiler may both choose refs.  
**Recommendation:** Resolver selects semantic refs; provider compiler only maps/limits/orders them.  
**Decision:** ACCEPT.

**Design patch:** define explicit authority matrix.

---

# ROUND 3 — Data & State Reviewer

## Findings

### CRITICAL — R3-F01
Parent image cannot be authoritative state by itself.  
**Impact:** visual defects can propagate.  
**Decision:** accepted StateSnapshot remains semantic authority; parent image is one conditioning artifact.

### HIGH — R3-F02
Need revision/version fields on Story, Entity, Reference, ShotSpec, ShotIR and StateSnapshot.  
**Decision:** ACCEPT.

### HIGH — R3-F03
Need optimistic concurrency or transaction strategy for user edit vs background job completion.  
**Decision:** OPEN — requires DB choice.

### HIGH — R3-F04
Need stable lineage to detect stale generation completion.  
**Decision:** ACCEPT; generation job records expected input versions/hashes.

**Patch:** add input-version fingerprint to jobs and stale-result check before acceptance.

---

# ROUND 4 — Security Reviewer

## Findings

### CRITICAL — R4-F01
Provider adapters may need credentials/session artifacts; storing them in project state is unacceptable.  
**Decision:** secrets isolated in OS/keychain/config secret store, referenced by credential ID only.

### HIGH — R4-F02
Imported screenplay/project files are untrusted.  
**Decision:** parsing is data-only; no embedded script execution.

### HIGH — R4-F03
Plugin architecture can create arbitrary filesystem/network access.  
**Decision:** plugin permission manifest required before plugin marketplace is considered.

### MEDIUM — R4-F04
Logs may leak prompts/private scripts/provider tokens.  
**Decision:** structured redaction policy required.

**Patch:** add security boundary document before L6.

---

# ROUND 5 — Reliability / Failure / Recovery Reviewer

## Findings

### BLOCKER — R5-F01
Ambiguous provider timeout can lead to duplicate paid jobs if retry blindly resubmits.  
**Decision:** introduce `UNKNOWN_REMOTE_STATE`; reconcile provider job ID/status before any re-submit.

### CRITICAL — R5-F02
Crash between artifact download and DB commit can orphan files.  
**Decision:** use staged artifact write + atomic metadata commit/reconciliation scan.

### HIGH — R5-F03
Provider job may finish after user edits ShotSpec.  
**Decision:** input fingerprint check; mark result `STALE_RESULT`, never auto-approve.

### HIGH — R5-F04
Cancellation semantics not yet defined for remote providers that cannot cancel.  
**Decision:** local state becomes `CANCEL_REQUESTED`; ignore/retain late artifact according to policy.

**Patch:** failure model expanded.

---

# ROUND 6 — Performance / Concurrency Reviewer

## Findings

### HIGH — R6-F01
Global concurrency number is insufficient; each provider/model has different quotas.  
**Decision:** layered limits:
`global → provider → model → operation type`.

### HIGH — R6-F02
Reference image preprocessing can become repeated I/O/CPU work.  
**Decision:** cache normalized reference derivatives by content hash.

### MEDIUM — R6-F03
Sequence QA on hundreds of shots can be expensive.  
**Decision:** hierarchical incremental QA; re-evaluate only affected sequence/project windows.

### MEDIUM — R6-F04
Large media should not live in DB blobs by default.  
**Decision:** DB stores metadata; artifact store owns files.

---

# ROUND 7 — Maintainability / Extensibility Reviewer

## Findings

### CRITICAL — R7-F01
Multiple imported repo schemas could create duplicate domain models.  
**Decision:** no external schema is canonical. All external code adapts to project contracts.

### HIGH — R7-F02
Provider-specific fields must never be added directly to ShotSpec.  
**Decision:** provider extension data lives in compiled request/adapters.

### MEDIUM — R7-F03
Genre packs can explode core complexity.  
**Decision:** genre knowledge as optional policy/plugins.

---

# ROUND 8 — Testing / Acceptance Reviewer

## Findings

### CRITICAL — R8-F01
No requirement→test traceability yet.  
**Decision:** cannot reach L7 until traceability matrix exists.

### HIGH — R8-F02
Need failure-injection tests for crash/restart, provider timeout, duplicate job, stale result, DB lock/corruption.  
**Decision:** ACCEPT.

### HIGH — R8-F03
Need creative benchmark distinct from unit tests.  
**Decision:** 3 projects × 100 shots target benchmark remains candidate.

### MEDIUM — R8-F04
QA metric calibration requires labeled acceptance dataset.  
**Decision:** research target.

---

# ROUND 9 — Deployment / Operations Reviewer

## Findings

### HIGH — R9-F01
Desktop-only vs local service architecture not yet frozen.  
**Decision:** open research.

### HIGH — R9-F02
Update while jobs are active can corrupt assumptions.  
**Decision:** update gate must block or checkpoint active production, then migrate schema with rollback/backup.

### MEDIUM — R9-F03
Artifact retention policy missing.  
**Decision:** add retention/cleanup requirement before freeze.

---

# ROUND 10 — Devil's Advocate / Red Team Design Review

## Findings

### CRITICAL — R10-F01
The design risks over-engineering by creating too many formal stages for simple one-shot use.  
**Impact:** poor UX, high implementation cost.  
**Decision:** ACCEPT. Add “progressive complexity”: simple requests use same contracts with minimal optional fields; UI hides advanced structures unless needed.

### HIGH — R10-F02
“8 layers” can become a rigid checklist and produce bloated prompts.  
**Decision:** layers are semantic state, not mandatory repeated prose. Compiler emits only provider-relevant information.

### HIGH — R10-F03
Targeted Repair could become a false promise if models ignore isolated prompt changes.  
**Decision:** repair engine must distinguish `PATCH_IN_PLACE`, `REGENERATE_FROM_ANCHOR`, and `REPLAN_SHOT`.

### HIGH — R10-F04
Reference Bible with many views can exceed provider ref limits.  
**Decision:** semantic resolver + provider capability profile chooses subset; do not upload all refs.

### MEDIUM — R10-F05
Sequence/Scene/Beat can be overkill for a 5-second clip.  
**Decision:** hierarchy remains canonical but supports auto-created single sequence/scene/beat wrappers.

---

# Current Review Outcome

No design freeze.

**Blockers:** 1 resolved conceptually, implementation contract not yet specified.  
**Critical unresolved areas:** persistence/transaction model, security model, formal contract schemas, test traceability, deployment/update model.  
**Maturity remains:** L4 — Researched Design.

---


# ROUND 11 — Persistence Technology Reviewer

**Scope:** SQLite WAL vs PostgreSQL vs DuckDB.

## Findings

### HIGH — R11-F01
Choosing PostgreSQL now would improve multi-user concurrency but create unnecessary deployment/support burden for the current local-first V1 assumptions.

**Decision:** keep PostgreSQL as explicit scale-up path, not mandatory V1 dependency.

### HIGH — R11-F02
DuckDB is attractive because it is embedded, but its primary design is analytical/bulk workloads rather than operational job-state churn.

**Decision:** reject DuckDB as operational source of truth; optional analytics later.

### MEDIUM — R11-F03
SQLite `synchronous=NORMAL` improves write latency but can lose recently committed transactions across power loss in WAL mode.

**Decision:** candidate default becomes `WAL + FULL`; benchmark before freeze, but durability wins unless evidence shows unacceptable overhead.

**Design change:** `PERSISTENCE_ARCHITECTURE.md`, ADR-0001.

---

# ROUND 12 — Transaction / Concurrency Reviewer

## Findings

### CRITICAL — R12-F01
A provider HTTP call must never occur inside a DB transaction.

**Impact:** long-held writer lock, poor concurrency, impossible distributed atomicity.

**Decision:** use PREPARE → SUBMIT → COMMIT REMOTE ID application protocol.

### CRITICAL — R12-F02
Read-then-write without revision checks can overwrite user edits with late background job updates.

**Decision:** optimistic `revision` checks + immutable creative versions.

### HIGH — R12-F03
Up to 12 generation slots does not require 12 DB writers; orchestrator writes can remain short/serialized.

**Decision:** maintain single-host write model for V1.

---

# ROUND 13 — Crash Consistency Reviewer

## Findings

### BLOCKER — R13-F01
Crash after remote provider accepts a job but before local DB stores the remote job ID can create duplicate paid generations on restart.

**Decision:** introduce `UNKNOWN_REMOTE_STATE`; reconcile before retry. No blind resubmit.

### CRITICAL — R13-F02
Artifact file and metadata cannot be atomically committed in one SQLite transaction.

**Decision:** staged immutable file protocol + checksum + DB commit + startup reconciler.

### HIGH — R13-F03
Late artifact from an obsolete ShotSpec can overwrite newer state unless all jobs carry input fingerprints.

**Decision:** `STALE_RESULT` hard gate.

---

# ROUND 14 — Backup / Migration Reviewer

## Findings

### HIGH — R14-F01
Copying only SQLite DB is not a project backup because artifact bytes live outside DB.

**Decision:** backup manifest must bind DB snapshot to immutable artifact hashes.

### HIGH — R14-F02
Opening a newer unsupported schema in write mode is unsafe.

**Decision:** schema compatibility gate before scheduler starts.

### MEDIUM — R14-F03
Destructive migrations need pre-migration backup and resumable data backfill.

**Decision:** add migration policy.

---

# ROUND 15 — Devil's Advocate: Persistence Simplification

## Findings

### HIGH — R15-F01
The proposed data model can become over-normalized and expensive to implement before core behavior is proven.

**Decision:** keep canonical ownership/entities, but permit JSON columns for evolving semantic substructures (8 layers, state details, QA dimensions) in V1. Do not prematurely normalize every nested field.

### HIGH — R15-F02
Content-addressed artifact storage may complicate user-visible file organization.

**Decision:** physical storage can be content-addressed while UI/export provides human-readable aliases/manifests.

### MEDIUM — R15-F03
Worker leases may be unnecessary in a strictly single-process V1.

**Decision:** retain lease fields as small forward-compatible orchestration metadata, but do not implement distributed-worker complexity until required.

**Review outcome:** no new unresolved BLOCKER introduced after design patches. Persistence architecture can advance to a reviewed candidate, but architecture remains unfrozen because security/contracts/traceability/deployment are still open.

---

# ROUND 16 — Desktop Security Boundary Reviewer

### CRITICAL — R16-F01
A generic renderer IPC bridge would recreate a Node-like privilege surface even with `nodeIntegration=false`.

**Decision:** expose capability-specific methods only; validate sender + schema + authorization on every privileged IPC.

### HIGH — R16-F02
Renderer must not access credential decryption API.

**Decision:** secret broker remains main-process only.

### HIGH — R16-F03
Remote/untrusted content in privileged BrowserWindow is unnecessary risk.

**Decision:** application renderer is local packaged content; external links open under explicit allowlist/policy.

---

# ROUND 17 — Secrets / Credential Reviewer

### CRITICAL — R17-F01
Putting encrypted provider secrets directly into project backups would copy credentials between machines/users unexpectedly.

**Decision:** project stores credential IDs only; credential vault is machine/user-scoped and excluded from project export.

### HIGH — R17-F02
`safeStorage` availability/security semantics differ by platform.

**Decision:** detect availability and define unsupported/degraded state rather than claiming universal protection.

### HIGH — R17-F03
Provider browser sessions require a different lifecycle than API keys.

**Decision:** credential type is explicit; session data remains provider/session scoped.

---

# ROUND 18 — Filesystem / Import Red Team

### BLOCKER — R18-F01
Imported archive/project paths can cause path traversal or symlink escape.

**Decision:** authorized-root path resolver + archive extraction policy + traversal tests.

### CRITICAL — R18-F02
Imported metadata must never trigger dynamic JS/module execution.

**Decision:** import is data-only; no `eval`, dynamic code execution, or arbitrary process invocation.

### HIGH — R18-F03
Generic shell command construction for ffmpeg creates injection risk.

**Decision:** fixed executable + argv array + no shell.

---

# ROUND 19 — Contract Architecture Reviewer

### CRITICAL — R19-F01
TypeScript interfaces alone cannot protect IPC/import/provider boundaries at runtime.

**Decision:** runtime validation required.

### HIGH — R19-F02
Using only Zod internal schemas would reduce language-neutral interoperability.

**Decision:** Zod 4 candidate + export Draft 2020-12 JSON Schema.

### HIGH — R19-F03
Zod transforms/custom types may not map safely to JSON Schema.

**Decision:** persisted/public contracts restricted to JSON-representable schemas.

---

# ROUND 20 — Contract Evolution Reviewer

### CRITICAL — R20-F01
Unknown enum values can change semantics even when object shape validates.

**Decision:** contract versions + strict semantic handling; unsupported major/semantic values fail explicitly.

### HIGH — R20-F02
Schema validation alone cannot verify cross-reference invariants.

**Decision:** every core contract has shape validation + semantic validator.

### MEDIUM — R20-F03
Provider capability data will become stale.

**Decision:** profile versions include `verified_at` and evidence.

---

# ROUND 21 — Observability Reviewer

### HIGH — R21-F01
Console logs are insufficient to reconstruct paid-job/recovery history.

**Decision:** durable operational events + structured logs.

### HIGH — R21-F02
Raw prompts/scripts in telemetry create privacy risk.

**Decision:** IDs/hashes/status/timings by default; content diagnostic capture opt-in.

### MEDIUM — R21-F03
Making OpenTelemetry required for local desktop adds infrastructure burden.

**Decision:** internal abstraction; OTel optional exporter.

---

# ROUND 22 — Process Topology Reviewer

### CRITICAL — R22-F01
Running orchestration/provider/ffmpeg work in Electron main expands failure domain and threatens UI/window security responsibilities.

**Decision:** utility-process production backend candidate.

### HIGH — R22-F02
A localhost service would require its own auth/origin/port security.

**Decision:** defer service topology until headless/multi-client requirement appears.

### MEDIUM — R22-F03
Utility process crash/restart requires reconnect/recovery protocol.

**Decision:** main supervises utility process; backend replays durable recovery before accepting work.

---

# ROUND 23 — Traceability Auditor

### HIGH — R23-F01
Previous design had requirements and tests conceptually but no explicit row-by-row mapping.

**Decision:** initial requirement traceability matrix created for FR/NFR/SEC/REL requirements.

### HIGH — R23-F02
Traceability currently names minimum tests, not exact test IDs.

**Decision:** sufficient for L5 candidate; exact test IDs belong after task decomposition / implementation plan.

### MEDIUM — R23-F03
Some creative requirements cannot be proven only by deterministic unit tests.

**Decision:** acceptance includes labeled fixtures + production benchmark evidence.

---

# ROUND 24 — Cross-Architecture Contradiction Reviewer

### CRITICAL — R24-F01
Main-process-only `safeStorage` conflicts with provider adapters executing in utility process unless secret flow is specified.

**Decision:** credential broker contract added; exact secret handoff implementation remains a required design spike.

### HIGH — R24-F02
State Engine and Artifact parent conditioning can disagree.

**Decision:** semantic StateSnapshot is authority; artifact is conditioning/evidence. Conflict blocks propagation.

### HIGH — R24-F03
Static/Motion compiler and Provider Compiler responsibilities could overlap.

**Decision:** canonical compiler produces semantic static/motion request; provider compiler maps capability/dialect only.

---

# ROUND 25 — Devil's Advocate / Complexity Reviewer

### HIGH — R25-F01
Security broker + utility process + backend contracts increases complexity for a single-user app.

**Decision:** keep because it isolates renderer privileges and long-running production work; do not add localhost service/microservices.

### HIGH — R25-F02
Zod + JSON Schema can create two perceived sources of truth.

**Decision:** Zod is implementation source only in TypeScript; exported JSON Schema is generated artifact. Domain documentation defines semantics.

### HIGH — R25-F03
Durable events can duplicate database state and become an accidental event-sourcing architecture.

**Decision:** events are audit/observability records only; current-state tables remain authoritative.

### MEDIUM — R25-F04
The traceability matrix can become bureaucracy if never exercised.

**Decision:** each future task/test must reference requirement IDs; acceptance review samples the matrix.

---

# Review status after Round 25

**New unresolved BLOCKER:** 0 after patches.  
**Known critical design items still requiring evidence/spike before hardening:** secret handoff implementation, SQLite concurrency/crash spikes, update/migration implementation proof, real provider reconciliation behavior per adapter.

The design can advance to **L5 — Reviewed Design Candidate**, but is not L6 Hardened and not L7 Frozen.

---

# ROUND 26 — Static QA Reviewer

### CRITICAL — R26-F01
A single aesthetic/semantic score can allow a wrong identity or story-critical prop to pass.

**Decision:** severity-based dimensions; any BLOCKING fail forces overall fail.

### HIGH — R26-F02
Reviewing only against prompt can miss canonical state/reference truth.

**Decision:** QA consumes ShotSpec/ShotIR + refs + state + parent, not prompt alone.

### HIGH — R26-F03
One monolithic vision reviewer may anchor across dimensions.

**Decision:** dimension-isolated reviewer contracts for high-risk checks.

---

# ROUND 27 — QA Calibration Reviewer

### CRITICAL — R27-F01
Without labeled near-miss fixtures, a QA system can look sophisticated but have high blocking false negatives.

**Decision:** labeled calibration set required; track precision/recall by defect class.

### HIGH — R27-F02
Reviewer confidence is not calibrated probability.

**Decision:** store confidence as reviewer metadata only; acceptance relies on tested policy.

### MEDIUM — R27-F03
Provider/model changes can shift QA error distribution.

**Decision:** calibration metrics are versioned by reviewer/model and periodically revalidated.

---

# ROUND 28 — Repair Root-Cause Reviewer

### CRITICAL — R28-F01
A visible camera failure may originate upstream from bad blocking, not L6 camera fields.

**Decision:** "earliest responsible layer" requires causal diagnosis, not defect-name lookup alone.

### HIGH — R28-F02
A repair may fix target field but break identity/state.

**Decision:** targeted recheck plus lightweight regression dimensions required.

### HIGH — R28-F03
Repeated repair can burn cost indefinitely.

**Decision:** bounded attempts + escalation modes.

---

# ROUND 29 — Continuity Repair Reviewer

### CRITICAL — R29-F01
Repairing an accepted end-state can invalidate descendants even if their prompts did not change.

**Decision:** dependency invalidation tracks semantic state ancestry, not only prompt hash.

### HIGH — R29-F02
Re-anchoring to canon may erase legitimate accumulated dirt/injury/state.

**Decision:** re-anchor combines canonical identity with current approved semantic state.

---

# ROUND 30 — Performance / Backpressure Reviewer

### HIGH — R30-F01
A single global concurrency setting ignores provider/model quotas and can cause rate-limit storms.

**Decision:** hierarchical token limits: global/provider/model/operation/local resource.

### HIGH — R30-F02
Bulk long-form jobs can starve interactive work.

**Decision:** priority + project fairness + oldest-ready.

### MEDIUM — R30-F03
Aggressive QA may become more expensive than generation.

**Decision:** store per-stage cost; allow policy profiles while never bypassing blocking QA.

---

# ROUND 31 — Cost Governance Reviewer

### HIGH — R31-F01
Estimated cost can be stale or unavailable.

**Decision:** store estimate basis/version and actual cost separately.

### HIGH — R31-F02
Hard budget must not reinterpret already-paid remote jobs as cancelable/refundable.

**Decision:** budget gate applies to new submissions; cancellation follows provider semantics.

### MEDIUM — R31-F03
Stale-result cost needs visibility to expose orchestration waste.

**Decision:** track wasted stale/failed candidate cost.

---

# ROUND 32 — Update / Migration Reviewer

### BLOCKER — R32-F01
Scheduler must not start while schema migration is incomplete/unsupported.

**Decision:** schema compatibility/migration gate precedes recovery and scheduler startup.

### CRITICAL — R32-F02
Destructive migration without verified backup can irreversibly break projects.

**Decision:** verified pre-migration backup required.

### HIGH — R32-F03
Remote job identity must survive app version change.

**Decision:** migration contract preserves job/provider identifiers and reconciliation semantics.

---

# ROUND 33 — SQLite Spike Evidence Reviewer

**Evidence reviewed:** `SQLITE_WAL_DESIGN_SPIKE_EVIDENCE.md`.

### Finding R33-F01 — POSITIVE EVIDENCE
The current sandbox completed all 1,800 short write transactions with 12 threads, no reported write errors, and correct final counter/event counts.

**Decision:** supports local metadata-write feasibility under the tested environment.

### Finding R33-F02 — POSITIVE EVIDENCE
Optimistic revision update detected stale second writer (`rowcount=0`).

**Decision:** keep revision-based concurrency conflict design.

### Finding R33-F03 — POSITIVE EVIDENCE WITH LIMITATION
Committed transaction survived abrupt process exit; uncommitted row did not; integrity check returned `ok`.

**Limitation:** not a physical power-loss test on target Windows hardware.

### Finding R33-F04
Artifact reconciliation spike correctly classified staging, orphan/uncommitted final, and READY-metadata/missing-file cases.

**Decision:** reconciler architecture strengthened.

---

# ROUND 34 — Evidence Sufficiency Reviewer

### HIGH — R34-F01
The SQLite spike ran in sandbox/Linux-like environment, not the target Windows desktop.

**Decision:** retain Windows-target spike before L6.

### HIGH — R34-F02
No real provider ambiguity spike has yet been executed.

**Decision:** architecture cannot be called hardened against duplicate paid jobs until at least the V1 provider paths are verified.

### HIGH — R34-F03
No real Electron safeStorage↔utilityProcess spike has been executed.

**Decision:** credential boundary remains reviewed candidate, not hardened.

---

# ROUND 35 — Devil's Advocate / Freeze Gate Reviewer

### CRITICAL — R35-F01
The design documentation is now deep enough that there is a risk of declaring success because the documents are comprehensive.

**Decision:** document completeness is not production evidence.

### HIGH — R35-F02
Static QA and Targeted Repair remain designs without calibrated execution evidence.

**Decision:** do not advance to L6 yet.

### HIGH — R35-F03
A 300-shot benchmark should not be used to discover basic architecture defects that smaller adversarial tests can expose earlier.

**Decision:** sequence:
small deterministic/failure spikes
→ QA calibration
→ repair benchmark
→ multi-provider integration
→ 300-shot production benchmark.

---

# Review status after Round 35

**Unresolved conceptual BLOCKER:** 0 after design patching.  
**Evidence blockers for L6:** real provider ambiguity, target-platform credential broker, target Windows DB/update spikes, QA calibration, repair benchmark.

**Current maturity:** L5.5 — Reviewed + Partial Hardening Evidence.

---

# ROUND 36 — Provider Ambiguity Auditor

**Scope:** submit → response → local persistence window.

### CRITICAL — R36-F01
FlowKit prevents duplicate submit only after the remote operation identifier is already persisted.

**Evidence:** `generate_scene_video()` re-polls when existing operation ID is found; repository unit test asserts submit is not called in that branch.

**Decision:** KEEP this behavior.

### BLOCKER — R36-F02
There is a crash/response-loss window after remote acceptance but before the operation handle is written locally.

**Impact:** next generic retry can create a second paid job.

**Decision:** add `SUBMITTING → UNKNOWN_REMOTE_STATE → RECONCILING/AMBIGUOUS_HOLD`; remove generic retry from this path.

**Resolved by design patch:** YES.

---

# ROUND 37 — Provider Capability Reviewer

### HIGH — R37-F01
An operation handle is not the same thing as idempotency.

**Decision:** provider profile separates:
- operation handle;
- idempotency;
- lookup by client token;
- list/search;
- artifact-prefix recovery.

### HIGH — R37-F02
No provider may inherit a generic "safe retry" flag from another provider family.

**Decision:** submission-recovery profile is versioned per provider/model family with evidence date.

---

# ROUND 38 — Veo Documentation Reviewer

### HIGH — R38-F01
Current documented Veo flow returns a server-assigned long-running operation and requires that operation to poll status.

**Decision:** once handle is durably stored, re-poll is safe architecture.

### HIGH — R38-F02
Current audited public `GenerateVideosParameters` / REST examples do not establish a caller-controlled idempotency key.

**Decision:** do not assume exactly-once submit across response loss.

### MEDIUM — R38-F03
Unique `outputGcsUri` can help identify completed output, but it does not prove whether an in-progress job exists.

**Decision:** classify as artifact-level fallback only.

---

# ROUND 39 — FlowKit Migration Reviewer

### CRITICAL — R39-F01
The existing `request.request_id` field is semantically overloaded when it stores a remote operation ID.

**Decision:** canonical model separates:
- local_request_id;
- provider_request_id;
- provider_operation_id;
- idempotency_key.

### HIGH — R39-F02
Four statuses PENDING/PROCESSING/COMPLETED/FAILED are insufficient for financially safe remote orchestration.

**Decision:** canonical job state machine includes submission/reconciliation ambiguity states.

---

# ROUND 40 — Fault Injection Reviewer

**Evidence reviewed:** `provider_ambiguity_simulation_results.json`.

### Finding R40-F01 — POSITIVE
Legacy Flow-like lost-response scenario created 2 remote jobs in the simulator.

**Decision:** duplicate hazard reproduced.

### Finding R40-F02 — POSITIVE
Safety-first HANDLE_ONLY policy created 1 remote job and held locally at `AMBIGUOUS_HOLD`.

**Decision:** financial safety invariant validated locally.

### Finding R40-F03 — POSITIVE
Simulated server-idempotency and client-token lookup recovered the original operation with 1 remote job.

**Decision:** reconciliation capability classes are useful and testable.

### Finding R40-F04 — POSITIVE WITH LIMITATION
1,500 randomized runs across HANDLE_ONLY/SERVER_IDEMPOTENCY/CLIENT_TOKEN_LOOKUP produced zero automatic duplicates under the safe algorithm.

**Limitation:** mock provider, not real billing/provider network.

---

# ROUND 41 — Recovery UX Reviewer

### HIGH — R41-F01
`AMBIGUOUS_HOLD` can appear as a "stuck job" if UI does not explain it.

**Decision:** UI must display:
- remote acceptance uncertain;
- automatic resubmit intentionally blocked;
- reconciliation attempts/evidence;
- available user action.

### HIGH — R41-F02
A manual "retry anyway" button could bypass safety.

**Decision:** any forced duplicate submit must be explicit, warn about possible duplicate charge, create a new attempt lineage, and never masquerade as ordinary retry.

---

# ROUND 42 — Evidence Sufficiency / Freeze Reviewer

### CRITICAL — R42-F01
Code inspection + documentation + local fault injection are not equivalent to live provider ambiguity proof.

**Decision:** mark this gate `PARTIAL_PROOF`, not CLOSED.

### HIGH — R42-F02
Live proof must be provider-specific because idempotency/reconciliation semantics vary.

**Decision:** every V1 provider adapter requires its own evidence record.

### HIGH — R42-F03
Flow web/private transport and official direct Veo API must not be treated as the same provider contract.

**Decision:** maintain separate recovery profiles/adapters.

---

# Review status after Round 42

**Conceptual provider-ambiguity BLOCKER:** resolved in architecture.

**Evidence blocker:** still open until at least one real V1 provider is fault-injected live and each shipping provider has a verified recovery profile.

**Current maturity:** remains L5.5 — Reviewed + Partial Hardening Evidence.

---

# ROUND 43 — Credential Boundary Auditor

### CRITICAL — R43-F01
A credential ID is not authorization to decrypt the credential.

**Decision:** broker authorizes exact provider + operation + Utility instance before decryption.

### CRITICAL — R43-F02
Renderer must not have a generic credential-decrypt IPC route.

**Decision:** renderer API exposes metadata/binding only; no secret-returning API.

---

# ROUND 44 — Electron safeStorage Reviewer

### HIGH — R44-F01
Electron `safeStorage` is documented as Main-process API and platform semantics differ.

**Decision:** Main remains credential broker; availability/backend is explicitly checked.

### HIGH — R44-F02
Linux can fall back to `basic_text`, which is not equivalent to strong OS secret storage.

**Decision:** persistent credentials default-block on insecure backend if Linux ships.

### MEDIUM — R44-F03
Electron recommends async safeStorage APIs.

**Decision:** async API is candidate implementation path.

---

# ROUND 45 — Main-vs-Utility Secret Flow Reviewer

### HIGH — R45-F01
Keeping all credentialed networking in Main avoids Utility plaintext but bloats Main's failure/security surface.

**Decision:** reject Main network proxy for V1.

### HIGH — R45-F02
Sending a plaintext secret to Utility enlarges trusted memory surface.

**Decision:** acceptable only while Utility is first-party trusted code; enforce scoped one-use lease and exclude untrusted plugins.

### HIGH — R45-F03
If third-party providers/plugins are later loaded in Utility, this decision becomes unsafe.

**Decision:** revisit with dedicated isolated provider process.

---

# ROUND 46 — Lease Lifecycle Reviewer

### CRITICAL — R46-F01
A reusable credential token becomes a second long-lived secret.

**Decision:** leases are one-use, short TTL, Utility-instance/provider/operation/version scoped.

### HIGH — R46-F02
Utility crash can leave valid unused leases.

**Decision:** Main revokes outstanding leases on Utility exit.

### HIGH — R46-F03
Credential rotation can leave queued stale leases.

**Decision:** lease binds credential version; rotation invalidates old version.

---

# ROUND 47 — Secret Leakage Reviewer

### CRITICAL — R47-F01
Provider SDK exceptions can echo headers/options and bypass naive message redaction.

**Decision:** normalize provider errors before logging/renderer exposure and redact structured sensitive fields before sink.

### HIGH — R47-F02
Project export should not move machine credential vault.

**Decision:** export credential IDs/bindings only.

### HIGH — R47-F03
Debug mode must not disable redaction.

**Decision:** redaction is invariant, not log-level preference.

---

# ROUND 48 — Local Credential Simulation Reviewer

**Evidence:** `credential_broker_simulation_results.json`.

### POSITIVE — R48-F01
Renderer secret request denied.

### POSITIVE — R48-F02
Authorized Utility received secret only through scoped lease.

### POSITIVE — R48-F03
Replay, expiry, wrong provider, wrong operation and invalid Utility identity were denied.

### POSITIVE — R48-F04
Rotation invalidated an old lease; Utility crash revoked unused lease.

### POSITIVE — R48-F05
Vault, project export, logs and full spike workdir scans contained no canary plaintext secret.

**Limitation:** simulated vault used AES-GCM, not Electron safeStorage.

---

# ROUND 49 — Browser Session Credential Reviewer

### CRITICAL — R49-F01
A browser cookie/session bundle has different lifecycle and privilege properties than an API key.

**Decision:** do not force browser sessions through generic string lease architecture.

### HIGH — R49-F02
Provider browser sessions should remain inside provider-specific isolated session boundary.

**Decision:** browser-session provider adapters require separate hardening review.

---

# ROUND 50 — Evidence Sufficiency / Devil's Advocate

### CRITICAL — R50-F01
A clean local simulation cannot prove Windows DPAPI, Electron IPC, packaged-app behavior, or memory hygiene.

**Decision:** Credential Broker remains PARTIAL_PROOF.

### HIGH — R50-F02
JavaScript garbage collection prevents a strong guarantee that plaintext memory is immediately zeroized.

**Decision:** do not make memory-zeroization claim; minimize scope/lifetime instead.

### HIGH — R50-F03
Architecture complexity is justified only if Renderer/Main/Utility boundaries remain simple and typed.

**Decision:** no plugin system, localhost server, or extra secret process added to V1 without new requirements.

---

# Review status after Round 50

**Credential Broker conceptual blocker:** resolved.

**Local simulation:** PASS.

**Windows Electron safeStorage / real utilityProcess proof:** OPEN.

**Current maturity:** remains L5.5 — Reviewed + Partial Hardening Evidence.

---

# ROUND 51 — Static QA Policy Auditor

### CRITICAL — R51-F01
A weighted aggregate can pass a shot with one catastrophic dimension failure if the remaining dimensions score high.

**Evidence:** synthetic policy spike produced 60/60 blocking false negatives under weighted-average policy at the tested threshold.

**Decision:** weighted average cannot be final acceptance authority.

### HIGH — R51-F02
A severity gate can solve policy masking but not sensor detection failure.

**Decision:** distinguish:
- acceptance policy correctness;
- reviewer/sensor detection quality.

Both require separate evidence.

---

# ROUND 52 — QA Sensor Calibration Reviewer

### CRITICAL — R52-F01
The current spike does not use real generated images and therefore does not measure identity/continuity vision-model recall.

**Decision:** keep Static QA status PARTIAL_PROOF; real labeled near-miss image set remains mandatory.

### HIGH — R52-F02
BLOCKING false negatives are more dangerous than false positives.

**Decision:** calibration dashboard prioritizes blocking false-negative rate per defect class.

---

# ROUND 53 — Repair Planner Auditor

### HIGH — R53-F01
The planner can deterministically map a defect class to a candidate owner and invalidation scope.

**Evidence:** 180 synthetic planner cases, zero invariant violations.

**Decision:** retain typed RepairPlan.

### CRITICAL — R53-F02
Mapping defect label to owner does not prove root cause.

**Decision:** RepairPlan owner must be a diagnosis with evidence, not a fixed dictionary lookup in production.

---

# ROUND 54 — Repair Economics Reviewer

### HIGH — R54-F01
Selective invalidation reduced synthetic logical work units relative to full-regenerate baseline.

**Evidence:** average synthetic scope reduction ~48%.

**Decision:** selective invalidation remains justified.

### HIGH — R54-F02
Synthetic work units are not provider prices or success probabilities.

**Decision:** do not claim monetary savings until live/provider benchmark.

---

# ROUND 55 — Regression Reviewer

### CRITICAL — R55-F01
Generative repair can fix the target and regress preserved dimensions.

**Decision:** every repair requires target recheck plus regression checks on identity/state/prop/continuity as applicable.

### HIGH — R55-F02
Preserve-set semantics are contractual, not guaranteed by model behavior.

**Decision:** "preserve" means desired invariant to verify, not a promise that generation will obey.

---

# ROUND 56 — Hardening Order Reviewer

### HIGH — R56-F01
Target-Windows persistence proof is currently blocked by environment, but other independent hardening work can continue.

**Decision:** mark Windows proof OPEN and continue QA/repair design evidence; do not pretend target proof exists.

### HIGH — R56-F02
Live provider ambiguity and Windows credential proof remain independent open gates.

**Decision:** they stay visible in readiness instead of blocking all unrelated design investigation.

---

# ROUND 57 — Cross-System Consistency Reviewer

### HIGH — R57-F01
QA severity taxonomy, Repair failure codes and ShotSpec layers must use one shared vocabulary.

**Decision:** create/maintain canonical defect-code registry before L6.

### HIGH — R57-F02
Sequence QA failures may not belong to one shot.

**Decision:** Repair architecture must support sequence-level replan without pretending all failures are shot-local.

---

# ROUND 58 — Devil's Advocate / Evidence Gate

### CRITICAL — R58-F01
The policy spikes are intentionally easy for deterministic logic and cannot be used as evidence that AI QA or AI repair works.

**Decision:** maturity remains L5.5.

### HIGH — R58-F02
A full repair benchmark needs actual generated artifacts, ideally with controlled injected defects or curated failed generations.

**Decision:** keep "Targeted Repair Benchmark" OPEN.

---

# Review status after Round 58

**Static QA acceptance-policy design:** strengthened with local policy evidence.  
**Targeted Repair planner/invalidation design:** strengthened with local policy evidence.  
**Real visual QA calibration:** OPEN.  
**Real generative repair efficacy:** OPEN.  
**Current maturity:** L5.5 — Reviewed + Partial Hardening Evidence.

---

# ROUND 59 — Scheduler Admission Reviewer

### CRITICAL — R59-F01
A single global concurrency limit can exceed provider-specific quotas even when total concurrency looks safe.

**Evidence:** local synthetic scheduler spike recorded provider-cap violations under global-only scheduling.

**Decision:** global-only admission is rejected.

### HIGH — R59-F02
Provider limit alone can still exceed model-specific limits.

**Decision:** maintain layered global/provider/model/operation admission.

---

# ROUND 60 — Fairness / Starvation Reviewer

### HIGH — R60-F01
A large 300-shot project can monopolize capacity if scheduling is FIFO-only.

**Decision:** use priority class + project fairness + oldest-ready.

### MEDIUM — R60-F02
Strict fairness can reduce total utilization when one project has no capacity-compatible jobs.

**Decision:** fairness is preference, not hard partition; scheduler may use spare capacity.

---

# ROUND 61 — Performance Evidence Reviewer

### POSITIVE — R61-F01
300-shot SQLite metadata queries, pagination and recursive descendant lookups were inexpensive in the current sandbox.

**Decision:** no evidence that metadata scale at hundreds of shots requires PostgreSQL or microservices.

### HIGH — R61-F02
Sandbox timings are not target Windows/UI/media timings.

**Decision:** keep target benchmark open.

---

# ROUND 62 — Cost Governance Reviewer

### HIGH — R62-F01
Budget control must gate new submissions, not reinterpret already-running remote jobs as cancellable/refundable.

**Decision:** budget admission applies before side-effecting submit.

### HIGH — R62-F02
Synthetic cost units are not provider prices.

**Decision:** no monetary savings/cost claim until provider billing evidence exists.

---

# ROUND 63 — Windows Persistence Harness Reviewer

### HIGH — R63-F01
A Windows-target harness now exists, but unexecuted harness code is not Windows evidence.

**Decision:** harness creation closes only the reproducibility/design gap, not the target-runtime proof gap.

### HIGH — R63-F02
Abrupt process exit is not physical power-cut testing.

**Decision:** do not claim hardware power-loss durability from the harness.

### MEDIUM — R63-F03
Migration resume marker must block scheduler until migration reaches COMPLETED.

**Decision:** retain migration gate as hard startup invariant.

---

# ROUND 64 — Benchmark Methodology Reviewer

### HIGH — R64-F01
A faster flat scheduler is not acceptable if it violates provider caps.

**Decision:** correctness/backpressure precede makespan optimization.

### HIGH — R64-F02
Performance benchmark must separately measure metadata, provider wait, local media I/O and QA compute.

**Decision:** no single "project runtime" number used as architecture proof.

---

# ROUND 65 — Cross-Subsystem Load Reviewer

### HIGH — R65-F01
Generation concurrency and QA/ffmpeg concurrency compete for different resources.

**Decision:** local CPU/GPU/media resource pools remain separate from remote provider admission.

### HIGH — R65-F02
Disk pressure can convert healthy scheduling into artifact failures.

**Decision:** low-disk admission check remains required before large batches.

---

# ROUND 66 — L6 Readiness Reviewer

### CRITICAL — R66-F01
The architecture has extensive local evidence but still lacks target-runtime/live-provider proof in several critical gates.

**Decision:** do not advance to L6 Hardened.

### Remaining evidence blockers
- Windows persistence/update harness execution;
- Windows Electron safeStorage/utilityProcess execution;
- live provider ambiguity fault injection;
- real-image Static QA calibration;
- real-generation Targeted Repair benchmark;
- representative real provider cost/rate-limit evidence.

**Current maturity remains:** L5.5 — Reviewed + Partial Hardening Evidence.

---

# ROUND 67 — QA Dataset Design Reviewer

### CRITICAL — R67-F01
A static QA benchmark without near-miss failures will overstate recall.

**Decision:** require obvious + near-miss + hard-negative fixtures per defect class.

### HIGH — R67-F02
Single-image fixtures cannot validate shot-to-shot continuity.

**Decision:** at least 25% pair/sequence-based fixtures.

---

# ROUND 68 — Ground Truth Reviewer

### HIGH — R68-F01
One human label is insufficient for subjective cinematic defects.

**Decision:** two independent labels + adjudication; preserve disagreement data.

### HIGH — R68-F02
Reviewer tuning against the same evaluation images will overfit.

**Decision:** locked holdout split.

---

# ROUND 69 — QA Generalization Reviewer

### CRITICAL — R69-F01
One provider/style/character demographic cannot establish universal QA quality.

**Decision:** stratify provider/model/style/shot-scale/environment.

### HIGH — R69-F02
Model/reviewer upgrades invalidate old calibration assumptions.

**Decision:** calibration is versioned and repeated after material reviewer changes.

---

# ROUND 70 — Targeted Repair Experimental Design Reviewer

### HIGH — R70-F01
Repair success cannot be judged only by fixing the named target defect.

**Decision:** acceptance requires no new blocking/high regression.

### HIGH — R70-F02
Full-regenerate baseline must use equivalent upstream truth.

**Decision:** benchmark controls story/state/reference/provider inputs.

---

# ROUND 71 — Repair Causality Reviewer

### CRITICAL — R71-F01
Poor targeted-repair result can come from wrong root-cause diagnosis rather than repair mode itself.

**Decision:** failed benchmark cases receive causal-diagnosis audit.

### HIGH — R71-F02
Provider stochasticity makes single paired result unreliable.

**Decision:** record seeds when available and use enough samples per failure class.

---

# ROUND 72 — Downstream Cost Reviewer

### HIGH — R72-F01
A current-shot repair may change end state and impose downstream invalidation cost.

**Decision:** benchmark includes descendant rework when semantic end state changes.

---

# ROUND 73 — Benchmark Gate Reviewer

### CRITICAL — R73-F01
Synthetic QA/repair spikes cannot be merged conceptually with real-image/live-generation proof.

**Decision:** evidence ledger distinguishes:
- policy simulation;
- local runtime evidence;
- real visual calibration;
- live provider proof.

---

# ROUND 74 — Architecture Freeze Readiness Reviewer

### CRITICAL — R74-F01
Protocols are now reproducible, but the key visual/live experiments have not been executed.

**Decision:** architecture still must not advance to L6.

### Positive
The remaining evidence requirements are now operationally specified rather than vague.

**Current maturity:** L5.5 — Reviewed + Partial Hardening Evidence.

---

# ROUND 75 — Provider Surface Separation Reviewer

### CRITICAL — R75-F01
Treating a model brand as one provider contract is unsafe because Flow Product, Gemini API Veo and Vertex AI Veo expose different quotas, billing, job handles and support guarantees.

**Decision:** provider identity includes provider + provider_surface + region + model/version.

### HIGH — R75-F02
Facts from private/undocumented Flow transport must not silently become official Veo API assumptions.

**Decision:** private Flow transport, if retained experimentally, gets a separate evidence profile.

---

# ROUND 76 — Quota Evidence Reviewer

### HIGH — R76-F01
Hard-coded provider caps age quickly and can be account/model/region specific.

**Decision:** scheduler reads versioned ProviderProfile values with `verified_at` and scope.

### HIGH — R76-F02
Documented model limits can differ from account-specific live limits.

**Decision:** allow account-observed/runtime backpressure overrides while preserving provenance.

---

# ROUND 77 — Billing Normalization Reviewer

### CRITICAL — R77-F01
A universal price-per-job cannot represent Flow credits, per-second Wan pricing, token-priced Seedance, provisioned throughput or local compute.

**Decision:** typed billing unit model accepted.

### HIGH — R77-F02
Credits and USD must not be compared numerically without explicit conversion policy.

**Decision:** budgets operate in explicit unit domains unless conversion is configured.

---

# ROUND 78 — Provider Task Retention Reviewer

### HIGH — R78-F01
Task-handle retention differs by provider surface (for example, current BytePlus task docs show a 7-day retention surface while current Wan legacy task docs state 24-hour task ID validity).

**Decision:** reconciliation deadline is ProviderProfile data.

### HIGH — R78-F02
Expired handles cannot be treated as ordinary polling failures.

**Decision:** adapter returns explicit expired/unknown recovery outcome.

---

# ROUND 79 — Cancellation Semantics Reviewer

### CRITICAL — R79-F01
A generic `cancel()` can falsely imply running remote work stopped.

**Decision:** expose queued-cancel, running-cancel and terminal-delete capabilities separately.

### HIGH — R79-F02
Local `CANCEL_REQUESTED` is intent, not remote evidence.

**Decision:** only provider-confirmed evidence yields `REMOTE_CANCELED`.

---

# ROUND 80 — Google Flow Product Risk Reviewer

### HIGH — R80-F01
Google Flow credits are documented per generation, not necessarily per user request.

**Decision:** cost estimator tracks requested candidates and actual generation count.

### HIGH — R80-F02
Flow product rate limiting is adaptive.

**Decision:** no fictitious fixed official RPM for Flow Product.

### CRITICAL — R80-F03
Private/internal Flow transport is not a supported public Veo API contract.

**Decision:** experimental private Flow adapter remains separate from Gemini/Vertex adapters.

---

# ROUND 81 — Wan Surface Reviewer

### CRITICAL — R81-F01
Applying Alibaba Cloud quotas/pricing to local Wan is a category error.

**Decision:** split local Wan and Alibaba Model Studio Wan adapters.

### HIGH — R81-F02
Local Wan is hardware-resource constrained.

**Decision:** local admission uses GPU/VRAM/model residency/CPU/disk pools.

---

# ROUND 82 — Job State Contradiction Reviewer

### CRITICAL — R82-F01
One status enum conflates scheduler ownership, provider acceptance, artifact materialization and creative approval.

**Decision:** four orthogonal state axes adopted.

### HIGH — R82-F02
UI still needs a compact status.

**Decision:** UI status is derived and non-authoritative.

---

# ROUND 83 — Document Authority Reviewer

### HIGH — R83-F01
Baseline V0.1 docs retained stale L4 wording after hardening advanced.

**Decision:** patch current headers; `PROJECT_STATE.md` remains maturity authority.

### HIGH — R83-F02
Historical review statements must not be erased.

**Decision:** preserve review history and patch current authority docs only.

---

# ROUND 84 — Freeze Readiness / Devil's Advocate

### CRITICAL — R84-F01
Provider research does not close live-provider, Windows, visual-QA or real-repair gates.

**Decision:** remain L5.5.

### HIGH — R84-F02
Provider-specific detail must not leak into canonical ShotIR.

**Decision:** ProviderProfile affects routing/compilation/runtime only.

---

# ROUND 85 — ProviderProfile Schema Reviewer

### HIGH — R85-F01
A prose-only ProviderProfile is vulnerable to field drift across adapters.

**Decision:** add Draft 2020-12 provider-profile schema and validate fixtures.

### POSITIVE
Five current provider-surface fixtures validate against the schema.

---

# ROUND 86 — Requirement / Traceability Reviewer

### CRITICAL — R86-F01
Traceability contained SEC/REL/PERF IDs that were not present in REQUIREMENTS, which made coverage look better than the canonical requirements actually supported.

**Decision:** add missing SEC-007..011, REL-006..008 and normalize PERF-001..003.

### POSITIVE
After patching, requirement-ID and traceability-ID sets match exactly: 64/64.

---

# ROUND 87 — Provider Evidence Freshness Reviewer

### HIGH — R87-F01
A structurally valid ProviderProfile can still be stale.

**Decision:** profile validity and evidence freshness are separate gates.

### HIGH — R87-F02
Account-specific quotas should not overwrite official evidence silently.

**Decision:** store observed account/runtime values as scoped overrides with timestamp/source.

---

# ROUND 88 — Cost Unit Safety Reviewer

### CRITICAL — R88-F01
Summing Flow credits and USD into one numeric project cost is dimensionally invalid.

**Decision:** aggregate by unit domain; cross-unit reporting requires explicit conversion snapshot.

### HIGH — R88-F02
Provider price changes can invalidate queued-job estimates.

**Decision:** each prepared request stores the price-evidence version used for its estimate.

---

# ROUND 89 — Recovery / Cancellation Contract Reviewer

### HIGH — R89-F01
Task retention and cancellation capabilities belong in the same provider lifecycle profile used for recovery.

**Decision:** task lifecycle + recovery are versioned together.

### HIGH — R89-F02
Deletion of a terminal task record is not cancellation of generation.

**Decision:** UI/telemetry use separate verbs and reason codes.

---

# ROUND 90 — Private Transport Governance Reviewer

### CRITICAL — R90-F01
A private/undocumented product transport may break without compatibility guarantees and can differ from supported API terms.

**Decision:** any such adapter is `EXPERIMENTAL_PRIVATE`, separately versioned, health-checked and never required for canonical project readability.

### HIGH — R90-F02
Canonical project data must remain usable if an experimental transport disappears.

**Decision:** no private request syntax stored in ShotSpec/ShotIR.

---

# ROUND 91 — Contract Fixture Validation Reviewer

### POSITIVE — R91-F01
Provider-profile fixtures validate against Draft 2020-12 schema using the installed validator.

### POSITIVE — R91-F02
Traceability scanner reports no missing or orphan requirement IDs after patch.

### LIMITATION
Schema validity does not prove provider facts are live-correct.

---

# ROUND 92 — L6 Evidence Gate Reviewer

### CRITICAL — R92-F01
The remaining blockers are evidence/runtime blockers rather than conceptual architecture contradictions.

**Decision:** do not lower the bar simply because the conceptual design is now coherent.

### Remaining L6 evidence
- Windows persistence/update run;
- Windows Electron credential-broker run;
- live ambiguity fault injection for shipping provider;
- real-image Static QA holdout metrics;
- real-generation repair benchmark;
- live/account quota/cost observations for shipping profiles.

**Current maturity:** L5.5 — Reviewed + Partial Hardening Evidence.

---

# ROUND 93 — Evidence Harness Completeness Reviewer

### HIGH — R93-F01
Several remaining L6 gates had protocols but not directly runnable harnesses/analyzers.

**Decision:** add:
- Electron Credential Broker live harness;
- generic live-provider ambiguity harness;
- Static QA calibration analyzer;
- Targeted Repair benchmark analyzer.

### HIGH — R93-F02
Harness creation must not be mislabeled as target proof.

**Decision:** L6 gate board explicitly separates HARNESS READY from LIVE/TARGET EVIDENCE.

---

# ROUND 94 — Electron Credential Broker Harness Reviewer

### CRITICAL — R94-F01
A conceptual Main→Utility lease needs target Electron evidence before it can be called hardened.

**Decision:** executable Electron harness created.

### HIGH — R94-F02
Renderer denial must be verified by public preload surface, not merely by documentation.

**Decision:** harness checks no secret-returning method and explicitly attempts a denied secret request.

### HIGH — R94-F03
Development Electron execution is not identical to packaged application behavior.

**Decision:** packaged-build rerun remains required before L6.

---

# ROUND 95 — Secret Material Lifetime Reviewer

### CRITICAL — R95-F01
Sending plaintext from Main to trusted Utility necessarily places plaintext in Utility memory.

**Decision:** do not claim zeroization; minimize scope/lifetime and keep Utility first-party/trusted.

### HIGH — R95-F02
A lease/session surviving Utility crash would become a reusable privilege.

**Decision:** target harness tests old Utility session rejection after process exit.

---

# ROUND 96 — Live Provider Fault Harness Reviewer

### CRITICAL — R96-F01
A generic "timeout" test is insufficient unless the request was actually dispatched across the provider side-effect boundary.

**Decision:** provider adapter contract requires explicit fault-mode implementation and documentation.

### HIGH — R96-F02
Provider-specific adapter code is necessary; a universal HTTP wrapper cannot prove each provider's semantics.

**Decision:** generic runner owns evidence format/state policy; shipping adapter owns transport fault injection/reconciliation.

---

# ROUND 97 — Billing Evidence Reviewer

### HIGH — R97-F01
No-duplicate proof without billing/credit observation can miss duplicate remote jobs that are hidden from the returned client result.

**Decision:** live harness requires remote-job enumeration/matching and billing/credit observation where provider exposes it.

### HIGH — R97-F02
Some products expose credits rather than USD billing.

**Decision:** evidence stores native billing unit rather than forcing conversion.

---

# ROUND 98 — Static QA Analyzer Reviewer

### HIGH — R98-F01
Calibration tooling must report false negatives even when other metrics look good.

**Decision:** analyzer reports per-class FN rate and aggregate blocking FN rate.

### POSITIVE — R98-F02
Local sample intentionally contained a missed blocking defect; analyzer reported blocking FN rate rather than averaging it away.

**Decision:** metric plumbing accepted.

---

# ROUND 99 — Repair Benchmark Neutrality Reviewer

### CRITICAL — R99-F01
A benchmark designed to prove Targeted Repair "wins" would be invalid.

**Decision:** paired analyzer reports whichever arm performs better.

### POSITIVE — R99-F02
Local sample showed full regeneration outperforming Targeted Repair on identity drift; analyzer preserved that result.

**Decision:** benchmark analysis is neutral enough for live evidence collection.

---

# ROUND 100 — Statistical Sufficiency Reviewer

### HIGH — R100-F01
One sample per defect class is not enough to route production repair policy.

**Decision:** retain protocol minimum of repeated cases per defect family; report per-class sample count.

### HIGH — R100-F02
QA calibration requires locked holdout; repair benchmark requires enough stochastic repetitions where provider output is variable.

**Decision:** protocols retain versioned dataset/seed/repetition evidence.

---

# ROUND 101 — Evidence Independence Reviewer

### CRITICAL — R101-F01
The same artifact cannot serve simultaneously as ground truth, model output and independent review evidence.

**Decision:** label source, prediction source and review decision remain distinct records.

### HIGH — R101-F02
Provider live proof must capture raw IDs/evidence but redact secrets.

**Decision:** evidence format includes identifiers/status/billing while security policy redacts credentials/session material.

---

# ROUND 102 — Runtime Gate Reviewer

### HIGH — R102-F01
The current environment cannot execute the Windows/Electron/live-provider gates.

**Decision:** do not invent evidence; mark HARNESS READY and preserve exact user-run commands.

### HIGH — R102-F02
Unavailability of one target runtime does not justify stopping unrelated hardening.

**Decision:** continue contradiction/traceability/provider research independently.

---

# ROUND 103 — Cross-Document Gate Consistency Reviewer

### HIGH — R103-F01
Readiness status was spread across Project State, Implementation Readiness and subsystem documents.

**Decision:** create `L6_EVIDENCE_GATE_BOARD_V0_12.md` as a derived gate dashboard; Project State remains maturity authority.

### MEDIUM — R103-F02
Dashboard must not become a second authority.

**Decision:** it references evidence and status; ADR/subsystem docs remain decision authorities.

---

# ROUND 104 — L6 Readiness / Devil's Advocate

### CRITICAL — R104-F01
The design now has runnable harnesses for every major open gate, but the most important target/live experiments still have not run.

**Decision:** maturity remains L5.5.

### POSITIVE
Remaining work is now executable rather than merely descriptive.

### Freeze rule reaffirmed

```text
HARNESS READY
≠
PROOF EXECUTED
≠
GATE CLOSED
```

---

# Review status after Round 104

**Conceptual/harness blockers:** no unresolved BLOCKER after patches.

**Target/live evidence blockers:** unchanged and explicitly tracked in L6 gate board.

**Current maturity:** L5.5 — Reviewed + Partial Hardening Evidence.

