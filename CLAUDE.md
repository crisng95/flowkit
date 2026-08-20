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
- **Các khối prompt nối bằng `brain.join_blocks` — mỗi khối một ĐOẠN, cách nhau dòng trống.**
  Header, style, culture_hint, body, guard khung đơn, footer, câu ngôn ngữ chữ, và mô tả entity
  vs mẫu sheet: tất cả là khối riêng. Trước đây nối bằng `". "` nên header dài 6 đoạn + style +
  mô tả + khối JSON 26KB của sheet nhân vật dính thành MỘT dòng, và chỗ nối đẻ ra `".."` khi
  khối trước đã có dấu chấm — mẫu bible thì lại bảo model đọc "the character description written
  immediately before this JSON" trong khi ranh giới ấy không nhìn thấy được. Thêm khối mới thì
  đưa vào `join_blocks`, đừng `f"{a}. {b}"`.
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
- **Mẫu sheet KHÔNG được tự đặt phong cách — style của dự án là nguồn duy nhất.** `sheet_location`
  và `sheet_location_one` từng kết thúc bằng "Photoreal, cinematic, deep detail". `compose_prompt`
  đặt style TRƯỚC rồi mới tới body, nên câu photoreal đứng sau ăn đứt style: dự án anime/comic ra
  ảnh bối cảnh ẢNH THẬT, trong khi sheet nhân vật/đạo cụ (không có câu đó) vẫn đúng style. Hậu quả
  nhìn thấy ở storyboard là ba triệu chứng tưởng rời nhau: bối cảnh khung hình khác hẳn ảnh tham
  chiếu (model không hoà giải nổi anime + ảnh thật nên tự bịa), vài khung tự dưng ra ảnh thật (khi
  nó bám ảnh tham chiếu), và nhân vật kém ổn định. Đo trên dự án "Hà Nội – Mưa đêm phố cổ": 39/39
  dự án đều dính, 38 dự án có style không phải photoreal. Thêm câu về chất liệu/độ chân thực vào
  mẫu sheet là lặp lại đúng lỗi này.
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
- **Flow thay reference part bằng CHÚ THÍCH TỰ SINH của ảnh đó — nên ảnh ref là bảng sheet thì
  model được bảo vẽ một bảng sheet.** Tên handle KHÔNG đi lên model: đo trên cùng hai ảnh, handle
  `{Mai}`/`{Phố Hàng Mã}` và handle vô nghĩa `{nhan vat}`/`{boi canh}` cho prompt tới Flow **giống
  hệt nhau từng ký tự** — `"Character design sheet for a woman walking down a street, in the style
  of the first image. The street is a rainy street market with lanterns, as seen in the second
  image."` Sheet 13 mục của nhân vật bị chú thích thành *"Character design sheet"*, và câu ấy đứng
  ĐẦU prompt: 3/3 biến thể ra lại một bảng 13 mục có tiêu đề + bảng màu + ô chất liệu, hoặc người
  cao bằng cả khung kèm panel chi tiết dán bên cạnh — thứ trông như "lỗi tỷ lệ" thật ra là layout
  sheet còn sót. Hệ quả: **ảnh ref nên là ảnh mà chú thích tự nhiên của nó ĐÚNG là thứ ta muốn nói**
  (một con người, một con phố). Bật `project.character_one` để ảnh nhân vật là một ảnh toàn thân
  thay vì bảng. Kèm theo, guard khung đơn bật cho MỌI node ảnh có ref, không chỉ shot
  ([graph.py](agent/studio/graph.py)). Muốn biết model thật sự nhận gì thì đọc
  `response.media[].image.generatedImage.prompt` — đừng đoán từ prompt mình gửi.
  Cũng ở đó: prompt tiếng Việt nhắc lại tên entity bằng chữ (do `dedupe_refs` hạ lần nhắc thứ hai
  xuống chữ thường) làm bản dịch **rụng mất hai mệnh đề trỏ ảnh** "in the style of the first image"
  / "as seen in the second image", chỉ còn mô tả bằng lời → model tự bịa một bối cảnh khớp mô tả.
  Prompt tiếng Anh mô tả KẾT QUẢ (kèm mốc neo tỷ lệ: "her head reaches the height of the shop
  doorways, she occupies one third of the frame height") giữ nguyên văn và ra đúng 4/4 lượt.
- **`bind_unreferenced` cho ảnh người dùng CỐ Ý nối vào.** Reference mà prompt không gọi tên chỉ
  đi lên dưới dạng `imageInputs` vô danh và model gần như bỏ qua — kết quả trông như một lượt sinh
  mới, chẳng liên quan ảnh tham chiếu, và trên Flow thì workflow hiện ra "không có ảnh tham chiếu
  nào". Bật ở node `image`, `editImage` và `replacebg` của Node Editor (người dùng kéo dây vào là
  cố ý). Với `editImage` nó gần như BẮT BUỘC: prompt sửa ảnh hầu như không ai viết `{token}` ("xoá
  cái xe đi"), nên không bật là mọi ảnh nối thêm đều bị bỏ qua. ĐỪNG bật nơi references là kho ứng
  viên để prompt tự chọn theo tên (candidates, frame storyboard): bind một entity shot không nhắc
  tới là mời model vẽ thêm nhân vật vào khung.
- **Flow DỊCH prompt không phải tiếng Anh, và bản dịch đánh rơi câu PHỦ ĐỊNH.** Prompt sửa ảnh
  phải viết bằng TIẾNG ANH, mô tả KẾT QUẢ mong muốn. Đo trên ảnh phố Hàng Mã thật, cùng một ảnh
  nguồn, chỉ đổi ngôn ngữ prompt:
  - `"xoá bỏ người và xe khỏi ảnh {hang ma src}"` → Flow ghi lại thành
    `"Busy street with festive decorations in first image."` (mất sạch câu lệnh, chỉ còn chú
    thích tự sinh của ảnh) → ảnh ra có ~60 người, gốc chỉ ~15. **Thêm, không xoá.**
  - `"Remove every person and every vehicle from this street. No pedestrians… Keep every shop,
    lantern, tree, building… exactly as they are."` → Flow giữ NGUYÊN VĂN → phố sạch bóng người,
    hàng quán/đèn/cây y nguyên.
  Prompt tiếng Việt KHÔNG phủ định thì vẫn sống ("làm sáng khuôn mặt" → "slightly brighten the
  face"); chỉ câu xoá/bỏ/không-có mới bị bản dịch nuốt. Xem `response.media[].image
  .generatedImage.prompt` để biết Flow THẬT SỰ nhận được gì — đó là chỗ soi mọi ca "model làm
  ngược ý tôi", đừng đoán từ prompt mình gửi.
  **Đã sang tiếng Anh rồi thì đừng tinh chỉnh câu chữ nữa — biến còn lại là SEED.** Chạy 4 lượt
  cùng ảnh, hai cách diễn đạt (một câu gọn vs. liệt kê "no motorbikes, no bicycles… anywhere" +
  "empty pavement"): xe máy dựng trên vỉa hè còn sót ở CẢ BỐN, và bản liệt kê kỹ hơn có lượt còn
  sót nhiều hơn bản gọn. `edit_image` dùng `seed = ts % 1000000` (ngẫu nhiên mỗi lượt) nên cùng
  một prompt ra kết quả khác nhau. Cách đúng là tăng `count` lên 2-4 rồi chọn bản sạch nhất, chứ
  không phải viết lại prompt lần thứ năm.
- **`IMAGE_INPUT_TYPE_BASE_IMAGE` không hiện trong danh sách ảnh tham chiếu của Flow UI** — đó là
  CHUYỆN BÌNH THƯỜNG, không phải ảnh chưa được attach. Flow chỉ liệt kê thumbnail cho input kiểu
  `REFERENCE`; ảnh nền của một lượt sửa vẫn được model dùng (kiểm bằng cách đọc
  `generatedImage.prompt` — Flow chèn chú thích của chính ảnh đó vào). Đừng đổi BASE_IMAGE sang
  REFERENCE chỉ để thấy thumbnail: đã đối chiếu hai đường trên cùng ảnh + cùng prompt tiếng Anh,
  BASE_IMAGE cho kết quả sát ảnh gốc hơn.
- **Dựng `structuredPrompt` thì THÊM part, đừng LỌC BỎ part.** Bỏ một reference part nằm GIỮA câu
  làm hai mảnh text hai bên dính thành hai part text liền kề — đúng kiểu vụn part khiến Flow trả
  400 (`push_text` chỉ gộp được lúc đang duyệt, không cứu được khâu lọc sau). `edit_image` từng
  dựng part rồi lọc mọi part của ảnh nền ra; giờ nó đưa ảnh nền vào `_build_structured_parts`
  cùng các reference khác rồi mới bù ở đầu nếu prompt không nhắc tới. Cùng lý do, mọi đường dùng
  prompt do NGƯỜI DÙNG viết đều `dedupe=True` — `edit_image` mặc định bật.
- **Engine video do `project.video_model` quyết định, luật nằm ở `graph.video_engine`.** Một
  chỗ duy nhất đọc cột đó; `api/studio.py._video_engine` gọi lại nó, nên Node Editor và ⚡ tạo
  nhanh không bao giờ chạy hai engine khác nhau. Giá trị: `"4"/"6"/"8"/"10"` → Omni Flash;
  `"veo_lite"`/`"veo_lite_4"` → Veo 3.1 Lite; `"veo"` → ép Veo trả tiền theo tier; **rỗng =
  mặc định**, và mặc định của tài khoản Ultra (`PAYGATE_TIER_TWO`) là **Veo Lite**. Thêm engine
  mới thì sửa `video_engine` + `_R2V_ENGINES` + `_engine_model_key` + `_clip_submit`, đừng rải
  thêm nhánh `if engine == ...` chỗ khác.
  **"Shot này render video được không" cũng chỉ hỏi MỘT chỗ: `_shot_video_blocker`.** Thiếu ảnh
  frame không còn là lỗi chung — Omni Flash và Veo Lite chạy text-to-video. Chỉ Veo trả tiền
  (i2v cần `startImage`) và shot dài hơn MỘT clip (nối clip lấy khung cuối clip trước làm ảnh
  đầu clip sau) mới thật sự cần ảnh. ⚡ từng shot gọi nó để BÁO LỖI, ✦ sinh hàng loạt gọi nó để
  LỌC; hai bên lệch nhau thì batch lẳng lặng bỏ qua đúng những shot ⚡ vẫn chạy được. Client
  không chép lại luật này — để server trả lời.
  **✦ sinh hàng loạt chạy theo LÔ, nhưng lô video nhỏ và giãn hơn hẳn lô ảnh.** Ảnh: 4/lô,
  cooldown ~10s, stagger phần mười giây. Video: `VIDEO_BATCH_SIZE=3`, cooldown 20–30s,
  stagger 4–8s — vì bắn 4 submit video thật sự đồng thời từng bị Google chặn ("hoạt động
  bất thường", 3/4 lượt hỏng) trong khi batch 4 ảnh chạy êm. Thứ thật sự tiết kiệm thời gian
  KHÔNG phải submit song song mà là POLL song song: submit đi qua single-flight lock của
  `flow_client` nên vốn đã nối đuôi nhau, còn render mất 30–240s. Cả lô dùng chung một
  `mediaGenerationContext.batchId` (`batch_id` xuyên từ `JobManager._run_batched` →
  `_generate_shot_video` → `_clip_submit`/`run_graph` → `flow_client`), đúng như Flow UI làm.
- **`veo_3_1_*_lite_low_priority` là bản 0 credit; `*_lite` KHÔNG.** "Veo 3.1 - Lite [Lower
  Priority]" (0đ, chỉ Ultra) và "Veo 3.1 - Lite" (vẫn tính tiền) là HAI model khác nhau, chỉ
  khác đuôi `_low_priority` trong key. BỐN key trong `models.json → veo_lite_models`, chọn theo
  ảnh truyền vào chứ không theo cờ: start+end → `interpolation`, chỉ start → `i2v`, chỉ
  reference → `r2v` ("inference"), KHÔNG ảnh nào → `t2v`. Đổi key ở đó là đổi hoá đơn — kiểm
  lại đuôi trước khi sửa.
  **Không ảnh nào KHÔNG phải lỗi thiếu ảnh — đó là text-to-video.** Đúng như Omni Flash: một
  endpoint riêng (`video:batchAsyncGenerateVideoText`) + một key riêng
  (`veo_3_1_t2v_lite_low_priority`), và riêng đường này Flow UI luôn gửi kèm
  `outputSpec.resolution = VIDEO_RESOLUTION_720P`. Gửi key r2v mà bỏ `referenceImages` đi thì
  Flow trả 400. Trước đây cả `flow_client` lẫn node "Tạo video" đều dựng hàng rào "cần ít nhất
  1 ảnh tham chiếu", nên cách dùng đơn giản nhất — gõ prompt rồi bấm tạo — là cách DUY NHẤT bị
  chặn, dù Flow vẫn làm được. Đừng dựng lại hàng rào đó.
  **Độ dài: chỉ kiểu nội suy mới chọn được (4/6/8s)**, và nó nằm TRONG model key như Omni
  Flash chứ không phải một field riêng — `veo_lite_frame_models` trong models.json. Tên key
  không đều, đừng suy ra theo công thức: 4s/6s là `veo_3_1_i2v_s_lite_{4,6}s_fl_low_priority`
  còn 8s lại là `veo_3_1_interpolation_lite_low_priority`. Inference và i2v thì Flow cứng 8s
  nên `duration_s` bị bỏ qua. Ngoài Omni Flash ra, mọi engine đều 8s ở cấp dự án —
  `_omni_duration` chỉ trả số cho Omni.
- **Upscale VIDEO chỉ có 1080p và 4K — KHÔNG có 2K.** Mức 2K là của upsample ẢNH
  (`UPSAMPLE_IMAGE_RESOLUTIONS`: ONE → 2K, Ultra → 4K); đừng suy từ bên ảnh sang video. Danh
  sách mức video + thứ tự tăng dần khai ở `models.json → upscale_video_order` +
  `upscale_models`; `hires.py` đọc từ đó chứ không hardcode, vì thứ tự ấy vừa dùng để hạ lựa
  chọn của dự án xuống trần tier vừa dùng để cắt ra danh sách mức chọn được.
- **Credit: chỉ VIDEO tính tiền.** Render clip ≈20 (0 với Veo Lite), upscale video lên **4K
  ≈50** (đắt hơn cả một lượt render mới), lên 1080p = 0. Mọi thao tác ẢNH đều 0 credit — kể cả
  upscale ảnh lên 2K/4K — nên đừng cảnh báo hay hỏi xác nhận trước batch ảnh. Bảng giá +
  `videoCost()` / `upscaleVideoCost()` ở [webapp/src/lib/credits.ts](webapp/src/lib/credits.ts).
- **Ảnh ĐEM RA NGOÀI phải là bản hi-res, ảnh HIỂN THỊ trong app thì không.** `image_path` là
  bản HD Flow phát ra, đủ để xem chứ đem ra ngoài là thiếu nét; bản 2K/4K nằm ở
  `image_hires_path` và xin riêng qua `upsampleImage` (0 credit, trần theo tier: ONE → 2K,
  Ultra → 4K). Mọi đường tải ảnh ra ngoài phải đi qua `hires.shot_image()` hoặc
  `GET /shots/{sid}/image/download` — endpoint đó tự xin Flow bản nét khi thiếu rồi mới trả
  file, nên nút ⬇ ra 4K kể cả khi dự án không bật "tự tải bản 2K/4K". Đừng trỏ nút tải thẳng
  vào `image_path`.
- **Tier: `_current_tier()` đoán TIER_ONE khi chưa đọc được** — dùng thẳng nó cho việc chọn độ
  phân giải là âm thầm hạ 4K xuống 2K trên tài khoản Ultra. Chỗ nào có `project` thì gọi
  `_current_tier_for(project)`; nó rơi về cột `project.paygate_tier`, vốn được
  `_sync_project_tier` cập nhật mỗi lần mở dự án (cột đó chỉ được GHI LÚC TẠO, nên nâng gói
  xong mọi dự án cũ vẫn mang tier cũ nếu không đồng bộ).
- `media_id` is always UUID format (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`), never `CAMS...`
- The agent holds no state; all generation goes through the connected extension.
  If `extension_connected: false`, open Google Flow in Chrome with the extension loaded.
- See [README.md](README.md) for the full endpoint table.
