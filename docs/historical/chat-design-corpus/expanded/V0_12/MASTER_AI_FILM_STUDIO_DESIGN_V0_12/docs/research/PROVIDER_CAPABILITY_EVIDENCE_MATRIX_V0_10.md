# PROVIDER_CAPABILITY_EVIDENCE_MATRIX_V0_10.md
# Provider Capability / Quota / Billing Evidence Matrix

**Verified at:** 2026-09-20  
**Status:** REVIEWED RESEARCH CANDIDATE  
**Rule:** provider/model facts are versioned evidence, never timeless architecture constants.

---

# 1. Provider identity is a surface, not only a brand

The architecture MUST distinguish:

```text
Google Flow product
≠ Gemini API Veo
≠ Vertex AI Veo
≠ private/undocumented Flow transport

Wan local open-source
≠ Alibaba Cloud Model Studio Wan
```

Canonical identity:

```text
provider
+ provider_surface
+ region
+ model_family
+ model_version
+ profile_version
+ verified_at
```

Evidence grades:

```text
A = current official API/model/pricing docs
B = current official product/help docs
C = official source repository
D = observed/private transport evidence
E = unknown / not established
```

---

# 2. Google Flow — product surface

```yaml
provider: GOOGLE
provider_surface: FLOW_PRODUCT
public_developer_api: NOT_ESTABLISHED
billing_model: CREDITS_PER_GENERATION
quota_model: PRODUCT_CREDITS_PLUS_ADAPTIVE_RATE_LIMIT
```

Current official Flow help documents that credits are charged per **generation**, not necessarily per user request, and one request can create multiple video generations. Current published examples include Veo 3.1 Lite/Fast/Quality with different credit costs. Product help also describes adaptive rate limiting after heavy usage rather than one stable developer RPM.

Architecture consequences:

```text
estimated Flow cost
= expected_generation_count × credits_per_generation
```

The runtime records:

```text
requested_candidate_count
actual_generation_count
credits_estimated
credits_observed?
```

Do not copy a Flow credit cost into a direct Veo API profile.

Evidence:
- https://support.google.com/flow/answer/16526234
- https://support.google.com/flow/answer/16353333
- https://labs.google/fx/tools/flow

---

# 3. Google Veo — Gemini API surface

```yaml
provider: GOOGLE
provider_surface: GEMINI_API
model_family: VEO_3_1
job_model: LONG_RUNNING_OPERATION
```

Current developer docs establish:
- asynchronous long-running operation;
- polling with the returned operation object/name;
- Veo 3.1 4/6/8-second generation modes;
- generated-video server retention currently documented as 2 days on this surface;
- account/project rate limits are tier-specific and should be obtained from the active rate-limit surface.

Recovery rule:

```text
operation.name already persisted
→ re-poll same operation

response lost before operation.name persistence
→ UNKNOWN_REMOTE_STATE
```

No caller-controlled idempotency key is assumed without separate evidence.

Evidence:
- https://ai.google.dev/gemini-api/docs/veo
- https://ai.google.dev/gemini-api/docs/rate-limits

---

# 4. Google Veo — Vertex AI surface

```yaml
provider: GOOGLE
provider_surface: VERTEX_AI
model_family: VEO_3_1
job_model: LONG_RUNNING_PREDICTION
```

Current model documentation for Veo 3.1/3.1 Fast documents items including:

```text
T2V / I2V
first + last frame generation
16:9 / 9:16
720p / 1080p
24 FPS
4 / 6 / 8 seconds
up to 4 results per request
up to 50 API requests/min/project on the current non-preview 3.1 model page
```

Preview/non-preview and quota products can differ. Google also documents provisioned-throughput/fixed-quota options for Veo.

Pricing is bound to `billing_surface + SKU/product + region + model_version + verified_at`. A price from Google Flow or another Google product is not a universal Vertex AI price.

Evidence:
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-1-generate
- https://cloud.google.com/vertex-ai/generative-ai/docs/video/generate-videos-from-text
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/provisioned-throughput/veo-models
- https://docs.cloud.google.com/vertex-ai/generative-ai/docs/release-notes

---

# 5. BytePlus ModelArk — Seedance

