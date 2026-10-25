# MASTER STUDIO — OPTIMAL HYBRID ARCHITECTURE V1 FROZEN
## Multi-Repo Independent Design Audit + KEEP / TAKE / REPLACE / DROP Matrix

**Ngày khóa thiết kế:** 2026-09-20  
**Mục tiêu:** Xây một kiến trúc AI-Native Visual & Film Studio không phụ thuộc vào một repo duy nhất, lấy đúng phân khúc mạnh nhất của từng nguồn, giữ những phần FlowKit đã có bằng chứng kỹ thuật tốt, thay các phần yếu bằng subsystem chuyên sâu hơn, và loại bỏ các shortcut dễ tạo “cảnh đẹp rời rạc”.

---

# 0. KẾT LUẬN ĐÃ KHÓA

Không nên dùng nguyên FlowKit làm toàn bộ studio.

Không nên bỏ FlowKit.

Không nên clone nguyên nhiều repo rồi trộn code trực tiếp.

Kiến trúc tối ưu nhất sau audit là:

```text
CANONICAL STUDIO SCHEMA
        │
        ├── screenplay/story intelligence
        ├── sequence/scene/beat/shot hierarchy
        ├── directing + cinematography decision
        ├── production assets + references
        ├── state/continuity engine
        ├── 8-layer ShotSpec
        ├── semantic Shot IR
        ├── provider-aware prompt compiler
        ├── generation orchestration
        ├── static/video QA
        ├── targeted repair
        └── editorial/export
```

và mỗi repo chỉ đóng vai trò **nguồn subsystem**.

Câu chốt:

> **FlowKit nên giữ làm một execution/reference/continuity backend mạnh, nhưng không còn là source of truth của story, scene, shot hay prompt.**

Source of truth mới phải là:

```text
Story
→ Sequence
→ Scene
→ Beat
→ Shot
→ Cinematography Intent
→ 8-Layer ShotSpec
→ Shot IR
```

Prompt chỉ là artifact được compile từ Shot IR.

---

# 1. CÁC REPO ĐÃ ĐÀO SÂU

Audit sử dụng source, schema, tests, skills/docs và commit hiện tại quan sát được ở thời điểm audit.

| Repo | Commit audit | License / lưu ý | Vai trò chính trong audit |
|---|---|---|---|
| `crisng95/flowkit` | `d7977fd51b87d4da2a25a05b896f5cdac064e030` | MIT | Flow execution, refs, chaining, queue, video QA |
| `zhangzhangco/film-production-skills` | `47b2a6a432235e716fa2aa0d08eefae76fdb34fd` | MIT | Shared contracts, story→beat→shot→IR→execution→review |
| `XucroYuri/take` | `47c17216b5ad74ee7dd376e8508266e29aefae2c` | MIT | Strong typed Beat/Shot core, validation, provider seam |
| `momorzq-oss/Continuity-Studio` | `2f818cc4d14f84e7b31236aa4d8e307a8c5b952b` | Apache-2.0 | Film Bible, state ledger, sequence planning, restart-safe workflow |
| `62656456/ai-film-skills` | `4a33628b789976f004079772c8dc77d3f317a566` | Apache-2.0 | Story causality, directing, cinematography reasoning, state/repair discipline |
| `wassermanproductions/scriptbreak` | `ed9efb86125b713ce430b7337f27392adec071a9` | Apache-2.0 | FDX/Fountain/PDF breakdown, elements, bibles, project look |
| `TheDesignFounder/DreamLayer-Eval` | `9d98f429905752b88d64b1aeab16ded81781894f` | GPLv3 | Image/video metrics and reproducible evaluation |
| `Nagacash/character-continuity-skill` | `97757802b607dbd1c1e850aca3ed1b1c9f362624` | code MIT, docs CC BY 4.0 | Canon/turnaround/detail plates/drift audit |
| `LinHao-city/StoryMind` | `00f9a0c7f67eeb3a076cf0a4a449ae7c856739ac` | AGPLv3 | StoryboardPlanner concept, shot planning, visual anchors |
| `LudwigKienle/ai-video-production-editor` | `a9c3e7d5689e8f8a3a3371ba0522c953908ba2fa` | GPL-3.0-or-later | 3D scene map, review/re-film, post-production ideas |
| `sankar2389/cine-studio` | `698045be85c12543f6c82e6ce61a3d8970dbe9cb` | MIT | Provider-neutral preproduction/NLE export ideas |
| `Alisa0808/vox-director` | `668ec3946fe0139bc985313b15c1a300fca42f94` | MIT | Short-form beat-map/pacing patterns |
| `kirklasalle/CineMatrix` | `62e58906e830a16f6b128c64bec61ea45e240595` | README ghi All rights reserved | Beat-sheet/tension/previs ideas only |

**Lưu ý license:** đây là ghi nhận kỹ thuật, không phải tư vấn pháp lý. Với sản phẩm thương mại đóng nguồn, ưu tiên code MIT/Apache-2.0. Repo GPL/AGPL hoặc All-rights-reserved nên dùng như tài liệu kiến trúc/nghiên cứu trừ khi đã xác định rõ cách tuân thủ license.

---

# 2. THANG BẰNG CHỨNG

Để tránh kiểu “repo ghi README là mạnh thì chấm mạnh”, dùng bốn cấp:

| Cấp | Điều kiện |
|---|---|
| **A** | Code/schema thật + test hoặc executable contract trực tiếp |
| **B** | Code/schema thật nhưng chưa thấy đủ test end-to-end cho claim |
| **C** | Docs/demo/artifact do repo công bố |
| **D** | Chưa tìm thấy implementation đủ để xác nhận |

Một module chỉ được chọn làm **core source** khi:

```text
A/B evidence
+
kiến trúc phù hợp
+
không tạo coupling xấu
+
license phù hợp hoặc chỉ học concept
```

---

# 3. PHẢN BIỆN ĐỘC LẬP — VÒNG 01
## “FlowKit đã end-to-end thì có cần ghép repo khác không?”

### Phản biện

FlowKit đúng là end-to-end về **workflow breadth**:

```text
story
→ entities
→ refs
→ scene images
→ clips
→ narration
→ concat
→ thumbnail
→ upload
```

Nhưng breadth ≠ depth.

Phần `Entity/Reference/Execution` có code path sâu.

Phần `Story/Beat/Shot/Cinematography Decision` không có cùng độ sâu cấu trúc.

### Quyết định

**GIỮ FlowKit**, nhưng hạ vai trò từ:

```text
MASTER FILM MODEL
```

xuống:

```text
GENERATION / CONTINUITY EXECUTION BACKEND
```

---

# 4. PHẢN BIỆN ĐỘC LẬP — VÒNG 02
## “Có cần formal Story → Sequence → Scene → Beat → Shot không?”

### Bằng chứng bổ sung

`film-production-skills` có:

```text
structure-screenplay
→ scenes
→ units
→ beats
→ rhythm_curve
```

và `plan-camera-shots` bind `beat_ids` vào shot segments.

`take` có Zod schema thật:

```text
beatSchema:
  id
  index
  summary
  purpose
  emotion
  sceneId

shotSchema:
  id
  beatId
  durationSec
  shotSize
  angle
  movement
  characters
  location
  lighting
  tone
  imagePrompt
  videoPrompt
```

### Phản biện

Không nhất thiết mọi dự án đều phải dùng Sequence.

Nhưng nếu studio phục vụ:

```text
short
long-form
series
documentary
commercial
```

thì Sequence phải là optional-but-first-class container, không nên bỏ khỏi canonical schema.

### Quyết định

**THAY** FlowKit scene-centric hierarchy bằng:

```text
PROJECT
└── STORY
    └── SEQUENCE
        └── SCENE
            └── BEAT
                └── SHOT
```

`SEQUENCE` có thể optional với clip cực ngắn, nhưng schema vẫn tồn tại.

---

# 5. PHẢN BIỆN ĐỘC LẬP — VÒNG 03
## “Beat có thực sự cần, hay Shot trực tiếp từ Scene là đủ?”

