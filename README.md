# Flow Kit — Proxy API Google Flow + Flow Studio

Một server cục bộ (FastAPI + WebSocket) ghép cặp với một extension Chrome để biến API
sinh ảnh/video của **Google Flow** thành các endpoint HTTP thường tại
`http://127.0.0.1:8100`. Bên trên lớp proxy đó là **Flow Studio** — một webapp dựng cả
video từ một ý tưởng: Kịch bản → Nhân vật/Bối cảnh → Storyboard → Shot → Ghép & Xuất bản.

- **Lõi proxy Flow** không giữ trạng thái: chỉ chuyển tiếp request tới extension rồi trả
  kết quả về.
- **Flow Studio** mới là phần có trạng thái — lưu dự án/scene/shot trong SQLite
  (`agent/studio.db`), cache media ở `./media/`, render cuối ở `./studio_media/`.

Extension Chrome lo phần lấy bearer token của Google Flow, giải reCAPTCHA và gọi thẳng
`aisandbox-pa.googleapis.com`. Agent Python chỉ là cầu nối WebSocket mỏng.

## Thành phần

- **`extension/`** — Extension Chrome MV3. Bắt bearer token, nói chuyện với Google Flow,
  kết nối agent qua WebSocket (`ws://127.0.0.1:9222`), trả kết quả qua HTTP callback
  (`POST /api/ext/callback`).
- **`agent/`** — Server FastAPI + WebSocket.
  - `main.py` — entry app, WebSocket cho extension, `/health`, `/api/ext/callback`, mount
    SPA + thư mục media tĩnh.
  - `api/flow.py` — toàn bộ endpoint `/api/flow/*` (relay tới Flow).
  - `api/tts.py` — `/api/tts/*`, proxy tới server OmniVoice chạy trên Google Colab.
  - `api/ai_agent.py` — `/api/agent/*`, chạy các coding-agent CLI headless.
  - `api/studio.py` — `/api/studio/*`, toàn bộ orchestration của Flow Studio.
  - `studio/` — lớp nghiệp vụ của Studio: `db.py` (SQLite + migration), `brain.py` (prompt
    cho AI), `assembler.py` (ghép video bằng ffmpeg), `davinci_xml.py` (xuất timeline
    Resolve), `vntext.py` (chuẩn hoá tiếng Việt trước TTS), `media_store.py`, `graph.py`.
  - `services/flow_client.py` — relay request sang extension và chờ phản hồi.
  - `services/headers.py` — header request ngẫu nhiên hoá.
  - `config.py`, `models.json` — danh sách endpoint + key model.
- **`webapp/`** — SPA React + Vite + Tailwind (giao diện Flow Studio).

## Cài đặt & Chạy

```bash
pip install -r requirements.txt

# (lần đầu / khi sửa webapp) build SPA — agent sẽ phục vụ nó
cd webapp && npm install && npm run build && cd ..

# chạy server: HTTP tại :8100, WebSocket cho extension tại :9222
python -m agent.main
```

Mở <http://127.0.0.1:8100>. Nạp thư mục `extension/` dạng *unpacked extension* trong
Chrome rồi đăng nhập Google Flow.

Chế độ dev có hot-reload: `cd webapp && npm run dev` (tự proxy `/api` + `/media` về
`:8100`).

## Kiểm tra nhanh (pre-flight)

```bash
curl -s http://127.0.0.1:8100/health
# {"status":"ok", "extension_connected": true, ...}
```

`extension_connected: false` nghĩa là chưa có extension — mở Google Flow trong Chrome với
extension đã nạp. Mọi việc sinh media đều phải đi qua extension đang kết nối.

## Yêu cầu môi trường

| Cần cho | Yêu cầu |
|---------|---------|
| Sinh ảnh/video Flow | Extension Chrome đã kết nối + đăng nhập Google Flow |
| Ghép & xuất video | `ffmpeg` + `ffprobe` trong PATH |
| Lồng tiếng (TTS) | Đặt URL server OmniVoice (xem mục TTS) |
| AI agent | `claude` và/hoặc `agy` đã đăng nhập sẵn trên máy chạy server |

