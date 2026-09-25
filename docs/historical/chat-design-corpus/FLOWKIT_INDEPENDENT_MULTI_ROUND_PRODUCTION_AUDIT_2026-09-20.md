# FLOWKIT — INDEPENDENT MULTI-ROUND PRODUCTION AUDIT

**Repository:** `crisng95/flowkit`  
**Repository URL:** https://github.com/crisng95/flowkit  
**Pinned commit audited:** `d7977fd51b87d4da2a25a05b896f5cdac064e030`  
**Commit date:** 2026-09-20  
**Audit purpose:** Kiểm tra bằng chứng thật trong source code, tests, skills/docs và artifact công khai để xác định chính xác FlowKit mạnh ở đâu, yếu ở đâu, và phần nào chỉ là claim/documentation chứ chưa đủ bằng chứng runtime độc lập.

---

# 0. KẾT LUẬN ĐẦU TIÊN

Sau nhiều vòng phản biện độc lập, kết luận cần khóa là:

> **FlowKit thực sự mạnh ở `ENTITY / REFERENCE / CONTINUITY / EXECUTION ORCHESTRATION`.**
>
> Đây không phải nhận xét “điền cho có”. Có code path thật, database fields thật, request flow thật và một phần có unit/integration-style tests chứng minh.

Tuy nhiên:

> **Không có đủ bằng chứng để nói FlowKit là một “Enterprise AI Film Studio hoàn chỉnh”, cũng không có đủ bằng chứng độc lập để khẳng định nó giữ consistency tuyệt đối cho 200–300 ảnh.**

README của repo đưa ra artifact của một project 50 scene và một story arc 25 scene. Đây là **bằng chứng do chính repo công bố**, đáng tham khảo nhưng không tương đương với một benchmark độc lập đã chạy lại.

FlowKit không thể hiện một subsystem hoàn chỉnh cho:

- story architecture sâu;
- beat sheet như first-class object;
- shot như first-class production object;
- cinematography decision engine dựa trên narrative intent;
- canonical 8-layer shot compiler;
- static-image QA chuyên biệt;
- state engine chi tiết cho wardrobe/injury/weather/prop progression;
- layer-targeted repair engine.

Do đó, cách mô tả chính xác nhất là:

```text
FLOWKIT
= production-oriented visual generation orchestrator
  có reference locking + continuity graph + batch execution + video QA

KHÔNG PHẢI
= full story/directing/cinematography intelligence engine
```

---

# 1. QUY TẮC CHẤM BẰNG CHỨNG

Để tránh kết luận cảm tính, audit này dùng 4 cấp bằng chứng:

| Cấp | Ý nghĩa |
|---|---|
| **A — Code + Test** | Có implementation thật và có test trực tiếp hoặc test tích hợp tương ứng |
| **B — Code** | Có implementation thật trong source, nhưng chưa thấy test đủ mạnh cho claim |
| **C — Repo Artifact / Docs** | Repo tự công bố workflow/output/screenshot; có giá trị nhưng chưa phải kiểm chứng độc lập |
| **D — Chưa chứng minh** | Không tìm thấy implementation/schema/test đủ để xác nhận claim |

Các từ **“Mạnh/Rất mạnh”** trong báo cáo chỉ được dùng khi có ít nhất bằng chứng **A hoặc B**.  
Không dùng screenshot đẹp làm căn cứ duy nhất để kết luận kiến trúc mạnh.

---

# 2. VÒNG PHẢN BIỆN 01 — PROJECT VISUAL LOCK CÓ THẬT KHÔNG?

## Claim cần kiểm

“FlowKit khóa visual style ở cấp project, không để mỗi scene tự chọn style lại.”

## Bằng chứng source

File:

- `agent/materials.py`
- `agent/api/scenes.py`
- `agent/api/projects.py`

Material registry có các field riêng:

```text
style_instruction
negative_prompt
scene_prefix
lighting
```

Project lưu `material`.

Khi tạo scene, `agent/api/scenes.py` đọc:

```text
scene.video_id
→ video.project_id
→ project.material
→ material.scene_prefix
```

sau đó prepend `scene_prefix` vào `body.prompt` nếu prompt chưa có prefix đó.

Đây là implementation thật, không chỉ nằm trong tài liệu.

Pinned source:

- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/materials.py
- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/api/scenes.py

## Phản biện

Điểm mạnh:

- style baseline được centralized;
- scene writer không cần tự nhớ lặp style ở từng scene;
- thay đổi material ở project có semantics rõ.

Điểm yếu:

`scene_prefix` được prepend vào `prompt` tại lúc create scene. Nhưng execution dùng:

```text
image_prompt OR prompt
```

nên một `image_prompt` tùy chỉnh có thể đi vòng qua prompt đã được material-prefix.

Nghĩa là Visual Lock **có thật nhưng chưa tuyệt đối bất biến**.

## Verdict

**MẠNH — Evidence B**

Không nâng lên “rất mạnh” vì override path chưa được compiler hóa thành một pipeline bắt buộc.

---

# 3. VÒNG PHẢN BIỆN 02 — ENTITY EXTRACTION CÓ PHẢI CHỈ LÀ TÊN GỌI?

## Claim cần kiểm

“FlowKit tách character/location/asset thành entity để tái sử dụng xuyên scene.”

## Bằng chứng source

