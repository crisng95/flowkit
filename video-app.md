# Flow Studio — Thiết kế & Kế hoạch Webapp tạo video

> Webapp tạo video kể chuyện end-to-end dựa trên các API sẵn có của Flow Kit:
> Google Flow (ảnh/video), OmniVoice (TTS), và AI-agent CLI (Claude Code / Antigravity).
> Tài liệu này là **bản thiết kế để duyệt trước khi code**.

Quyết định đã chốt:
- **Frontend:** React + Vite + Tailwind (SPA, build tĩnh, FastAPI serve).
- **Lưu trữ:** SQLite nhúng trong agent (`agent/studio.db`).
- **Phạm vi v1:** Full pipeline — Script → Assets → Storyboard → Shots → **Assemble** (ghép + TTS + overlay + export).

---

## 1. Mục tiêu

Một giao diện web tối, 4 bước (theo `./samples/`), biến một ý tưởng/kịch bản
thành video hoàn chỉnh mà người dùng **không cần gõ lệnh CLI**. AI-agent đóng vai
"bộ não" sinh kịch bản, mô tả khung hình, và prompt; Flow lo sinh ảnh/video;
OmniVoice lo lồng tiếng; ffmpeg lo ghép.

Nguyên tắc giữ nguyên từ Flow Kit:
- Agent vẫn là **relay** tới Google Flow qua extension (cần extension kết nối).
- `media_id` luôn là **UUID**; lưu kèm `primary_media_id` để refresh URL khi hết hạn.
- Mọi thứ chạy **local** (`127.0.0.1`), không lộ ra ngoài.

---

## 2. Luồng UX (map theo screenshot)

Thanh tab trên cùng: **1. Script · 2. Assets · 3. Storyboard · 4. Shots** (+ **5. Assemble** mới).
Ô **Style** (textbox tự do, có preset gợi ý) ở góc phải áp dụng cho toàn project.

### 2.1 Script — `samples/script.png`
- **Ô tạo script từ idea/nội dung (mới):** một panel "Generate Script" gồm:
  - **Idea / Content** (textarea lớn): nhập một ý tưởng ngắn *hoặc* dán nguyên một
    đoạn nội dung dài.
  - **Target duration** (tùy chọn, ô số + đơn vị giây/phút): thời lượng video mong muốn.
  - **☑ Storytelling** (checkbox): bật **chế độ kể chuyện dẫn bằng giọng đọc** (xem §2.6).
  - Nút **Generate** → AI sinh kịch bản screenplay hoàn chỉnh.
- **Logic theo duration:**
  - **Có duration:** AI **nén** (tóm gọn, bỏ chi tiết phụ) hoặc **giãn** (thêm cảnh,
    mô tả, lời thoại) nội dung cho **vừa khít** thời lượng. Backend quy đổi duration →
    **ngân sách shot** (`≈ duration / shot_duration`, mặc định 8s/shot) và **ngân sách
    lời** cho narration (≈ 2.5 từ/giây) để AI căn độ dài.
  - **Không có duration:** AI giữ **đầy đủ** nội dung đã nhập, số scene/shot tự nhiên
    theo nội dung (không nén/giãn).
- **Hiển thị đúng chuẩn screenplay Hollywood** (industry-standard, kiểu Final Draft):
  - Font **Courier** (12pt) đơn cách; canh lề chuẩn ngành.
  - **Scene Heading / Slugline:** `INT./EXT. ĐỊA ĐIỂM - THỜI GIAN` (in hoa).
  - **Action** căn trái cả dòng; **Character** in hoa, thụt giữa; **Parenthetical** trong
    ngoặc; **Dialogue** khối thụt; **Transition** (`CUT TO:`) căn phải.
  - Toolbar **Scene Heading / Action / Character / Dialogue / Parenthetical / Transition**
    (đủ phần tử chuẩn, không chỉ Title/Scene/Dialog/Transition).
  - Lưu nội bộ ở định dạng **Fountain** (markup screenplay chuẩn) → render ra layout trên.
- Ô chat dưới cùng: *"Describe the story, edit scenes, update dialog…"* → gọi **AI-agent** sửa kịch bản theo yêu cầu (sau khi đã sinh).
- Khi lưu: backend **parse** kịch bản → danh sách **scene** (slugline `INT./EXT. … - …`), lời thoại, hành động, **địa điểm** của scene.

### 2.2 Assets — `samples/entities.png`
- **Asset Library** chia 3 nhóm: **Characters / Locations / Props**.
- Mỗi asset = thẻ (`MediaCard`, §8.1) có ảnh tham chiếu, mô tả dưới.
- **Thêm asset** — nhiều cách:
  - **AI Generate** (sinh ảnh ref từ prompt) · **Upload** (ảnh local).
  - **＋ Thêm mới** thủ công (`POST /projects/{id}/entities`).
  - **Chọn từ thư viện** (mới): mở **Media Library** chọn **bất kỳ ảnh nào trong bất kỳ
    project nào** làm asset (xem dưới).
- **Gán ảnh có sẵn làm ảnh chính của asset (tránh gen lại):** mỗi asset có thể **đặt ảnh
  chính** bằng cách chọn ảnh trong Media Library **hoặc dán thẳng một `media_id`** — miễn là
  **id hợp lệ và còn tồn tại trên Flow**. Backend **xác thực** qua `GET /api/flow/media/{id}`
  (`redirected:true` = hợp lệ) → tải file local → set làm ảnh asset; **không cần generate lại**.
- **Xóa asset** — nút 🗑 trên thẻ (`DELETE /entities/{id}`, xóa bản ghi + file local).
- AI-agent **trích entity** từ kịch bản → tạo sẵn thẻ rỗng kèm mô tả; người dùng generate/upload/chọn.
- **✦ Auto gen** (nút cấp tab): tự động sinh ảnh ref cho **mọi asset chưa có ảnh** (batch, §2.10).
- Ảnh asset → `media_id` dùng làm **reference** cho storyboard/shots.

**Quy tắc ảnh ref theo loại (để tham chiếu sạch, ít nhiễu):**
- **Character → character design sheet:** **nhiều góc nhìn** trong một ảnh (front / 3/4 /
  side / back), pose trung tính (T-pose/A-pose), biểu cảm trung tính; **nền trắng trơn,
  KHÔNG bối cảnh, không đổ bóng nền**. Tùy chọn **góc đặc thù** (chỉ chân dung, hoặc full-body)
  qua tham số. Prompt template tự thêm: *"character design sheet, multiple turnaround views
  (front, 3/4, side, back), neutral pose, plain solid white background, no scene, no props,
  studio reference"*.
- **Prop → product/design sheet nhiều góc:** vật thể đơn lẻ thể hiện **nhiều góc nhìn**
  (front / 3/4 / side / top), **nền trắng trơn, KHÔNG ảnh nền, không đổ bóng nền**. Prompt
  template tự thêm: *"object design sheet, multiple angles (front, 3/4, side, top), isolated
  on plain solid white background, no background scene, no shadow, studio product reference"*.
- **Location → establishing shot** của địa điểm (GIỮ bối cảnh — đây là cảnh nền, không tách nền).

Mặc định ảnh ref nhân vật dùng `IMAGE_ASPECT_RATIO_LANDSCAPE` để chứa đủ các góc; có thể chỉnh.

**Media Library xuyên project (mới):** một trình duyệt ảnh gom **mọi ảnh trong toàn studio**
— asset + frame storyboard của **tất cả project** — có thumbnail, lọc theo project/loại/tên.
Dùng để: (a) tạo asset từ ảnh có sẵn ở project khác; (b) **chọn ảnh tham chiếu** cho storyboard
(RefPicker, §2.3) từ bất kỳ đâu. Vì `media_id` là **toàn cục trên Flow**, ảnh từ project khác
vẫn dùng làm `character_media_ids` được.

### 2.3 Storyboard — `samples/storyboard.png`
- **Storyboard chứa các ẢNH của scene.** Mỗi **scene** có N **frame** (vd 6 frames),
  mỗi frame là **một ảnh tĩnh** — đây là khâu tạo hình ảnh.
- Nút **Autofill Scene** (AI điền mô tả tất cả frame) và **✦ Auto gen** (sinh ảnh hàng loạt —
  theo scene hoặc cả project, batch §2.10).
- Panel phải mỗi frame: **Title**, **Frame Description**, **Reference Assets**, nút **Create image**.
- **Reference Assets (RefPicker):** chọn từ asset của project, **hoặc từ Media Library xuyên
  project** (§2.2) — tham chiếu **bất kỳ ảnh nào ở bất kỳ project nào**. (≤10 ref, xem dưới.)
  - **Hiển thị thumbnail các ảnh tham chiếu** đã chọn; **click vào để xem phóng to** (Lightbox).