`GOOGLE_API_KEY` là tuỳ chọn — auth tới `aisandbox-pa.googleapis.com` do bearer token của
extension gánh. Để trống (mặc định) thì bỏ luôn tham số `?key=`.

---

## Flow Studio

Quy trình dựng video chạy trên các API bên dưới, có một AI agent làm "bộ não" sinh
kịch bản/prompt, một **Node Editor** cho pipeline tuỳ biến, và xuất **DaVinci Resolve XML**.

**Quy trình:** Ý tưởng → Kịch bản (Fountain) → tách Nhân vật/Bối cảnh/Đạo cụ (asset có ảnh
tham chiếu) → Storyboard (chia frame) → Shot (ảnh frame + video) → Ghép → Xuất bản.

**Các khả năng chính:**

- **Chế độ Storytelling (audio-first):** mỗi scene được viết lời đọc liền mạch, **TTS cả
  scene trong một lần đọc** (giữ trọn cảm xúc, không cắt vụn), rồi các *beat* hình ảnh được
  ánh xạ lên đúng timeline của audio thật ("đọc tới đâu, hình tới đó").
- **Chuẩn hoá tiếng Việt trước TTS** (`vntext.py`): đổi số → chữ, viết tắt, giờ, ngày,
  tiền tệ, ký tự đặc biệt (`-`, `_`, `%`…) sang dạng đọc chuẩn rồi mới cắt đoạn cho TTS.
- **Tuỳ chọn ngôn ngữ theo dự án:** ngôn ngữ **kịch bản/lời thoại/lời đọc** (`script_lang`,
  mặc định Tiếng Việt) và ngôn ngữ **chữ viết/vẽ trong ảnh** (`image_text_lang`); từ đặc thù
  tiếng nước ngoài (thuật ngữ/nhãn hiệu) được giữ nguyên.
- **Prompt shot giàu điện ảnh:** mỗi shot được ép nêu rõ cỡ cảnh, góc & độ cao máy, tiêu cự
  + DOF, ánh sáng, bố cục/layout — và một lớp **chuyển động** riêng cho video (loại chuyển
  động máy, rack focus, biến đổi ánh sáng/khói theo thời gian) đúng kiểu image-to-video.
- **Video nối dài >8s:** beat dài hơn một clip Veo (~8s) được render thành nhiều clip i2v
  nối tiếp (clip sau bắt đầu từ frame cuối của clip trước) rồi concat thành một shot liền.
- **Caption từ khoá định giờ:** cụm từ then chốt được vẽ lên video đúng lúc lời đọc chạm
  tới, và xuất kèm vào XML/SRT cho Resolve.
- **Nhạc nền:** tải một file nhạc cho dự án → khi ghép, nhạc tự được lặp cho đủ độ dài và
  trộn **dưới** giọng đọc ở mức âm lượng cấu hình được (giọng đọc giữ nguyên). Không có file
  thì bỏ qua.
- **Xuất DaVinci Resolve XML (FCP7/xmeml):** track video + track title (caption) + track
  audio (lời đọc từng scene), kèm `captions.srt` (chạy được cả bản Resolve Free).
- **Node Editor:** đồ thị tuỳ biến cho asset/shot (tạo ảnh → sửa ảnh → tạo video), có
  "⚡ Tạo nhanh" từng node và "🔒 Lock" để giữ media ưng ý khi chạy lại toàn tuyến.

Toàn bộ endpoint nằm dưới `/api/studio/*`. Nhóm chính (chi tiết trong
[agent/api/studio.py](agent/api/studio.py)):