`agent/api/projects.py` có `COMPOSITION_GUIDELINES` cho nhiều loại entity:

- `character`
- `location`
- `creature`
- `visual_asset`
- `generic_troop`
- `faction`

`_build_character_profile(...)` không chỉ lưu tên. Nó build:

```text
description
image_prompt
```

và chọn composition khác nhau tùy entity type.

Ví dụ logic:

- character → full body, head-to-toe, front-facing, neutral background;
- location → establishing shot, full environment, depth/spatial layout;
- visual_asset → complete form, materials, surface detail.

DB schema cũng cho character/entity các field:

```text
name
slug
entity_type
description
image_prompt
reference_image_url
media_id
```

Nguồn:

- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/api/projects.py
- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/db/crud.py

## Phản biện

Điểm mạnh:

- entity là dữ liệu persisted, không phải chỉ là từ khóa prompt;
- entity có identity riêng và media ID riêng;
- type-specific composition giúp reference generation có cấu trúc.

Điểm yếu:

- naming `character_names` ở scene gây nhập nhằng vì thực tế có thể chứa location/asset;
- chưa phải `WORLD_BIBLE` sâu với relationship graph, spatial topology, costume variants, prop lifecycle;
- reference entity vẫn thiên về single reference image.

## Verdict

**MẠNH — Evidence B**

---

# 4. VÒNG PHẢN BIỆN 03 — CANONICAL REFERENCE CÓ ĐƯỢC DÙNG THẬT Ở GENERATION KHÔNG?

## Claim cần kiểm

“Reference không chỉ tạo ra để xem; media_id được resolve và truyền thật vào image generation.”

## Bằng chứng implementation

`agent/sdk/services/operations.py::generate_scene_image()`:

1. đọc `scene.character_names`;
2. parse danh sách;
3. lấy toàn bộ project characters/entities;
4. match slug hoặc name;
5. lấy `media_id`;
6. nếu entity được yêu cầu nhưng thiếu `media_id`, trả lỗi;
7. truyền `character_media_ids` sang `client.generate_images(...)`.

Code có logic fail rõ:

```text
Waiting for reference images: ...
```

và call cuối truyền:

```text
character_media_ids=char_media_ids
```

Nguồn:

https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/sdk/services/operations.py

## Bằng chứng test trực tiếp

`tests/unit/test_operations.py` có test:

```text
test_resolves_character_media_ids_from_project
```

Test dựng project characters:

```text
Hero   → media UUID A
Castle → media UUID B
Other  → media UUID C
```

Scene chỉ request `Hero` + `Castle`.

Test assert rằng:

- A có trong `character_media_ids`;
- B có trong `character_media_ids`;
- C không được gửi.

Có thêm test:

```text
test_returns_error_when_character_refs_missing_media_id
```

xác nhận entity referenced nhưng chưa có media ID sẽ làm generation trả error.

Nguồn:

https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/tests/unit/test_operations.py

## Vì sao đây là bằng chứng quan trọng?

Đây không phải:

```text
"hãy giữ nhân vật nhất quán"
```

viết trong prompt.

Đây là:

```text
Scene entity name
→ resolve canonical entity
→ resolve persisted media_id
→ attach real reference inputs
→ generation call
```

Tức identity conditioning có đường dữ liệu thật.

## Verdict

**RẤT MẠNH — Evidence A**

Đây là một trong các phần mạnh nhất repo.

---

# 5. VÒNG PHẢN BIỆN 04 — REFERENCE GENERATION CÓ PIPELINE RIÊNG KHÔNG?

## Claim cần kiểm

“Reference được tạo trước scene và được persisted để làm source of truth.”

## Bằng chứng implementation/test

`OperationService.generate_reference_image()` có path:

```text
entity.image_prompt
→ generate_images
→ extract generated URL/media
→ upload/extract media_id
→ persist media_id vào entity
```

`tests/unit/test_operations.py` có:

- `test_normal_path_generates_and_uploads`
- `test_fast_path_upload_only_when_url_exists`
- `test_fast_path_falls_back_to_uuid_from_url`

Điều này chứng minh code không chỉ mô tả quy trình; có test cho cả normal path và recovery path.

`skills/fk-gen-images.md` còn quy định scene generation phải abort nếu reference entity chưa có `media_id`.

Nguồn:

- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/tests/unit/test_operations.py
- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/skills/fk-gen-images.md

## Phản biện

Mạnh ở pipeline identity anchor.

Chưa mạnh ở reference bible cấp studio vì chưa thấy schema chính thức cho:

```text
front
left 3/4
right 3/4
profile
face close-up
eyes
hands
expression set
wardrobe variants
```

## Verdict

**RẤT MẠNH ở “single canonical reference pipeline” — Evidence A**  
**CHƯA phải advanced multi-view reference bible — Evidence D**

---

# 6. VÒNG PHẢN BIỆN 05 — SCENE DATABASE CÓ THẬT SỰ STRUCTURED?

## Bằng chứng

`agent/models/scene.py::SceneCreate` có:

```text
video_id
display_order
prompt
image_prompt
video_prompt
transition_prompt
character_names
parent_scene_id
chain_type
source
```

DB `scene` lưu các trường tương ứng cùng trạng thái output:

```text
vertical_image_media_id
horizontal_image_media_id
vertical_video_media_id
horizontal_video_media_id
...
```

Nguồn:

- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/models/scene.py
- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/db/crud.py

## Phản biện

Đây là production-friendly hơn lưu prompt vào file text rời rạc.

Nhưng `Scene` đang gánh quá nhiều trách nhiệm:

```text
narrative unit
generation unit
static prompt holder
motion prompt holder
continuity node
output state holder
```

Repo chưa có first-class:

```text
Beat
Shot
ShotSpec
SequenceState
```

Vì vậy scene-centric design thuận tiện cho app nhưng giới hạn nếu muốn đi sâu ngôn ngữ phim.

## Verdict

**MẠNH về production data model — Evidence B**  
**CHƯA sâu về film grammar hierarchy — Evidence D cho Beat/Shot objects**

---

# 7. VÒNG PHẢN BIỆN 06 — ROOT / CONTINUATION CÓ PHẢI CHỈ LÀ DOC?

## Claim cần kiểm

“Continuation dùng parent image thật làm base image.”

## Bằng chứng source

`OperationService.edit_scene_image()`:

- ưu tiên `source_media_id` nếu truyền vào;
- nếu không có và scene có `parent_scene_id`, load parent;
- lấy `parent.<orientation>_image_media_id`;
- nếu vẫn không có thì mới fallback scene image hiện tại;
- gọi `client.edit_image(...)`.

Docstring còn mô tả input ordering:

```text
[base_image, char_A, char_B, ...]
```

Tức:

```text
parent generated image
+
canonical entity refs
+
child prompt
→ edit image
```

Nguồn:

https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/sdk/services/operations.py

## Bằng chứng test

`tests/unit/test_operations.py` test:

- edit calls source media ID đúng;
- fallback scene image media ID;
- không có source thì fail.

Hiện phần test được đọc chưa cho thấy một test riêng assert **parent_scene_id → parent media ID**, vì vậy parent lookup implementation được xếp Evidence B; base-image edit path nói chung có Evidence A.

## Phản biện

Đây là kiến trúc tốt vì continuity được giữ bằng **visual state inheritance**, không chỉ bằng câu “same character”.

Nhưng `_build_continuation_prompt` hiện prepend một instruction rất mạnh theo hướng:

```text
different moment
new angle
new composition
change environment/setup
```

Đây có thể quá mạnh cho các continuation tinh tế như:

- micro-expression change;
- bàn tay nhấc một vật;
- nhân vật chỉ quay đầu nhẹ;
- camera giữ trục để preserve spatial continuity.

Một production-grade system nên có:

```text
continuity_mode:
  PRESERVE
  EVOLVE
  TRANSFORM
```

hoặc `delta_strength`.

## Verdict

**RẤT MẠNH về ý tưởng parent-state inheritance — Evidence A/B**  
**CHƯA tinh chỉnh đủ continuation semantics — Evidence B**

---

# 8. VÒNG PHẢN BIỆN 07 — DEPENDENCY WAVES CÓ THẬT HAY CHỈ NÓI CHO HAY?

## Bằng chứng

`skills/fk-gen-images.md` định nghĩa rõ:

```text
Wave 1:
ROOT / no parent → GENERATE_IMAGE

Wave 2:
CONTINUATION whose parent in Wave 1 → EDIT_IMAGE

Wave 3:
CONTINUATION whose parent in Wave 2 → EDIT_IMAGE

Wave N:
parent in Wave N-1
```

Nó yêu cầu build wave map bằng cách walk `parent_scene_id`.

Scenes cùng wave được coi độc lập và có thể chạy parallel.

Repo còn quy định:

```text
Never submit EDIT_IMAGE before parent image COMPLETED.
```

và regen parent sẽ invalidate children.

Nguồn:

https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/skills/fk-gen-images.md

## Phản biện

Đây là một điểm production thật sự tốt:

```text
graph dependency
+
parallel independent nodes
+
sequential dependent nodes
```

Nó tốt hơn loop scene 1→300 tuyến tính.

Tuy nhiên bằng chứng ở đây chủ yếu là skill/orchestration contract. Audit hiện tại chưa chạy live một chain lớn để xác nhận scheduler thực tế ở scale 200–300.

## Verdict

**MẠNH — Evidence B/C**

Không được phép đổi câu này thành:

> “Đã chứng minh 300 scene chạy ổn.”

Bằng chứng hiện tại chưa đủ cho claim đó.

---

# 9. VÒNG PHẢN BIỆN 08 — REGEN CASCADE CÓ GIẢI QUYẾT STALE CONTINUITY?

## Bằng chứng

`fk-gen-images.md` ghi rõ:

```text
REGENERATE_IMAGE
→ clears downstream video/upscale for scene

regenerating parent CONTINUATION
→ invalidates children
→ re-run to re-edit descendants
```

Đây là đúng tư duy dependency invalidation:

```text
parent changed
→ child visual state no longer trustworthy
```

## Phản biện

Điều này cho thấy tác giả hiểu consistency là **dependency problem**, không chỉ prompt problem.

Tuy vậy audit chưa tìm thấy một automated lineage/version graph kiểu:

```text
artifact_hash
source_generation_id
reference_version
parent_version
prompt_compiler_version
```

Nên invalidation có logic nhưng chưa phải full provenance system.

## Verdict

**MẠNH về dependency semantics — Evidence B**  
**CHƯA enterprise provenance — Evidence D**

---

