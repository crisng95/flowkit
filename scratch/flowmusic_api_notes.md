# Google Flow Music (flowmusic.app) — API notes (WIP)

Captured trực tiếp từ user qua DevTools, xác nhận từng endpoint một trước khi code.
KHÔNG đoán field ngoài những gì đã xác nhận ở đây.

## Kiến trúc

- Frontend: Next.js (`www.flowmusic.app`), Vercel.
- Backend chính của app: Next.js API routes `/__api/*` trên chính `www.flowmusic.app`
  — CÓ header `Authorization` (đã sửa lại — HAR trước đó bị Chrome/Edge lược bỏ header
  nhạy cảm khi export "Copy"). Cần xác nhận lại: token gì (Supabase JWT hay khác),
  header tên chính xác, có kèm cookie không. `sec-fetch-site: same-origin`.
- Auth provider: Supabase, tại `sb.flowmusic.app` (project ref `ednjccqcmbxeaxbidinr`).
  Gọi trực tiếp từ browser bằng `apikey` (anon key, public) + `Authorization: Bearer <supabase JWT>`.
- Captcha: Cloudflare Turnstile (site key `0x4AAAAAABF6ZHvFYAQ-ls6B`) — chưa rõ áp dụng ở
  bước nào (đăng nhập? tạo bài hát?).
- Media: file audio/video/ảnh serve qua `storage.googleapis.com/producer-app-public/...`.
- Analytics: PostHog (`ph.flowmusic.app`), bỏ qua.

## Endpoint đã xác nhận

### `GET https://sb.flowmusic.app/auth/v1/user`
- Lấy thông tin user hiện tại (Supabase Auth).
- Headers:
  - `apikey`: Supabase **anon key** — public, cố định, an toàn để hardcode
    (giống publishable key trong bundle JS, không phải secret).
  - `authorization: Bearer <supabase JWT>` — JWT **của từng user**, KHÔNG hardcode,
    KHÔNG lưu giá trị thật vào repo. Decode payload cho thấy:
    `sub` = user id, `email`, `app_metadata.provider: "google"`, `session_id`,
    `iat`/`exp` cách nhau **3600s (1h)** — giống hệt vòng đời token `ya29` của Flow
    video → dùng lại được pattern bắt token qua `webRequest` + alarm refresh 45' có sẵn.
  - `sec-fetch-site: same-site` (gọi cross-subdomain từ `www.flowmusic.app` sang
    `sb.flowmusic.app`, cùng site apex `flowmusic.app`).
- Response: Supabase user object đầy đủ — `id` (= user id dùng ở các URL khác, vd
  `/__api/users/{id}/playlists`), `email`, `user_metadata` (avatar_url, full_name, ...
  lấy từ Google profile), `identities[]`.
- **Ghi chú bảo mật**: user đã dán nguyên JWT thật vào chat — KHÔNG được ghi giá trị đó
  vào bất kỳ file nào trong repo (kể cả scratch/), vì repo này auto-commit+push mỗi
  prompt. Chỉ ghi cấu trúc/shape, không ghi giá trị token.

### `GET https://www.flowmusic.app/__api/billing/subscription`
- Auth: gửi **cả hai** — `authorization: Bearer <supabase JWT>` (cùng token dùng cho
  `sb.flowmusic.app`) **và** cookie session (`sb-sb-auth-token.0` / `.1` — Supabase SSR
  chẻ JWT+refresh_token ra nhiều cookie khi vượt giới hạn kích thước 1 cookie).
  → route `/__api/*` là Next.js API route dùng `@supabase/ssr`, đọc session từ cookie
  (SSR-style), header Authorization có vẻ là gửi kèm thêm chứ không chắc bắt buộc.
  **Kế hoạch cài đặt**: bắt Bearer token qua `webRequest` (như Flow video) + relay
  request từ background.js với `credentials: 'include'` (Chrome tự đính cookie thật
  của domain vì extension có host permission) — giống hệt cách `handleTrpcRequest`
  đã làm với `/fx/api/auth/session` của Flow, không cần tự dựng lại cookie.
