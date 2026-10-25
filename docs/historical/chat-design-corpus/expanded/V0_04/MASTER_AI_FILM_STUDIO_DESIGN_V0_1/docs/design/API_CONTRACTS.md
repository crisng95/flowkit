# API_CONTRACTS.md
# Canonical Contract Model — Deep Dive V0.3

**Status:** REVIEWED CANDIDATE  
**Goal:** another coding agent must not need to invent cross-module message semantics.

---

# 1. Contract Strategy Options

## Option A — TypeScript interfaces only

Pros:
- simple;
- excellent developer ergonomics.

Cons:
- erased at runtime;
- weak external interoperability;
- no runtime validation by itself.

**Reject as sole contract.**

## Option B — JSON Schema first

Pros:
- language-neutral;
- standard;
- excellent interchange/documentation.

Cons:
- TypeScript developer ergonomics and refinements require tooling;
- implementation can drift unless generated/validated systematically.

**Keep as interoperability format.**

## Option C — Zod 4 runtime schemas + JSON Schema export

Pros:
- runtime validation;
- TypeScript inference;
- first-party `z.toJSONSchema()`;
- can target Draft 2020-12;
- schema metadata/IDs.

Risks:
- some Zod constructs are not representable in JSON Schema;
- TypeScript/Zod becomes implementation dependency.

**Preferred candidate if V1 runtime is TypeScript.**

---

# 2. Candidate Decision

For a TypeScript V1:

```text
Zod 4 schema
= runtime implementation contract

z.toJSONSchema(...)
→ JSON Schema Draft 2020-12
= exported interoperability/documentation contract
```

Public/persisted contracts are limited to JSON-serializable structures that round-trip conceptually into JSON Schema.

Do not use transforms/custom runtime-only schema semantics in persistent/public boundaries if they cannot be represented.

If the implementation language changes, JSON Schema Draft 2020-12 remains the language-neutral compatibility target.

---

# 3. Envelope

Every command/query crossing a major module/process boundary uses a versioned envelope.

## Request

```json
{
  "contract": "studio.command",
  "contract_version": "1.0.0",
  "request_id": "req_...",
  "correlation_id": "corr_...",
  "project_id": "prj_...",
  "expected_revision": 42,
  "payload": {}
}
```

## Success

```json
{
  "contract": "studio.result",
  "contract_version": "1.0.0",
  "request_id": "req_...",
  "correlation_id": "corr_...",
  "status": "OK",
  "result": {},
  "diagnostics": [],
  "lineage": []
}
```

## Failure

```json
{
  "contract": "studio.result",
  "contract_version": "1.0.0",
  "request_id": "req_...",
  "correlation_id": "corr_...",
  "status": "ERROR",
  "error": {
    "code": "CONCURRENCY_CONFLICT",
    "message": "Human-readable safe message",
    "retryable": false,
    "details": {}
  }
}
```

Sensitive raw provider error detail is not returned to low-privilege renderer.

---

# 4. Error Taxonomy

Top-level namespaces:

```text
VALIDATION_*
AUTH_*
PERMISSION_*
NOT_FOUND_*
CONFLICT_*
STATE_*
DEPENDENCY_*
CAPABILITY_*
PROVIDER_*
RATE_LIMIT_*
TIMEOUT_*
CANCEL_*
STORAGE_*
ARTIFACT_*
QA_*
REPAIR_*
MIGRATION_*
INTERNAL_*
```

Examples:

```text
VALIDATION_SCHEMA
CONFLICT_REVISION
STATE_NOT_APPROVED
DEPENDENCY_PARENT_NOT_READY
CAPABILITY_REFERENCE_LIMIT
PROVIDER_UNKNOWN_REMOTE_STATE
RATE_LIMIT_PROVIDER
ARTIFACT_CHECKSUM_MISMATCH
QA_BLOCKING_FAILURE
REPAIR_ESCALATED
```

Retryability is explicit, not inferred from HTTP-like status.

---

# 5. Versioning

Contract version uses semantic major/minor/patch meaning:

- MAJOR: incompatible field/semantic change;
- MINOR: backwards-compatible additive fields;
- PATCH: documentation/validation clarification that does not change valid instances materially.

Persisted objects also have domain schema version where needed.

Consumers:
- MUST reject unsupported major;
- SHOULD ignore documented additive optional fields;
- MUST NOT silently reinterpret an unknown enum semantic.

---

# 6. Core Contract IDs

Candidate stable logical schema IDs:

```text
studio.project.v1
studio.story-version.v1
studio.sequence.v1
studio.scene.v1
studio.beat.v1
studio.shot.v1
studio.entity.v1
studio.entity-version.v1
studio.reference-asset.v1
studio.state-snapshot.v1
studio.directing-decision.v1
studio.cinematography-decision.v1
studio.shot-spec.v1
studio.shot-ir.v1
studio.compiled-request.v1
studio.generation-job.v1
studio.artifact.v1
studio.qa-result.v1
studio.repair-plan.v1
studio.dependency-edge.v1
studio.provider-profile.v1
studio.timeline.v1
studio.export-manifest.v1
```

---

# 7. ShotSpec Contract Rules

Required invariant checks beyond field shape:

```text
shot_id exists
beat_id matches shot parent
start_state exists/allowed
entity refs resolve to project
reference versions belong to entities
parent shot not self
expected duration valid for production format
L8 references valid dependency edge
camera movement phases consistent with duration
static spec does not contain impossible temporal multi-shot sequence
```

These are semantic validators, not only JSON Schema checks.

---

# 8. ShotIR Contract Rules

ShotIR must contain:
- exact ShotSpec version;
- resolved entity versions;
- resolved semantic reference roles;
- resolved start-state;
- static observable state;
- temporal delta;
- continuity constraints;
- QA expectations.

ShotIR MUST NOT contain:
- provider upload positions;
- provider RPC IDs;
- model-specific undocumented magic tokens;
- credentials.

---

# 9. Provider Capability Profile

```json
{
  "profile_id": "provider-profile:veo:x",
  "version": "2026-09-20.1",
  "provider": "VEO",
  "model": "model-name",
  "verified_at": "ISO-8601",
  "capabilities": {
    "text_to_image": false,
    "image_to_video": true,
    "first_frame": true,
    "last_frame": true,
    "multi_reference": true,
    "max_references": 3,
    "audio": true
  },
  "limits": {
    "durations_seconds": [4, 8],
    "aspect_ratios": ["16:9", "9:16"]
  },
  "evidence": []
}
```

`verified_at` and evidence prevent stale capability assumptions from looking timeless.

---

# 10. Reference Binding

Semantic binding:

```json
{
  "reference_asset_id": "ref_...",
  "entity_version_id": "entv_...",
  "role": "IDENTITY",
  "required": true,
  "priority": 100
}
```

Provider compiler produces:

```text
upload index / media ID / image role
```

as implementation-specific output.

---

# 11. Generation Command

```json
{
  "shot_ir_version_id": "sir_...",
  "artifact_kind": "STATIC_IMAGE",
  "preferred_provider_profile_id": "pp_...",
  "policy": {
    "allow_fallback": true,
    "max_cost": null,
    "priority": "NORMAL"
  }
}
```

The command does not accept arbitrary raw provider request bodies from renderer.

---

# 12. Job Event

```json
{
  "event_id": "evt_...",
  "event_type": "GENERATION_JOB_STATUS_CHANGED",
  "occurred_at": "...",
  "project_id": "...",
  "job_id": "...",
  "from": "SUBMITTED",
  "to": "POLLING",
  "reason_code": null,
  "correlation_id": "..."
}
```

Events support observability; they do not replace authoritative current-state rows.

---

# 13. QA Contract

```json
{
  "artifact_id": "...",
  "shot_spec_version_id": "...",
  "reviewer_type": "VISION_SEMANTIC",
  "reviewer_version": "...",
  "dimensions": [
    {
      "name": "IDENTITY",
      "verdict": "PASS",
      "severity": "BLOCKING",
      "evidence": []
    }
  ],
  "overall_verdict": "PASS"
}
```

Overall pass rule is policy-driven. A BLOCKING failed dimension forces overall fail.

---

# 14. Repair Contract

```json
{
  "failure_code": "CAMERA_INTENT_MISMATCH",
  "responsible_layer": "L6_CAMERA",
  "repair_mode": "PATCH_IN_PLACE",
  "preserve": [
    "L1_SUBJECT",
    "L2_STATE",
    "L3_ACTION",
    "L4_ENVIRONMENT",
    "L5_TIME",
    "L7_STYLE",
    "L8_CONTINUITY"
  ],
  "patches": [],
  "invalidate": [],
  "recheck": ["CAMERA", "COMPOSITION", "CONTINUITY"]
}
```

---

# 15. IPC Contract Rule

Renderer IPC uses the exact same validated application-command contracts, but not every internal command is exposed.

Expose only UI-approved capabilities.

The main/security broker can reject:
- invalid sender;
- unsupported contract version;
- unauthorized project;
- malformed payload;
- privileged-only command.

---

# 16. Contract Testing

Every contract needs:
- valid fixture;
- invalid fixture set;
- backwards-compatibility test for supported minor versions;
- semantic invariant tests;
- JSON Schema export test;
- IPC/provider adapter boundary test where applicable.

---

# 17. Official References

JSON Schema Draft 2020-12:
https://json-schema.org/draft/2020-12

Zod JSON Schema conversion:
https://zod.dev/json-schema
