# DATA_MODEL.md
# Canonical Data Model — Draft V0.2

**Status:** DRAFT  
**Purpose:** define ownership and relationships, not final SQL DDL.

---

# 1. Core Aggregate Map

```text
Project
├── SourceVersion[]
├── StoryVersion[]
├── FilmBibleVersion[]
├── Sequence[]
│   └── Scene[]
│       └── Beat[]
│           └── Shot[]
├── Entity[]
│   └── EntityVersion[]
│       └── ReferenceAsset[]
├── StateSnapshot[]
├── SpatialBaseline[]
├── DirectingDecision[]
├── CinematographyDecision[]
├── ShotSpecVersion[]
├── ShotIRVersion[]
├── CompiledRequest[]
├── GenerationJob[]
│   └── Artifact[]
├── QAResult[]
├── RepairPlan[]
├── DependencyEdge[]
├── TimelineVersion[]
└── ExportManifest[]
```

---

# 2. Identity Rules

Use opaque stable IDs (UUID/ULID or equivalent).

Human-readable sequence/shot numbers are display/order fields, not primary identity.

Never use mutable names as foreign keys.

---

# 3. Project

Fields:

```text
project_id
title
status
production_format_profile
active_story_version_id
active_film_bible_version_id
created_at
updated_at
revision
```

---

# 4. StoryVersion

Prefer immutable version record:

```text
story_version_id
project_id
parent_story_version_id?
version_number
source_version_ids[]
premise
theme?
dramatic_question?
causal_model_json
status
content_hash
created_at
created_by
```

Statuses:

```text
DRAFT
ROUGH_SCRIPT
REVIEWED
APPROVED
LOCKED
SUPERSEDED
```

---

# 5. Narrative Hierarchy

## Sequence

```text
sequence_id
project_id
story_version_id
display_order
purpose
entry_state_id?
expected_exit_state?
revision
```

## Scene

```text
scene_id
sequence_id
display_order
slugline?
location_entity_id?
story_time
scene_function
entry_state_id?
expected_exit_state?
revision
```

## Beat

```text
beat_id
scene_id
display_order
summary
purpose
change
emotion
information_priority
entry_state_id?
expected_exit_state?
revision
```

## Shot

```text
shot_id
beat_id
display_order
duration_target_ms?
active_shot_spec_version_id?
active_static_artifact_id?
active_video_artifact_id?
status
revision
```

---

# 6. Entity / Reference

## Entity

```text
entity_id
project_id
entity_type
canonical_name
status
active_entity_version_id
created_at
revision
```

## EntityVersion

```text
entity_version_id
entity_id
version_number
description
locked_features_json
allowed_variation_json
state_contract_json
content_hash
approval_status
created_at
```

## ReferenceAsset

```text
reference_asset_id
entity_version_id
artifact_id
reference_role
view_angle?
state_variant?
wardrobe_variant?
approved
quality_status
```

Reference roles may include:

```text
CANON
IDENTITY
FRONT_FULL
SIDE_FULL
BACK_FULL
THREE_QUARTER
FACE_CLOSE
EXPRESSION
WARDROBE
LOCATION
PROP
STYLE
```

---

# 7. StateSnapshot

Immutable after approval:

```text
state_snapshot_id
project_id
source_shot_id?
story_time
location_entity_version_id?
character_states_json
prop_states_json
environment_state_json
lighting_state_json
spatial_baseline_id?
approval_status
content_hash
created_at
```

Only approved/locked snapshots may become downstream continuity authority.

---

# 8. DirectingDecision

```text
directing_decision_id
shot_id
beat_id
version
narrative_function
audience_endpoint
information_order_json
performance_intent_json
rhythm_role
decision_basis
status
content_hash
```

---

# 9. CinematographyDecision

```text
cinematography_decision_id
shot_id
version
blocking_json
framing
camera_position_json
camera_height
angle
lens
movement_json
focus_strategy
composition_json
lighting_strategy_json
edit_relation
decision_basis
status
content_hash
```

---

# 10. ShotSpecVersion

Immutable compiled creative spec:

```text
shot_spec_version_id
shot_id
version_number
directing_decision_id
cinematography_decision_id
start_state_snapshot_id
expected_end_state_json
layer_1_json
layer_2_json
layer_3_json
layer_4_json
layer_5_json
layer_6_json
layer_7_json
layer_8_json
content_hash
status
created_at
```

Do not store only one giant prompt.

---

# 11. ShotIRVersion

```text
shot_ir_version_id
shot_id
shot_spec_version_id
version_number
resolved_entity_versions_json
resolved_reference_roles_json
resolved_state_json
semantic_static_json
semantic_motion_json
continuity_constraints_json
qa_expectations_json
content_hash
created_at
```

No provider-specific parameter names.

---

# 12. CompiledRequest