- Response:
  ```json
  {
    "data": {
      "provider": "g1_entitlement",
      "subscription_tier": "plus",
      "subscription_plan": "plus-monthly",
      "current_period_end": null,
      "update_to": null,
      "cancel_at": null,
      "past_due": null
    },
    "has_g1_entitlement": "plus"
  }
  ```

### `GET https://www.flowmusic.app/__api/billing/credits`
- Auth: giống trên (Bearer + cookie).
- Response:
  ```json
  {
    "data": { "tokens_remaining": 126600.0, "credits_remaining": 10550.0 },
    "add_token_transactions": [
      { "id": "uuid", "created_at": "iso", "type": "daily-free", "hours": 0.1,
        "amount": 360, "credits": 30, "description": null },
      { "id": "uuid", "created_at": "iso", "type": "subscription-refill", "hours": 33.0,
        "amount": 120000, "credits": 10000, "description": null }
    ]
  }
  ```
  → hệ thống có 2 đơn vị: `tokens` (dùng để trừ khi generate, chi tiết trong
  `add_token_transactions`) và `credits` (hiển thị cho user, quy đổi ~1 credit = 12
  tokens theo 2 dòng mẫu trên: 360/30=12, 120000/10000=12). Loại giao dịch thấy được:
  `daily-free` (free hàng ngày), `subscription-refill` (nạp theo gói).

### `GET https://www.flowmusic.app/__api/projects?offset=0&limit=20`
- Auth: giống trên.
- Response mẫu (user chưa có project nào): `{"projects":[]}`
- Chưa biết shape 1 project item (user chưa tạo project) — sẽ ghi lại khi user tạo project
  hoặc thấy account nào có sẵn project.

### `GET https://www.flowmusic.app/__api/conversations?limit=30&offset=0`
- Auth: giống trên.
- Danh sách "conversation" (mỗi lượt chat/compose = 1 conversation, **nhạc tạo ra nằm
  trong từng conversation này**, chưa thấy field bài hát/clip ở list level).
- Response: mảng object:
  ```json
  {
    "id": "uuid",
    "created_at": "iso",
    "user_id": "uuid",
    "title": "string (tên tự sinh, có vẻ theo chủ đề bài hát)",
    "last_message_at": "iso",
    "is_thriller": null,
    "is_headless_space": false,
    "project_id": null
  }
  ```
- **Cần tiếp**: mở 1 conversation cụ thể (GET chi tiết theo id, hoặc
  `/__api/conversations/{id}` hoặc `/__api/conversations/{id}/messages`) để thấy shape
  bài hát/clip thật (audio url, lyrics, style, status...).

### `GET https://www.flowmusic.app/__api/conversations/{id}` — **PHÁT HIỆN LỚN: đây là AGENT CHAT, không phải REST tạo nhạc có tham số**

Response = `{id, created_at, title, user_id, project_id, messages: [...]}`. `messages[]` là
log message của một **agent framework kiểu PydanticAI** (`part_kind`:
`user-prompt` | `text` | `tool-call` | `tool-return` | `retry-prompt`, có `tool_name`,
`tool_call_id`, `usage{...}`). Nghĩa là:

- **Client KHÔNG tự gọi API sinh nhạc với tham số cấu trúc** (khác hẳn Flow video —
  `batchGenerateImages` với body cấu trúc rõ ràng). Client chỉ gửi **1 tin nhắn chat dạng
  văn bản tự nhiên** (vd mô tả bài hát, hoặc "Generate the video", "Check video status").
  Một AI agent chạy **phía server** đọc tin nhắn, tự quyết định gọi tool nào
  (`audio__create_song`, `image__create_image`, `video__create_music_video`,
  `synthetic__suggest_actions`...) với tham số do chính model đó tự soạn.
