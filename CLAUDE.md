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
- **Prompt header/footer: hai đường khác nhau.** Đường thường (storyboard, render video ở tab
  Shots) vẫn tự chèn `project.prompt_header/footer` qua `brain.compose_prompt`. Trong NODE
  EDITOR thì KHÔNG: chỉ chèn khi trên canvas có node `promptHeader` / `promptFooter` nối vào
  node tạo ảnh/tạo video, và node để text rỗng nghĩa là "lấy giá trị của dự án".
  `compose_prompt(..., header=, footer=)` là chỗ phân nhánh. Chỉ `image`/`video` nhận bọc —
  `editImage`/`replacebg` chạy prompt nguyên văn. Xem [agent/studio/graph.py](agent/studio/graph.py).
- `media_id` is always UUID format (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`), never `CAMS...`
- The agent holds no state; all generation goes through the connected extension.
  If `extension_connected: false`, open Google Flow in Chrome with the extension loaded.
- See [README.md](README.md) for the full endpoint table.