# 10. VÒNG PHẢN BIỆN 09 — CINEMATOGRAPHY: NGHỀ HAY TỪ ĐIỂN?

## Bằng chứng có thật

`skills/fk-camera-guide.md` có vocabulary khá rộng:

### Shot size

- EWS
- WS
- MS
- CU
- ECU
- Macro

### Movement

- dolly
- pan
- tilt
- tracking
- crane
- gimbal
- handheld
- whip pan
- arc
- POV
- static
- rack focus

### Angle

- eye-level
- low-angle
- high-angle
- bird's-eye
- Dutch
- OTS
- worm's-eye

### Lens/focus

- 18mm
- 35mm
- 50mm
- 85mm
- anamorphic
- shallow DOF
- deep focus
- rack focus

### Lighting

- golden hour
- high-key
- low-key
- noir
- backlight
- soft natural
- motivated
- practicals
- tungsten
- fluorescent
- neon
- candlelight
- volumetric
- chiaroscuro
- blue hour

Nó còn map một phần technique → effect/mood:

```text
low angle → dominance
high angle → vulnerability
Dutch → tension
golden hour → nostalgia/romance
blue hour → melancholy/mystery
shallow DOF → subject isolation
```

Nguồn:

https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/skills/fk-camera-guide.md

## Phản biện quan trọng

Đây là **cinematography dictionary + usage heuristics**, chưa phải một **cinematography decision engine**.

Không thấy first-class schema kiểu:

```text
narrative_function
emotional_target
audience_distance
information_priority
power_relation
rhythm_curve
shot_function
```

được transform deterministically thành:

```text
shot_size
angle
lens
movement
lighting
duration
cut_behavior
```

Nghĩa là FlowKit biết:

```text
"low angle có thể gợi dominance"
```

nhưng chưa có hệ thống chính thức trả lời:

```text
"Beat này tại sao phải dùng low angle thay vì eye-level?"
```

## Verdict

**KHÁ MẠNH về vocabulary — Evidence B**  
**TRUNG BÌNH/KHÁ về cinematic decision logic — phần lớn phụ thuộc LLM reasoning**  
**CHƯA đạt narrative cinematography engine — Evidence D**

---

# 11. VÒNG PHẢN BIỆN 10 — STORY / BEAT / SCENE / SHOT

## Điều repo làm thật

README mô tả pipeline:

```text
story
→ entities
→ reference images
→ scene images
→ 8s clips
→ narration
→ concat
```

`fk-create-project.md` yêu cầu đầu vào:

- project name;
- story / brief plot summary;
- material;
- characters;
- locations;
- visual assets;
- number of scenes;
- orientation.

Sau đó system tạo scenes.

## Điều không tìm thấy

Search code/default branch không cho thấy:

```text
Beat model
BeatSheet model
NarrativeBeat schema
ShotSpec model
```

“Shot” xuất hiện trong camera guide và prompt prose, nhưng không phải first-class DB object tương đương Scene.

Do đó hierarchy thật của FlowKit gần:

```text
STORY
→ ENTITY
→ SCENE / generation unit
→ IMAGE
→ VIDEO
```

hơn:

```text
STORY
→ SEQUENCE
→ SCENE
→ BEAT
→ SHOT
→ SHOT SPEC
→ PROMPT COMPILER
```

## Verdict

**MẠNH từ Scene/Entity trở xuống**  
**KHÔNG đủ bằng chứng để gọi Beat/Shot architecture là mạnh**

---

# 12. VÒNG PHẢN BIỆN 11 — STATIC PROMPT COMPILER CÓ THẬT KHÔNG?

## Hiện trạng

FlowKit có prompt formula/guideline.

`fk-create-project.md` yêu cầu scene prompt mô tả:

```text
action
environment
mood
camera/composition
```

Và có formula gần:

```text
Subject
+ action
+ location
+ specific visual detail
+ camera/composition
```

Project material cung cấp style prefix.

Entity appearance đi bằng reference.

Đây là một architecture hợp lý.

## Nhưng

Không thấy một canonical object:

```text
ShotSpec {
  subject_refs,
  state,
  wardrobe,
  action,
  emotion,
  environment,
  time,
  atmosphere,
  camera,
  lens,
  lighting,
  continuity,
  must_preserve,
  must_change
}
```

rồi compiler:

```text
ShotSpec
→ normalize
→ validate
→ resolve refs
→ provider-specific compile
→ final prompt
```

Hiện prompt vẫn là prose field.

## Một code gap đáng chú ý

Execution:

```text
prompt = image_prompt OR prompt
```

Nếu `image_prompt` có giá trị, nó có thể bypass:

- `prompt` đã material-prefixed;
- automatic continuation transformation, vì code chỉ auto-build continuation khi **không có `image_prompt`**.

Đây là dấu hiệu chưa có một canonical prompt compilation path duy nhất.

## Verdict

**KHÁ về prompt conventions**  
**CHƯA đạt canonical layer compiler — Evidence B/D**

---

# 13. VÒNG PHẢN BIỆN 12 — VIDEO QA CÓ THẬT KHÔNG?

## Bằng chứng source

`agent/services/video_reviewer.py` có weighted dimensions:

```text
character_consistency  0.25
prompt_adherence       0.20
motion_quality         0.20
visual_fidelity        0.15
temporal_coherence     0.10
composition            0.10
```

