"""Music Client — communicates with Google Flow Music (flowmusic.app) via the same Chrome
extension WebSocket bridge used for Flow video.

Kiến trúc khác hẳn Flow video (xem agent/config.py cho chi tiết): không có REST tạo nhạc
với tham số cấu trúc — server chạy 1 AI agent, client chỉ gửi tin nhắn chat tự nhiên vào
`/__api/conversation`, agent phía Google tự gọi tool (`audio__create_song`, ...) và trả kết
quả qua SSE. Extension lo phần submit + đọc SSE tới khi xong rồi trả về 1 lần (khớp mô hình
request/response hiện có — xem `handleMusicStreamRequest` trong extension/background.js).
"""
import asyncio
import json
import logging
import time
import uuid
from typing import Optional

from agent.config import (
    FLOWMUSIC_WEB_API, MUSIC_ENDPOINTS,
    MUSIC_GENERATION_TIMEOUT, MUSIC_STATUS_POLL_INTERVAL, MUSIC_STATUS_POLL_TIMEOUT,
)

logger = logging.getLogger(__name__)


class MusicClient:
    """Sends commands to the Chrome extension (Flow Music side) via the shared WebSocket."""

    def __init__(self):
        self._extension_ws = None
        self._pending: dict[str, asyncio.Future] = {}
        self._music_key: Optional[str] = None
        self._identity: Optional[dict] = None
        # Serialize tạo nhạc (submit+SSE) qua extension — 1 tab trình duyệt dùng chung, tránh
        # 2 lượt chat chồng lên nhau làm rối job_id/SSE. Đọc trạng thái (poll/list) không cần.
        self._lock = asyncio.Lock()

    def set_extension(self, ws):
        self._extension_ws = ws

    def clear_extension(self):
        self._extension_ws = None
        pending_copy = list(self._pending.items())
        for _, future in pending_copy:
            if not future.done():
                future.set_exception(ConnectionError("Extension disconnected"))
        self._pending.clear()

    @property
    def connected(self) -> bool:
        return self._extension_ws is not None

    @property
    def identity(self) -> Optional[dict]:
        return self._identity

    async def handle_message(self, data: dict):
        """Handle a message from the extension. Called for every WS frame — messages not
        meant for the music client (ping/pong/token_captured của Flow video...) đều bị bỏ
        qua lặng lẽ (không phải lỗi, đơn giản là "không phải phần của tôi")."""
        if data.get("type") == "music_token_captured":
            self._music_key = data.get("musicKey")
            logger.info("Flow Music key captured from extension")
            return

        if data.get("type") == "music_identity":
            ident = data.get("identity") or {}
            if ident.get("email") or ident.get("sub"):
                prev = (self._identity or {}).get("email")
                self._identity = ident
                if ident.get("email") != prev:
                    logger.info("Tài khoản Flow Music: %s", ident.get("email") or ident.get("sub"))
            return

        req_id = data.get("id")
        if req_id and req_id in self._pending:
            if not self._pending[req_id].done():
                self._pending[req_id].set_result(data)
            return

    async def _send(self, method: str, params: dict, timeout: float = 60,
                     *, serialize: bool = False) -> dict:
        if not self._extension_ws:
            return {"error": "Extension not connected"}
        if serialize:
            async with self._lock:
                return await self._send_raw(method, params, timeout)
        return await self._send_raw(method, params, timeout)

    async def _send_raw(self, method: str, params: dict, timeout: float) -> dict:
        if not self._extension_ws:
            return {"error": "Extension not connected"}

        req_id = str(uuid.uuid4())
        future = asyncio.get_running_loop().create_future()
        self._pending[req_id] = future

        try:
            await self._extension_ws.send(json.dumps({
                "id": req_id, "method": method, "params": params,
            }))
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return {"error": f"Timeout ({timeout}s) waiting for {method}"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            self._pending.pop(req_id, None)

    def _url(self, endpoint_key: str, **kwargs) -> str:
        return f"{FLOWMUSIC_WEB_API}{MUSIC_ENDPOINTS[endpoint_key].format(**kwargs)}"

    async def _api(self, method: str, endpoint_key: str, *, path_kwargs: dict = None,
                    query: dict = None, body: dict = None, timeout: float = 30) -> dict:
        url = self._url(endpoint_key, **(path_kwargs or {}))
        if query:
            from urllib.parse import urlencode
            url = f"{url}?{urlencode(query)}"
        return await self._send("music_api_request", {
            "url": url, "method": method, "body": body,
        }, timeout=timeout, serialize=False)

    # ─── High-level API ──────────────────────────────────────

    async def send_message(self, content: str, conversation_id: str = None,
                            client_context: dict = None,
                            model_name: str = "producer:standard", mode: str = "standard",
                            timeout: float = None) -> dict:
        """Gửi 1 tin nhắn chat (tạo bài hát mới, hoặc tiếp tục 1 conversation có sẵn).

        Trả về dict {job_id, conversation_id, parts, tool_returns, text, done, timed_out}
        (hoặc {"error": ...}) — extension đã đọc hết SSE tới event "final" trước khi trả.
        """
        return await self._send("music_stream_request", {
            "content": content,
            "conversation_id": conversation_id,
            "client_context": client_context or {},
            "model_name": model_name,
            "mode": mode,
            "timeout_s": timeout or MUSIC_GENERATION_TIMEOUT,
        }, timeout=(timeout or MUSIC_GENERATION_TIMEOUT) + 15, serialize=True)

    async def get_song_status(self, operation_id: str) -> dict:
        return await self._api("GET", "song_status", path_kwargs={"operation_id": operation_id})

    async def get_clips(self, clip_ids: list[str]) -> dict:
        """POST /__api/clips — trả {"clips": {clip_id: {...audio_url, wav_url, title, ...}}}."""
        return await self._api("POST", "clips_batch", body={"clip_ids": clip_ids})

    async def get_conversation(self, conversation_id: str) -> dict:
        return await self._api("GET", "conversation_get", path_kwargs={"conversation_id": conversation_id})

    async def list_conversations(self, limit: int = 30, offset: int = 0) -> dict:
        return await self._api("GET", "conversations_list", query={"limit": limit, "offset": offset})

    async def rename_conversation(self, conversation_id: str, title: str) -> dict:
        return await self._api("PATCH", "conversation_rename",
                                path_kwargs={"conversation_id": conversation_id}, body={"title": title})

    async def delete_conversation(self, conversation_id: str, *, delete_clips: bool = False,
                                   delete_spaces: bool = False,
                                   delete_music_videos: bool = False) -> dict:
        return await self._api("DELETE", "conversation_delete",
                                path_kwargs={"conversation_id": conversation_id}, body={
                                    "delete_clips": delete_clips,
                                    "delete_spaces": delete_spaces,
                                    "delete_music_videos": delete_music_videos,
                                })

    async def get_credits(self) -> dict:
        return await self._api("GET", "billing_credits", timeout=15)

    async def _wait_clip_ready(self, clip_id: str, poll_timeout: float) -> dict:
        """Poll /__api/clips tới khi audio đã render xong (duration.status == 'completed').

        `/__api/audio-create-song-status/{operation_id}` — endpoint poll "chính thức" thấy
        trong HAR — trả 401 Unauthorized qua relay dù cùng cơ chế Bearer+cookie như mọi
        endpoint `/__api/*` khác đã xác nhận hoạt động (vd `/clips`, `/conversations`);
        nguyên nhân chưa rõ (có thể route này cần thêm điều kiện phía server không thấy
        trong header). Poll thẳng `/__api/clips` vừa né được lỗi đó, vừa đỡ phải gọi 2 API
        (status rồi clips) — clip sẵn sàng là có ngay audio_url/wav_url/title/lyrics.
        """
        deadline = time.monotonic() + poll_timeout
        last_clip: Optional[dict] = None
        while time.monotonic() < deadline:
            res = await self.get_clips([clip_id])
            if not _is_error(res):
                data = res.get("data", res)
                clip = ((data or {}).get("clips") or {}).get(clip_id)
                if clip:
                    last_clip = clip
                    if (clip.get("duration") or {}).get("status") == "completed" and clip.get("audio_url"):
                        return clip
            await asyncio.sleep(MUSIC_STATUS_POLL_INTERVAL)
        return {"clip_id": clip_id, "error": f"Timeout polling clip ({poll_timeout}s)",
                **({"partial": last_clip} if last_clip else {})}

    async def create_song(self, prompt: str, conversation_id: str = None,
                           timeout: float = None) -> dict:
        """Tạo bài hát: gửi prompt → chờ SSE xong → poll `/__api/clips` từng clip tới khi có
        audio_url.

        Trả về: {conversation_id, job_id, text, songs: [{clip_id, operation_id, title,
        audio_url, wav_url, image_url, duration_s, lyrics}], raw_tool_returns}.
        Trả {"error": ...} nếu bất kỳ bước nào thất bại.
        """
        result = await self.send_message(prompt, conversation_id=conversation_id, timeout=timeout)
        if _is_error(result):
            return {"error": result.get("error", "send_message failed")}
        payload = result.get("data", result)
        if not isinstance(payload, dict):
            return {"error": "Unexpected response shape from extension"}

        tool_returns = [
            p for p in payload.get("tool_returns", [])
            if p.get("tool_name") == "audio__create_song"
        ]
        if not tool_returns:
            return {
                "error": "Agent không gọi audio__create_song trong lượt này "
                         "(có thể prompt bị hiểu thành việc khác — xem 'text')",
                "text": payload.get("text"),
                "conversation_id": payload.get("conversation_id"),
                "job_id": payload.get("job_id"),
            }

        # Mỗi tool-return có thể mang 1-2 clip (A/B test: clip_id + clip_id_b). Nhớ luôn
        # operation_id đi kèm mỗi clip_id — dùng để đối chiếu ngược lại bên dưới, đảm bảo
        # clip lấy về đúng là clip vừa tạo ở lượt NÀY, không phải bài nào khác lỡ trùng
        # thời điểm poll.
        clip_to_operation: dict[str, str] = {}
        for tr in tool_returns:
            content = tr.get("content") or {}
            if content.get("status") != "success":
                continue
            if content.get("clip_id") and content.get("operation_id"):
                clip_to_operation[content["clip_id"]] = content["operation_id"]
            if content.get("clip_id_b") and content.get("operation_id_b"):
                clip_to_operation[content["clip_id_b"]] = content["operation_id_b"]

        if not clip_to_operation:
            return {
                "error": "audio__create_song không trả clip_id hợp lệ",
                "raw_tool_returns": tool_returns,
                "conversation_id": payload.get("conversation_id"),
            }

        polled = await asyncio.gather(*[
            self._wait_clip_ready(clip_id, MUSIC_STATUS_POLL_TIMEOUT) for clip_id in clip_to_operation
        ])

        songs, failed = [], []
        for clip_id, c in zip(clip_to_operation, polled):
            if not c.get("audio_url"):
                failed.append(c)
                continue
            # /__api/clips trả về theo key = clip_id đã hỏi, nhưng vẫn đối chiếu lại id +
            # operation_id bên trong response khớp với clip vừa tạo ở tool-return — phòng
            # trường hợp server trả nhầm/đổi shape mà không báo lỗi rõ ràng.
            if c.get("id") != clip_id or c.get("op_id") != clip_to_operation[clip_id]:
                failed.append({**c, "error": "clip/operation id không khớp — bỏ qua để an toàn"})
                continue
            songs.append({
                "clip_id": c.get("id"),
                "operation_id": c.get("op_id"),
                "title": c.get("title"),
                "audio_url": c.get("audio_url"),
                "wav_url": c.get("wav_url"),
                "image_url": c.get("image_url"),
                "duration_s": float(c["duration"]["value"]) if c.get("duration", {}).get("value") else None,
                "lyrics": (c.get("lyrics") or {}).get("value", {}).get("text"),
            })

        return {
            "conversation_id": payload.get("conversation_id"),
            "job_id": payload.get("job_id"),
            "text": payload.get("text"),
            "songs": songs,
            "failed": failed if failed else None,
            "raw_tool_returns": tool_returns,
        }


    # ─── Music video (video__create_music_video) ─────────────
    #
    # ĐẮT VÀ CHẬM: ~500 credit và 15-30 phút mỗi video (vì vậy trước đây cố tình không làm).
    # Không có REST nào nhận tham số — vẫn phải nói bằng lời với agent phía Flow Music, y hệt
    # `create_song`. Agent thường đi hai nhịp: `video__propose_music_video` (thẻ đề xuất cho
    # người dùng bấm xác nhận) rồi mới `video__create_music_video`. Cái sau mới tiêu credit,
    # nên `auto_confirm` chỉ gửi ĐÚNG MỘT lượt xác nhận khi nhịp đầu dừng ở đề xuất.

    @staticmethod
    def _video_tool_returns(payload: dict, tool: str) -> list[dict]:
        return [p for p in (payload.get("tool_returns") or []) if p.get("tool_name") == tool]

    @staticmethod
    def _video_job_id(tool_returns: list[dict]) -> Optional[str]:
        for tr in tool_returns:
            content = tr.get("content")
            if isinstance(content, dict) and content.get("job_id"):
                return content["job_id"]
        return None

    async def create_music_video(self, clip_id: str, conversation_id: str = None, *,
                                  aspect_ratio: str = "16:9", render_lyrics: bool = False,
                                  note: str = "", start_s: int = 0, duration_s: int = 60,
                                  auto_confirm: bool = True,
                                  timeout: float = None) -> dict:
        """Đặt lệnh render music video cho một bài hát đã có.

        Trả {conversation_id, status, video_job_id, text, raw_tool_returns} với status:
          • "submitted" — agent đã gọi `video__create_music_video` (ĐANG TIÊU CREDIT)
          • "proposed"  — mới dừng ở đề xuất, chưa render (auto_confirm=False, hoặc lượt xác
                          nhận vẫn không đẩy agent đi tiếp)
          • "not_called"— agent hiểu tin nhắn thành việc khác; đọc `text` để biết nó nói gì
        KHÔNG chờ render xong (15-30 phút) — hỏi tiếp bằng `music_video_status(clip_id)`.
        """
        # Mọi THAM SỐ phải nằm ở lượt ĐỀ XUẤT: `video__propose_music_video` nhận
        # {clip_id, start_time, end_time, duration_s, aspect_ratio, user_message,
        # display_lyrics}, còn `video__create_music_video` KHÔNG nhận field nào (mọi field
        # đều bị server trả "extra_forbidden" — đo trên conversation thật). Nên tin nhắn đầu
        # nói đủ ý, tin nhắn xác nhận thì để trống trơn.
        lyrics_line = ("Render the lyrics on screen." if render_lyrics
                       else "Do not render lyrics on screen.")
        end_s = int(start_s) + int(duration_s)
        msg = (f"Create the music video for this song, using the segment from "
               f"{int(start_s)}s to {end_s}s ({int(duration_s)} seconds). "
               f"Use aspect ratio {aspect_ratio}. {lyrics_line}")
        if note:
            msg = f"{msg} Visual direction: {note.strip()}"

        # current_song_id = bài đang mở trên player của Flow Music UI. Không đặt thì agent
        # phải tự đoán "this song" là bài nào — với conversation nhiều bài là đoán sai.
        ctx = {"current_song_id": clip_id, "song_queue": [{"id": clip_id}]}
        result = await self.send_message(msg, conversation_id=conversation_id,
                                          client_context=ctx, timeout=timeout)
        if _is_error(result):
            return {"error": result.get("error", "send_message failed")}
        payload = result.get("data", result)
        if not isinstance(payload, dict):
            return {"error": "Unexpected response shape from extension"}
        conv_id = payload.get("conversation_id") or conversation_id

        created = self._video_tool_returns(payload, "video__create_music_video")
        job_id = self._video_job_id(created)
        proposed = self._video_tool_returns(payload, "video__propose_music_video")

        if not job_id and proposed and auto_confirm:
            # Nhịp hai: xác nhận đúng MỘT lần. Gửi lại nữa là mời agent submit lần thứ hai —
            # mỗi lần submit là ~500 credit, không phải thứ đáng thử vận may.
            confirm = await self.send_message(
                "Yes, create that music video now.", conversation_id=conv_id,
                client_context=ctx, timeout=timeout)
            if not _is_error(confirm):
                payload2 = confirm.get("data", confirm)
                if isinstance(payload2, dict):
                    created2 = self._video_tool_returns(payload2, "video__create_music_video")
                    job_id = self._video_job_id(created2) or job_id
                    created = created + created2
                    payload["text"] = payload2.get("text") or payload.get("text")

        status = "submitted" if job_id else ("proposed" if proposed else "not_called")
        if status == "submitted":
            logger.warning("Flow Music: đã đặt render music video (job %s) cho clip %s "
                           "— ~500 credit, 15-30 phút", job_id, clip_id)
        return {
            "conversation_id": conv_id,
            "clip_id": clip_id,
            "status": status,
            "video_job_id": job_id,
            "text": payload.get("text"),
            "raw_tool_returns": created + proposed,
        }

    async def music_video_status(self, clip_id: str) -> dict:
        """Music video của một bài đã xong chưa → {status, video_url, video_clip_id}.

        Video KHÔNG nằm trong clip audio: clip audio chỉ mang `video_id` trỏ sang một clip
        riêng (`op_type: video__create_music_video`) và `video_url` nằm ở clip đó. URL của
        Flow Music là URL tĩnh public (bucket producer-app-public) nên lấy được là tải thẳng,
        không cần ký lại như Flow video.
        """
        res = await self.get_clips([clip_id])
        if _is_error(res):
            return {"error": res.get("error", "get_clips failed")}
        clip = (((res.get("data", res)) or {}).get("clips") or {}).get(clip_id)
        if not clip:
            return {"error": f"Không thấy clip {clip_id}"}

        if clip.get("video_url"):
            return {"status": "done", "video_url": clip["video_url"],
                    "video_clip_id": clip.get("video_id") or clip_id}

        video_id = clip.get("video_id")
        if not video_id:
            return {"status": "none", "clip_id": clip_id,
                    "note": "Bài này chưa có music video nào được đặt render."}

        res2 = await self.get_clips([video_id])
        if _is_error(res2):
            return {"error": res2.get("error", "get_clips failed")}
        vclip = (((res2.get("data", res2)) or {}).get("clips") or {}).get(video_id) or {}
        url = vclip.get("video_url")
        return {
            "status": "done" if url else "pending",
            "video_url": url,
            "video_clip_id": video_id,
            "title": vclip.get("title") or clip.get("title"),
        }


def _is_error(result: dict) -> bool:
    return bool(result.get("error")) or (isinstance(result.get("status"), int) and result["status"] >= 400)


# Singleton
_client: Optional[MusicClient] = None


def get_music_client() -> MusicClient:
    global _client
    if _client is None:
        _client = MusicClient()
    return _client