```text
compiled_request_id
shot_ir_version_id
compiler_version
provider_profile_version
provider
model
generation_mode
prompt_text
negative_prompt_text?
reference_binding_json
provider_params_json
input_manifest_json
input_fingerprint
created_at
```

Compiled request is immutable.

---

# 13. GenerationJob

```text
generation_job_id
compiled_request_id
project_id
shot_id
artifact_kind

scheduler_state
provider_state
artifact_state
creative_state

attempt
submission_attempt_id
local_submission_key
idempotency_key?
provider
provider_surface
region?
model
model_version?
provider_request_id?
provider_operation_id?
worker_id?
lease_until?
heartbeat_at?

billing_unit_kind?
unit_price_snapshot?
estimated_quantity?
actual_quantity?
currency_or_credit_unit?
estimated_cost?
actual_cost?
price_evidence_version?

input_fingerprint
error_code?
error_detail_redacted?
created_at
submitted_at?
finished_at?
```

The old generic `status`/overloaded provider-job identity must not be the only source of truth.

---

# 14. Artifact

```text
artifact_id
generation_job_id
artifact_kind
relative_path
sha256
byte_size
mime_type
width?
height?
duration_ms?
status
input_fingerprint
created_at
```

Statuses:

```text
STAGING
READY
STALE_RESULT
QUARANTINED
MISSING
REJECTED
APPROVED
```

---

# 15. QAResult

```text
qa_result_id
artifact_id
shot_spec_version_id
reviewer_type
reviewer_version
dimensions_json
findings_json
severity
verdict
evidence_json
created_at
```

No single weighted score is authoritative.

---

# 16. RepairPlan

```text
repair_plan_id
shot_id
failed_artifact_id
failure_code
responsible_layer
root_cause_hypothesis
preserve_json
patch_json
invalidate_json
recompile_static
recompile_motion
recheck_dimensions_json
status
created_at
```

---

# 17. DependencyEdge

```text
edge_id
project_id
from_shot_id
to_shot_id
edge_type
source_artifact_role?
required
created_at
```

Types:

```text
ROOT
CONTINUATION
INSERT
BRANCH
```

Graph cycle prevention is mandatory for dependency edges that imply execution ancestry.

---

# 18. Revision / Optimistic Concurrency

Coordination rows use:

```text
revision INTEGER NOT NULL
```

Update pattern must include expected revision.

Immutable version records do not need in-place semantic edits; create a new version.

---

# 19. Soft Delete / History

Do not hard-delete production history by default.

Use:

```text
archived_at
superseded_by
status
```

Hard delete reserved for explicit cleanup/retention flows.

---

# 20. Index Strategy — Initial

Candidates:

```text
shot(beat_id, display_order)
beat(scene_id, display_order)
scene(sequence_id, display_order)
sequence(project_id, display_order)

generation_job(status, created_at)
generation_job(provider, status)
generation_job(lease_until)
artifact(generation_job_id)
artifact(sha256)

dependency_edge(from_shot_id)
dependency_edge(to_shot_id)

qa_result(artifact_id, created_at)
state_snapshot(project_id, created_at)
```

Final indexes require query-plan/benchmark validation.

---

# 21. Data Ownership

| Data | Owner |
|---|---|
| source versions | Ingest |
| story versions | Story Engine |
| film bible | Production Memory |
| sequence/scene/beat/shot identity | Narrative Domain |
| entity/version/ref metadata | Entity/Reference |
| state snapshots | State Engine |
| directing decision | Directing Engine |
| cinematography decision | Cinematography Engine |
| ShotSpec | Shot Domain |
| ShotIR | Compiler-preflight layer |
| compiled request | Compiler |
| jobs | Orchestrator |
| artifact metadata | Artifact Store |
| QA results | QA |
| repair plans | Repair Engine |
| timeline/export | Editorial |


# 22. Provider Submission Recovery Profile

```text
provider_recovery_profile_id
provider
model_family
version
idempotency_mode
operation_handle_mode
lookup_by_client_token
list_recent_operations
unique_output_prefix
ambiguous_resubmit_policy
verified_at
evidence_json
```

GenerationJob additionally requires:

```text
submission_attempt_id
local_submission_key
provider_request_id?
provider_operation_id?
submission_state
ambiguity_started_at?
last_reconcile_at?
```

The old generic `request_id` naming must not be used for multiple meanings.


# 23. CostRecord / Billing Evidence

```text
cost_record_id
generation_job_id
provider
provider_surface
model_version
billing_unit_kind
currency_or_credit_unit
unit_price_snapshot
estimated_quantity
actual_quantity
estimated_cost
actual_cost
billing_surface
price_evidence_version
price_verified_at
created_at
```

Supported unit kinds include credits/generation, USD/generation, USD/video-second, USD/billable-second, USD/M video-tokens, provisioned capacity, local-compute estimate, and unknown.