Có verdict logic và `_fix_guide(...)`.

Có các pattern:

- drift;
- wrong character;
- count mismatch;
- logo/text;
- wrong role/action;
- reverse motion.

Nguồn:

https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/services/video_reviewer.py

## Bằng chứng test tốt

`tests/unit/test_video_reviewer.py` không chỉ mock tất cả.

File tự mô tả integration-style tests cho:

```text
real ffmpeg frame extraction
REVIEW_MAX_FRAMES cap
contact-sheet chunking
```

Nó tạo synthetic MP4 thật bằng ffmpeg rồi verify:

- frame count;
- sheet count;
- downsampling;
- no-waste layouts;
- malformed analysis không được biến thành score giả hợp lệ.

Đây là bằng chứng đáng kể.

Nguồn:

https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/tests/unit/test_video_reviewer.py

## Verdict

**MẠNH — Evidence A**

Video QA là một trong các phần có bằng chứng kỹ thuật tốt hơn mức “documentation claim”.

---

# 14. VÒNG PHẢN BIỆN 13 — REPAIR CÓ THẬT HAY CHỈ RETRY?

## Bằng chứng

`video_reviewer.py::_fix_guide()` có mapping:

```text
drift
→ simplify motion / steadier camera

wrong character
→ strengthen character differentiation

wrong count
→ make one character dominant

logo
→ no logo / no text constraint

wrong action
→ clarify role/action

composition
→ modify camera directions
```

`skills/fk-pipeline.md` còn mô tả:

```text
review
→ select scenes below threshold
→ improve video_prompt based on errors/fix_guide
→ regen
→ review again
```

và max two fix/regen cycles.

Nguồn:

- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/services/video_reviewer.py
- https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/skills/fk-pipeline.md

## Phản biện

Có repair loop thật về mặt orchestration.

Nhưng repair vẫn gần:

```text
error
→ heuristic prompt rewrite
→ regenerate
```

chưa phải:

```text
error
→ identify failed semantic layer
→ freeze all passing layers
→ patch only failed layer
→ recompile deterministic prompt
→ verify repaired dimension
```

## Verdict

**KHÁ — Evidence B**

Gọi là “repair loop” được.  
Gọi là “advanced layer-targeted repair engine” thì chưa đủ bằng chứng.

---

# 15. VÒNG PHẢN BIỆN 14 — STATIC IMAGE QA CÓ TƯƠNG ĐƯƠNG VIDEO QA KHÔNG?

## Kết quả tìm kiếm

Có video reviewer rõ.

Có review board và image generation status.

Có thể regen scene image khi video review cho thấy nguồn ảnh kém.

Nhưng audit không tìm thấy subsystem tương đương:

```text
StaticImageReviewer
```

với dimensions chính thức:

```text
identity
wardrobe
prop correctness
location correctness
camera/composition
lighting
anatomy
artifact
continuity vs parent
```

trước khi đưa ảnh sang video.

## Hệ quả

Một scene image có thể:

```text
status = COMPLETED
media_id = valid
```

nhưng vẫn sai:

- tay;
- quần áo;
- prop;
- camera;
- emotional expression;
- layout;
- continuity.

Pipeline chưa chứng minh có một gate tự động mạnh để chặn các lỗi đó trước video generation.

## Verdict

**ĐÂY LÀ GAP LỚN — Evidence D cho dedicated static QA**

---

# 16. VÒNG PHẢN BIỆN 15 — BATCH / PRODUCTION EXECUTION CÓ NỀN THẬT KHÔNG?

## Bằng chứng

Repo có:

- FastAPI API;
- SQLite persistence;
- request table;
- queue worker;
- statuses;
- retry paths;
- batch request workflow;
- dependency waves;
- skip completed;
- stage routing;
- resumability;
- image/video/upscale/TTS/concat stages.

README mô tả dashboard theo dõi throughput và stage status.

`fk-pipeline.md` đọc state hiện tại rồi chọn stage cần chạy, thay vì chạy lại tất cả.

## Đây là điểm quan trọng

Production-scale không chỉ là “generate được ảnh”.

Nó cần:

```text
persist state
resume
skip completed
retry failed
dependency ordering
batch
status
artifact IDs
```

FlowKit có khá nhiều trong số này.

## Verdict

**RẤT MẠNH ở orchestration so với một prompt-only repo — Evidence B/C**

Không đồng nghĩa với “enterprise distributed orchestration”. Đây vẫn là local-oriented FastAPI/SQLite/worker architecture.

---

# 17. VÒNG PHẢN BIỆN 16 — CÓ BẰNG CHỨNG OUTPUT THẬT KHÔNG?

## Repo tự công bố

README chứa:

### Visual consistency example

Repo trình bày:

- Doctor character qua 4 scene;
- Defector character qua ICU/hospital/interview/Seoul;
- ghi chú rằng các frame thuộc một **50-scene project**.

### Story arc example

Repo trình bày một **25-scene** F-15E Rescue story arc.

### Extension screenshot

README ghi screenshot có:

```text
614 total requests
328 success
```

### Live API claim

README nói migrated Flow API được verified end-to-end cho một số mode.

Nguồn:

https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/README.md

## Phản biện bắt buộc

Đây là:

```text
repo-provided evidence
```

không phải:

```text
independent benchmark performed in this audit
```

Audit này không được phép biến claim:

```text
50-scene project shown in README
```

thành:

```text
đã kiểm chứng độc lập rằng hệ thống luôn giữ 50/200/300 ảnh giống nhau
```

Hai câu hoàn toàn khác nhau.

## Verdict

**Có bằng chứng artifact C**  
**Không có benchmark độc lập cho 200–300 ảnh — D**

---

# 18. VÒNG PHẢN BIỆN 17 — TEST EVIDENCE CÓ PHẢI “PASS CHO CÓ”?

## Bằng chứng test đã đọc

### `test_operations.py`

Có test trực tiếp cho:

- prompt/aspect args;
- resolve entity media IDs;
- block missing refs;
- edit source image;
- missing source error;
- reference generation;
- recovery when URL exists but media_id missing;
- queue request creation;
- tránh resubmit video operation đã submit.

Điểm cuối đáng chú ý: test comment nói resubmit nhầm có thể tốn tiền, nên test đảm bảo retry sẽ repoll operation cũ.

### `test_video_reviewer.py`

Có synthetic MP4 thật + ffmpeg thật cho contact-sheet pipeline.

Nó còn có test chống “fabricated plausible score” khi reviewer trả malformed data.

Đây là test có ý nghĩa production, không chỉ assert `True`.

## Tuy nhiên

Recent commit message ngay trước HEAD nói:

```text
352 -> 365 tests
```

Audit này **không tự chạy toàn bộ 365 test**.

GitHub connector ở HEAD cũng không trả workflow run/combined status nào cho commit được audit.

Do đó report không được ghi:

```text
"365/365 PASS"
```

như một bằng chứng độc lập.

Điều được phép ghi:

```text
"Commit message báo 365 tests; audit đã đọc một số tests có chất lượng tốt.
Chưa independently execute full test suite trong audit này."
```

## Verdict

**Có test thật và một số test chất lượng tốt — Evidence A cho các code path đã inspect**  
**Full-suite green tại HEAD: CHƯA XÁC MINH**

---

# 19. BẢNG VERDICT CUỐI — KHÔNG TÔ HỒNG

| Capability | Verdict | Evidence | Lý do |
|---|---:|---:|---|
| Project material/style lock | Mạnh | B | Có registry + auto prefix thật |
| Entity data model | Mạnh | B | Persisted entity type/profile/media |
| Canonical reference generation | Rất mạnh | A | Có implementation + tests |
| Reference reuse in scenes | Rất mạnh | A | Resolve media IDs + block missing + tests |
| Character/entity consistency architecture | Rất mạnh | A/C | Reference input path thật + repo artifacts |
| ROOT/CONTINUATION concept | Rất mạnh | A/B | Base-image edit + parent logic |
| Dependency waves | Mạnh | B/C | Explicit graph/wave orchestration |
| Regen invalidation | Mạnh | B | Parent/child dependency semantics |
| Batch/resume/queue orchestration | Rất mạnh | B/C | API/DB/worker/stage routing |
| Cinematography vocabulary | Mạnh | B | Guide rộng, technique→effect mapping |
| Cinematography decision intelligence | Chưa mạnh | D/B | Không có narrative-intent decision schema |
| Story engine | Cơ bản | C | Chủ yếu nhận story/brief rồi visualise |
| Beat sheet engine | Chưa có subsystem rõ | D | Không thấy first-class Beat |
| Shot hierarchy | Chưa có subsystem rõ | D | Shot nằm trong prose/docs |
| 8-layer shot compiler | Không có | D | Không có canonical structured compiler |
| Static prompt conventions | Khá | B | Có formula/rules |
| Static image QA | Yếu/gap | D | Không thấy dedicated structured reviewer |
| Video QA | Mạnh | A | Reviewer + real ffmpeg integration tests |
| Repair loop | Khá | B | Error→guide→regen, nhưng chưa layer-targeted |
| 50-scene consistency proof | Có repo artifact | C | README trình bày |
| 200–300 image consistency proof | Chưa chứng minh | D | Không có independent benchmark |
| Enterprise AI-native studio | Chưa | — | Thiếu story/beat/shot/state/static QA/repair/provenance |

---

# 20. VẬY “FLOWKIT RẤT MẠNH” CỤ THỂ Ở ĐÂU?

Nếu chỉ được giữ lại bốn claim “rất mạnh”, audit giữ:

## 20.1 Canonical reference path

```text
Entity
→ Reference prompt
→ Generated reference
→ media_id
→ Persist
→ Reuse
```

Có code + tests.

---

## 20.2 Reference conditioning at scene execution

```text
Scene character_names
→ entity lookup
→ media_id[]
→ generate_images(character_media_ids=...)
```

Có code + test xác nhận entity đúng được gửi và entity không referenced không được gửi.

---

## 20.3 Visual-state continuity

```text
ROOT image
→ child CONTINUATION
→ parent image as BASE_IMAGE
→ canonical references
→ EDIT_IMAGE
```

Đây là tư duy mạnh hơn việc generate từng frame từ text độc lập.

---

## 20.4 Production orchestration

```text
persisted request state
+ queue
+ retries
+ dependency ordering
+ waves
+ skip completed
+ resume
+ QA/review stage
```

Đây là lý do repo có giá trị lớn hơn một collection prompt.

---

# 21. PHẦN NÀO KHÔNG NÊN COPY NGUYÊN?

