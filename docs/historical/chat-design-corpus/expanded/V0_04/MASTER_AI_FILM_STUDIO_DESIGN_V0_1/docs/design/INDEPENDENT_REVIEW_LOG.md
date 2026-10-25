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