### Phản biện

Nếu không có Beat:

```text
Scene
→ AI tự chọn shot
```

AI rất dễ tối ưu từng shot cho “đẹp” thay vì tối ưu **biến đổi cảm xúc/thông tin**.

`film-production-skills` định nghĩa beat boundary bằng thay đổi:

- objective;
- action;
- relationship;
- information;
- emotion;
- spatial state.

`take` buộc beat có:

```text
summary
purpose
emotion
```

### Quyết định

**GIỮ Beat là first-class object.**

Beat là tầng:

```text
WHY THIS MOMENT EXISTS
```

Shot là:

```text
HOW THE AUDIENCE SEES IT
```

---

# 6. PHẢN BIỆN ĐỘC LẬP — VÒNG 04
## “Story Engine có nên ép Blake Snyder / 3-act / Hero’s Journey?”

### Phản biện

CineMatrix có 15-Beat Sheet hữu ích cho diagnostic.

Nhưng `film-production-skills` cố tình không ép story vào một fixed dramatic template.

Điều này phù hợp studio đa ngách hơn.

### Quyết định

**BỎ fixed story formula khỏi core.**

Cho phép plugin:

```text
Story Framework Plugin
├── Three Act
├── Save the Cat
├── Hero's Journey
├── Kishōtenketsu
├── Documentary Arc
├── Commercial Hook-Problem-Solution
└── Custom
```

Nhưng canonical story model chỉ lưu:

```text
causality
objective
pressure
change
information
emotion
state
```

---

# 7. PHẢN BIỆN ĐỘC LẬP — VÒNG 05
## “Cinematography dictionary có đủ không?”

### Kết quả

Không đủ.

FlowKit camera guide biết:

```text
low angle → dominance
high angle → vulnerability
dolly-in → emphasis
golden hour → nostalgia
```

Nhưng `ai-film-skills` đưa ra tầng sâu hơn:

```text
story causality
character purpose
blocking
spatial action
audience effect
story function
actor action
physical image
→ camera design
```

và ghi rõ:

> cụ thể technique là lựa chọn; không map cơ học từ emotion word sang shot.

### Quyết định

**THAY Cinematography Dictionary làm bộ não** bằng:

```text
CINEMATOGRAPHY DECISION ENGINE
```

Dictionary chỉ còn là toolbox.

---

# 8. PHẢN BIỆN ĐỘC LẬP — VÒNG 06
## “Cinematography Decision Engine phải nhận gì?”

Đầu vào tối thiểu:

```text
beat_id
narrative_function
character_objective
obstacle
pressure_change
emotional_target
audience_distance
information_priority
power_relation
rhythm_role
blocking
spatial_baseline
continuity_obligations
previous_shot_context
```

Đầu ra:

```text
shot_function
framing
camera_position
camera_height
camera_angle
camera_distance
lens
movement
focus_strategy
composition
duration
lighting_strategy
sound_attention
edit_relation
decision_basis
```

### Quy tắc quan trọng

Không được:

```text
sad → close-up
power → low-angle
tension → Dutch
```

một cách máy móc.

Phải là:

```text
narrative purpose
+ audience relationship
+ blocking
+ information order
→ compare visual strategies
→ choose one
```

---

# 9. PHẢN BIỆN ĐỘC LẬP — VÒNG 07
## “Shot có cần start/action/end state không?”

### Bằng chứng

`film-production-skills::plan-camera-shots` yêu cầu segment có:

```text
start_state
action
end_state
```

Continuity Studio lưu production memory, continuity snapshots và chuyển approved End State sang next Start State.

### Kết luận

Đây là một trong những nâng cấp quan trọng nhất so với FlowKit.

### Quyết định

**LẤY.**

Canonical Shot phải có:

```text
START STATE
→ ACTION PATH
→ END STATE
```

Motion prompt được compile từ transition này.

---

# 10. PHẢN BIỆN ĐỘC LẬP — VÒNG 08
## “Entity System của FlowKit có nên thay?”

### Kết luận

Không.

Đây là phần mạnh của FlowKit.

FlowKit có:

```text
entity
→ reference prompt
→ reference image
→ media_id
→ scene entity resolution
→ reference inputs
```

có unit test trực tiếp cho resolve `media_id` và block khi reference thiếu.

### Quyết định

**GIỮ lõi Entity/Reference binding của FlowKit.**

Nhưng đổi schema tên:

```text
character_names
```

không nên tiếp tục làm field chứa cả character/location/asset.

Thay bằng:

```text
entity_refs[]
```

với:

```text
entity_id
entity_type
reference_role
required
version
```

---

# 11. PHẢN BIỆN ĐỘC LẬP — VÒNG 09
## “Reference một ảnh có đủ?”

### Kết quả

Không cho studio production cao cấp.

`ai-film-skills::character-asset` có contract:

```text
front full body
90° side full body
back full body
medium head-to-waist
```

và state variants.

`character-continuity-skill` bổ sung:

```text
canon frame
turnaround
detail plates
continuity sheet
drift audit
```

Continuity Studio E2E test còn assert các view như:

```text
FULL_BODY_FRONT
FULL_BODY_SIDE
FULL_BODY_BACK
FRONT
LEFT_PROFILE
THREE_QUARTER
CLOSE_FACE
NEUTRAL_EXPRESSION
```

### Quyết định

**NÂNG** FlowKit single canonical reference thành:

```text
REFERENCE BIBLE
```

---

# 12. REFERENCE BIBLE V1

```text
ENTITY
├── CANON_FRAME
├── IDENTITY_ANCHORS
├── FRONT_FULL
├── SIDE_90_FULL
├── BACK_FULL
├── THREE_QUARTER
├── MEDIUM
├── FACE_CLOSE
├── EXPRESSION_SET
├── HAND_DETAIL          optional
├── HAIR_DETAIL          optional
├── WARDROBE_VARIANTS
├── STATE_VARIANTS
└── APPROVAL / VERSION
```

Không phải mọi shot upload tất cả refs.

Reference Resolver chọn đúng subset theo:

```text
shot need
provider max refs
identity risk
state
framing
generation mode
```

---

# 13. PHẢN BIỆN ĐỘC LẬP — VÒNG 10
## “Continuity chỉ cần parent image là đủ?”

### Kết quả

Không.

Parent image giữ rất nhiều implicit state, nhưng cũng có thể truyền lỗi.

Phải tách:

```text
CANONICAL STATE
+
SEQUENCE STATE
+
PARENT VISUAL STATE
+
SHOT DELTA
```

### Quyết định

**GIỮ** parent-image inheritance của FlowKit.

**BỔ SUNG** Continuity Ledger kiểu Continuity Studio.

---

# 14. STATE ENGINE V1

```text
StateSnapshot
├── story_time
├── location_id
├── spatial_positions
├── screen_direction
├── character_states[]
│   ├── identity_version
│   ├── wardrobe
│   ├── hair
│   ├── makeup
│   ├── dirt
│   ├── wetness
│   ├── injury
│   ├── carried_props
│   ├── emotional_external_state
│   └── pose/blocking
├── prop_states[]
├── environment_state
├── lighting_sources
├── weather
├── damage/wear
└── approved_from_shot
```

Mọi shot:

```text
START_STATE
→ DELTA
→ END_STATE
```

Chỉ `END_STATE` đã QA/approve mới được truyền sang shot kế tiếp.

---

# 15. PHẢN BIỆN ĐỘC LẬP — VÒNG 11
## “ROOT / CONTINUATION của FlowKit có nên bỏ?”

### Kết luận

Không.

Đây là một primitive tốt.

### Quyết định

**GIỮ nhưng nâng thành dependency edge.**

```text
edge_type:
  ROOT
  CONTINUATION
  INSERT
  BRANCH
```

`ROOT`:

```text
fresh visual generation
+ canonical refs
+ current state
```

`CONTINUATION`:

```text
parent accepted image
+ canonical refs
+ current state
+ shot delta
```

`INSERT`:

```text
same story state
+ different visual attention
```

`BRANCH`:

```text
same source state
→ multiple candidate shots/takes
```