- Bằng chứng: 1 lần agent tự gọi `video__create_music_video` kèm `args` đầy đủ (client
  KHÔNG hề gửi các field này, đây là agent tự nhớ context) → bị server reject
  `"extra_forbidden... Extra inputs are not permitted"` → agent tự sửa, gọi lại với
  `args: {}` (rỗng) → thành công, trả `{job_id, message: "submitted job"}`. Việc tool
  schema đổi giữa 2 lần gọi (agent tự retry) chứng tỏ đây là function-calling nội bộ của
  LLM, không phải endpoint public nhận tham số đó trực tiếp.
- **Kết luận cho việc tích hợp**: KHÔNG cố tái tạo `audio__create_song`/
  `video__create_music_video` như REST call với tham số riêng — không có cửa đó. Muốn tự
  động hoá, chỉ có 1 cách: **POST một tin nhắn chat tự nhiên** vào conversation (giống hệt
  người dùng gõ prompt), để agent phía server tự lo phần còn lại. Input = văn bản mô tả
  bài hát (giống hệt prompt hiện đang soạn cho Suno ở `fk-gen-music`, có thể tái dùng!),
  output = poll/lắng nghe message mới xuất hiện trong conversation.

#### Tool call đã thấy (tham khảo prompt engineering, KHÔNG gọi trực tiếp được):

- `audio__create_song(sound_prompt: str)` → trả
  `{status, clip_id, clip_id_b, a_b_test_id, operation_id, estimated_time (giây, vd 35.0), operation_id_b}`.
  `sound_prompt` là mô tả nhạc cụ/nhịp/tâm trạng bằng tiếng Anh, khá chi tiết (kiểu Suno
  style prompt). Đây là bài **instrumental** (không lời) trong ví dụ này — chưa thấy field
  lyrics, cần capture thêm 1 conversation có lời hát để biết lyrics truyền qua đâu.
- `image__create_image(prompt: str, aspect_ratio: "9:16")` → trả `{image_url: "https://storage.googleapis.com/producer-app-public/assets/{uuid}.jpg"}`
  — dùng để tạo ảnh style/cover cho music video.
- `video__propose_music_video(inputs: {clip_id, start_s, duration_s, resolution: "720p", aspect_ratio, user_message, render_lyrics, style_image_url, likeness_image_url})`
  → bước "đề xuất" (preview card cho user xác nhận), `content: null`.