## 21.1 Không copy `Scene = mọi thứ`

Nên tách:

```text
SEQUENCE
→ SCENE
→ BEAT
→ SHOT
```

và chỉ `SHOT` là generation unit.

---

## 21.2 Không dùng prose prompt làm source of truth

Nên có:

```text
SHOT_SPEC
```

là source of truth, prompt chỉ là compiled artifact.

---

## 21.3 Không cho `image_prompt` bypass compiler

Nên:

```text
PROJECT LOCK
+
ENTITY LOCK
+
SEQUENCE STATE
+
SHOT SPEC
+
OPTIONAL OVERRIDE
→ CANONICAL COMPILER
```

Không field nào được quyền vô tình bỏ style/continuity lock.

---

## 21.4 Không coi cinematography dictionary là cinematography intelligence

Nên thêm:

```text
NARRATIVE FUNCTION
↓
EMOTIONAL TARGET
↓
AUDIENCE INFORMATION
↓
VISUAL STRATEGY
↓
CINEMATOGRAPHY DECISION
↓
SHOT SPEC
```

---

## 21.5 Không bỏ Static QA

Phải có:

```text
STATIC GENERATE
↓
STATIC QA
├── identity
├── state/wardrobe
├── prop
├── location
├── camera
├── composition
├── lighting/style
├── anatomy/artifact
└── parent continuity
↓
PASS / TARGETED REPAIR
```

---

# 22. KIẾN TRÚC NÊN LẤY TỪ FLOWKIT + NÂNG CẤP

Kiến trúc hợp lý hơn cho một AI-native production studio:

```text
IDEA / TOPIC
↓
STORY ENGINE
↓
ROUGH SCRIPT
↓
SCRIPT LOCK
↓
SEQUENCE PLAN
↓
SCENE PLAN
↓
BEAT PLAN
↓
SHOT PLAN
↓
────────────────────────────────────────────
WORLD / REFERENCE SYSTEM
├── PROJECT BIBLE
├── ENTITY REGISTRY
│   ├── CHARACTER
│   ├── LOCATION
│   ├── PROP
│   └── VISUAL ASSET
└── CANONICAL REFERENCES
↓
────────────────────────────────────────────
STATE ENGINE
├── identity state
├── wardrobe state
├── prop state
├── location state
├── weather/time state
├── injury/dirt/wetness state
└── sequence continuity state
↓
────────────────────────────────────────────
SHOT INTELLIGENCE
├── narrative function
├── emotional target
├── audience attention
├── information priority
└── cinematography decision
↓
8-LAYER SHOT SPEC
↓
REFERENCE RESOLVER
↓
STATIC PROMPT COMPILER
↓
PROVIDER ADAPTER
↓
STATIC IMAGE
↓
STATIC QA
↓
TARGETED REPAIR
↓
MOTION PROMPT COMPILER
↓
VIDEO
↓
MOTION QA
↓
SEQUENCE QA
↓
FINAL MASTER
```

Continuity không phải một bước cuối. Nó chạy xuyên suốt:

```text
Canonical reference
+
Sequence state
+
Parent visual state
+
Current shot delta
```

---

# 23. 8-LAYER NÊN NẰM Ở ĐÂU?

Không đặt 8-Layer ở Story.

Không đặt 8-Layer ở Beat.

Không đặt 8-Layer ở toàn Scene.

Nên đặt ở **SHOT SPEC**:

```text
L1 SUBJECT / IDENTITY REFERENCES
L2 STATE / WARDROBE / PROPS
L3 ACTION / EMOTION
L4 ENVIRONMENT
L5 TIME / ATMOSPHERE
L6 CAMERA / COMPOSITION
L7 LIGHTING / STYLE
L8 CONTINUITY / MUST-PRESERVE / MUST-CHANGE
```

Sau đó:

```text
SHOT SPEC
├── STATIC COMPILER
└── MOTION COMPILER
```

Static = trạng thái keyframe.

Motion = delta theo thời gian.

---

# 24. CINEMATOGRAPHY NÊN ĐƯỢC NÂNG NHƯ THẾ NÀO?

FlowKit hiện tại phần lớn có:

```text
Technique
→ effect / mood association
```

Hệ mạnh hơn phải là:

```text
Beat purpose
↓
What should audience feel?
↓
What should audience notice?
↓
How close should audience feel to character?
↓
What must change from previous shot?
↓
Choose visual grammar
↓
camera/lens/movement/light/composition
```

Ví dụ:

```text
BEAT:
Nhân vật lần đầu nhận ra giọng mẹ.

NARRATIVE FUNCTION:
Recognition.

EMOTIONAL TARGET:
Disbelief before grief.

AUDIENCE INFORMATION ORDER:
1. tape starts
2. voice heard
3. character recognizes
4. viewer waits
5. reaction lands

CINEMATOGRAPHY STRATEGY:
Do not begin close.
Hold medium/static first.
Begin slow push only after recognition.
End in close-up.
Do not cut reaction too early.
```

Đây mới là `cinematography decision`, không phải chọn “85mm + bokeh” vì đẹp.

---

# 25. ĐIỀU QUAN TRỌNG NHẤT VỀ CONSISTENCY 200–300 ẢNH

Không được hiểu:

```text
FlowKit có prompt tốt
→ 300 ảnh giống nhau
```