---

# 16. PHẢN BIỆN ĐỘC LẬP — VÒNG 12
## “Continuation có nên auto thêm ‘completely different moment’?”

### Kết luận

Không làm luật toàn cục.

FlowKit hiện có transformation helper rất mạnh.

Nó hữu ích khi cần thay góc/composition rõ.

Nhưng gây hại cho:

- subtle reaction;
- micro movement;
- match cut;
- spatially conservative edit;
- same-axis progression.

### Quyết định

**BỎ global hardcoded continuation phrase.**

Thay bằng:

```text
continuity_transform_mode:
  PRESERVE
  EVOLVE
  REFRAME
  TRANSFORM
```

và:

```text
must_preserve[]
must_change[]
forbidden_changes[]
```

---

# 17. PHẢN BIỆN ĐỘC LẬP — VÒNG 13
## “8-Layer nằm ở đâu?”

### Quyết định

**8-Layer nằm trong ShotSpec.**

Không nằm ở Story.

Không nằm ở Beat.

Không nằm ở Scene.

```text
SHOT SPEC

L1 SUBJECT / IDENTITY
L2 STATE / WARDROBE / PROPS
L3 ACTION / PERFORMANCE / EMOTION
L4 ENVIRONMENT / BLOCKING / SPACE
L5 TIME / ATMOSPHERE
L6 CAMERA / OPTICS / COMPOSITION
L7 LIGHTING / COLOR / STYLE
L8 CONTINUITY / CONSTRAINTS
```

---

# 18. 8-LAYER SHOT SPEC — CANONICAL CONTRACT

```yaml
shot_spec:
  shot_id:
  beat_id:
  scene_id:
  sequence_id:

  intent:
    narrative_function:
    emotional_target:
    audience_distance:
    information_priority:
    rhythm_role:
    decision_basis:

  L1_subject:
    entity_refs: []
    identity_versions: []

  L2_state:
    wardrobe:
    props:
    hair_makeup:
    physical_state:
    state_snapshot_id:

  L3_action:
    start_pose:
    action_path:
    reaction:
    end_pose:
    performance_notes:

  L4_environment:
    location_ref:
    spatial_baseline_id:
    blocking:
    landmarks:
    foreground_midground_background:

  L5_time_atmosphere:
    story_time:
    time_of_day:
    weather:
    atmosphere:

  L6_camera:
    shot_size:
    camera_position:
    camera_height:
    angle:
    distance:
    lens_mm:
    sensor_or_lens_family:
    movement:
    movement_phases:
    focus:
    depth_of_field:
    composition:
    screen_direction:

  L7_lighting_style:
    motivated_sources:
    key_fill_rim_relation:
    contrast:
    palette:
    material_response:
    project_style_id:

  L8_continuity:
    parent_shot_id:
    edge_type:
    must_preserve: []
    must_change: []
    forbidden_changes: []
    start_state_id:
    expected_end_state:
```

---

# 19. PHẢN BIỆN ĐỘC LẬP — VÒNG 14
## “Prompt có thể tiếp tục làm source of truth không?”

### Kết luận

Không.

FlowKit có:

```text
prompt
image_prompt
video_prompt
```

và `image_prompt OR prompt` tạo nhiều compilation path.

Đây là nguy cơ:

```text
custom field
→ bypass project style
→ bypass continuation transform
→ bypass locks
```

### Quyết định

**BỎ prompt-as-source-of-truth.**

Canonical:

```text
ShotSpec
↓
Shot IR
↓
Compiler
├── Static Request
└── Motion Request
```

Prompt chỉ là output.

---

# 20. SHOT IR — TẦNG QUAN TRỌNG NHẤT ĐỂ GHÉP NHIỀU REPO

Ý tưởng này lấy mạnh từ `film-production-skills::compile-generation-prompts`.

```yaml
shot_ir:
  segment_id:
  beat_ids: []
  entity_ids: []
  reference_bindings: []
  narrative_facts: {}
  state_facts: {}
  static_observable_state: {}
  temporal_action: {}
  camera_design: {}
  lighting_design: {}
  continuity_constraints: {}
  provider_neutral_constraints: {}
  qa_expectations: {}
```

Shot IR **không chứa cú pháp riêng của Nano Banana/Veo/WAN**.

---

# 21. PHẢN BIỆN ĐỘC LẬP — VÒNG 15
## “Static và Motion có nên compile riêng?”

### Kết luận

Bắt buộc.

`film-production-skills` đã tách:

```text
storyboard_frames
image_requests
video_requests
```

và yêu cầu:

> static frame descriptions separate from temporal video instructions.

### Quyết định

**GIỮ nguyên nguyên tắc:**

```text
1 SHOT
→ 1 STATIC KEYFRAME SPEC
→ 1 MOTION DELTA SPEC
```

Static:

```text
what exists at t0
```

Motion:

```text
what changes from t0 → tN
```

---

# 22. STATIC COMPILER V1

```text
Shot IR
↓
resolve canonical identity refs
↓
resolve state refs
↓
resolve location/prop refs
↓
apply L8 locks
↓
apply project visual DNA
↓
apply provider capability profile
↓
compile natural-language prompt
↓
compile reference roles separately
```

Không lặp identity prose nếu provider đang nhận image refs mạnh và repetition có thể conflict.

---

# 23. MOTION COMPILER V1

Input:

```text
approved static frame
+
start state
+
action path
+
camera motion
+
performance delta
+
end state
```

Output phải tách:

```text
subject motion
camera motion
environment motion
timing
sound
end condition
negative temporal constraints
```

Không được biến static prompt thành video prompt chỉ bằng thêm:

```text
"slowly moves..."
```

---

# 24. PHẢN BIỆN ĐỘC LẬP — VÒNG 16
## “Provider integration nên giữ FlowKit hay thay?”

### Kết luận

Cả hai.

FlowKit có Google Flow integration và reference/edit/chaining path đáng giữ.

Nhưng provider abstraction tổng quát của nó không nên là lõi canonical.

`take` có provider layer:

```text
capability registry
stable errors
retryable classification
rate limiting
timeouts
failover
job registry
```

có tests cho transport.

`film-production-skills` còn yêu cầu:

```text
provider capability profile
generation mode
reference roles
compatibility result
issues
alternatives
```

### Quyết định

```text
CANONICAL EXECUTION ENGINE
    │
    ├── ProviderCapabilityRegistry
    ├── ProviderRouter
    ├── Retry/RateLimit/ErrorTaxonomy
    └── JobRegistry
          │
          ├── GoogleFlowAdapter   ← lấy từ FlowKit
          ├── WANAdapter
          ├── VeoAdapter
          ├── SeedanceAdapter
          ├── KlingAdapter
          └── ...
```

FlowKit trở thành một provider/backend chuyên biệt, không sở hữu Story/Shot schema.

---

# 25. PHẢN BIỆN ĐỘC LẬP — VÒNG 17
## “Execution Orchestration của FlowKit giữ gì?”

**GIỮ:**

```text
request persistence
status lifecycle
skip completed
retry
resume
dependency ordering
wave execution
parent dependency
regen invalidation
artifact IDs
batch status
```

**NÂNG THÊM từ film-production-skills/take:**

```text
idempotency_key
provider-neutral error code
estimated/actual cost
checksum
lineage
capability mismatch
dry run
```

---

# 26. JOB MODEL V1

```yaml
generation_job:
  job_id:
  request_id:
  shot_id:
  artifact_type: image|video|audio
  provider:
  model:
  generation_mode:
  status: queued|running|succeeded|failed|blocked|canceled
  attempt:
  idempotency_key:
  dependency_ids: []
  provider_job_id:
  estimated_cost:
  actual_cost:
  error_code:
  retryable:
  started_at:
  finished_at:
  artifact_ids: []
```

---

# 27. PHẢN BIỆN ĐỘC LẬP — VÒNG 18
## “Static QA có thể chỉ dùng CLIPScore không?”

### Kết luận

Không.

DreamLayer Eval có implementation cho nhiều metrics:

```text
CLIPScore
aesthetic
sharpness/noise/artifact
YOLO composition
DINO subject/background consistency
```

Nhưng metric không hiểu đủ:

```text
đúng outfit?
đúng cassette?
đúng left/right?
đúng cảm xúc?
đúng dramatic intent?
```

### Quyết định

Static QA phải là **multi-layer QA**, không phải một score.

---

# 28. STATIC QA V1

```text
STATIC OUTPUT
↓
A. TECHNICAL QA
   sharpness
   corruption
   anatomy/artifact heuristics

B. METRIC QA
   prompt alignment
   reference similarity
   subject similarity
   object presence/count
   composition signals

C. SEMANTIC VISION QA
   identity
   wardrobe
   prop
   location
   action state
   camera/composition
   lighting/style

D. CONTINUITY QA
   compare canonical refs
   compare parent accepted frame
   compare expected start/end state
   screen direction
   spatial landmarks

E. INTENT QA
   does shot communicate intended beat function?
   is information priority readable?
```

Không gộp thành một điểm duy nhất để che lỗi critical.

---

# 29. PHẢN BIỆN ĐỘC LẬP — VÒNG 19
## “Video QA của FlowKit có nên thay?”

### Kết luận

Không thay hoàn toàn.

FlowKit video reviewer có:

```text
character_consistency
prompt_adherence
motion_quality
visual_fidelity
temporal_coherence
composition
```

và integration-style ffmpeg contact-sheet tests.

### Quyết định

**GIỮ FlowKit Video QA làm một reviewer.**

Bổ sung:

```text
DreamLayer-style metrics:
  temporal flicker
  subject consistency
  background consistency
  motion smoothness

Narrative review:
  action progression
  shot function
  emotional progression
  start/end state compliance
```

---

# 30. VIDEO QA V1

```text
VIDEO
↓
Frame/Motion Metrics
+
Vision Reviewer
+
ShotSpec Compliance
+
Start/End State Verification
+
Cross-Shot Continuity
+
Narrative Intent Check
↓
QAResult
```

---

# 31. PHẢN BIỆN ĐỘC LẬP — VÒNG 20
## “Repair chỉ cần regenerate lại?”

### Kết luận

Không.

`ai-film-skills` có một principle rất mạnh:

```text
visible failure
→ return to earliest responsible decision
→ preserve unaffected accepted decisions
```

Đây là nền tảng tốt nhất cho Targeted Repair.

### Quyết định

**THAY retry/regenerate chung chung bằng Layer-Targeted Repair.**

---

# 32. TARGETED REPAIR ENGINE V1

Map lỗi → owner:

```text
IDENTITY_MISMATCH
→ Reference Resolver / L1

WARDROBE_STATE_MISMATCH
→ State Engine / L2

PROP_MISMATCH
→ State + L2

ACTION_MISMATCH
→ L3 / Motion Compiler

SPATIAL_CONTINUITY_FAIL
→ L4 + L8

CAMERA_FAIL
→ L6

LIGHTING_STYLE_FAIL
→ L7

PARENT_DRIFT
→ L8 / Continuity

MODEL_CAPABILITY_FAIL
→ Provider Router

NARRATIVE_INTENT_FAIL
→ Directing/Cinematography layer
```

Repair algorithm:

```text
1. identify earliest responsible layer
2. freeze all passing layers
3. patch only responsible state/spec
4. recompile affected request
5. invalidate only dependent artifacts
6. regenerate
7. re-run targeted QA
8. propagate accepted end-state
```

---

# 33. REPAIR PLAN CONTRACT

```yaml
repair_plan:
  failure_id:
  shot_id:
  failure_code:
  responsible_layer:
  root_cause_hypothesis:
  preserve:
    - ...
  patch:
    - field:
      old:
      new:
      reason:
  invalidate:
    - artifact_id
  recompile:
    static: true|false
    motion: true|false
  recheck_dimensions:
    - ...
```

Đây là module chưa thấy repo nào làm hoàn chỉnh đúng mức này.

**Nên tự xây.**

---

# 34. PHẢN BIỆN ĐỘC LẬP — VÒNG 21
## “Cần provenance/lineage không?”

### Kết luận

Có, nếu studio muốn scale.

`film-production-skills` dùng shared result envelope:

```text
contract_version
request_id
status
diagnostics
lineage
handoff
```

Mỗi request provider còn biết:

```text
segment
beat
asset refs
reference roles
model
generation mode
compatibility
issues
```

### Quyết định

**LẤY mô hình contract/lineage làm xương sống.**

---

# 35. ARTIFACT LINEAGE V1

Mỗi output phải truy ngược được:

```text
artifact
→ generation attempt
→ provider request
→ compiled prompt
→ Shot IR
→ ShotSpec
→ Beat
→ Scene
→ Sequence
→ Story version
```

và:

```text
reference versions
state snapshot
project visual DNA version
compiler version
provider adapter version
QA result
repair history
```

---

# 36. PHẢN BIỆN ĐỘC LẬP — VÒNG 22
## “Cần restart-safe workflow không?”

### Kết luận

Có.

Continuity Studio E2E test chứng minh workflow có thể:

```text
start automatic production
→ stop server
→ restart
→ recover completed stages
→ continue at main-character checkpoint
→ finish production package
```

Manual E2E cũng kiểm:

```text
user changes Movie DNA
→ restart
→ preserve choice
→ resume exact incomplete stage
```

### Quyết định

**LẤY restart-safe stage state machine.**

Không được phụ thuộc vào chat context để biết đang ở đâu.

---

# 37. PRODUCTION STATE MACHINE V1

```text
NOT_STARTED
↓
IN_PROGRESS
↓
WAITING_INPUT
↓
READY_FOR_REVIEW
↓
APPROVED
↓
LOCKED
```

Failure path:

```text
FAILED
REPAIR_PENDING
BLOCKED
```

Mỗi stage có:

```text
stage_id
version
status
inputs
outputs
decision log
blocking reason
resume anchor
```

---

# 38. PHẢN BIỆN ĐỘC LẬP — VÒNG 23
## “Cần 3D previs không?”

Không bắt buộc mọi project.

Nhưng với:

- nhiều nhân vật;
- action;
- spatial continuity;
- 180° rule;
- camera path phức tạp;
- location geometry quan trọng;

thì text-only spatial reasoning không đủ ổn định.

`ai-video-production-editor` có 2D scene map → 3D props/camera frustum.

`ai-film-skills` có experimental whitebox-previs-executor.

### Quyết định

**ADD optional SPATIAL PREVIS plugin.**

Không đặt vào hard dependency của mọi shot.

---

# 39. SPATIAL BASELINE

```yaml
spatial_baseline:
  location_id:
  coordinate_system:
  landmarks: []
  entrances_exits: []
  character_marks: []
  prop_positions: []
  camera_safe_zones: []
  axis_lines: []
  motivated_light_sources: []
```

Cinematography Engine đọc baseline trước khi đổi camera.

---

# 40. PHẢN BIỆN ĐỘC LẬP — VÒNG 24
## “Post-production có thuộc core generation không?”

Không.

Nhưng studio end-to-end cần handoff.

Cine Studio có MIT và NLE export ideas.

AI Video Production Editor có Edit/Color/Fairlight/Deliver nhưng GPL.

### Quyết định

Core chỉ cần:

```text
non-destructive timeline
selected takes
source in/out
audio tracks
export manifest
```

NLE UI có thể là module riêng.

Ưu tiên học/tái dùng code permissive từ MIT repo khi phù hợp.

---

# 41. FINAL CANONICAL ARCHITECTURE

