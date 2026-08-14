# Flow Kit

Minimal Google Flow API proxy: FastAPI + WebSocket server (`agent/`) + Chrome
extension (`extension/`). No local DB, no queue, no skills — a pure relay to the
Google Flow API via the extension.

Base URL: `http://127.0.0.1:8100`

## Pre-flight

```bash
curl -s http://127.0.0.1:8100/health
# Must return: {"status":"ok", "extension_connected": true, ...}
```

## Run

```bash
python -m agent.main   # HTTP on :8100, extension WebSocket on :9222
```

## Layout

- `agent/main.py` — app entry, extension WebSocket, `/health`, `/api/ext/callback`
- `agent/api/flow.py` — all `/api/flow/*` endpoints
- `agent/api/tts.py` — `/api/tts/*` proxy to the OmniVoice server on Google Colab
  (set the rotating Colab URL via `PUT /api/tts/config` or `OMNIVOICE_BASE_URL`)
- `agent/api/ai_agent.py` — `/api/agent/*` runs coding-agent CLIs (Claude Code,
  Antigravity) headless as subprocesses. Registry in `config.py` (`AI_AGENTS`),
  env-overridable. Defaults to bypassing CLI permissions — local-only.
- `agent/services/flow_client.py` — relays requests to the extension over WS
- `agent/services/headers.py` — randomized headers
- `agent/config.py`, `agent/models.json` — endpoints + model keys
- `extension/` — Chrome MV3 extension (token capture, reCAPTCHA, Flow calls)

## Notes

- **Mỗi dự án thuộc về một tài khoản Flow.** Extension đọc account đang đăng nhập từ
  `labs.google/fx/api/auth/session` và đẩy lên agent; `project.account_id` ghi lại chủ sở
  hữu. `/studio/projects` chỉ trả dự án của account hiện tại, mọi endpoint đụng tới dự án
  của account khác trả 403. Chưa xác định được account → không lọc, chỉ cảnh báo trên UI.
  Xem [agent/studio/accounts.py](agent/studio/accounts.py).
- **Hai kiểu nhạc, đừng lẫn.** `project.bgm_path` = MỘT bài trộn chìm dưới lời đọc (⚙ cấu
  hình dự án). Bảng `music_track` = playlist nhiều bài của chế độ music video
  (`project.music_mode`): nhạc là tiếng duy nhất, các bài cách nhau `music_gap` giây, và tổng
  thời lượng playlist quyết định độ dài video — hình được lặp cho phủ kín, thừa thì cắt.
  Xem [agent/studio/music.py](agent/studio/music.py) + tab "Nhạc" trong workspace.
- **⚡ tạo nhanh CHẠY chính đồ thị của shot/entity** (`_gen_via_graph` → `run_graph` với
  `only_node` = node sinh nối vào Output), nên nó và Node Editor ra kết quả y hệt nhau. Chỉ
  chạy đúng node đó, không chạy cả đồ thị — node phía trên giữ nguyên kết quả đã có. Chưa có
  đồ thị → rơi về đường dựng prompt trực tiếp, vốn tương đương đồ thị mặc định. Ngoại lệ:
  beat dài hơn một clip vẫn đi `_chained_video` (đồ thị chỉ mô tả MỘT clip).
  Mọi đường kết thúc ở `_commit_shot_media` / `_commit_entity_media` (tải về, ghi DB, lịch sử
  phiên bản, đổi tên trên Flow, auto hi-res/upscale).
- **Prompt header/footer đi bằng NODE, không chèn ngầm.** Chỉ vào prompt khi có node
  `promptHeader` / `promptFooter` nối vào node tạo ảnh/tạo video; node để text rỗng = lấy
  `project.prompt_header/footer`. `compose_prompt(..., header=, footer=)` là chỗ phân nhánh.
  Chỉ `image`/`video` nhận bọc — `editImage`/`replacebg` chạy prompt nguyên văn.
  Xem [agent/studio/graph.py](agent/studio/graph.py).
