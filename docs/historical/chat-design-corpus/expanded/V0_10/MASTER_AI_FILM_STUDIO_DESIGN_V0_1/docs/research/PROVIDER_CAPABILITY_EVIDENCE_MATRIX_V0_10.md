# PROVIDER_CAPABILITY_EVIDENCE_MATRIX_V0_10.md
# Provider Capability / Quota / Billing Evidence Matrix

**Verified at:** 2026-09-20  
**Status:** REVIEWED RESEARCH CANDIDATE  
**Rule:** Provider/model facts are versioned evidence, never timeless architecture constants.

---

# 1. Why provider surfaces must be separated

The same model family can be exposed through materially different products:

```text
Google Flow product
≠
Gemini API Veo
≠
Vertex AI Veo
≠
private/undocumented Flow transport
```

Likewise:

```text
Wan local open-source
≠
Alibaba Cloud Model Studio Wan API
```

and:

```text
Seedance model family
≠
one immutable quota/pricing profile
```

Therefore the canonical provider key is not just a brand/model name.

Use:

```text
provider
provider_surface
region
model_family
model_version
account_scope
profile_version
verified_at
```

---

# 2. Evidence Grades

```text
A = official current API/model/pricing documentation
B = official product/help documentation
C = official repository/source
D = inferred/observed private transport
E = unknown / not established
```

Architecture decisions that can spend money or create duplicate jobs require A/B evidence or live adapter evidence.

---

# 3. Google Flow — Product Surface

## Profile

```yaml
provider: GOOGLE
provider_surface: FLOW_PRODUCT
transport: PRODUCT_UI_OR_PRODUCT_INTERNAL
public_developer_api: NOT_ESTABLISHED
billing_model: CREDITS_PER_GENERATION
quota_model: PRODUCT_CREDITS_PLUS_DYNAMIC_RATE_LIMIT
```

## Current official product evidence

Google Flow help currently documents:
- credits are charged **per generation, not per request**;
- one user request may create multiple video generations;
- Veo 3.1 Lite / Fast / Quality use different Flow/AI credit amounts;
- rate limiting can occur and can tighten after high daily usage;
- limits/costs can change.

Examples documented on 2026-09-20:

```text
Veo 3.1 Lite:
  4s / 6s / 8s / extend
  non-Ultra: 10 credits / generation
  Ultra: 5 credits / generation

Veo 3.1 Fast:
  non-Ultra: 20
  Ultra: 10

Veo 3.1 Quality:
  8s / extend
  100 credits / generation
```

Product help also states failed generations are not charged credits.

## Architecture consequence

Cost estimate for Flow must be:

```text
expected_generations
×
credits_per_generation
```

not:

```text
requests × price
```

and the adapter must record:

```text
requested_candidate_count
actual_generation_count
credits_estimated
credits_observed?
```

Do not hard-code an RPM because product help describes adaptive rate limiting rather than a stable public developer quota.

## Evidence

- https://support.google.com/flow/answer/16526234
- https://support.google.com/flow/answer/16353333
- https://labs.google/fx/tools/flow

---

# 4. Google Veo — Gemini API Surface

## Profile

```yaml
provider: GOOGLE
provider_surface: GEMINI_API
model_family: VEO_3_1
transport: PUBLIC_API
job_model: LONG_RUNNING_OPERATION
```

Official current developer documentation establishes:
- generation starts a long-running operation;
- the returned operation is polled until `done`;
- an operation `name` can be used to re-create/re-fetch the operation;
- supported Veo 3.1 durations include 4, 6, and 8 seconds;
- request latency can range from seconds to several minutes;
- generated video retention on this surface is documented as 2 days;
- active rate limits depend on project usage tier and should be read from AI Studio.

## Recovery consequence

```text
operation.name persisted
→ re-poll existing operation
```

If the response is lost before the operation name is persisted:

```text
UNKNOWN_REMOTE_STATE
```

No caller-controlled idempotency key is assumed unless separately verified.

## Evidence

- https://ai.google.dev/gemini-api/docs/veo
- https://ai.google.dev/gemini-api/docs/rate-limits

---

# 5. Google Veo — Vertex AI Surface

## Profile