```text
┌───────────────────────────────────────────────┐
│ 00 INPUT / INGEST                             │
│ Idea / Brief / Screenplay / Existing Project  │
└──────────────────────┬────────────────────────┘
                       ↓
┌───────────────────────────────────────────────┐
│ 01 SCREENPLAY STRUCTURE                       │
│ Scenes / Units / Beats / Production Facts     │
└──────────────────────┬────────────────────────┘
                       ↓
┌───────────────────────────────────────────────┐
│ 02 STORY INTELLIGENCE                         │
│ Causality / Objectives / Pressure / Arcs      │
│ Story Blueprint / Film Bible                  │
└──────────────────────┬────────────────────────┘
                       ↓
┌───────────────────────────────────────────────┐
│ 03 NARRATIVE HIERARCHY                        │
│ Story → Sequence → Scene → Beat               │
└──────────────────────┬────────────────────────┘
                       ↓
┌───────────────────────────────────────────────┐
│ 04 PRODUCTION ASSETS                          │
│ Entity Registry / Reference Bible / Versions  │
└──────────────────────┬────────────────────────┘
                       ↓
┌───────────────────────────────────────────────┐
│ 05 STATE / CONTINUITY                         │
│ State Ledger / Spatial Baseline / Timeline    │
└──────────────────────┬────────────────────────┘
                       ↓
┌───────────────────────────────────────────────┐
│ 06 DIRECTING INTENT                           │
│ Narrative function / Audience / Information   │
└──────────────────────┬────────────────────────┘
                       ↓
┌───────────────────────────────────────────────┐
│ 07 CINEMATOGRAPHY DECISION                    │
│ Blocking + camera + lens + motion + light     │
└──────────────────────┬────────────────────────┘
                       ↓
┌───────────────────────────────────────────────┐
│ 08 SHOT SPEC                                  │
│ Canonical 8 Layers                            │
└──────────────────────┬────────────────────────┘
                       ↓
┌───────────────────────────────────────────────┐
│ 09 SHOT IR / PREFLIGHT                        │
│ IDs / refs / states / capabilities / gates    │
└──────────────────────┬────────────────────────┘
                       ↓
         ┌─────────────┴─────────────┐
         ↓                           ↓
┌──────────────────┐        ┌──────────────────┐
│ STATIC COMPILER  │        │ MOTION COMPILER  │
└────────┬─────────┘        └────────▲─────────┘
         ↓                            │
┌────────────────────────────────────┴──────────┐
│ 10 PROVIDER ROUTER / EXECUTION                 │
│ Flow / WAN / Veo / Seedance / Kling / ...     │
└──────────────────────┬────────────────────────┘
                       ↓
               STATIC GENERATION
                       ↓
┌───────────────────────────────────────────────┐
│ 11 STATIC QA                                  │
│ metrics + vision + continuity + intent        │
└──────────────────────┬────────────────────────┘
                       ↓
               PASS? ──NO──► TARGETED REPAIR
                       │                 │
                      YES                └──► recompile
                       ↓
                MOTION COMPILER
                       ↓
                VIDEO GENERATION
                       ↓
┌───────────────────────────────────────────────┐
│ 12 MOTION / VIDEO QA                          │
└──────────────────────┬────────────────────────┘
                       ↓
               PASS? ──NO──► TARGETED REPAIR
                       │
                      YES
                       ↓
┌───────────────────────────────────────────────┐
│ 13 ACCEPTED END STATE                         │
│ transfer to next shot                         │
└──────────────────────┬────────────────────────┘
                       ↓
┌───────────────────────────────────────────────┐
│ 14 SEQUENCE QA                                │
│ rhythm / continuity / visual grammar          │
└──────────────────────┬────────────────────────┘
                       ↓
┌───────────────────────────────────────────────┐
│ 15 EDITORIAL / AUDIO / EXPORT                 │
│ timeline / VO / SFX / music / delivery        │
└───────────────────────────────────────────────┘
```

---

# 42. KEEP / TAKE / REPLACE / DROP — FINAL MATRIX

## A. FLOWKIT — GIỮ

| Module | Quyết định |
|---|---|
| Entity persistence | **KEEP** |
| Reference generation/media IDs | **KEEP** |
| Missing-reference blocking | **KEEP** |
| Reference resolution per generation | **KEEP** |
| Parent image as edit base | **KEEP** |
| ROOT / CONTINUATION concept | **KEEP + EXTEND** |
| Dependency waves | **KEEP** |
| Queue/status/retry/resume | **KEEP** |
| Skip completed | **KEEP** |
| Parent regen invalidation | **KEEP** |
| Google Flow adapter/transport | **KEEP AS PROVIDER ADAPTER** |
| Video contact-sheet reviewer | **KEEP + EXTEND** |

---

# 43. FLOWKIT — THAY

| FlowKit hiện tại | Thay bằng |
|---|---|
| Story → Scene trực tiếp | Story → Sequence → Scene → Beat → Shot |
| `Scene` là generation unit | `Shot` là generation unit |
| `character_names` overloaded | typed `entity_refs` |
| `prompt/image_prompt/video_prompt` là source data | ShotSpec → Shot IR → compiler |
| camera dictionary + LLM tự chọn | Cinematography Decision Engine |
| single ref per entity | Reference Bible + resolver |
| implicit continuity | State Ledger + parent visual state |
| hardcoded continuation transform | continuity transform modes |
| material prefix as visual lock | Project Visual DNA + compiled L7 |
| static completion = request completed | Static QA gate |
| generic retry/regenerate | Targeted Repair |
| provider/domain coupling | provider capability registry + adapters |
| weak lineage | artifact lineage chain |

---

# 44. FLOWKIT — BỎ

**BỎ khỏi canonical architecture:**

```text
Scene == Shot
```

```text
prompt string == source of truth
```

```text
custom image_prompt được phép bypass locks
```

```text
continuation nào cũng phải "completely different moment"
```

```text
style lock chỉ bằng prepend string
```

```text
mọi lỗi đều regen toàn shot
```

```text
cinematography chọn kỹ thuật chỉ vì emotion keyword
```

```text
request COMPLETED == creative PASS
```

---

# 45. FILM-PRODUCTION-SKILLS — LẤY

Đây là repo **nên lấy cấu trúc contract nhiều nhất**.

**TAKE:**

```text
shared request/result envelope
stable IDs
lineage
diagnostics
handoff
partial/blocked status semantics

screenplay structure:
  scenes
  units
  beats
  rhythm

production assets:
  identity anchors
  allowed variation
  variants
  coverage

shot planning:
  spatial baseline
  continuity rules
  start/action/end state
  preflight

prompt compilation:
  semantic shot IR
  static/video separation
  provider capability profiles
  reference roles
  compatibility issues

execution:
  idempotency
  durable jobs
  cost
  checksums

review:
  reversible decisions
  selected/rejected/revision-needed
  non-destructive timeline
```

**DO NOT TAKE blindly:**

Nó là Agent Skills/contract architecture; không phải mọi stage đều là một production runtime hoàn chỉnh. Dùng làm schema/contract backbone, không thay thế FlowKit execution adapter.

---

# 46. TAKE — LẤY

**TAKE:**

```text
pure domain core
Beat/Shot typed schemas
Zod validation
dangling-reference checks
controlled cinematography vocabulary
provider seam
stable error taxonomy
retry / timeout / rate limit
capability-aware routing
job registry
mock provider testing
```

### Điều chỉnh

Shot schema của `take` hiện còn đơn giản so với mục tiêu của studio.

Không dùng nguyên:

```text
imagePrompt
videoPrompt
```

làm canonical fields.

Thay bằng:

```text
ShotSpec
ShotIR
compiled_artifacts
```

---

# 47. CONTINUITY STUDIO — LẤY

Đây là nguồn tốt nhất cho **production memory/state architecture**.

**TAKE:**

```text
Movie DNA / Visual DNA
Story + Film Bible
Character state
Asset manifest
Flat stable asset IDs
Shot Planner
Sequence Planner
Prompt Workspace
Continuity Ledger
Story Timeline
Audio Bible
approved End State → next Start State
attempt history
approval locks
restart-safe automatic/manual workflow
```

### Không lấy nguyên

Không để `Sequence` trở thành generation unit thay `Shot`.

Trong kiến trúc của studio:

```text
Sequence = narrative/continuity container
Shot = generation unit
```

---

# 48. AI-FILM-SKILLS — LẤY

Đây là nguồn tốt nhất cho **nghề đạo diễn/cinematography logic** trong nhóm audit.