- **Prompt NGẦM nằm ở một chỗ duy nhất: `brain.PROMPT_DEFAULTS`.** Guard khung đơn, câu ngôn
  ngữ chữ trong ảnh, ba mẫu sheet nhân vật/đạo cụ/bối cảnh, khối CINEMATOGRAPHY và MOTION —
  tất cả đọc qua `brain.prompt_part(project, key)`. Mỗi khoá `k` có cột `project.tpl_<k>`:
  trống = mặc định trong code, `"-"` = tắt hẳn, khác = nguyên văn người dùng. Thêm khối ngầm
  mới thì thêm vào `PROMPT_DEFAULTS` + migration `tpl_<k>` + `PROMPT_KEYS` ở webapp, đừng nội
  suy thẳng hằng số vào prompt. Xem tab Thiết lập → 🧩 Prompt ngầm.
  **Bản mặc định được CHÉP vào DB**, không để trống: dự án mới lấy `brain.default_tpl_row()`,
  dự án cũ được `brain.seed_prompt_defaults()` bù lúc khởi động (chỉ đụng ô rỗng, chạy lại
  không đè). Hệ quả: sửa mặc định trong code KHÔNG lan sang dự án đã có — muốn lan thì phải
  bấm "Đặt lại" từng ô. `prompt_part` vẫn rơi về mặc định khi ô rỗng, nhưng đó là lưới an
  toàn chứ không còn là đường chính.
- **Prompt VIDEO cũng phải đi qua `compose_prompt`, với `media="video"`.** Ảnh và video dùng
  hai khối ngôn ngữ khác nhau (`image_text` / `video_text`) vì model video hiểu "in the image"
  là ảnh tham chiếu rồi vẫn bịa biển hiệu tiếng Trung vào các frame sau. Đường không qua đồ
  thị (`_generate_shot_video` fallback, `_chained_video`) bọc bằng `_video_prompt(...)`, tương
  đương node "Tạo video" — đừng gửi thẳng `motion_prompt` cho `_clip_submit`.
- **Ảnh bối cảnh: lưới 4 khung hay một ảnh.** `project.location_frames` (4 mặc định | 1) đổi
  ba thứ CÙNG LÚC — mẫu prompt (`sheet_location` vs `sheet_location_one`), việc dán nhãn bốn
  ô lên bản hiển thị (`label_quadrants`, 3 chỗ gọi), và đoạn phụ `single_frame_grid` của guard
  khung đơn. Đọc qua `brain.location_frames(project)`, đừng kiểm tra cột trực tiếp.
- **Token `{tên}` lặp lại = Flow trả 400, nên prompt do NGƯỜI DÙNG viết luôn bật `dedupe_refs`.**
  `_build_structured_parts` biến mỗi `{tên}` khớp reference thành một reference part; gọi lại
  cùng một entity ở nhiều câu thì sinh nhiều part trỏ CÙNG một `mediaId` trong khi `imageInputs`
  chỉ có một mục, và Flow trả 400 `INVALID_ARGUMENT`. Đo trên shot thật của Book-03-chapter-37:
  **33 part / 16 reference → 400**, `dedupe_refs=True` còn 11 part / 5 reference → chạy, cùng
  nguyên văn prompt. Với dedupe, ảnh được ĐỊNH NGHĨA ở lần nhắc đầu (giữ nguyên ngoặc, bind vào
  ảnh) còn các lần sau rơi xuống chữ thường — model chỉ cần biết ảnh này TÊN gì một lần. Đã bật:
  node `image` của Node Editor, `replacebg`, frame shot, candidates, `POST /api/flow/generate-image`
  (mặc định `true`); `generate_video_from_references` bật cứng vì prompt timeline gọi lại cùng
  một frame ở nhiều mốc là chuyện thường. Kèm theo, `push_text` phải GỘP mảnh text vào part liền
  trước: mỗi token không bind cắt đoạn văn làm đôi, để mỗi mảnh thành một part thì structuredPrompt
  vụn ra hàng chục mảnh và cũng 400. Đừng đổ cho prompt dài — 9306 ký tự chạy tốt, 6078 ký tự vẫn
  hỏng khi part bị vụn. Triệu chứng đánh lừa: agent báo *"Flow không trả media (có thể bị chặn)"*
  vì `res["error"]` rỗng; muốn thấy mã lỗi thật thì gửi lại qua `POST /api/flow/generate-image`.