| Nhóm | Endpoint tiêu biểu |
|------|--------------------|
| Hệ thống | `GET /health`, `GET /options`, `GET /credits`, `GET/PUT /settings` |
| Bảo trì | `POST /maintenance/purge-orphans?dry_run=false` (dọn dòng mồ côi trong DB) |
| Dự án | `GET/POST /projects`, `GET/PATCH/DELETE /projects/{pid}`, `PUT /projects/{pid}/cover` |
| Kịch bản | `POST /projects/{pid}/script/generate`, `PUT /projects/{pid}/script`, `POST …/script/chat`, `GET …/scenes` |
| Nhân vật/Bối cảnh | `GET/POST /projects/{pid}/entities`, `…/entities/extract`, `…/assets/generate-all`, `PATCH/DELETE /entities/{eid}`, `…/entities/{eid}/generate` |
| Thư viện asset | `GET /library/entities`, `GET /library/all-media`, `…/entities/import`, `…/entities/import-media` |
| Storyboard | `POST /projects/{pid}/storyboard/generate-all`, `…/storyboard/autofill-all`, `POST /scenes/{sid}/storyboard/autofill`, `GET /projects/{pid}/storyboard/export` |
| Shot | `GET/POST /scenes/{sid}/shots`, `PATCH/DELETE /shots/{sid}`, `…/shots/{sid}/image`, `…/video`, `…/video/resume`, `…/prompts`, `…/upscale`, `…/insert`, `POST /projects/{pid}/shots/generate-all` |
| Ảnh 2K/4K | `GET /projects/{pid}/hires/status`, `POST /projects/{pid}/hires/generate-all`, `POST /shots/{sid}/hires` |
| Video 1080p/4K | `GET /projects/{pid}/upscale/status`, `POST /projects/{pid}/upscale/generate-all`, `POST /shots/{sid}/upscale` |
| Storytelling | `POST /scenes/{sid}/beats`, `POST /projects/{pid}/voiceover`, `POST /shots/{sid}/narration` |
| Node graph | `GET/PUT /shots/{sid}/graph`, `POST /shots/{sid}/graph/run` (tương tự cho `/entities/{eid}/graph`) |
| Ghép & Xuất | `POST /projects/{pid}/assemble`, `…/assemble-images`, `…/export`, `…/export/davinci-xml`, `GET /fonts` |
| Nhạc nền | `POST /projects/{pid}/bgm` (upload), `POST …/bgm/copy` (chép từ dự án khác), `DELETE /projects/{pid}/bgm` |

---

## Endpoint Flow (`/api/flow/*`)

| Method | Path | Mục đích |
|--------|------|----------|
| GET  | `/status` | Trạng thái kết nối extension + có flow key chưa |
| GET  | `/credits` | Credit người dùng / paygate tier |
| POST | `/create-project` | Tạo project mới trên Flow |
| GET  | `/delete-project/{project_id}` | Xoá project Flow |
| GET  | `/change-project-cover/{project_id}/{media_id}` | Đổi ảnh bìa project |
| POST | `/generate-image` | Sinh ảnh từ prompt (+ ref nhân vật tuỳ chọn) |
| POST | `/edit-image` | Sửa một ảnh đã có |
| POST | `/upload-image` | Upload ảnh cục bộ → `media_id` |
| POST | `/generate-video` | Video i2v từ ảnh đầu (+ ảnh cuối tuỳ chọn, để nối clip) |
| POST | `/generate-video-omni` | Video r2v (Omni Flash, `abra_r2v_{4,6,8,10}s`) |
| POST | `/generate-video-refs` | Video từ các ảnh tham chiếu |
| POST | `/upscale/video` | Upscale một video đã sinh |
| POST | `/check-status` | Poll operation async (video/upscale) |
| PATCH| `/change-displayname` | Đổi tên một media/workflow item |
| GET  | `/media/{primary_media_id}` | Metadata media + URL ký tươi |
| GET  | `/project/{project_id}` | Nội dung một project Flow từ xa |
| GET  | `/projects` | Liệt kê project Flow từ xa |