- `video__create_music_video(...)` → khi thành công trả `{job_id, message: "submitted job"}`.
  Video render async, **15–30 phút**, kết quả tự xuất hiện trong chat khi xong (server
  push — nghi là qua Supabase Realtime WS thấy trong bundle JS, cần xác nhận thêm; có thể
  cũng chỉ là client tự poll lại conversation).

  **Bổ sung 2026-08-17 — đọc log tool-call của conversation THẬT (`1104e19c`, "Giấy màu ướt
  mưa - Hàng Mã"):** hai tool này chia việc rất rạch ròi, và đây là chỗ dễ hiểu nhầm nhất:
  - **Tham số nằm ở `propose`, KHÔNG ở `create`.** `video__propose_music_video` nhận
    `{inputs: {clip_id, start_time, end_time, duration_s, aspect_ratio, user_message,
    display_lyrics}}` (tên field snake_case, bọc trong `inputs`; agent thử camelCase và
    không bọc `inputs` đều bị 422). Nó trả `content: null` — chỉ dựng thẻ đề xuất trên UI.
  - **`video__create_music_video` không nhận field NÀO.** Mọi biến thể đều bị chặn:
    `{inputs: {...}}` → `extra_forbidden` ở `inputs`; đưa field ra ngoài → `extra_forbidden`
    ở từng field một. Khớp với lần bắt được trước đây: chỉ `args: {}` rỗng mới chạy. Tức là
    server tự lấy thông số từ đề xuất đang treo — `create` chỉ là cái nút "đồng ý".
  - **Trong conversation này agent KHÔNG bao giờ submit được**: 6 lần gọi `create` đều 422,
    rồi agent bỏ cuộc và nhắn *"I ran into a technical hiccup… please try clicking the
    confirmation button on the proposal card above directly"*. Cả hai clip của conversation
    tới giờ vẫn `video_id: null`, `video_url: null` → tài khoản này CHƯA có music video nào
    render xong.
  - Hệ quả cho tự động hoá: lượt chat đầu phải nói đủ thông số (để `propose` bắt đúng), lượt
    xác nhận phải **trống trơn** ("Yes, create that music video now.") để agent không nhét
    field vào `create`. Đường chắc ăn hơn là gọi thẳng REST mà nút xác nhận trên thẻ dùng —
    JS bundle có `/video/generate`, **chưa xác nhận path/schema thật** (xem mục "Còn thiếu").

### `GET /__api/music-video/{job_id}/status` — tiến độ + KẾT QUẢ music video (đo thật 2026-08-17)

`job_id` = giá trị `video__create_music_video` trả về. Đây là **nguồn sự thật duy nhất**:
- `state.current_stage`: `02_visual_aesthetic` → `03_video_planning_from_song` →
  `04_video_continuing_shot` → `06_postprocess`; `state.status`: `running` | `completed` | `error`.
- `state.final_video_url`: MP4 tĩnh public (`producer-app-public/music-video/{job_id}/{job_id}.mp4`).
- `state.message`: in lại nguyên văn tham số job nhận được (Clip ID / Style image URL /
  Likeness image URL / Start time / Duration / Aspect ratio / Resolution / `<user_message>`)
  → **chỗ để kiểm xem yêu cầu của mình có tới nơi không**, đừng đoán.
- `state.total_runtime_s`, `token_estimate`, `needs_credits`, `error_message`.

**Clip audio KHÔNG được cập nhật**: video xong rồi mà `/__api/clips` vẫn trả `video_id: null`,
`video_url: null` → tra trạng thái qua clip là sai đường, phải giữ `job_id`.

#### Ba phép đo đắt giá (mỗi lượt 750 credit)

1. **Giá & thời gian**: 750 credit (9000 token) cho 60s/720p, ~8,6 phút — không phải "~500
   credit, 15-30 phút" như ghi chú cũ. Credit trừ **lúc render xong**, không phải lúc submit
   (đo bằng vòng lấy số dư 2 phút/lần: đứng yên suốt lúc render, tụt đúng mẫu có `completed`).
   Job `error` (`video__create_video_clip_async exceeded max retries count of 5`) **không bị
   trừ**.
2. **`client_context.current_song_id` KHÔNG ghim được bài**: conversation có 2 bài (A/B), đặt
   `current_song_id` = bài A mà agent vẫn đưa bài B cho `propose` → render nhầm bài. Phải gọi
   **đích danh clip id trong câu chữ**, và đối chiếu lại `state.clip_id` ngay sau khi submit.
3. **Chỉ MỘT câu mô tả cảnh sống sót vào `user_message`**. Mọi câu chỉ thị kèm theo ("Visual
   style: …", "giữ một phong cách xuyên suốt") đều bị agent bỏ khi soạn tham số. Muốn phong
   cách tới nơi thì **ghép nó vào đầu câu tả cảnh dưới dạng tính từ**. Không neo phong cách
   thì mỗi cảnh một chất liệu — job `06551f8b` (60s): giây 3 ảnh thật, giây 18 mô hình giấy
   cắt dán, giây 33 tranh bán 3D, giây 50 đất nặn; job `9c10e2b7` thì photoreal toàn bộ dù
   nội dung mô tả y hệt. Kênh chắc chắn hơn là **`style_image_url`** — field thật của
   `propose`; lấy URL công khai bằng cách nhờ chính agent gọi `image__create_image`.
   Cảnh báo kèm theo: từ vừa là nội dung vừa là chất liệu ("paper-craft street" = phố hàng mã)
   bị đọc thành chất liệu dựng cảnh → ra hẳn diorama giấy.
- `synthetic__suggest_actions(action1, action2, action3)` → gợi ý 3 nút hành động nhanh
  cho UI, không cần quan tâm khi build automation.

#### Còn thiếu để hoàn thiện luồng tự động hoá:

1. **POST gửi tin nhắn chat** (quan trọng nhất, vẫn chưa thấy) — đoán là
   `POST /__api/conversations` (tạo mới + tin nhắn đầu) và/hoặc
   `POST /__api/conversations/{id}/messages` (gửi tiếp trong conversation có sẵn).
   Cần: request body thật, response (stream hay JSON 1 lần?).
2. Response có stream (SSE/chunked) không, hay client phải tự poll lại
   `GET /__api/conversations/{id}` để thấy message mới?
3. Lấy **URL audio** của 1 clip đã xong (clip_id → mp3/m4a url) — nghi qua
   `POST /__api/clips` (đã thấy request `{"clip_ids":[...]}"` ở HAR trước, chưa có response
   body).
4. Ví dụ có **lyrics** (bài hát có lời, không phải instrumental) để biết field lyrics nằm ở
   đâu trong `audio__create_song` args.
5. WebSocket Supabase Realtime — có dùng để đẩy trạng thái/video xong theo thời gian thực
   không.

### `GET https://www.flowmusic.app/__api/audio-create-song-status/{operation_id}` — poll trạng thái tạo nhạc
- `operation_id` = giá trị trả về từ tool `audio__create_song` ở trên.
- Response:
  ```json
  {
    "operation_id": "uuid",
    "status": "complete",
    "progress": null,
    "clip_id": "uuid",
    "error_type": null,
    "error_message": null
  }
  ```
- `status` chắc còn có giá trị khác lúc đang chạy (vd `"processing"`/`"pending"`) —
  chưa capture được lúc đang generate (bài mẫu đã complete sẵn). Nếu tiện, capture thêm
  1 lần lúc status còn đang chạy (progress có giá trị số?) sẽ chắc chắn hơn.
- Kết hợp với `estimated_time` (giây) từ `audio__create_song` → poll theo chu kỳ vài giây
  cho tới khi `status == "complete"`, rồi lấy audio URL qua `clip_id` (endpoint `/__api/clips`).

### `POST https://www.flowmusic.app/__api/clips` — lấy chi tiết clip (audio URL ở đây)
- Body: `{"clip_ids": ["uuid", ...]}`
- Response: `{"clips": {"<clip_id>": {...}, ...}}`, mỗi clip:
  ```json
  {
    "id": "uuid", "author_id": "uuid",
    "op_id": "uuid (== operation_id)", "op_type": "audio__create_song",
    "duration": {"status": "completed", "value": "175.76 (giây, string)"},
    "lyrics": {"status": "completed", "value": {"id": "uuid", "text": "[Instrumental]"}},
    "lyrics_timing": {"status": "not_requested"},
    "user_edited_lyrics_id": null,
    "title": "Paper Lanterns",
    "privacy": "unlisted", "allow_public_use": true,
    "has_vocals": null, "has_cid_match": null,
    "image_id": "uuid", "video_id": null,
    "created_at": "iso", "deleted_at": null,
    "operation": {
      "op_type": "audio__create_song", "conversation_id": "uuid",
      "sound_prompt": "...", "title": "...", "seed": null, "lyrics_id": ""
    },
    "is_favorite": false, "preference_state": "disliked|null",
    "favorite_count": 0, "play_count": 4, "is_remix_eligible": true,
    "audio_url": "https://storage.googleapis.com/producer-app-public/clips/{clip_id}.m4a",
    "wav_url": "https://storage.googleapis.com/producer-app-public/clips/{clip_id}.wav",
    "image_url": "https://storage.googleapis.com/producer-app-public/assets/{image_id}.jpg",
    "video_url": null
  }
  ```
- **Cực quan trọng, khác hẳn Flow video**: `audio_url`/`wav_url`/`image_url` là URL
  **tĩnh, không ký (không query param hết hạn)**, nằm trên bucket public
  `producer-app-public` → không có bài toán URL hết hạn phải refresh liên tục như
  `ai-sandbox-videofx` của Flow video. Tải trực tiếp bằng URL này là xong, không cần
  đi qua extension để lấy signed URL.
- Bài mẫu là instrumental nên `lyrics.value.text == "[Instrumental]"` — khi có lời hát
  thật thì trường này chắc chứa lyrics thật (chưa xác nhận).
- `video_url: null` — vì clip này chưa có music video (video vẫn nằm trong `video_id`
  của 1 clip riêng `op_type: video__create_music_video`, không nằm trong clip audio này).

### `POST https://www.flowmusic.app/__api/conversation` (số ít, khác `GET .../conversations`) — **gửi tin nhắn chat, đây là API tạo nhạc thật sự**
- Body:
  ```json
  {
    "conversation_id": "uuid (conversation có sẵn — CHƯA xác nhận field/behaviour khi tạo MỚI, có thể null hoặc omit)",
    "parts": [{"content": "mô tả bài hát bằng ngôn ngữ tự nhiên", "part_kind": "user-prompt"}],
    "client_context": {
      "current_song_id": "uuid | null (clip đang mở trên UI player)",
      "song_queue": [{"id": "uuid"}, ...],
      "selected_model": null,
      "lyrics_id_map": {},
      "ghostwriter_version": "standard"
    },
    "model_name": "producer:standard",
    "mode": "standard"
  }
  ```
- Response: `{"job_id": "uuid"}` — **async**, KHÔNG trả kết quả ngay.
- **Còn thiếu để hoàn thiện chỗ này** (quan trọng, chặn việc code xong luồng end-to-end):
  1. Cách tạo conversation MỚI (từ trang chủ, chưa có `conversation_id`) — request thật
     khi bắt đầu 1 bài hát hoàn toàn mới, có gửi `conversation_id: null` hay gọi endpoint
     khác trước để lấy id rồi mới POST vào đây?
  2. `job_id` liên hệ thế nào với kết quả — có endpoint check trạng thái riêng theo
     `job_id` (kiểu `/__api/jobs/{job_id}` hay tương tự), hay chỉ cần poll lại
     `GET /__api/conversations/{id}` tới khi thấy message/tool-call mới xuất hiện?
  3. `song_queue`/`current_song_id` có bắt buộc phải đúng không, hay gửi rỗng/null vẫn
     chạy được (quan trọng vì automation sẽ không có UI player state thật)?

### Tạo conversation MỚI — dùng chung `POST /__api/conversation` (chưa có full JSON để đối chiếu)
- User xác nhận: cùng endpoint `POST /__api/conversation`, chỉ khác nội dung `parts[0].content`
  là prompt bài hát mới. **Chưa có** full request body/response để xác nhận chắc
  `conversation_id` được gửi là `null` hay bị lược khỏi JSON hoàn toàn khi tạo mới — suy
  đoán hợp lý dựa theo cấu trúc đã biết, cần full JSON để chốt.

### `GET https://www.flowmusic.app/__api/messages/{message_id}/stream?last_id=0` — **SSE streaming, có vẻ đây mới là cách theo dõi tiến trình thật**
- Phát hiện mới từ user — nghi đây là cơ chế real-time chính (Server-Sent Events) để
  client nhận từng phần phản hồi của agent (text, tool-call, tool-return) khi đang chạy,
  thay vì poll REST đơn thuần.
- **Chưa xác nhận**:
  - `{message_id}` lấy từ đâu — có phải chính là `job_id` trả về từ
    `POST /__api/conversation`, hay là 1 id khác (vd id của user-prompt message, lấy từ
    GET conversation)?
  - Nội dung thực tế của stream (mỗi event/dòng SSE chứa gì — text chunk? toàn bộ
    tool-call JSON? kết thúc bằng gì?).
  - `last_id=0` dùng để resume từ đâu (chắc là index/offset của event cuối đã nhận).
- User nghi ngờ: "khi chạy xong thì API sẽ chẳng trả về cái gì" — cần làm rõ ý: stream tự
  đóng kết nối khi xong (bình thường với SSE), hay gọi lại sau khi xong thì rỗng/404?
- **Việc cần làm tiếp**: mở tab Network, lọc theo "stream", xem nội dung response (DevTools
  có tab riêng cho EventStream — trong Network, click vào request đó rồi xem tab
  "EventStream"/"Messages"), copy vài dòng event đầu + dòng cuối cùng lúc job hoàn tất.

### `DELETE https://www.flowmusic.app/__api/conversations/{id}` — xoá conversation
- Body: `{"delete_clips": false, "delete_spaces": false, "delete_music_videos": false}`
  (3 cờ đều `false` trong ví dụ user gửi — chưa rõ ý nghĩa chính xác khi `true`, có thể
  điều khiển xoá cascade luôn clip/space/music-video liên quan hay chỉ xoá bản ghi
  conversation. Mặc định `false` hết là an toàn — chỉ xoá conversation).
- Response: `null`.

### `PATCH https://www.flowmusic.app/__api/conversations/{id}` — đổi tên conversation
- Body: `{"title": "tên mới"}`
- Response: `null` (204-kiểu, không trả gì).
- Không cần cho luồng automation nhưng ghi lại cho đủ.
- Conversation mới tạo ở bước trước có id `44fd5aa0-1829-47b1-95f1-cc56065a3aca` — xác nhận
  có 1 conversation mới được tạo ra, nhưng vẫn chưa rõ **id này lấy từ đâu** (response của
  `POST /__api/conversation` lúc tạo mới, hay phải GET lại `/__api/conversations` list để
  tìm cái mới nhất). Cần full request/response của bước tạo mới để chốt.

## Endpoint thấy path nhưng CHƯA xác nhận response/body

(từ HAR homepage — chỉ có headers, không có response body)

- `POST /__api/clips` — body `{"clip_ids": [...]}"` → lấy chi tiết nhiều clip theo id.
- `GET /__api/conversations?limit=&offset=`
- `GET /__api/projects?offset=&limit=`
- `GET /__api/billing/credits`
- `GET /__api/billing/subscription`
- `GET /__api/producer/access-granted`
- `GET /__api/featured/clips/featured?limit=&offset=`
- `GET /__api/users/{user_id}/playlists?favorites=&public=&offset=&limit=`
- `GET /__api/users/settings/onboarding`
- `GET /__api/users/settings/custom-instructions`
- `GET /__api/partner-referral`
- `GET /__api/auth/google/scope?name=...`
- `POST /__api/usernames/get` — body `{"user_ids": [...]}`
- `POST /__api/users` — body `{"user_ids": [...]}`
- `POST /__api/personalize/scores` — body `{"user_ids": [...]}`
- `POST /__api/personalize/level` — body rỗng

## Còn thiếu (quan trọng nhất — chưa capture được)

- Tạo bài hát mới (prompt/lyrics/style → generate) — endpoint thật sự chưa thấy.
- Poll trạng thái generate (nghi là `/audio-create-song-status/...` theo tên thấy trong JS bundle,
  chưa xác nhận path thật + response shape).
- Lấy URL audio bài hát đã xong (stream/download).
- List "My Songs" / library thật (`/library/my-songs` theo JS bundle, path `/__api/...` thật chưa rõ).
- Tạo music video từ bài hát (`/video/generate` theo JS bundle).
- WebSocket Supabase Realtime — dùng để báo trạng thái generate real-time hay chỉ REST poll?