- **`bind_unreferenced` cho ảnh người dùng CỐ Ý nối vào.** Reference mà prompt không gọi tên chỉ
  đi lên dưới dạng `imageInputs` vô danh và model gần như bỏ qua — kết quả trông như một lượt sinh
  mới, chẳng liên quan ảnh tham chiếu. Bật ở node `image` và `replacebg` của Node Editor (người
  dùng kéo dây vào là cố ý). ĐỪNG bật nơi references là kho ứng viên để prompt tự chọn theo tên
  (candidates, frame storyboard): bind một entity shot không nhắc tới là mời model vẽ thêm nhân
  vật vào khung.
- **Engine video do `project.video_model` quyết định, luật nằm ở `graph.video_engine`.** Một
  chỗ duy nhất đọc cột đó; `api/studio.py._video_engine` gọi lại nó, nên Node Editor và ⚡ tạo
  nhanh không bao giờ chạy hai engine khác nhau. Giá trị: `"4"/"6"/"8"/"10"` → Omni Flash;
  `"veo_lite"`/`"veo_lite_4"` → Veo 3.1 Lite; `"veo"` → ép Veo trả tiền theo tier; **rỗng =
  mặc định**, và mặc định của tài khoản Ultra (`PAYGATE_TIER_TWO`) là **Veo Lite**. Thêm engine
  mới thì sửa `video_engine` + `_R2V_ENGINES` + `_engine_model_key` + `_clip_submit`, đừng rải
  thêm nhánh `if engine == ...` chỗ khác.
- **`veo_3_1_*_lite_low_priority` là bản 0 credit; `*_lite` KHÔNG.** "Veo 3.1 - Lite [Lower
  Priority]" (0đ, chỉ Ultra) và "Veo 3.1 - Lite" (vẫn tính tiền) là HAI model khác nhau, chỉ
  khác đuôi `_low_priority` trong key. Ba key trong `models.json → veo_lite_models`, chọn theo
  ảnh truyền vào chứ không theo cờ: start+end → `interpolation`, chỉ start → `i2v`, không start
  → `r2v` ("inference"). Đổi key ở đó là đổi hoá đơn — kiểm lại đuôi trước khi sửa.
  **Độ dài: chỉ kiểu nội suy mới chọn được (4/6/8s)**, và nó nằm TRONG model key như Omni
  Flash chứ không phải một field riêng — `veo_lite_frame_models` trong models.json. Tên key
  không đều, đừng suy ra theo công thức: 4s/6s là `veo_3_1_i2v_s_lite_{4,6}s_fl_low_priority`
  còn 8s lại là `veo_3_1_interpolation_lite_low_priority`. Inference và i2v thì Flow cứng 8s
  nên `duration_s` bị bỏ qua. Ngoài Omni Flash ra, mọi engine đều 8s ở cấp dự án —
  `_omni_duration` chỉ trả số cho Omni.
- **Credit: chỉ VIDEO tính tiền.** Render clip ≈20 (0 với Veo Lite), upscale video lên **4K
  ≈50** (đắt hơn cả một lượt render mới), lên 1080p = 0. Mọi thao tác ẢNH đều 0 credit — kể cả
  upscale ảnh lên 2K/4K — nên đừng cảnh báo hay hỏi xác nhận trước batch ảnh. Bảng giá +
  `videoCost()` / `upscaleVideoCost()` ở [webapp/src/lib/credits.ts](webapp/src/lib/credits.ts).
- `media_id` is always UUID format (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`), never `CAMS...`
- The agent holds no state; all generation goes through the connected extension.
  If `extension_connected: false`, open Google Flow in Chrome with the extension loaded.
- See [README.md](README.md) for the full endpoint table.