**TAKE:**

```text
story causality before camera terminology
character objective / obstacle / strategy
audience endpoint
information order
blocking + camera designed together
world state fixed, projection recomputed per camera
complex camera movement with start/trigger/phases/end
earliest broken layer repair
preserve unaffected accepted decisions
actual pixels for image verdict
actual motion for video verdict
```

**Character asset:**

```text
script-first design basis
facts vs design inference
multi-view minimum
state variants
locked features
approval gate
```

### Không lấy nguyên tất cả genre presets

Genre packs chỉ là optional specialized plugins.

Core phải genre-neutral.

---

# 49. SCRIPTBREAK — LẤY

**TAKE cho ingest layer:**

```text
FDX
Fountain
PDF
TXT
scene headings
INT/EXT
day/night
characters
props
wardrobe
vehicles
VFX
background
character/location bibles
starter shot calls
Project Look ingestion
```

ScriptBreak cực hữu ích khi đầu vào đã là screenplay thật.

Không dùng nó làm Story/Cinematography brain.

---

# 50. CHARACTER-CONTINUITY-SKILL — LẤY

**TAKE:**

```text
canon frame
turnaround discipline
detail plates
locked identity block concept
per-shot continuity sheet
drift contact-sheet audit
repair-vs-regenerate thinking
```

FlowKit lo media execution.

Module này nâng **reference methodology**.

---

# 51. DREAMLAYER EVAL — LẤY MỘT PHẦN

**TAKE concept/metric layer:**

```text
CLIPScore
technical quality
object/prompt adherence
DINO subject consistency
DINO background consistency
temporal flicker
motion smoothness
reproducible metric records
```

### Không dùng metric để quyết định nghệ thuật

Không được:

```text
higher aesthetic score = better shot
```

QA metrics chỉ là sensor.

Director/intent QA vẫn cần semantic reviewer.

### License

GPLv3: nếu sản phẩm đóng nguồn, không bê nguyên implementation mà chưa đánh giá license. Có thể tự triển khai metric layer hoặc tách boundary phù hợp sau review pháp lý.

---

# 52. STORYMIND — GIỮ LÀ REFERENCE, KHÔNG LÀ CORE DEPENDENCY

Điểm đáng học:

```text
shot plan before generation
shot scale
movement
lighting
emotional beat
character anchors
visual anchors
```

Nhưng:

- phần này đã được cover sâu hơn bằng `film-production-skills + take + ai-film-skills`;
- AGPLv3 làm code reuse cần cân nhắc;
- không cần thêm một story/shot brain song song gây duplicate authority.

**Decision: STUDY ONLY.**

---

# 53. AI VIDEO PRODUCTION EDITOR — OPTIONAL REFERENCE

Điểm mạnh đáng học:

```text
3D scene map
camera frustum
set blockout
continuity review
re-film queue
timeline/edit/color/sound
```

Nhưng core là GPL.

**Decision:**

```text
Study 3D spatial UX / post UX.
Do not make it a core code dependency unless license strategy allows.
```

---

# 54. CINE STUDIO — OPTIONAL TAKE

MIT, đáng lấy:

```text
provider interface ideas
screenplay editor ideas
production planning
NLE exports:
  FCPXML
  EDL
  CapCut-style handoff
```

Không cần duplicate FlowKit/take orchestration.

---

# 55. VOX DIRECTOR — PLUGIN ONLY

Lấy cho:

```text
short-form beat map
hook/pacing
beat visual pattern
```

Không dùng làm film-wide story grammar.

---

# 56. CINEMATRIX — STUDY ONLY

Có:

```text
15-beat diagnostic
tension curve
storyboard/camera ideas
```

Nhưng:

- fixed formula không phù hợp core universal;
- README hiện ghi All rights reserved.

**Decision: concept only, không copy code.**

---

# 57. SINGLE SOURCE OF TRUTH

Hệ thống tuyệt đối không có nhiều master song song.

Authority order:

```text
1. LOCKED STORY FACTS
2. LOCKED PRODUCTION ASSETS
3. APPROVED STATE SNAPSHOT
4. APPROVED DIRECTING/CINEMATOGRAPHY DECISION
5. SHOT SPEC
6. SHOT IR
7. COMPILED PROVIDER REQUEST
8. GENERATED ARTIFACT
```

Nếu prompt conflict với ShotSpec:

```text
ShotSpec thắng.
```

Nếu parent image conflict với approved canonical state:

```text
approved state + canonical refs thắng.
```

---

# 58. AUTHORITY / MUTABILITY MODEL

```text
IMMUTABLE UNTIL EXPLICIT REVISION
├── story facts
├── identity anchors
├── approved dialogue
└── accepted asset versions

VERSIONED MUTABLE
├── visual DNA
├── sequence state
├── cinematography decisions
├── ShotSpec
└── compiler profiles

EPHEMERAL
├── provider prompt
├── provider job ID
├── candidate generation
└── temporary reference ordering
```

---

# 59. CINEMATOGRAPHY DECISION FLOW

```text
BEAT
↓
What changes?
↓
What must audience know?
↓
What should audience feel?
↓
How close/far should audience feel from character?
↓
What is actor physically doing?
↓
Where are bodies/objects in space?
↓
What visual information must be preserved from previous shot?
↓
Compare visual strategies
↓
Select shot grammar
↓
Record decision basis
```

Ví dụ không còn:

```text
sad → 85mm CU
```

mà:

```text
recognition before grief
→ hold environment initially
→ delay reaction
→ medium static
→ only after recognition start push-in
→ close-up at emotional landing
```

---

# 60. SHOT DESIGN PRE-FLIGHT

Trước generation, gate phải check:

```text
[ ] beat purpose known
[ ] dominant action count is executable
[ ] duration plausible
[ ] entity refs valid
[ ] state snapshot exists
[ ] location spatial baseline exists if required
[ ] screen direction coherent
[ ] camera path does not contradict blocking
[ ] static keyframe is a single observable moment
[ ] video delta has start/action/end
[ ] provider supports requested reference roles
[ ] prompt cannot bypass locked fields
```

Fail preflight → không tốn generation credits.

---

# 61. PROVIDER CAPABILITY PROFILE

```yaml
provider_profile:
  provider:
  model:
  media:
  supports:
    text_to_image:
    image_to_image:
    text_to_video:
    image_to_video:
    first_frame:
    last_frame:
    multi_reference:
    character_reference:
    audio:
  limits:
    max_refs:
    duration:
    aspect_ratios:
    resolutions:
  prompt_dialect:
  negative_prompt_support:
  known_constraints:
  verified_at:
```

Compiler không được tự giả định capability.

---

# 62. REFERENCE RESOLVER

```text
ShotSpec
↓
Identify required entities
↓
Identify required state variant
↓
Choose best canonical refs
↓
Respect provider max refs
↓
Assign roles:
  IDENTITY
  WARDROBE
  LOCATION
  PROP
  FIRST_FRAME
  LAST_FRAME
  STYLE
↓
Return ordered binding
```

Provider-specific upload order là output của resolver/adapter, không phải canonical story data.

---

# 63. INVALIDATION GRAPH

Một sửa đổi không được làm regenerate cả phim.

Ví dụ:

```text
Character C01 identity v2
```

invalidate:

```text
shots using C01
+ descendants whose visual state inherited those shots
```

không invalidate:

```text
unrelated character chain
unrelated location-only shots
approved audio
story structure
```

---

# 64. QA SEVERITY MODEL

```text
BLOCKING
  identity wrong
  wrong character
  wrong prop critical to story
  missing required action
  spatial impossibility
  major continuity break

HIGH
  wardrobe/state mismatch
  camera contradicts intent
  key composition miss
  visible anatomy defect
  end state incorrect

MEDIUM
  minor lighting drift
  background detail drift
  small prompt miss

COSMETIC
  micro texture preference
  non-critical aesthetic variation
```

Không lấy weighted average để cho BLOCKING lỗi “trung hòa” bởi điểm đẹp cao.

---

# 65. SEQUENCE QA