```yaml
provider: GOOGLE
provider_surface: VERTEX_AI
model_family: VEO_3_1
transport: PUBLIC_API
job_model: LONG_RUNNING_PREDICTION
```

Current model documentation for `veo-3.1-generate-001` / Fast documents:

```text
text-to-video
image-to-video
first+last-frame generation
16:9 / 9:16
720 / 1080
24 FPS
4 / 6 / 8 seconds
up to 4 videos per request
up to 50 API requests/minute/project for current non-preview 3.1 model page
```

Preview and non-preview model quotas can differ.

Google also documents Provisioned Throughput/fixed-quota options for Veo model families.

## Pricing caution

Google exposes Veo across multiple Cloud/product pricing surfaces. The studio must bind cost evidence to:

```text
billing_surface
SKU/product
region
model_version
verified_at
```

Do **not** use a Flow credit cost or another Google product's `/count` price as the universal Vertex AI cost.

## Evidence

- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-1-generate
- https://cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos-from-text
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/provisioned-throughput/veo-models
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/release-notes

---

# 6. BytePlus ModelArk — Seedance 1.0 Pro

## Profile

```yaml
provider: BYTEPLUS
provider_surface: MODELARK
model_family: SEEDANCE_1_0_PRO
job_model: ASYNC_TASK
billing_model: USD_PER_M_VIDEO_TOKENS
```

Current official model documentation establishes:
- text-to-video;
- first-frame image-to-video;
- optional last-frame image for supported model version;
- asynchronous create-task → query-task flow;
- one current documented primary-account concurrency limit of 10 for `seedance-1-0-pro-250528`;
- RPM documented as 600 for that version;
- tasks exceeding concurrency can queue;
- rate-limit values are model-version/account scoped.

Current pricing page documents:
- Seedance 1.0 Pro: 2.5 USD/M video tokens online;
- Seedance 1.0 Pro Fast: 1 USD/M video tokens online;
- pricing depends on estimated video token consumption;
- failed generation is not charged.

## Evidence

- https://docs.byteplus.com/en/docs/ModelArk/1587798
- https://docs.byteplus.com/docs/ModelArk/1099320

---

# 7. BytePlus ModelArk — Seedance Task API

The current task API exposes:

```text
create
retrieve
list
cancel/delete
```

Task status vocabulary includes:

```text
queued
running
cancelled
succeeded
failed
expired
```

Current docs show:
- create returns a task ID;
- one current API surface documents task-ID retention of 7 days;
- DELETE can cancel a queued task;
- a running task is documented as not cancellable on the referenced API route.

## Architecture consequence

Canonical adapter cancellation must distinguish:

```text
CANCELABLE_QUEUED
NOT_CANCELABLE_RUNNING
DELETE_RECORD_AFTER_TERMINAL
```

Do not map all states to a generic `cancel()` promise.

The 7-day task-retention window is part of the provider reconciliation profile.

## Evidence

- https://docs.byteplus.com/en/docs/ModelArk/Video_Generation_API
- https://docs.byteplus.com/en/docs/ModelArk/1521720
- https://docs.byteplus.com/en/docs/Byteplus_LAS/video_gen_enhanced

---

# 8. Alibaba Cloud Model Studio — Wan API

## Profile

```yaml
provider: ALIBABA_CLOUD
provider_surface: MODEL_STUDIO
model_family: WAN
job_model: ASYNC_TASK
billing_model: USD_PER_VIDEO_SECOND
```

Official current documentation establishes:
- Wan video tasks are asynchronous;
- create task → poll using returned `task_id`;
- current Wan 2.7 text-to-video docs state task generation often takes minutes;
- current docs state task IDs for the legacy Wan protocol are valid for 24 hours;
- the documentation explicitly warns not to create duplicate tasks;
- model/API key/endpoint are region scoped.

Current rate-limit documentation includes examples:

```text
wan2.7-t2v:      RPS 5, concurrency 5
wan2.7-i2v:      RPS 5, concurrency 5
wan2.7-r2v:      RPS 5, concurrency 5
wan2.2-t2v-plus: RPS 2, concurrency 2
```

Limits are model/region/version scoped and must be refreshed.