Đúng hơn là:

```text
canonical references
+
persistent project style
+
parent visual inheritance
+
dependency graph
+
re-anchor roots
+
batch state management
→ giảm drift đáng kể
```

Nhưng:

> **Source code không chứng minh consistency tuyệt đối ở scale 200–300.**

Muốn đưa claim đó lên Evidence A, cần benchmark thực tế:

```text
N = 300 generated images

Measure:
- face/identity similarity
- wardrobe accuracy
- prop identity
- location continuity
- state continuity
- camera adherence
- style consistency
- failure/regeneration rate
- drift by chain depth
- drift after ROOT re-anchor
```

Không có benchmark đó thì không được viết “300 ảnh proven”.

---

# 26. BENCHMARK NÊN CHẠY NẾU MUỐN CHỨNG MINH THẬT

Một test production đúng nên gồm ít nhất:

```text
3 stories độc lập
× 100 shots/story
= 300 shots
```

Mỗi story có:

```text
3–5 characters
3–6 recurring locations
5–10 recurring props/assets
multiple wardrobe states
multiple time-of-day states
ROOT + CONTINUATION chains
location changes
time skips
emotion changes
camera variation
```

Thu metric:

```text
Identity pass rate
State pass rate
Prop pass rate
Location pass rate
Continuity pass rate
Static QA first-pass rate
Average regen count
Chain-depth drift
Cost per accepted shot
Median latency per accepted shot
```

Chỉ khi đó mới được tuyên bố:

```text
"production-proven at 300-shot scale"
```

---

# 27. FINAL VERDICT

## Điều audit xác nhận thật

FlowKit **không chỉ là một repo prompt**.

Nó có architecture thật cho:

```text
Project material
Entity registry
Reference generation
Reference media IDs
Scene persistence
Reference resolution
Base-image editing
ROOT/CONTINUATION
Dependency waves
Queue/request state
Retry/resume
Video QA
Repair/regenerate loop
```

Một số phần quan trọng có **unit/integration-style tests thật**.

## Điều audit không xác nhận

Không có đủ bằng chứng để nói FlowKit đã hoàn thiện:

```text
Story Engine
Beat Sheet Engine
Shot Engine
Cinematography Decision Engine
8-Layer Compiler
Static QA Engine
Layer-targeted Repair Engine
Enterprise Provenance
200–300-shot benchmark
```

## Câu kết luận nên dùng trong thiết kế

> **FlowKit đáng lấy làm reference architecture cho `REFERENCE + CONTINUITY + EXECUTION`, không nên lấy làm full blueprint cho toàn bộ AI Film Studio.**

Nếu xây hệ production cao hơn, nên:

```text
GIỮ từ FlowKit:
Entity Registry
Canonical Reference
media_id reuse
ROOT / CONTINUATION
Parent Image Inheritance
Dependency Waves
Queue / Resume
Video QA concepts

BỔ SUNG:
Sequence
Beat
Shot
Narrative Intent
Cinematography Decision Engine
8-Layer Shot Spec
State Engine
Static QA
Targeted Repair
Versioned Lineage
```

---

# 28. SOURCE INDEX — PINNED TO AUDITED COMMIT

Để tránh `main` thay đổi làm audit mất dấu, toàn bộ link quan trọng dưới đây pin vào commit:

`d7977fd51b87d4da2a25a05b896f5cdac064e030`

### Core architecture

- `README.md`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/README.md

- `agent/materials.py`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/materials.py

- `agent/api/projects.py`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/api/projects.py

- `agent/api/scenes.py`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/api/scenes.py

- `agent/models/scene.py`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/models/scene.py

- `agent/db/crud.py`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/db/crud.py

### Generation / consistency / continuity

- `agent/sdk/services/operations.py`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/sdk/services/operations.py

- `agent/services/flow_client.py`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/services/flow_client.py

- `skills/fk-gen-refs.md`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/skills/fk-gen-refs.md

- `skills/fk-gen-images.md`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/skills/fk-gen-images.md

- `skills/fk-create-project.md`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/skills/fk-create-project.md

### Cinematography / QA / pipeline

- `skills/fk-camera-guide.md`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/skills/fk-camera-guide.md

- `agent/services/video_reviewer.py`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/agent/services/video_reviewer.py

- `skills/fk-review-video.md`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/skills/fk-review-video.md

- `skills/fk-pipeline.md`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/skills/fk-pipeline.md

### Tests inspected

- `tests/unit/test_operations.py`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/tests/unit/test_operations.py

- `tests/unit/test_video_reviewer.py`  
  https://github.com/crisng95/flowkit/blob/d7977fd51b87d4da2a25a05b896f5cdac064e030/tests/unit/test_video_reviewer.py

---

# 29. AUDIT INTEGRITY NOTE

Audit này cố tình tách ba loại câu:

### Được chứng minh bằng source/test

```text
"reference media IDs được resolve và gửi vào generation"
```

### Được repo tự công bố nhưng chưa chạy lại độc lập

```text
"50-scene project giữ appearance xuyên nhiều setting"
```

### Chưa được chứng minh

```text
"FlowKit giữ consistency tuyệt đối cho 200–300 ảnh"
```

Ba loại này **không được trộn với nhau**.

Đó là nguyên tắc quan trọng nhất để tránh audit “PASS cho có lệ”.

---

**END OF AUDIT**