Shot QA tốt chưa đủ.

Sau một sequence:

```text
check:
  emotional progression
  information order
  shot-size rhythm
  camera repetition
  screen direction
  lighting/time continuity
  wardrobe/prop progression
  state inheritance
  pacing
  visual monotony
  climax emphasis
```

Đây là tầng giúp tránh:

> “20 shot đều đẹp nhưng đoạn phim không có nhịp.”

---

# 66. PROJECT-LEVEL QA

Cuối phim:

```text
Story payoff
Character arc
Visual DNA
Identity stability
World consistency
Sequence rhythm
Audio continuity
Edit continuity
Delivery specs
Missing/rejected shots
```

---

# 67. DỮ LIỆU TỐI THIỂU CẦN PERSIST

```text
project
story_versions
sequences
scenes
beats
shots
shot_specs
shot_ir_versions
entities
entity_versions
reference_assets
state_snapshots
spatial_baselines
cinematography_decisions
compiled_requests
generation_jobs
artifacts
qa_results
repair_plans
dependency_edges
timeline
export_manifests
```

---

# 68. UI WORKSPACE NÊN PHẢN ÁNH DOMAIN

Không làm UI chỉ có:

```text
Scene 1
Scene 2
Scene 3
```

Nên:

```text
Story
├── Sequence 01
│   ├── Scene 01
│   │   ├── Beat 01
│   │   │   ├── Shot 01A
│   │   │   └── Shot 01B
│   │   └── Beat 02
│   └── Scene 02
└── Sequence 02
```

Shot workspace:

```text
Intent
Cinematography
8 Layers
References
State
Static
Motion
QA
Repair history
```

---

# 69. KHÔNG ĐỂ USER PHẢI ĐIỀN MỌI FIELD

Canonical schema sâu không có nghĩa UI bắt user nhập hàng trăm trường.

Agent tự đề xuất:

```text
story interpretation
beat
camera
lighting
state
```

User chỉ cần:

```text
approve
edit
lock
override
```

Schema sâu là để **machine reasoning/validation**, không phải biến UI thành spreadsheet.

---

# 70. MINIMUM VIABLE CORE

Để tránh overengineering, build theo thứ tự:

```text
P0 Canonical IDs + hierarchy
P1 Entity/Reference bridge
P2 ShotSpec + Shot IR
P3 Static/Motion compilers
P4 Provider router + FlowKit adapter
P5 State engine
P6 Static QA
P7 Video QA fusion
P8 Targeted Repair
P9 Sequence QA
P10 Post/export
P11 Optional 3D previs
```

Không xây 3D trước khi ShotSpec/State/QA ổn.

---

# 71. SOURCE PRIORITY FOR ACTUAL CODE REUSE

## Ưu tiên cao — permissive

```text
FlowKit                     MIT
film-production-skills      MIT
take                        MIT
Continuity Studio           Apache-2.0
ai-film-skills              Apache-2.0
ScriptBreak                 Apache-2.0
Cine Studio                 MIT
character-continuity code   MIT
```

## Chỉ học concept trước

```text
StoryMind                    AGPLv3
DreamLayer Eval              GPLv3
AI Video Production Editor   GPL-3.0-or-later
CineMatrix                   All rights reserved
```

`DreamLayer` metrics có thể được tái thiết kế/triển khai độc lập dựa trên papers/libraries phù hợp thay vì copy code GPL nếu sản phẩm cần giữ license khác.

---

# 72. NHỮNG MODULE KHÔNG ĐƯỢC DUPLICATE AUTHORITY

Không tồn tại đồng thời:

```text
FlowKit Scene prompt
AND
Take shot prompt
AND
Continuity sequence prompt
```

cùng làm master.

Chỉ có:

```text
ShotSpec/ShotIR = master
```

Các repo khác chỉ feed/consume canonical data.

---

# 73. FINAL SOURCE MAP

```text
SCREENPLAY INGEST
  ScriptBreak
  + film-production-skills/structure-screenplay

STORY / CAUSALITY
  ai-film-skills/director-agent
  + film-production-skills/shape-story-blueprint

BEAT / SHOT DOMAIN
  film-production-skills
  + take typed core

CINEMATOGRAPHY
  ai-film-skills/ai-storyboard-director
  + film-production-skills/plan-camera-shots

ASSETS
  FlowKit Entity
  + ai-film-skills character/scene/prop asset
  + character-continuity discipline

STATE / CONTINUITY
  Continuity Studio
  + FlowKit parent-image chaining

SHOT SPEC / PROMPT
  custom 8-Layer ShotSpec
  + film-production-skills Shot IR/compiler

PROVIDER RUNTIME
  take provider seam
  + custom adapters
  + FlowKit as Google Flow adapter

EXECUTION
  FlowKit queue/waves/retry/resume
  + take transport/error taxonomy
  + film-production job contracts

STATIC QA
  custom semantic QA
  + DreamLayer-inspired metrics

VIDEO QA
  FlowKit reviewer
  + metric layer
  + narrative/state QA

REPAIR
  custom Targeted Repair
  + ai-film-skills earliest-responsible-layer principle

POST
  film-production-skills non-destructive timeline
  + Cine Studio NLE handoff ideas
```

---

# 74. CÁC REPO KHÔNG CẦN ĐƯA VÀO CORE

```text
StoryMind
→ useful corroboration but duplicate shot brain

Vox Director
→ useful short-form plugin only

CineMatrix
→ optional beat diagnostic, not universal grammar

AI Video Production Editor
→ excellent UX/3D/post reference, GPL core not required
```

Càng nhiều brain cùng viết story/camera càng dễ conflict.

Mục tiêu không phải “tích hợp nhiều repo nhất”.

Mục tiêu là:

```text
mỗi trách nhiệm chỉ có một authority
```

---

# 75. FINAL KEEP / REPLACE / ADD / DROP SUMMARY

## KEEP

```text
FlowKit:
  Entity
  Reference media IDs
  Reference blocking
  Parent image edit
  ROOT/CONTINUATION
  Dependency waves
  Queue/retry/resume
  Invalidation
  Flow adapter
  Video reviewer
```

## REPLACE

```text
Scene-centric narrative
→ Story/Sequence/Scene/Beat/Shot

Camera dictionary as decision brain
→ Cinematography Decision Engine

Prompt fields as master
→ ShotSpec + Shot IR

Single-reference identity
→ Reference Bible

Implicit continuity
→ State Engine

Global continuation transformation
→ continuity modes + must-preserve/change

Generic regen
→ Targeted Repair
```

## ADD

```text
Screenplay importer
Story causality engine
Film Bible
Sequence
Beat
Shot
State Snapshot
Spatial Baseline
8-Layer ShotSpec
Shot IR
Provider Capability Registry
Static QA
Sequence QA
Artifact Lineage
RepairPlan
Restart-safe production state
Optional 3D previs
Non-destructive editorial timeline
```

## DROP

```text
duplicate masters
prompt bypass paths
hardcoded universal camera/emotion mapping
fixed story formula as mandatory
request-completed == creative-pass
regen-everything repair strategy
provider-specific fields leaking into story schema
```

---

# 76. FINAL FROZEN PIPELINE

```text
IDEA / SCRIPT
↓
INGEST
↓
STORY CAUSALITY
↓
STORY BLUEPRINT / FILM BIBLE
↓
SEQUENCE
↓
SCENE
↓
BEAT
↓
DIRECTING INTENT
↓
CINEMATOGRAPHY DECISION
↓
SHOT
↓
8-LAYER SHOT SPEC
↓
STATE + REFERENCE RESOLUTION
↓
SHOT IR
↓
PREFLIGHT
↓
STATIC COMPILER
↓
PROVIDER ROUTER
↓
STATIC GENERATION
↓
STATIC QA
├── FAIL → TARGETED REPAIR ↺
└── PASS
     ↓
MOTION COMPILER
↓
VIDEO GENERATION
↓
VIDEO QA
├── FAIL → TARGETED REPAIR ↺
└── PASS
     ↓
ACCEPT END STATE
↓
NEXT SHOT
↓
SEQUENCE QA
↓
EDITORIAL / AUDIO
↓
PROJECT QA
↓
EXPORT
```