Current pricing is per successful output duration (or input+output duration for some modes), with region/resolution-specific pricing; failed requests are documented as uncharged for the listed video-generation rules.

Example current Singapore pricing:

```text
Wan 2.7 T2V:
  720p  = $0.10 / second
  1080p = $0.15 / second

Wan 2.7 I2V:
  720p  = $0.10 / second
  1080p = $0.15 / second

Wan 2.7 R2V:
  720p  = $0.10 / billable second
  1080p = $0.15 / billable second
```

These values are evidence snapshots, not architecture constants.

## Recovery consequence

Persist task ID immediately.

Because current documentation gives a 24-hour task-ID validity window:

```text
reconciliation_deadline
```

must be provider-profile data.

## Evidence

- https://www.alibabacloud.com/help/en/model-studio/text-to-video-api-reference
- https://www.alibabacloud.com/help/en/model-studio/rate-limit
- https://www.alibabacloud.com/help/en/model-studio/model-pricing
- https://www.alibabacloud.com/help/en/model-studio/image-to-video-general-api-reference

---

# 9. Wan2.2 — Local Open-Source Surface

## Profile

```yaml
provider: LOCAL
provider_surface: WAN2_2_LOCAL
transport: LOCAL_PROCESS
billing_model: LOCAL_COMPUTE
quota_model: LOCAL_RESOURCE_POOL
```

Official Wan repository source exposes model/task configurations such as:

```text
t2v-A14B
i2v-A14B
ti2v-5B
s2v-14B
animate-14B
```

and 480p/720p-oriented size configurations.

This surface has no remote-provider billing quota.

Its admission policy is based on:

```text
GPU VRAM
GPU count
model residency
CPU RAM
disk
local process concurrency
thermal/runtime stability
```

Do not apply Alibaba Cloud RPS/concurrency/pricing to a local Wan adapter.

## Evidence

- https://github.com/Wan-Video/Wan2.2
- https://github.com/Wan-Video/Wan2.2/blob/main/generate.py

---

# 10. Kling

**Current status: UNVERIFIED FOR CORE V1**

No sufficiently strong current official API evidence was captured in this research pass to freeze:
- task lifecycle;
- quotas;
- billing;
- idempotency/reconciliation;
- cancellation semantics.

Therefore:

```text
KlingAdapter
= optional candidate
≠ core V1 provider contract
```

until an official/current provider profile is captured and reviewed.

---

# 11. Provider Profile Schema Patch

```yaml
provider_profile:
  provider:
  provider_surface:
  region:
  account_scope:
  model_family:
  model_version:
  profile_version:

  capabilities: {}

  quota:
    kind:
    rpm:
    rps:
    concurrency:
    queue_behavior:
    source_scope:

  task_lifecycle:
    async:
    handle_kind:
    handle_retention:
    list_supported:
    cancel_queued:
    cancel_running:
    delete_terminal:

  billing:
    billing_surface:
    unit_kind:
    currency:
    unit_price:
    charge_on_success_only:
    estimation_formula:
    effective_at:

  recovery:
    idempotency_mode:
    reconcile_methods: []
    ambiguous_resubmit_policy:
    reconciliation_deadline:

  evidence:
    verified_at:
    sources: []
    live_verified: false
```

---

# 12. Canonical Billing Unit Types

Cost Engine must support different unit families:

```text
CREDITS_PER_GENERATION
USD_PER_GENERATION
USD_PER_VIDEO_SECOND
USD_PER_BILLABLE_SECOND
USD_PER_M_VIDEO_TOKENS
PROVISIONED_CAPACITY
LOCAL_COMPUTE_ESTIMATE
UNKNOWN
```

No universal `price_per_job`.

---

# 13. Canonical Quota Rule

Scheduler does not embed provider numbers.

Instead:

```text
ProviderProfile
→ AdmissionPolicy
```

Numbers can be:
- official static snapshot;
- account-specific fetched value;
- locally configured override;
- live-observed backpressure.

Every number carries:

```text
verified_at
evidence_source
scope
expiry_or_refresh_policy
```

---

# 14. Design Decision

Freeze direction, not current numeric values:

```text
PROVIDER FACTS
= VERSIONED EVIDENCE

NOT
= GLOBAL CONSTANTS
```