- **Gán ảnh có sẵn làm ảnh của frame (tránh gen lại):** ngoài *Create image*, frame có thể
  **đặt ảnh** bằng cách chọn ảnh trong Media Library **hoặc dán `media_id`** hợp lệ trên Flow
  (xác thực `redirected:true` → tải local) — giống asset (§2.2), **không cần generate**.
- **Auto-tham chiếu địa điểm:** mọi shot trong **một scene cùng một địa điểm** → prompt tạo
  ảnh **bắt buộc tham chiếu ảnh `location` của scene** (`scene.location_entity_id`) để giữ
  bối cảnh nhất quán. Ảnh location được **thêm sẵn** vào Reference Assets của mọi frame trong scene.
- **Giới hạn tham chiếu: tối đa 10 ảnh ref** (`character_media_ids`). Thứ tự ưu tiên khi
  vượt: **location của scene → nhân vật xuất hiện trong beat → props** (cắt bớt phần dư,
  cảnh báo trên UI).
- *Create image* → `/api/flow/generate-image`, prompt = description + style, **kèm `references`**.
- **Prompt nhúng tên entity trong `{...}`** để tách reference chính xác: mỗi `{handle}` khớp
  một reference sẽ thành một **part riêng** trong `structuredPrompt` (xem §5.1) → model gắn
  đúng từng ảnh ref vào từng entity, **tránh lẫn** khi có nhiều reference. Vd:
  `"{Thao} dắt tay {Luong} đi trong {Countryside Village}"` → 3 reference part + text xen kẽ.
  (Dùng `{}` thay vì `[]` để **không xung đột** với token điều khiển như timestamp `[00:05]`.)
- Kết quả: mỗi frame có `image_media_id` + file local → **đầu vào cho tab Shots**.

### 2.4 Shots — `samples/shots.png`
- **Shots DỰA VÀO ảnh storyboard để render VIDEO.** Mỗi shot = 1 frame ảnh ở
  storyboard được "làm động" thành clip → **quan hệ 1 frame ↔ 1 shot** (cùng card/title).
- Panel phải: **Preview** (ảnh frame), **Video Model** (Veo i2v / **Omni Flash**), **Duration**
  (Omni Flash: 4/6/8/10s), **Shot Title**, **Visual Prompt**, **Motion Prompt**, nút **Generate Video**.
- *Generate Video* → `/api/flow/generate-video` lấy **ảnh frame làm start image** → poll `/api/flow/check-status` → tùy chọn upscale 4K.
- Toggle **Auto download** + nút **✦ Auto gen** (sinh video toàn bộ shot — batch §2.10).

> **Luồng dữ liệu:** Scene → Storyboard sinh **ảnh frame** (`image_*`) → Shots dùng
> chính ảnh đó làm start image để sinh **video** (`video_*`). Vì 1:1, hai tab là **hai
> view trên cùng bản ghi `shot`**: Storyboard sửa phần ảnh, Shots sửa/render phần video.

### 2.5 Assemble (mới)
- Lồng tiếng: nhập/auto-sinh **narrator text** mỗi shot → `/api/tts/synthesize` → WAV.
- Ghép: trim mỗi clip vừa độ dài narration, burn **text overlay**, **concat** bằng ffmpeg.
- Xuất: `final.mp4` + **thumbnail** (AI) + **SRT** + **metadata SEO** (AI) + **DaVinci Resolve XML** (§2.8). (Upload YouTube để tùy chọn, dùng skill sẵn có.)

### 2.6 Chế độ Storytelling (narration-driven)
Khi bật checkbox **Storytelling**, **giọng đọc TTS là trục xuyên suốt video** và hình
ảnh/video phải **bám sát thời điểm đang đọc**. Khác với chế độ mặc định (dẫn bằng
cảnh/lời thoại), pipeline đảo thứ tự thành **audio-first**:

1. **Sinh lời đọc (voiceover)** liền mạch từ idea/duration — đây là nội dung chính.
2. **Chia scene theo đoạn nội dung gốc:** AI cắt voiceover thành các **đoạn liền mạch,
   nối tiếp nhau phủ kín toàn bộ nội dung** — **mỗi đoạn = một scene**. Một scene thường
   gắn với **một địa điểm** nhất định (ghi vào `location_entity_id` của scene). Các đoạn
   **không chồng lấn, không bỏ sót** (ghép lại = nguyên văn voiceover).
3. **Cắt beat trong scene:** mỗi scene chia tiếp thành **beat** (mỗi câu/mệnh đề = một
   hành động/khoảnh khắc). **1 beat → 1 shot.** Mỗi beat ghi rõ **hành động đang diễn ra**.
4. **TTS từng beat** → đo **độ dài audio thực** của beat → đó là **độ dài hình mục tiêu**
   và **mốc thời gian** của beat trên timeline.
5. **Phủ đủ độ dài audio bằng nhiều shot khi cần (quy tắc đã chốt):**
   - Nếu `narration_duration ≤ shot_duration` (≈8s) → **1 shot** cho beat.
   - Nếu **dài hơn 8s** → **tạo thêm shot bù vào**: chia beat thành
     `ceil(narration_duration / 8)` shot con, mỗi shot ≤8s, tổng độ dài hình **≥ độ dài
     audio của beat** (shot cuối trim vừa khít).
   - Các shot con cùng beat **nối tiếp hình cho liền mạch**: shot sau dùng **frame cuối
     của shot trước làm start image** (chain, theo tinh thần `fk-gen-chain-videos`), và
     `motion_prompt` **tiếp diễn hành động** (vd "đang mở cửa" → "bước qua ngưỡng cửa").