`media_id` luôn ở dạng UUID (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`), không bao giờ `CAMS…`.

## Endpoint TTS (`/api/tts/*`)

Proxy tới một server [OmniVoice](https://github.com/k2-fsa) chạy trên Google Colab. URL
tunnel của Colab (ngrok/localtunnel) đổi mỗi phiên, nên đặt lúc chạy bằng
`PUT /api/tts/config` (hoặc biến môi trường `OMNIVOICE_BASE_URL`). URL được **lưu lại**
trong DB nên không mất khi khởi động lại server.

| Method | Path | Mục đích |
|--------|------|----------|
| GET  | `/config` | Xem URL OmniVoice hiện tại |
| PUT  | `/config` | Đặt URL — `{"base_url": "https://<id>.ngrok-free.app"}` |
| GET  | `/health` | Trạng thái server OmniVoice + nạp model |
| POST | `/synthesize` | TTS — `{text, voice_id?, voice?, speed?, instruct?}` → `{audio: base64 WAV, …}` |
| GET  | `/voices` | Liệt kê voice đã đăng ký |
| POST | `/voices` | Thêm voice clone — `{voice: base64, title, desciption?}` |
| POST | `/voices/remove` | Xoá voice — `{voice_id}` |

```bash
# trỏ tới tunnel Colab đang chạy, rồi tổng hợp giọng
curl -X PUT http://127.0.0.1:8100/api/tts/config \
  -H 'Content-Type: application/json' -d '{"base_url":"https://abc123.ngrok-free.app"}'
curl -X POST http://127.0.0.1:8100/api/tts/synthesize \
  -H 'Content-Type: application/json' -d '{"text":"Xin chào","voice_id":0}'
```

## Endpoint AI Agent (`/api/agent/*`)

Chạy các coding-agent CLI (Claude Code, Antigravity, …) headless như subprocess để tự động
hoá: viết script, sinh prompt, sửa file trong một thư mục làm việc. Agent chạy
non-interactive, **mặc định bypass permission** (ghi file / chạy lệnh tự do) — chỉ expose
trên `127.0.0.1`.

| Method | Path | Mục đích |
|--------|------|----------|
| GET  | `/agents` | Liệt kê agent đã cấu hình + binary có sẵn trên máy hay không |
| POST | `/run` | Chạy agent headless → `{ok, exit_code, stdout, stderr, duration}` |

Body `POST /run`:

| Trường | Mặc định | Mô tả |
|--------|----------|-------|
| `agent` | — | Key trong registry (`claude`, `antigravity`) |
| `prompt` | — | Nội dung giao cho agent |
| `cwd` | thư mục hiện tại | Thư mục làm việc của agent |
| `model` | mặc định CLI | Override model key |
| `timeout` | `AGENT_CLI_TIMEOUT` (600s) | Giới hạn thời gian; quá thì kill + 504 |
| `extra_args` | `[]` | Cờ thêm truyền thẳng cho CLI |
| `skip_permissions` | `AGENT_SKIP_PERMISSIONS` (true) | Override bypass permission |
| `env` | `{}` | Biến môi trường thêm cho tiến trình |

```bash
# Xem agent nào đã cài
curl -s http://127.0.0.1:8100/api/agent/agents

# Giao việc cho Claude Code trong một thư mục
curl -X POST http://127.0.0.1:8100/api/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"agent":"claude","prompt":"Tóm tắt README.md trong 3 gạch đầu dòng","cwd":"D:/youtube/editor/flowkit"}'
```

Agent có sẵn: `claude` (Claude Code, prompt qua stdin) và `antigravity` (binary `agy`, cú
pháp `agy -p "<prompt>" --model X --dangerously-skip-permissions`). Cả hai CLI phải được
**đăng nhập sẵn** trên máy chạy server — nếu chưa auth, agent sẽ treo tới khi timeout (504).

Antigravity (`agy`) là một ứng dụng **TUI**: ở print mode nó chỉ render ra terminal thật,
nên khi bị pipe stdout sẽ rỗng. Server tự chạy `agy` dưới một **PTY giả** (ConPTY qua
`pywinpty` trên Windows, module `pty` trên POSIX) rồi strip ANSI để trả về plain text —
bật/tắt qua cờ `pty` trong registry. Cài `pywinpty` (đã có trong `requirements.txt`) để
dùng được agent này trên Windows.

Registry agent + cờ mặc định nằm ở [`agent/config.py`](agent/config.py) (`AI_AGENTS`),
override được hết qua env (`AGENT_CLAUDE_BIN`, `AGENT_ANTIGRAVITY_BIN`,
`AGENT_ANTIGRAVITY_ARGS`, `AGENT_CLI_TIMEOUT`, `AGENT_SKIP_PERMISSIONS`, …).

## Repo gốc
https://github.com/crisng95/flowkit

## Giấy phép

MIT — xem [LICENSE](LICENSE).