---

# 77. NGUYÊN TẮC FROZEN

1. **Story facts không được prompt compiler tự sửa.**
2. **Beat xác định WHY; Shot xác định HOW.**
3. **Camera phải có lý do từ narrative/audience/blocking, không chọn chỉ vì đẹp.**
4. **ShotSpec là source of truth, không phải prompt.**
5. **Static và Motion compile riêng.**
6. **Continuity là state chạy xuyên pipeline, không phải bước cuối.**
7. **Canonical refs + current state + parent visual + shot delta cùng tồn tại.**
8. **Generated artifact phải QA trước khi trở thành state authority.**
9. **Repair quay về layer gây lỗi sớm nhất và giữ nguyên phần đã đúng.**
10. **Provider capability không được giả định.**
11. **Một responsibility chỉ có một authority.**
12. **Mọi artifact quan trọng phải trace được lineage.**
13. **Không tuyên bố production-proven nếu chưa benchmark thật.**
14. **Không lấy test count hoặc README claim làm bằng chứng creative quality.**
15. **Ưu tiên code permissive cho sản phẩm thương mại.**

---

# 78. BENCHMARK ĐỂ ĐƯỢC PHÉP GỌI LÀ PRODUCTION-GRADE

Sau khi code, test tối thiểu:

```text
3 project
× 100 shots
= 300 shots
```

Phải có:

```text
multi-character
multiple wardrobes
recurring props
recurring locations
time changes
weather changes
ROOT/CONTINUATION/INSERT
camera variation
emotional progression
dialogue
action
subtle continuity
```

Metric:

```text
identity first-pass rate
wardrobe/state pass rate
prop pass rate
spatial continuity pass rate
camera adherence
static first-pass QA
video first-pass QA
average regen count
repair success rate
chain-depth drift
ROOT re-anchor recovery
cost per accepted shot
latency per accepted shot
```

Chỉ sau benchmark mới dùng claim:

```text
production-proven at 300-shot scale
```

---

# 79. FILES / SOURCE EVIDENCE — IMPORTANT LINKS

## FlowKit

- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/sdk/services/operations.py
- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/skills/fk-gen-images.md
- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/skills/fk-camera-guide.md
- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/services/video_reviewer.py
- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/tests/unit/test_operations.py
- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/tests/unit/test_video_reviewer.py

## Film Production Skills

- https://github.com/zhangzhangco/film-production-skills/blob/47b2a6a432235e716fa2aa0d08eefae76fdb34fd/workflow.yaml
- https://github.com/zhangzhangco/film-production-skills/blob/47b2a6a432235e716fa2aa0d08eefae76fdb34fd/skills/structure-screenplay/SKILL.md
- https://github.com/zhangzhangco/film-production-skills/blob/47b2a6a432235e716fa2aa0d08eefae76fdb34fd/skills/plan-camera-shots/SKILL.md
- https://github.com/zhangzhangco/film-production-skills/blob/47b2a6a432235e716fa2aa0d08eefae76fdb34fd/skills/compile-generation-prompts/SKILL.md
- https://github.com/zhangzhangco/film-production-skills/blob/47b2a6a432235e716fa2aa0d08eefae76fdb34fd/skills/review-and-assemble/SKILL.md

## take

- https://github.com/XucroYuri/take/blob/47c17216b5ad74ee7dd376e8508266e29aefae2c/packages/core/src/schemas.ts
- https://github.com/XucroYuri/take/blob/47c17216b5ad74ee7dd376e8508266e29aefae2c/packages/core/src/validate.ts
- https://github.com/XucroYuri/take/blob/47c17216b5ad74ee7dd376e8508266e29aefae2c/skills/take/references/workflow.md
- https://github.com/XucroYuri/take/blob/47c17216b5ad74ee7dd376e8508266e29aefae2c/skills/take/references/shot-language.md
- https://github.com/XucroYuri/take/blob/47c17216b5ad74ee7dd376e8508266e29aefae2c/packages/provider/src/transport/http.ts

## Continuity Studio

- https://github.com/momorzq-oss/Continuity-Studio/blob/2f818cc4d14f84e7b31236aa4d8e307a8c5b952b/README.md
- https://github.com/momorzq-oss/Continuity-Studio/blob/2f818cc4d14f84e7b31236aa4d8e307a8c5b952b/server/automatic-production-director.test.ts
- https://github.com/momorzq-oss/Continuity-Studio/blob/2f818cc4d14f84e7b31236aa4d8e307a8c5b952b/server/manual-production-director.test.ts

## Open Film Skills

- https://github.com/62656456/ai-film-skills/blob/4a33628b789976f004079772c8dc77d3f317a566/skills/director-agent/SKILL.md
- https://github.com/62656456/ai-film-skills/blob/4a33628b789976f004079772c8dc77d3f317a566/skills/ai-storyboard-director/SKILL.md
- https://github.com/62656456/ai-film-skills/blob/4a33628b789976f004079772c8dc77d3f317a566/skills/character-asset/SKILL.md
- https://github.com/62656456/ai-film-skills/blob/4a33628b789976f004079772c8dc77d3f317a566/docs/SKILL_DESIGN_SYSTEM.md
- https://github.com/62656456/ai-film-skills/blob/4a33628b789976f004079772c8dc77d3f317a566/skills/director-agent/references/screenplay-state-engine.md

## ScriptBreak

- https://github.com/wassermanproductions/scriptbreak/blob/ed9efb86125b713ce430b7337f27392adec071a9/README.md
- https://github.com/wassermanproductions/scriptbreak/blob/ed9efb86125b713ce430b7337f27392adec071a9/mcp/scriptbreak-mcp.mjs

## DreamLayer Eval

- https://github.com/TheDesignFounder/DreamLayer-Eval/blob/9d98f429905752b88d64b1aeab16ded81781894f/dream_layer_backend/dream_layer_backend_utils/video_quality_metrics.py
- https://github.com/TheDesignFounder/DreamLayer-Eval/blob/9d98f429905752b88d64b1aeab16ded81781894f/dream_layer_backend/dream_layer_backend_utils/clip_score_metrics.py
- https://github.com/TheDesignFounder/DreamLayer-Eval/blob/9d98f429905752b88d64b1aeab16ded81781894f/dream_layer_backend/txt2vid_server.py

## Other references

- https://github.com/Nagacash/character-continuity-skill
- https://github.com/LinHao-city/StoryMind
- https://github.com/LudwigKienle/ai-video-production-editor
- https://github.com/sankar2389/cine-studio
- https://github.com/Alisa0808/vox-director
- https://github.com/kirklasalle/CineMatrix

---

# 80. DESIGN FREEZE VERDICT

Sau các vòng phản biện, kiến trúc tối ưu **không phải**:

```text
FlowKit++
```

và cũng không phải:

```text
merge tất cả repo
```

Mà là:

```text
ONE CANONICAL STUDIO MODEL
+
BEST-OF-BREED SUBSYSTEMS
+
ONE AUTHORITY PER RESPONSIBILITY
```

Cụ thể:

```text
Narrative contracts
  ← film-production-skills + ai-film-skills

Beat/Shot typed domain
  ← take + film-production-skills

Ingest
  ← ScriptBreak

Assets/References
  ← FlowKit + ai-film-skills + continuity discipline

State
  ← Continuity Studio

Cinematography
  ← ai-film-skills + plan-camera-shots

Prompt compilation
  ← custom ShotSpec/IR + film-production-skills

Execution
  ← FlowKit + take provider runtime

Static QA
  ← custom + metric layer

Video QA
  ← FlowKit + metrics + state/intent review

Repair
  ← custom earliest-responsible-layer engine

Post
  ← non-destructive timeline + optional NLE integration
```

Đây là bản thiết kế nên dùng làm **frozen architecture baseline** trước khi chia task code.

---

**END — MASTER STUDIO OPTIMAL HYBRID ARCHITECTURE V1 FROZEN**