6. **Hình bám audio:** `motion_prompt` **mã hóa đúng hành động của beat** (vd beat "anh
   mở cửa bước vào" → *nhân vật mở cửa và bước vào*). Khi ghép, các clip của beat được
   **trim/fit khít vào đoạn audio** của beat ⇒ "đọc tới đâu, hình tới đó".
7. **Timeline:** narration nối liền thành một track audio; mỗi clip đặt tại `start_time`
   = tổng độ dài các shot trước đó → đồng bộ ở mức **beat/clip**.

> **Giới hạn trung thực:** video sinh-tạo không đảm bảo khớp **từng frame**; ta đồng bộ
> ở mức **beat (mỗi hành động một clip, trim theo audio)** + motion prompt mô tả hành động.
> Người dùng có thể tinh chỉnh mốc cắt trong tab Assemble hoặc trong DaVinci sau khi import XML.

### 2.7 Settings (màn hình thiết lập)
Màn hình **Settings** (icon ⚙ trên TopNav, mở dạng trang/drawer) gồm 2 cấp:

**A. Global (app-level)** — lưu vào bảng `kv`, áp mặc định cho project mới:
| Nhóm | Tùy chọn |
|------|----------|
| **AI Agent** | Agent (`claude` / `antigravity`), model của agent (lấy từ `GET /api/agent/agents`), timeout |
| **Image model** | `NANO_BANANA_PRO` / `NANO_BANANA_2` (từ `models.json`) |
| **Video model** | Veo i2v (theo tier+aspect) · **Omni Flash** (r2v đa-độ-dài `abra_r2v_{4,6,8,10}s`, cần ≥1 ref) · upscale 4K/1080p |
| **Style** | **Textbox tự do** (nhập style-prompt tùy ý, vd *"gritty cinematic, teal-orange, 35mm film grain"*) + vài **preset gợi ý** điền nhanh (Realistic/Cinematic/Anime…). **Áp vào MỌI prompt ảnh & video** (xem dưới) |
| **Aspect ratio** | Landscape / Portrait (16:9 / 9:16) |
| **Paygate tier** | **Tự nhận từ `/api/flow/credits`** (`userPaygateTier`) — KHÔNG do người dùng chọn; hiển thị ở StatusPills |
| **TTS** | OmniVoice base URL (`PUT /api/tts/config`), giọng mặc định (`voice_id`, từ `/api/tts/voices`), speed, từ/giây |
| **Shot** | `shot_duration` mặc định (≤8s), auto-download, throttle batch |
| **Storytelling** | Bật mặc định, ngôn ngữ giọng đọc |

**B. Per-project (override)** — chỉnh trong project, lưu vào bảng `project`:
- Style, aspect_ratio, paygate_tier, image_model, video_model, voice_id, shot_duration,
  storytelling. Bộ chọn **Style** trên TopNav (góc phải, theo screenshot) là lối tắt của
  thiết lập per-project này.

Thứ tự ưu tiên: **per-project > global > mặc định cứng**. Settings cũng hiển thị **trạng
thái phụ thuộc**: extension (Flow), OmniVoice, `claude`/`agy`, ffmpeg — báo đỏ nếu thiếu.

**Style áp xuyên suốt (quy tắc bắt buộc):** `style` là một **chuỗi style-prompt tự do** do
người dùng nhập (textbox), **không fix cứng danh sách**. Có vài **preset gợi ý** chỉ để bấm
điền nhanh rồi sửa tiếp tùy ý. Backend **tự chèn style-prompt vào MỌI prompt sinh media**:
ảnh ref asset (kể cả character/prop design sheet), ảnh storyboard frame, video shot (visual +
motion), thumbnail. Đảm bảo toàn project **nhất quán một phong cách**. Đổi style → các lần
gen **mới** theo style mới (media đã tạo giữ nguyên trừ khi re-gen). Style là **per-project**
(textbox Style trên TopNav là lối tắt sửa nhanh).

### 2.8 Export DaVinci Resolve XML
- Nút **Export → DaVinci XML** trong tab Assemble.
- Sinh file **FCP7 XML (xmeml `.xml`)** — định dạng DaVinci Resolve import tốt — mô tả
  một **timeline**: track video (các clip shot theo thứ tự, in/out, đúng `start_time`/
  `duration`) + track audio (TTS narration, +nhạc nền nếu có) + (tùy chọn) marker theo beat.
- Tham chiếu tới **file media đã tải về local** (`studio_media/<project>/...`) để Resolve
  relink. Cho người dùng **dựng/chỉnh cuối trong Resolve** thay vì chỉ ffmpeg.
- (Tùy chọn cân nhắc thêm **FCPXML `.fcpxml`** nếu cần độ chính xác cao hơn — xem §12.)

### 2.9 Node Editor (kéo-thả, render ảnh/video)
Nút **✎ Edit** trên mỗi `MediaCard` (asset / frame / shot) mở một **trình soạn node
kéo-thả** kiểu ComfyUI: ghép các node thành **đồ thị (DAG)**; bấm **Run** → backend thực thi
đồ thị → render ra **ảnh/video** và gán làm media của thẻ đó.

**Loại node (map thẳng API đã có):**
| Nhóm | Node | API/nguồn |
|------|------|-----------|
| **Input** | Reference Image (chọn Media Library / `media_id`), Text Prompt, Style, Aspect Ratio, Source Image (ảnh hiện tại của thẻ), Start/End Frame | DB / Media Library |
| **Image** | Generate Image, Edit Image (sửa ảnh từ source + prompt), Upscale Image | `generate-image`, `edit-image`, `upscale-image` |
| **Video** | I2V (start image→video), Start+End Frame→video, R2V (từ refs), Upscale Video, Chain (frame cuối→start image kế) | `generate-video`, `generate-video-start-end`, `generate-video-refs`, `upscale/video` |
| **Audio** | TTS (text→WAV) | `/api/tts/synthesize` |
| **Logic/AI** | Prompt Builder (AI sinh/tinh prompt), Combine Refs (gộp ≤10 ảnh) | `/api/agent/run` |
| **Output** | Result → media của thẻ (lưu local + đổi tên) | orchestration |

**Cơ chế:**
- Đồ thị lưu **JSON** vào DB (`graph_json` của shot/entity) — sửa lại, chạy lại nhiều lần.
- **Run** = tạo **job nền** (§9): backend **topo-sort** đồ thị, chạy từng node, áp **rate-limit**
  (ảnh 2–6s, video 15–30s), **tải local + đổi tên** ở node Output, stream tiến độ qua WS.
- Mặc định mỗi thẻ có sẵn một **đồ thị tối giản** (Refs + Prompt → Generate → Output) tương
  đương nút Create/Generate hiện tại; người dùng mở rộng khi cần (vd thêm Edit Image, Chain).
- Có **node template/preset** (i2v cơ bản, r2v, chain nhiều shot, edit-rồi-animate…).

### 2.10 Auto Gen hàng loạt (nút cấp tab)
Mỗi tab có nút **✦ Auto gen** tạo tự động **toàn bộ** media của tab:
| Tab | Auto gen | Phạm vi mặc định |
|-----|----------|------------------|
| **Assets** | sinh ảnh ref mọi asset | asset **chưa có ảnh** (tùy chọn: tạo lại tất cả) |
| **Storyboard** | sinh ảnh mọi frame | frame chưa có ảnh — theo **scene** hoặc **cả project** |
| **Shots** | sinh video mọi shot | shot **đã có ảnh** nhưng chưa có video |

**Cơ chế (dùng JobManager §9):**
- **QUY TẮC CHÍNH — bỏ qua item ĐÃ CÓ media:** Auto gen **chỉ tạo những item còn thiếu**
  (ảnh/video chưa có, tức `*_media_id`/`*_path` còn trống hoặc file local không tồn tại).
  Item nào **đã có rồi thì KHÔNG tạo lại** → idempotent, bấm lại an toàn, không tốn credit
  thừa. Muốn tạo lại phải bật **Force re-gen** (mặc định TẮT), hoặc dùng **⚡ gen nhanh** /
  Node Editor trên từng thẻ.
- Tạo **1 job cha** + nhiều **job con** (chỉ cho item còn thiếu), chạy **tuần tự**, tôn trọng
  **rate-limit** (ảnh 2–6s, video 15–30s; ~6 URL ảnh nghỉ 2–6s), **tải local + đổi tên** sau mỗi item.
- Tiến độ + item đang chạy hiển thị realtime qua **WS**; **dừng/tiếp tục** được.
- Trước khi chạy, đếm số item **còn thiếu**, ước tính **credit** và cảnh báo nếu vượt số dư.

---

## 3. Kiến trúc tổng thể

```
┌────────────────────────────────────────────────────────────┐
│  Browser — React SPA (Vite + Tailwind)                      │
│  Tabs: Script · Assets · Storyboard · Shots · Assemble      │
└───────────────┬───────────────────────────┬────────────────┘
                │ REST /api/studio/*         │ WS /api/studio/ws (tiến độ job)
┌───────────────▼───────────────────────────▼────────────────┐
│  FastAPI agent (đã có) + lớp Studio mới                     │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │ api/studio.py│  │ services/jobs │  │ services/assembler│ │
│  │ (CRUD+điều   │  │ (hàng đợi job │  │ (ffmpeg ghép/    │  │
│  │  phối)       │  │  asyncio)     │  │  overlay/TTS mux)│  │
│  └──────┬───────┘  └──────┬────────┘  └────────┬─────────┘  │
│         │ db.py (SQLite studio.db)              │            │
│  ┌──────▼───────────────────────────────────────▼────────┐  │
│  │ Tái dùng: flow_client (WS→extension) · api/tts ·       │  │
│  │           api/ai_agent (claude/agy CLI)                │  │
│  └────────────────────────────────────────────────────────┘  │
└──────┬──────────────────┬───────────────────┬───────────────┘
       │ WS :9222          │ httpx             │ subprocess/PTY
   Chrome Extension    OmniVoice (Colab)   Claude / agy CLI
       │
   Google Flow API
```

Webapp **không gọi thẳng** `/api/flow/*` hay `/api/agent/run`. Nó gọi `/api/studio/*`
— lớp điều phối lo: lưu DB, gọi flow/agent/tts đúng thứ tự, theo dõi job, **tải media về
local** (`./media/`, mount tĩnh) để hiển thị không cần URL mỗi lần. Như vậy frontend mỏng,
mọi logic ở backend (dễ test, dễ tái dùng cho CLI sau này).

---

## 4. Mô hình dữ liệu (SQLite — `agent/studio.db`)

```sql
project(
  id TEXT PK, title TEXT, flow_project_id TEXT,        -- id project bên Google Flow
  style TEXT DEFAULT 'Realistic',
  aspect_ratio TEXT DEFAULT 'VIDEO_ASPECT_RATIO_LANDSCAPE',
  paygate_tier TEXT DEFAULT 'PAYGATE_TIER_ONE',
  image_model TEXT, video_model TEXT,                  -- override model (NULL = theo global)
  voice_id INT, agent TEXT,                            -- TTS voice + AI agent cho project này
  idea TEXT,                                           -- idea/nội dung gốc người dùng nhập
  target_duration INT,                                 -- giây; NULL = full nội dung (không nén/giãn)
  shot_duration INT DEFAULT 8,                          -- độ dài mặc định mỗi shot (giây)
  storytelling INT DEFAULT 0,                           -- 1 = chế độ narration-driven (§2.6)
  voiceover_raw TEXT,                                  -- lời đọc liền mạch (storytelling)
  script_raw TEXT,                                     -- kịch bản gốc (fountain-like)
  status TEXT, created_at, updated_at)

entity(                                                -- Characters/Locations/Props
  id TEXT PK, project_id FK, type TEXT,                -- character|location|prop
  name TEXT, description TEXT, ref_prompt TEXT,
  media_id TEXT, primary_media_id TEXT, workflow_id TEXT,
  image_path TEXT,                                     -- ./media/<project_id>/<media_id>.png (tải về 1 lần)
  image_url TEXT,                                      -- cache URL tạm (chỉ dùng lúc tải)
  graph_json TEXT,                                     -- đồ thị Node Editor (§2.9) của asset này
  -- workflow_id để ĐỔI TÊN (PATCH change-displayname); primary_media_id để LẤY url tải file
  created_at, updated_at)

scene(
  id TEXT PK, project_id FK, idx INT,
  heading TEXT, slug TEXT, action TEXT, dialog TEXT,   -- parse từ script (slugline INT./EXT.)
  location_entity_id TEXT,                             -- entity type=location của scene → auto-ref mọi shot
  source_segment TEXT,                                 -- (storytelling) đoạn voiceover gốc của scene
  source_start INT, source_end INT,                    -- vị trí ký tự trong voiceover (đoạn liền mạch)
  created_at)

shot(                                                  -- 1 bản ghi = 1 frame ảnh + 1 video
  id TEXT PK, scene_id FK, idx INT, title TEXT,
  beat_id TEXT, part_idx INT DEFAULT 0,                -- gom shot con cùng 1 beat (storytelling);
                                                       -- part_idx>0 = shot bù khi audio >8s, chain frame
  is_chained INT DEFAULT 0,                            -- 1 = start image lấy từ frame cuối shot trước
  -- ── Storyboard (ẢNH) ──
  description TEXT,                                     -- mô tả frame
  ref_entity_ids TEXT,                                 -- JSON list entity.id (reference assets)
  image_media_id TEXT, image_primary_id TEXT, image_workflow_id TEXT,
  image_path TEXT,                                     -- ./media/<project_id>/<image_media_id>.png
  -- ── Shots (VIDEO render từ ảnh trên) ──
  visual_prompt TEXT, motion_prompt TEXT,
  beat_action TEXT,                                    -- hành động của beat (storytelling, để khớp motion)
  video_model TEXT, duration INT DEFAULT 8,
  video_media_id TEXT, video_primary_id TEXT, video_workflow_id TEXT,
  video_path TEXT,                                     -- ./media/<project_id>/<video_media_id>.mp4
  upscale_path TEXT, upscale_url TEXT,
  operation_json TEXT,                                 -- {operation:{name:mediaId}, sceneId} để poll
  graph_json TEXT,                                     -- đồ thị Node Editor (§2.9) của shot này
  -- workflow_id (ảnh & video) để ĐỔI TÊN; *_path = file local tải về (nguồn hiển thị chính)
  -- ── Audio / timeline (assemble + storytelling) ──
  narrator_text TEXT, narration_path TEXT,             -- TTS WAV
  narration_duration REAL,                             -- độ dài audio thực (giây) → fit clip
  start_time REAL,                                     -- mốc bắt đầu trên timeline (giây)
  status TEXT, created_at, updated_at)

job(                                                   -- theo dõi tác vụ nền
  id TEXT PK, project_id FK, type TEXT, target_id TEXT,
  status TEXT, progress REAL, message TEXT, error TEXT,
  created_at, updated_at)

asset(                                                 -- output cuối
  id TEXT PK, project_id FK, kind TEXT,                -- final_video|thumbnail|srt|metadata
  path TEXT, meta_json TEXT, created_at)

kv(key TEXT PK, value TEXT)                            -- cấu hình (tts voice, omnivoice url…)
```

Ghi chú:
- Dùng `aiosqlite` (async) hoặc `sqlite3` trong threadpool. File `studio.db` thêm vào `.gitignore`.
- **Tải media về local ngay khi tạo xong** → nguồn hiển thị chính là **file local**, không
  gọi URL mỗi lần mở app (tránh spam server Flow). Xem §4.1.
- **URL chỉ là phái sinh, dùng một lần để tải.** `*_primary_id` (bền vững) là handle; gọi
  `/api/flow/media/{primary_id}` lấy URL → tải file → lưu `*_path`. Sau đó dùng file local.

### 4.1 Local media store (`./media/`)
```
media/<project_id>/<media_id>.png      # ảnh (storyboard frame, ref entity)
media/<project_id>/<media_id>.mp4      # video shot / upscale
studio_media/<project_id>/...          # output khâu Assemble (clip đã trim, final.mp4, wav, xml)
```
- Sau khi **tạo xong + đổi tên**: lấy URL qua `media/{primary_id}` → **tải file** về
  `./media/<project_id>/<media_id>.<ext>` → lưu đường dẫn vào `*_path`.
- FastAPI **mount tĩnh** `./media` (vd `/media/...`) để frontend hiển thị trực tiếp; chỉ
  khi thiếu file mới tải lại từ `primary_id`.
- `./media/` và `./studio_media/` thêm vào `.gitignore`.

---

## 5. API backend mới (`/api/studio/*`)

| Method | Path | Việc |
|--------|------|------|
| GET | `/projects` | Danh sách project (từ DB; có thể sync `/api/flow/projects`) |
| POST | `/projects` | Tạo project (DB + `/api/flow/create-project` lấy `flow_project_id`) |
| GET/PATCH/DELETE | `/projects/{id}` | Đọc/sửa/xóa project |
| POST | `/projects/{id}/script/generate` | Sinh script từ `{idea, target_duration?}` — nén/giãn cho khớp duration, không có duration thì full |
| PUT | `/projects/{id}/script` | Lưu script + parse → scenes |
| POST | `/projects/{id}/script/chat` | Ô chat: gửi instruction → AI-agent sửa script → trả script mới |
| POST | `/projects/{id}/entities/extract` | AI trích entity từ script → tạo thẻ asset |
| POST | `/projects/{id}/assets/generate-all` | **✦ Auto gen** ảnh mọi asset (batch §2.10) |
| POST | `/projects/{id}/entities` | Thêm entity mới (thủ công) |
| POST | `/projects/{id}/entities/from-media` | Tạo entity từ ảnh có sẵn (chọn trong Media Library, kể cả project khác) |
| PUT | `/entities/{id}/image` | **Gán ảnh chính** từ `media_id` có sẵn — xác thực tồn tại trên Flow (`redirected:true`) → tải local, không gen lại |
| PATCH/DELETE | `/entities/{id}` | Sửa / **xóa** entity + file local |
| GET | `/media/library` | **Thư viện ảnh xuyên project** (asset + frame của mọi project) — lọc `?project_id&type&q`, có thumbnail local |
| POST | `/entities/{id}/generate` | Sinh ảnh ref (`/api/flow/generate-image`) |
| POST | `/entities/{id}/upload` | Upload ảnh ref (`/api/flow/upload-image`) |
| POST | `/scenes/{id}/storyboard/autofill` | AI điền mô tả + ref cho mọi frame |
| POST | `/projects/{id}/storyboard/generate-all` · `/scenes/{id}/storyboard/generate-all` | **✦ Auto gen** ảnh mọi frame (cả project / 1 scene) |
| POST | `/projects/{id}/shots/generate-all` | **✦ Auto gen** video mọi shot (batch §2.10) |
| POST | `/scenes/{id}/shots` | Thêm shot mới vào **cuối** scene |
| POST | `/shots/{id}/insert` | **Chèn** shot mới ngay sau shot này (reindex `idx`) |
| PATCH/DELETE | `/shots/{id}` | Sửa (title/description/prompt…) / **xóa** shot + file local |
| POST | `/shots/{id}/image` | Tạo ảnh frame (gen-image + ref entities) |
| PUT | `/shots/{id}/image-from-media` | **Gán ảnh frame** từ `media_id` có sẵn — xác thực trên Flow (`redirected:true`) → tải local, không gen lại |
| GET/PUT | `/shots/{id}/graph` · `/entities/{id}/graph` | Đọc/lưu **đồ thị Node Editor** (§2.9) |
| POST | `/shots/{id}/graph/run` · `/entities/{id}/graph/run` | **Chạy đồ thị** (job nền) → render media, tải local, đổi tên |
| POST | `/shots/{id}/prompts` | AI sinh visual_prompt + motion_prompt |
| POST | `/shots/{id}/video` | Tạo video (gen-video → poll) |
| POST | `/shots/{id}/upscale` | Upscale 4K |
| POST | `/shots/{id}/narration` | Sinh narrator text (AI) + TTS (`/api/tts/synthesize`) |
| POST | `/projects/{id}/voiceover` | (Storytelling) Sinh lời đọc liền mạch + cắt **beat** → tạo shots |
| POST | `/projects/{id}/assemble` | Ghép cuối (ffmpeg): trim theo narration + overlay + concat + mux TTS |
| POST | `/projects/{id}/export` | Thumbnail (AI) + SRT + metadata SEO |
| POST | `/projects/{id}/export/davinci-xml` | Sinh **DaVinci Resolve XML** (timeline tham chiếu media local) |
| POST | `/media/ensure/{primary_id}` | Đảm bảo file local tồn tại: lấy URL → tải về `./media/...` → trả `local_path` (fallback khi thiếu file) |
| GET/PUT | `/settings` | Đọc/ghi thiết lập **global** (bảng `kv`) |
| GET | `/options` | Danh mục chọn được: models (`models.json`), styles, aspect, tiers, voices (`/api/tts/voices`), agents (`/api/agent/agents`) |
| GET | `/jobs/{id}` · WS `/ws` | Trạng thái/tiến độ job (live) |
| GET | `/health` | Gộp `/health` + `/api/flow/status` + `/api/tts/health` + ffmpeg/agent check |

Mỗi tác vụ "nặng" (generate ảnh/video/TTS/assemble) tạo một **job** và chạy nền;
frontend nhận tiến độ qua **WebSocket** (khớp nút *Auto generate*).

### 5.1 Hợp đồng API Flow thực tế (đã gọi thật để verify — 2026-06-18)

> Các shape dưới đây **lấy từ phản hồi thật**, không phải mô tả README. Webapp phải
> bóc tách đúng các đường dẫn này.

**`GET /api/flow/credits`** → phẳng:
```json
{ "credits": 1799, "userPaygateTier": "PAYGATE_TIER_ONE",
  "topUpCredits": 890, "subscriptionCredits": 909, "sku": "G1_TIER1" }
```

**`GET /api/flow/projects`** → bọc tRPC sâu, bóc tại
`data.result.data.json.result.projects[]`, mỗi item:
`{ projectId, projectInfo:{ projectTitle, thumbnailMediaKey }, creationTime }`.

**`POST /api/flow/generate-image`** → trả ngay khi xong (đồng bộ):
```jsonc
{ "media": [{ "name": "<UUID=mediaId>", "workflowId": "<UUID>",
    "image": { "generatedImage": {
      "mediaId": "<UUID>",                 // ✅ media_id UUID (dùng cái này)
      "mediaGenerationId": "CAMS...",      // ⚠️ id nội bộ base64, KHÔNG phải media_id
      "fifeUrl": "https://flow-content.google/image/<id>?Expires=...&Signature=...", // hết hạn!
      "modelNameType": "GEM_PIX_2", "aspectRatio": "...", "seed": 886269 },
      "dimensions": { "width": 1376, "height": 768 } } }],
  "workflows": [{ "name": "<workflowId>", "projectId": "...",
    "metadata": { "displayName": "Red apple on white table",  // ⚠️ Flow tự đặt theo prompt
      "primaryMediaId": "<UUID=mediaId>", "batchId": "<UUID>" } }] }
```
→ lưu `mediaId` (=`media[0].image.generatedImage.mediaId`), `workflow_id`
(=`workflows[0].name`), `primary_media_id` (=`metadata.primaryMediaId`).

**Reference theo `structuredPrompt` (đã verify thật + sửa API):** để model **không lẫn các
entity**, prompt build dạng **mảng part xen kẽ** thay vì gộp 1 text. API `generate-image`
nhận thêm `references: [{handle, media_id}]` + `image_model`; prompt nhúng `{handle}`:
```jsonc
// body: { prompt: "{Thao} dắt tay {Luong} trong {Countryside Village}",
//         references: [{handle:"Thao", media_id:"..."}, {handle:"Luong", ...}, {handle:"Countryside Village", ...}],
//         image_model: "NARWHAL", project_id, aspect_ratio }
// → flow_client tách thành:
"structuredPrompt": { "parts": [
  { "reference": { "media": { "handle": "Thao", "mediaId": "<uuid>" } } },
  { "text": " dắt tay " },
  { "reference": { "media": { "handle": "Luong", "mediaId": "<uuid>" } } },
  { "text": " trong " },
  { "reference": { "media": { "handle": "Countryside Village", "mediaId": "<uuid>" } } }
] }
// + imageInputs: [{name:<uuid>, imageInputType:"IMAGE_INPUT_TYPE_REFERENCE"}, ...]  (theo thứ tự ref)
```
Token `{lạ}` không khớp reference → giữ làm text (bỏ ngoặc nhọn). Không có `references` → 1 text part
(hành vi cũ). **Đã test thật:** trả `media`+`workflows`, model `NARWHAL`, mediaId UUID, có URL.

**`POST /api/flow/generate-video-refs` (r2v) — cùng cấu trúc:** dùng y hệt cơ chế trên cho
`textInput.structuredPrompt` (xen kẽ reference/text theo `{handle}`) + `referenceImages`
(`imageUsageType: IMAGE_USAGE_TYPE_ASSET`, theo thứ tự ref) + `mediaGenerationContext.audioFailurePreference:
"BLOCK_SILENCED_VIDEOS"`. Nhận thêm `references` + `video_model` (vd `veo_3_1_r2v_lite`).
**Đã test thật (3 ref):** parts = `[ref:Red fox, text, ref:Hung, text, ref:An, text]`,
`videoGenerationImageInputs` count = 3, status `SCHEDULED` → mỗi entity gắn đúng ảnh riêng.
> ⚠️ Prompt có dấu tiếng Việt phải gửi qua **JSON UTF-8 hợp lệ** (frontend làm đúng tự nhiên);
> test bằng `curl -d` inline dễ hỏng UTF-8 → FastAPI báo *"error parsing the body"* (lỗi client, không phải API).

**`POST /api/flow/generate-video-omni` — Omni Flash (model video mới của Google, đã tích hợp):**
r2v **đa-độ-dài** dùng chung endpoint `batchAsyncGenerateVideoReferenceImages`; model key theo
số giây: `abra_r2v_4s/6s/8s/10s` (map trong `models.json → omni_flash_models`). Body y hệt r2v
(structuredPrompt `{handle}` + referenceImages + audioFailurePreference) — chỉ khác `videoModelKey`.
Ràng buộc: **≥1 reference**, aspect chỉ **PORTRAIT/LANDSCAPE**, `duration_s ∈ {4,6,8,10}`.
```jsonc
// body: { prompt:"{Red fox} runs then sees {Hung}...", project_id, duration_s:8,
//         aspect_ratio:"VIDEO_ASPECT_RATIO_LANDSCAPE",
//         reference_media_ids:[...], references:[{handle,media_id}...] }
```
**Đã test thật:** `model: abra_r2v_8s`, mode `REFERENCE_TO_VIDEO`, res 720P, 3 refImages,
status `SCHEDULED`; duration sai (vd 7s) → 400 báo lỗi rõ. Poll/đổi tên/tải local như video khác.
Đây là model sau bộ chọn **Video Model "Omni Flash"** trong UI Shots (§2.4).

**`PATCH /api/flow/change-displayname`** → đổi tên, **`media_id` = workflowId** (KHÔNG phải mediaId):
```json
// body: { "media_id": "<workflowId>", "project_id": "...", "display_name": "scene01_shot01" }
// resp: { "name": "<workflowId>", "metadata": { "displayName": "scene01_shot01", ... } }
```

**`GET /api/flow/media/{primaryMediaId}`** → lấy URL ảnh/video từ id, trả **gọn**:
```json
{ "url": "https://flow-content.google/image/<id>?Expires=...&Signature=...", "redirected": true }
```
> Chỉ cần **id đúng** là lấy được URL (`redirected:true`); `redirected:false` = id sai/chưa
> sẵn sàng. Dùng URL này để **tải file về local một lần** (§4.1) rồi hiển thị từ file —
> **không** gọi lại mỗi lần mở app. Bản thân endpoint này **cũng bị rate-limit** (§5.2).

**`POST /api/flow/generate-video`** → submit async (model auto `veo_3_1_i2v_s_fast`, res 720P, ~20 credit):
```jsonc
{ "remainingCredits": 1779,
  "workflows": [{ "name": "<workflowId>", "metadata": { "primaryMediaId": "<UUID>", "displayName": "..." } }],
  "media": [{ "name": "<UUID=mediaId>", "workflowId": "...",
    "mediaMetadata": { "mediaStatus": { "mediaGenerationStatus": "MEDIA_GENERATION_STATUS_SCHEDULED" } } }] }
```
→ giữ `<mediaId>` (media[0].name) để poll.

**`POST /api/flow/check-status`** → body `{ "media": [{ "name": "<mediaId>", "projectId": "<flowProjectId>" }] }`
(⚠️ shape CŨ `{operations:[{operation:{name},sceneId}]}` nay bị Flow trả **400
INVALID_ARGUMENT** với mọi operation). Trả:
```jsonc
{ "media": [{ "name": "<mediaId>", "projectId": "...", "workflowId": "...",
    "mediaMetadata": { "mediaStatus": {
        "mediaGenerationStatus": "MEDIA_GENERATION_STATUS_SUCCESSFUL" } },  // hoặc _FAILED
    "video": { "generatedVideo": {...}, "dimensions": { "length": "10s" } } }],
  "remainingCredits": 705 }
```
Chưa xong → `mediaGenerationStatus` còn `SCHEDULED`/`IN_PROGRESS`/`ACTIVE`.
`_FAILED` kèm `mediaStatus.failureReasons` (vd `PROMINENT_PERSON`) → hỏng hẳn, đừng chờ tiếp.

⚠️ Response **KHÔNG còn URL** (`fifeUrl`/`servingBaseUri` đã biến mất). Xong rồi thì phải
resolve riêng qua `GET /api/flow/media/{mediaId}` → `{url, redirected:true}` rồi mới tải.

### 5.2 Quy tắc rate-limit & đổi tên (BẮT BUỘC trong orchestration)

- **Tạo ảnh:** chờ **có kết quả** rồi **chờ 2–6s** (random) mới tạo ảnh tiếp → tránh rate-limit.
- **Tạo video:** giữa hai lần submit **chờ 15–30s**.
- **`media/{primaryMediaId}` (lấy URL) cũng bị rate-limit:** sau mỗi **~6 URL ảnh** trong
  một batch thì **nghỉ 2–6s** mới lấy tiếp.
- **Tải về local ngay sau khi tạo xong + đổi tên:** lấy URL → tải file →
  `./media/<project_id>/<media_id>.<ext>` → lưu `*_path`. Nguồn hiển thị sau đó là **file local**.
- **Đổi tên ngay sau khi tạo xong** (cả ảnh & video): `PATCH change-displayname` với
  `workflow_id`, đặt tên có ý nghĩa (vd `s01_shot03_img`, `s01_shot03_vid`) thay cho
  chuỗi mô tả Flow tự gán.
- **Tối đa 10 ảnh tham chiếu** mỗi lần `generate-image` (`character_media_ids` ≤ 10). Luôn
  **gồm ảnh location của scene**; vượt 10 thì cắt theo ưu tiên location → nhân vật → props.
- JobManager (§9) thực thi tất cả các quy tắc trên khi chạy batch.

### 5.3 Aspect ratio: ảnh vs video (dễ sai)
Flow dùng **hai enum khác nhau**: ảnh `IMAGE_ASPECT_RATIO_{LANDSCAPE,PORTRAIT}`, video
`VIDEO_ASPECT_RATIO_{LANDSCAPE,PORTRAIT}`. Project chỉ lưu **một hướng** (`aspect_ratio` kiểu
video); backend **suy ra enum ảnh tương ứng** khi gọi generate-image để **ảnh storyboard khớp
khung video** (tránh khung lệch khi i2v). Helper `to_image_aspect(video_aspect)` /
`to_video_aspect(...)` trong studio. Omni Flash chỉ nhận PORTRAIT/LANDSCAPE (không SQUARE).

---

## 6. AI-agent là "bộ não" (hợp đồng JSON)

Mọi bước cần AI gọi `/api/agent/run` (đã build) với **prompt template** yêu cầu
model trả **JSON nghiêm ngặt**, backend parse. Chạy `claude` (stdin) hoặc `agy` (PTY).

| Tác vụ | Input | Output JSON mong đợi |
|--------|-------|----------------------|
| **Sinh script từ idea** | idea/nội dung + `target_duration?` + ngân sách shot/lời | `{ "script": "<fountain>", "estimated_duration": <giây> }` |
| **Sinh voiceover + cắt beat** (storytelling) | idea/script + `target_duration?` | `{ "voiceover": "...", "beats": [{idx, narrator_text, beat_action, visual_prompt, motion_prompt}] }` |
| **Tách shot bù** (beat audio >8s) | beat_action + số shot cần | `{ "parts": [{part_idx, motion_prompt}] }` — chuỗi motion tiếp diễn cho từng đoạn 8s |
| Sửa script (chat) | script hiện tại + instruction | `{ "script": "<fountain>" }` |
| Parse scenes | script | `[{idx, heading, slug, action, dialog, location_name}]` (mỗi scene 1 địa điểm) |
| Trích entity | script | `[{type, name, description, ref_prompt}]` (gồm cả `location`); `ref_prompt` theo loại: **character → design sheet nhiều góc, nền trắng, không bối cảnh**; **prop → design sheet nhiều góc, isolated nền trắng, không ảnh nền**; **location → establishing shot có bối cảnh** |
| Autofill storyboard | scene + entity list + style + **location scene** | `[{idx, title, description, ref_entity_names[]}]` (mặc định gồm location của scene, tổng **≤10** ref); **mô tả nhúng tên entity trong `{...}`** để API tách reference (§5.1) |
| Sinh prompt shot | frame description + style | `{ visual_prompt, motion_prompt }` (visual_prompt nhúng `{entity}` khớp ref) |
| Narrator text | scene/shot | `{ narrator_text }` |
| Thumbnail/SEO | project | `{ thumbnail_prompt, title, description, tags[] }` |

Thiết kế: một module `agent/services/brain.py` bọc việc dựng prompt + gọi
`/api/agent/run` + parse JSON + retry nếu output không hợp lệ. Cho phép chọn agent
(`claude`/`antigravity`) trong Settings.

**Style trong mọi prompt media:** các task sinh prompt (ref asset, storyboard, prompt shot,
thumbnail) **luôn nhận `style` của project** và chèn style-prompt tương ứng vào kết quả →
toàn bộ ảnh/video nhất quán phong cách (xem §2.7). Character/prop design sheet vẫn giữ
nền trắng nhưng theo đúng style (vd anime sheet vs realistic sheet).

**Cơ chế duration (task sinh script):** backend đưa vào prompt một *ngân sách* rõ ràng —
`target_duration` → số shot mục tiêu (`duration / shot_duration`) và số từ narration
mục tiêu (`duration × ~2.5 từ/giây`). Prompt hướng dẫn model:
- Nếu nội dung **dài hơn** ngân sách → **nén**: tóm gọn, bỏ chi tiết phụ, gộp cảnh.
- Nếu **ngắn hơn** → **giãn**: thêm cảnh, mô tả không gian, lời thoại, nhịp.
- Nếu **không có** `target_duration` → giữ **full** nội dung, không ép độ dài.
Sau khi parse scenes/shots, backend đối chiếu `estimated_duration` với mục tiêu và có
thể cảnh báo/đề xuất chỉnh nếu lệch nhiều.

---

## 7. Ghép video (Assemble) — ffmpeg

Phụ thuộc mới: **ffmpeg** (binary hệ thống). Pipeline mỗi project:
1. Tải video mỗi shot (đã refresh URL) về `studio_media/<project>/shotNN.mp4`.
2. Sinh narrator text → TTS → `shotNN.wav`; đo **`narration_duration`** (ffprobe).
3. **Trim/fit clip cho khớp độ dài narration** (skill `fk-concat-fit-narrator`).
   - **Storytelling:** đây là điểm đồng bộ — các clip của beat (1 hoặc nhiều shot bù khi
     audio >8s) **nối lại phủ đủ độ dài audio**, shot cuối trim khít, đặt tại `start_time`
     ⇒ "đọc tới đâu hình tới đó".
4. Burn **text overlay** (title/lời thoại/phụ đề) bằng `drawtext`.
5. **Concat** toàn bộ shot → `final.mp4`; mux audio TTS (+ nhạc nền nếu có).
6. Sinh **thumbnail** (AI prompt → gen-image), **SRT**, **metadata** → lưu `asset`.

### 7.1 Export DaVinci Resolve XML
- Module `services/davinci_xml.py` dựng **FCP7 xmeml (`.xml`)** từ các `shot` + narration:
  - `<sequence>` với khung hình/`timebase` (fps), độ phân giải theo `aspect_ratio`.
  - **Track video 1:** mỗi shot là `<clipitem>` trỏ tới file local (`pathurl=file://…`),
    `start`/`end`/`in`/`out` quy ra **frame** từ `start_time` + `duration`.
  - **Track audio 1:** các WAV narration nối theo `start_time` (storytelling) hoặc theo shot.
  - (Tùy chọn) `<marker>` mỗi beat để dễ nhảy điểm trong Resolve.
- Trả đường dẫn `project.xml`; người dùng **Import Timeline** trong Resolve, media relink
  từ `studio_media/`.

Tất cả chạy trong `services/assembler.py` (+ `davinci_xml.py`), dưới job nền, stream tiến độ qua WS.

---

## 8. Cấu trúc frontend (`webapp/`)

```
webapp/
  index.html
  vite.config.ts            # dev proxy /api → http://127.0.0.1:8100
  src/
    main.tsx, App.tsx
    api/client.ts           # fetch wrapper + WS job progress
    store/                  # Zustand: project, ui, jobs
    components/
      TopNav.tsx            # tabs + Style + trạng thái extension/tts
      script/ScriptEditor.tsx + Toolbar + ChatBox
      assets/AssetLibrary.tsx + GenerateDialog + MediaLibrary(cross-project picker)
      storyboard/Storyboard.tsx + FrameGrid + FramePanel(RefPicker→MediaLibrary, ref thumbnails→Lightbox, set-image-from-media)
      shots/Shots.tsx + ShotPanel(model/duration/prompts)
      assemble/Assemble.tsx + Timeline + RenderPanel
      settings/Settings.tsx + ModelPicker + StyleInput(textbox + preset chips) + VoicePicker + DependencyStatus
      nodeeditor/NodeEditor.tsx (React Flow) + NodePalette + nodes/* + RunBar
      common/ MediaCard, Lightbox, JobProgress, MediaImage, StatusBadge, AddInsertButton
  dist/                     # build → FastAPI StaticFiles mount '/'
```

### 8.1 MediaCard (thẻ ảnh/video dùng chung — Storyboard & Shots)
Thẻ chuẩn cho frame ảnh và shot video (Asset cũng tái dùng):
```
┌─────────────────────┐
│                     │   ← trên: ẢNH (thumbnail) hoặc VIDEO (poster + ▶ play)
│   [media preview]   │     · hover hiện hàng nút: ⚡ gen nhanh · ⤢ phóng to · ✎ edit · ⭳ download · 🗑 xóa
│                     │
├─────────────────────┤
│ 01  Shot title      │   ← dưới: số thứ tự + TIÊU ĐỀ
│ mô tả ngắn…          │     · MÔ TẢ (frame description / prompt), 1–2 dòng, click sửa
└─────────────────────┘
      [＋ chèn] [＋ thêm]   ← nút CHÈN (vào giữa) và THÊM MỚI (cuối) giữa/ sau thẻ
```
Hành vi:
- **⚡ Gen nhanh** → tạo **ngay một chạm** bằng prompt/ref/setting **hiện có** của thẻ, không
  cần mở panel hay Node Editor: Storyboard gọi `POST /shots/{id}/image`, Shots gọi
  `/shots/{id}/video`, Asset gọi `/entities/{id}/generate`. Dành cho người không muốn chỉnh kỹ.
- **Click vào media** → mở **Lightbox** (phóng to ảnh / player video, phím ←/→ duyệt thẻ).
- **✎ Edit** → mở **Node Editor** (§2.9) — dựng pipeline kéo-thả để render lại ảnh/video của thẻ.
- **⭳ Download** → tải file local (`/media/...`) về máy; nếu chưa có thì gọi
  `POST /media/ensure/{primary_id}` trước.
- **🗑 Xóa** → `DELETE /shots/{id}` (xóa bản ghi + file local); xác nhận trước.
- **＋ Chèn** → `POST /shots/{id}/insert` thêm shot **ngay sau** thẻ này (reindex `idx`).
- **＋ Thêm mới** → `POST /scenes/{id}/shots` thêm shot **cuối scene**.
- **Trạng thái:** badge góc (chưa tạo / đang tạo / xong / lỗi) bám job WS.
- Storyboard hiện phần **ảnh**, Shots hiện phần **video** — cùng `MediaCard`, khác `mediaKind`.

- **State:** React Query (cache REST) + Zustand (UI) + WS cho job realtime.
- **Theme:** Tailwind dark, bo góc, đúng tông trong screenshot.
- **MediaImage:** hiển thị từ **file local** (`/media/<project_id>/<media_id>.<ext>`); nếu
  thiếu file thì gọi backend tải lại từ `primary_id` rồi hiện. Không gọi URL Flow mỗi lần render.
- **Dev:** `vite dev` (proxy /api + /media). **Prod:** `vite build` → `webapp/dist` → FastAPI
  `app.mount('/', StaticFiles(directory='webapp/dist', html=True))`.
- **Media tĩnh:** `app.mount('/media', StaticFiles(directory='media'))` để phục vụ file đã
  tải về; frontend trỏ thẳng `<img src="/media/<project_id>/<media_id>.png">`.

---

## 9. Job nền & tiến độ

- `services/jobs.py`: `JobManager` in-process (asyncio). Mỗi job có `id, type, status, progress, message`.
- API tạo job trả `job_id` ngay; worker chạy async; cập nhật DB + **broadcast WS**.
- Batch (*Auto generate*) = tạo nhiều job con + 1 job cha gộp tiến độ, chạy **tuần tự**
  (không song song) để tôn trọng rate-limit.
- **Rate-limit (xem §5.2):** sau mỗi ảnh chờ **2–6s**; giữa hai video chờ **15–30s**.
- **Poll video:** worker tự gọi `/api/flow/check-status` với `{media:[{name, projectId}]}`
  tới khi `mediaGenerationStatus = SUCCESSFUL`, rồi resolve URL qua `media/{mediaId}`.
- **Đổi tên tự động:** ngay khi ảnh/video xong → `change-displayname` bằng `workflow_id`.
- **Tải về local:** sau đổi tên → `media/{primaryMediaId}` lấy URL → tải file về
  `./media/<project_id>/<media_id>.<ext>` → lưu `*_path`. Mỗi **~6 URL ảnh** nghỉ **2–6s**.
- **Hiển thị:** frontend đọc **file local** (`/media/...`); chỉ khi thiếu mới tải lại từ `primary_id`.

### 9.1 Single-flight tới Flow (extension dùng chung)
Extension là **một kênh WS duy nhất** → mọi call Flow (ảnh/video/poll/get-url) phải đi qua
**một hàng đợi serialize toàn cục** (asyncio lock/queue) trong agent. Lý do: nếu batch và
thao tác tay (⚡ gen nhanh, Node Editor) chạy song song, request đan nhau làm hỏng rate-limit
và có thể lẫn captcha. Quy tắc: **tất cả lệnh Flow xếp 1 hàng**; rate-limit (§5.2) tính trên
hàng này; poll video không chặn submit khác (poll riêng, nhịp giãn). UI hiện "đang bận" khi
hàng đợi đầy.

### 9.2 Lỗi & retry
- Mỗi item (shot/entity) có `status`: `pending | running | done | error` + `error` text.
- Lỗi Flow hay gặp: hết credit, captcha fail, transient 5xx, media chưa sẵn sàng. Worker
  **retry có backoff** (vd 3 lần, 5→15→30s) cho lỗi tạm; lỗi cứng (hết credit) → dừng + báo.
- UI: thẻ lỗi có badge đỏ + nút **Thử lại**; batch **bỏ qua item lỗi**, chạy tiếp, tổng kết
  cuối ("3 lỗi / 20"). Tham chiếu phân loại lỗi của skill `fk-doctor`.

---

## 10. Phụ thuộc thêm

- Backend: `aiosqlite` (hoặc stdlib). **ffmpeg** (binary). `pywinpty` (đã có, cho `agy`).
- Frontend: Node + toolchain Vite/React/Tailwind/React-Query/Zustand + **React Flow (@xyflow/react)** cho Node Editor.
- Cần: extension kết nối (Flow auth), OmniVoice URL cấu hình, `claude`/`agy` đã đăng nhập.

---

## 11. Kế hoạch triển khai (theo phase)

| Phase | Nội dung | Kết quả kiểm chứng |
|-------|----------|--------------------|
| **0. Scaffolding** ✅ | `studio/db.py`+schema, `studio/media_store.py`, `api/studio.py` (project CRUD + flow-projects import + thumbnail cache + `/settings`,`/options`,`/health`), `webapp/` React+Vite+Tailwind (ProjectGrid có thumbnail, CreateModal, Workspace 5 tab, StatusPills), mount `/media` + SPA | **ĐÃ XONG & verify thật:** tạo/list/xóa project; thumbnail tải-cache-serve (200/png); SPA serve tại `/`; health xanh |
| **1. Script** ✅ | `studio/brain.py` (agent JSON + scene parser + prompt templates); `/script/generate`, `/script`, `/script/chat`, `/scenes`; ScriptTab (GeneratePanel idea+duration, Courier editor, ChatBox, scenes sidebar) | **ĐÃ XONG & verify thật:** claude sinh script từ idea (est 24s, 2 scene); chat thêm scene 3; parse + lưu scenes OK |
| **2. Assets** ✅ | brain entity-extract + per-type design-sheet prompts; `/entities/extract`, `/entities` CRUD, `/entities/{id}/generate`, `/entities/{id}/image` (từ media_id), `/assets/generate-all` (throttle 2–6s, idempotent); AssetsTab (3 nhóm, AssetCard ⚡/🗑, extract/auto-gen) | **ĐÃ XONG & verify thật:** trích 4 entity (đúng loại); gen ảnh character design-sheet → tải local 451KB; rename trên Flow |
| **3. Storyboard** ✅ | brain autofill ({Entity} tokens); `/scenes/{id}/storyboard/autofill`, shot CRUD/insert, `/shots/{id}/image` (refs {handle}+auto location, ≤10), `image-from-media`, scene/project generate-all; StoryboardTab (scene grids, MediaCard, FramePanel RefPicker, Lightbox) | **ĐÃ XONG & verify thật:** autofill 4 frame (refs tự gồm location); gen frame → ảnh có reference tải local 785KB |
| **4. Shots** ✅ | brain visual/motion prompts; `/shots/{id}/prompts`, `/video` (i2v submit → poll inline → download), `/upscale`, `/shots/generate-all` (throttle 15–30s); ShotsTab (video MediaCard hover-play, ShotPanel preview/prompts/AI/upscale) | **ĐÃ XONG & verify thật:** i2v render → poll done → video tải local 2.2MB mp4 |
| **5. Assemble** ✅ | `assembler.py` (ffmpeg normalize+concat, narration mux -shortest=fit), `davinci_xml.py` (FCP7 xmeml); `/shots/{id}/narration` (AI+TTS), `/assemble`, `/export` (SEO+SRT+thumbnail), `/export/davinci-xml`; mount `/studio-media`; AssembleTab | **ĐÃ XONG & verify thật:** ghép 2 clip (mixed res/fps→chuẩn hóa) → final.mp4 5s; DaVinci XML hợp lệ 120f |
| **6. Node Editor** ✅ | `studio/graph.py` (topo-sort + cycle check + executor: prompt/refs/image/editImage/video/output → Flow ops); `/shots|entities/{id}/graph` GET/PUT + `/graph/run`; NodeEditor (React Flow, palette, inspector, Save/Run), ✎ trên MediaCard + AssetCard | **ĐÃ XONG & verify thật:** topo-sort + cycle detect; chạy đồ thị prompt→image→output → ảnh gán vào entity |
| **7. Polish** ✅ | SettingsDrawer (agent/image-model/style/tier/OmniVoice URL + dependency status), ⚙ trên header, README Flow Studio | **ĐÃ XONG & verify thật:** options/settings get-put; SPA serve; tất cả 5 tab + node editor + settings hoạt động |

Ước lượng: mỗi phase ~1 mốc làm việc; Phase 0–1 là nền tảng quan trọng nhất.

---

## 12. Rủi ro & điểm cần chốt thêm

- **Phụ thuộc extension/auth:** không có extension thì không sinh được media → UI phải báo trạng thái rõ (banner đỏ) và chặn hành động.
- **URL phái sinh + cache local:** tải media về `./media/<project_id>/...` ngay khi tạo xong; hiển thị từ file local, không gọi URL mỗi lần. `media/{primary_id}` (lấy URL) bị rate-limit → mỗi ~6 URL ảnh nghỉ 2–6s.
- **Độ tin cậy output AI:** model có thể trả JSON sai → cần retry + validate schema; cho sửa tay.
- **Giới hạn credit/đồng thời của Flow:** batch *Auto generate* nên throttle. Extension là kênh dùng chung → **serialize mọi call Flow qua 1 hàng đợi** (§9.1) để tránh đan request/captcha.
- **Aspect ảnh ≠ aspect video:** hai enum khác nhau; phải map để ảnh storyboard khớp khung video (§5.3).
- **ffmpeg/`agy`:** cần cài sẵn; `agy` chạy PTY và phải đăng nhập.
- **Frame/shot (ĐÃ CHỐT):** Storyboard chứa ảnh của scene, Shots render video từ chính ảnh đó → quan hệ 1:1, gộp làm một bản ghi `shot` (§4). Hai tab là hai view trên cùng bản ghi.
- **Đồng bộ với skill `fk-*`:** v1 dùng store SQLite riêng; nếu cần CLI skills đọc chung dữ liệu, cân nhắc export/import hoặc thống nhất store ở v2.
- **Sync storytelling không tuyệt đối:** video sinh-tạo không khớp từng frame; đồng bộ ở mức **beat/clip** (1 hành động = 1 clip, trim theo audio) + motion prompt. Hành động phức tạp nên tách nhiều beat. Cho chỉnh mốc cắt thủ công + xuất XML để tinh chỉnh trong Resolve.
- **Beat dài hơn clip Veo (ĐÃ CHỐT):** clip ≈8s. Beat audio >8s → **tự tạo thêm shot bù** (`ceil(dur/8)` shot con), nối tiếp bằng chain frame cuối→start image, motion prompt tiếp diễn, shot cuối trim khít. Phủ đủ độ dài audio của beat.
- **DaVinci XML tương thích:** ưu tiên FCP7 xmeml (Resolve đọc ổn); cần đúng `timebase`/fps và đường dẫn `file://` hợp lệ trên Windows. Nếu lệch, fallback cân nhắc FCPXML hoặc EDL+media. Cần test import thực trên Resolve.

---

## 13. Đề xuất bổ sung (tùy chọn — bạn chọn cái nào vào v1)

Các ý dưới đây **chưa đưa vào phạm vi**; liệt kê để bạn cân nhắc:

| # | Bổ sung | Giá trị | Ghi chú |
|---|---------|---------|---------|
| 1 | **Nhạc nền (Suno)** trong Assemble | Cao cho video kể chuyện | Dùng skill `fk-gen-music`; thêm track audio nền, ducking dưới giọng đọc |
| 2 | **Chọn 1 trong N ảnh ứng viên** | Cao | `generate-image` có thể trả nhiều ảnh; cho user chọn bản đẹp thay vì lấy ảnh đầu |
| 3 | **Hiển thị credit + cảnh báo** ở TopNav | Cao | Gọi `/api/flow/credits`; chặn batch nếu thiếu (đã có ước tính ở §2.10) |
| 4 | **Kéo sắp xếp lại scene/shot** | Trung bình | Reorder bằng drag (hiện mới có chèn/thêm/xóa) |
| 5 | **Export/Import project (.zip)** | Trung bình | Gói `studio.db` rows + `./media` → backup/di chuyển máy |
| 6 | **Khóa seed / tái lập** | Trung bình | Lưu + cho nhập seed để tái tạo ảnh/video giống hệt |
| 7 | **Ngôn ngữ UI tiếng Việt** | Trung bình | i18n; mặc định tiếng Việt theo người dùng |
| 8 | **Phiên bản media (history)** | Thấp | Giữ các lần gen cũ để hoàn tác thay vì ghi đè |
| 9 | **Upload YouTube ngay trong app** | Thấp | Dùng skill `fk-youtube-upload` (hiện để optional ngoài luồng) |

Khuyến nghị cho v1: **#1, #2, #3** (bám sát chất lượng output + tránh lãng phí credit).

---

## 14. Tóm tắt một dòng

Webapp `Flow Studio` = lớp điều phối SQLite + React 5-tab phủ lên các API có sẵn,
với AI-agent (claude/agy) làm bộ não sinh kịch bản/mô tả/prompt, Flow sinh ảnh-video,
OmniVoice lồng tiếng, ffmpeg ghép — đưa từ ý tưởng tới `final.mp4` ngay trên trình duyệt.
Hỗ trợ **chế độ storytelling** (giọng đọc dẫn dắt, hình bám sát thời điểm đọc) và
**export DaVinci Resolve XML** để dựng/chỉnh cuối chuyên nghiệp.