Seedance profiles are model-version specific.

For the currently documented `seedance-1-0-pro-250528` surface:

```text
async create task → query task ID
concurrency: 10 / primary account / model version
RPM: 600 / primary account / model version
above concurrency: tasks can queue
```

Current pricing docs list Seedance 1.0 Pro at 2.5 USD/M video tokens and Pro Fast at 1 USD/M video tokens for online inference. Pricing is based on video token consumption and successful generations.

Task API documentation exposes create/retrieve/list/cancel-or-delete operations. A current task surface documents 7-day task-ID retention. Current delete semantics distinguish queued vs running: a queued task may be cancelled, while the documented running state is not cancellable through that route.

Architecture consequences:

```text
cancel_queued
cancel_running
delete_terminal
handle_retention
```

must be separate capabilities.

Evidence:
- https://docs.byteplus.com/en/docs/ModelArk/1587798
- https://docs.byteplus.com/docs/ModelArk/1099320
- https://docs.byteplus.com/en/docs/ModelArk/Video_Generation_API
- https://docs.byteplus.com/en/docs/ModelArk/1521720

---

# 6. Alibaba Cloud Model Studio — Wan API

```yaml
provider: ALIBABA_CLOUD
provider_surface: MODEL_STUDIO
model_family: WAN
job_model: ASYNC_TASK
billing_model: USD_PER_VIDEO_SECOND or USD_PER_BILLABLE_SECOND by mode
```

Current official documentation establishes asynchronous create-task → poll-task behavior and region-scoped endpoint/key/model requirements. Current Wan 2.7 text-to-video documentation states legacy task IDs are valid for 24 hours and explicitly warns against duplicate task creation.

Current rate-limit examples include:

```text
wan2.7-t2v:      RPS 5, concurrency 5
wan2.7-i2v:      RPS 5, concurrency 5
wan2.7-r2v:      RPS 5, concurrency 5
wan2.2-t2v-plus: RPS 2, concurrency 2
```

Current Singapore pricing examples include:

```text
Wan 2.7 T2V 720p:  $0.10 / successful output second
Wan 2.7 T2V 1080p: $0.15 / successful output second
Wan 2.7 I2V 720p:  $0.10 / successful output second
Wan 2.7 I2V 1080p: $0.15 / successful output second
```

Reference-to-video may bill input+output duration depending on mode; prices are region/resolution/model/version scoped.

Architecture consequence: `reconciliation_deadline` is provider-profile data, not a generic constant.

Evidence:
- https://www.alibabacloud.com/help/en/model-studio/text-to-video-api-reference
- https://www.alibabacloud.com/help/en/model-studio/rate-limit
- https://www.alibabacloud.com/help/en/model-studio/model-pricing
- https://www.alibabacloud.com/help/en/model-studio/image-to-video-general-api-reference

---

# 7. Wan2.2 — local open-source surface

```yaml
provider: LOCAL
provider_surface: WAN2_2_LOCAL
billing_model: LOCAL_COMPUTE_ESTIMATE
quota_model: LOCAL_RESOURCE_POOL
```

Official Wan source exposes local task families such as:

```text
t2v-A14B
i2v-A14B
ti2v-5B
s2v-14B
animate-14B
```

with 480p/720p-oriented configurations. This surface has no Alibaba Cloud API quota/billing contract.

Admission depends on:

```text
GPU/VRAM
GPU count
model residency
CPU RAM
disk
local worker concurrency
```

Evidence:
- https://github.com/Wan-Video/Wan2.2
- https://github.com/Wan-Video/Wan2.2/blob/main/generate.py

---

# 8. Kling

**Status: UNVERIFIED FOR CORE V1.**

This research pass did not capture sufficiently strong current official evidence to freeze task lifecycle, quota, billing, idempotency/reconciliation and cancellation behavior. Therefore Kling remains an optional adapter candidate until a current official provider profile is captured.

---

# 9. Canonical ProviderProfile additions

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

Billing unit types:

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

---

# 10. Decision

Freeze the **evidence model**, not current numeric values:

```text
PROVIDER FACTS
= VERSIONED EVIDENCE
≠ GLOBAL CONSTANTS
```
