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
