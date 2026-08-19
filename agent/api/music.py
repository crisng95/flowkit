"""Google Flow Music (flowmusic.app) endpoints — relay qua cùng 1 extension WS với Flow video.

Khác Flow video: không có API tạo nhạc với tham số cấu trúc. `POST /create-song` là API
tiện dụng bậc cao (gửi prompt → chờ agent phía Google tạo bài → poll → trả audio_url thẳng);
`POST /send-message` là API bậc thấp cho các lượt chat tiếp theo trong 1 conversation (đổi
tỉ lệ video, yêu cầu chỉnh sửa...).
"""
import os
import re
import unicodedata
from typing import Optional
from urllib.parse import quote, urlparse

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from agent.services.music_client import get_music_client

router = APIRouter(prefix="/music", tags=["music"])


class CreateSongRequest(BaseModel):
    prompt: str
    conversation_id: Optional[str] = None   # None → tạo conversation mới
    timeout: Optional[float] = None          # giây, mặc định MUSIC_GENERATION_TIMEOUT


class SendMessageRequest(BaseModel):
    content: str
    conversation_id: Optional[str] = None
    client_context: Optional[dict] = None
    model_name: str = "producer:standard"
    mode: str = "standard"
    timeout: Optional[float] = None


class RenameConversationRequest(BaseModel):
    title: str


class CreateMusicVideoRequest(BaseModel):
    clip_id: str                              # bài hát (clip audio) muốn dựng video
    conversation_id: Optional[str] = None     # conversation chứa bài đó (nên có)
    aspect_ratio: str = "16:9"                # "16:9" | "9:16" | "1:1"
    render_lyrics: bool = False
    note: Optional[str] = None                # NỘI DUNG khung hình (cái gì xuất hiện)
    # PHONG CÁCH — tách khỏi `note` có chủ đích. Không nói phong cách thì mỗi cảnh một chất
    # liệu (đo thật: ảnh thật → giấy cắt dán → tranh 3D → đất nặn trong cùng một video 60s).
    style: Optional[str] = None
    # Ảnh neo phong cách: URL công khai, hoặc "auto" để Flow Music tự sinh ảnh neo từ `style`
    # (+ `note`) trước khi đặt render. Đây là kênh neo CHẮC nhất — xem create_music_video.
    style_image_url: Optional[str] = None
    start_s: int = 0                          # video dựng theo MỘT ĐOẠN của bài, không cả bài
    duration_s: int = 60
    # False = chỉ để agent ĐỀ XUẤT, không bấm nút render (không tốn credit) — dùng để thử.
    auto_confirm: bool = True
    timeout: Optional[float] = None


class ClipsRequest(BaseModel):
    clip_ids: list[str]


def _require_connected():
    client = get_music_client()
    if not client.connected:
        raise HTTPException(503, "Extension not connected")
    return client


def _raise_if_error(result: dict):
    if result.get("error"):
        status = result.get("status") if isinstance(result.get("status"), int) else 502
        raise HTTPException(status, result["error"])


@router.get("/status")
async def music_status():
    """Trạng thái kết nối extension + tài khoản Flow Music đang đăng nhập."""
    client = get_music_client()
    return {
        "connected": client.connected,
        "music_key_present": client._music_key is not None,
        "account": client.identity,
    }


@router.get("/credits")
async def get_credits():
    client = _require_connected()
    result = await client.get_credits()
    _raise_if_error(result)
    return result.get("data", result)


@router.post("/create-song")
async def create_song(body: CreateSongRequest):
    """Tạo bài hát từ 1 mô tả bằng ngôn ngữ tự nhiên (tiếng Anh khuyến nghị — giống style
    prompt của Suno: nhạc cụ, nhịp, tâm trạng...). `conversation_id` bỏ trống → tạo mới.

    Blocking tới khi có audio_url (thường 30-70s/lượt) — trả lỗi rõ ràng nếu agent phía
    Google không hiểu prompt thành lệnh tạo nhạc (vd trả lời bằng câu hỏi làm rõ thay vì gọi
    tool), hoặc nếu generate/poll timeout.
    """
    client = _require_connected()
    result = await client.create_song(body.prompt, conversation_id=body.conversation_id,
                                       timeout=body.timeout)
    if result.get("error") and not result.get("songs"):
        raise HTTPException(502, result)
    return result


@router.post("/send-message")
async def send_message(body: SendMessageRequest):
    """API bậc thấp: gửi 1 tin nhắn chat vào conversation (mới hoặc có sẵn), trả nguyên
    kết quả agent (parts/tool_returns/text) — dùng cho các lượt sau khi đã có bài hát (vd
    yêu cầu tạo music video, đổi tỉ lệ khung hình...)."""
    client = _require_connected()
    result = await client.send_message(
        body.content, conversation_id=body.conversation_id,
        client_context=body.client_context, model_name=body.model_name,
        mode=body.mode, timeout=body.timeout,
    )
    _raise_if_error(result)
    return result.get("data", result)


@router.post("/create-music-video")
async def create_music_video(body: CreateMusicVideoRequest):
    """Đặt lệnh dựng MUSIC VIDEO của Flow Music cho một bài hát đã có.

    ⚠ **~750 credit và ~9 phút mỗi video** (đo trên 5 lượt thật) — đắt hơn mọi thứ khác trong
    Flow Kit gộp lại, nhưng credit chỉ trừ khi render XONG; job hỏng giữa chừng không mất gì.
    Endpoint này KHÔNG chờ render xong: nó trả về ngay khi agent phía Flow Music nhận việc.
    Hỏi kết quả bằng `GET /api/music/music-video-job/{job_id}` — KHÔNG phải qua clip_id, clip
    audio không bao giờ được cập nhật.

    `auto_confirm=false` → chỉ lấy ĐỀ XUẤT (agent gọi `video__propose_music_video`), không
    render, không tốn credit. Dùng để xem agent hiểu yêu cầu thế nào trước khi tiêu tiền.

    Trả `status`: `submitted` (đã đặt render) | `proposed` (mới đề xuất) | `not_called`
    (agent hiểu thành việc khác — đọc `text`).
    """
    client = _require_connected()
    result = await client.create_music_video(
        body.clip_id, conversation_id=body.conversation_id,
        aspect_ratio=body.aspect_ratio, render_lyrics=body.render_lyrics,
        note=body.note or "", style=body.style or "",
        style_image_url=body.style_image_url,
        start_s=body.start_s, duration_s=body.duration_s,
        auto_confirm=body.auto_confirm, timeout=body.timeout)
    _raise_if_error(result)
    return result


@router.get("/conversations/{conversation_id}/videos")
async def conversation_music_videos(conversation_id: str):
    """Music video ĐÃ đặt render trong một conversation (kèm link nếu xong).

    Dùng để nhặt lại video đã trả tiền hôm trước thay vì render lại — Flow Music không có API
    "liệt kê video của tôi", dấu vết duy nhất nằm trong log tin nhắn của conversation.
    """
    client = _require_connected()
    result = await client.conversation_music_videos(conversation_id)
    _raise_if_error(result)
    return result


@router.get("/music-video-job/{job_id}")
async def music_video_job_status(job_id: str):
    """Tiến độ + kết quả theo `job_id` mà `POST /create-music-video` trả về.

    Đã chuẩn hoá: {status, stage, video_url, clip_id, duration_s, runtime_s, error, raw}.
    Đây là NGUỒN SỰ THẬT duy nhất cho music video."""
    client = _require_connected()
    result = await client.music_video_job_status(job_id)
    _raise_if_error(result)
    return result.get("data", result)


@router.get("/music-video/{clip_id}")
async def music_video_status(clip_id: str):
    """Music video của bài `clip_id` xong chưa → `{status, video_url, video_clip_id}`.

    `status`: `done` (có `video_url`, tải thẳng được — URL tĩnh public) | `pending` (đang
    render) | `none` (chưa từng đặt render bài này).
    """
    client = _require_connected()
    result = await client.music_video_status(clip_id)
    _raise_if_error(result)
    return result


@router.get("/song-status/{operation_id}")
async def song_status(operation_id: str):
    client = _require_connected()
    result = await client.get_song_status(operation_id)
    _raise_if_error(result)
    return result.get("data", result)


@router.post("/clips")
async def get_clips(body: ClipsRequest):
    """Lấy chi tiết clip (audio_url/wav_url/title/lyrics/...) theo clip_id."""
    client = _require_connected()
    result = await client.get_clips(body.clip_ids)
    _raise_if_error(result)
    return result.get("data", result)


@router.get("/conversations")
async def list_conversations(limit: int = 30, offset: int = 0):
    client = _require_connected()
    result = await client.list_conversations(limit=limit, offset=offset)
    _raise_if_error(result)
    return result.get("data", result)


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    client = _require_connected()
    result = await client.get_conversation(conversation_id)
    _raise_if_error(result)
    return result.get("data", result)


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(conversation_id: str, body: RenameConversationRequest):
    client = _require_connected()
    result = await client.rename_conversation(conversation_id, body.title)
    _raise_if_error(result)
    return {"ok": True}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, delete_clips: bool = False,
                               delete_spaces: bool = False, delete_music_videos: bool = False):
    """Xoá 1 conversation (và bài hát trong đó) khỏi tài khoản Flow Music. Mặc định chỉ xoá
    bản ghi conversation — bật `delete_clips`/`delete_music_videos` nếu muốn xoá luôn media
    liên quan (ý nghĩa chính xác của các cờ này chưa được Flow Music tài liệu hoá, suy ra từ
    tên field — cẩn thận khi bật)."""
    client = _require_connected()
    result = await client.delete_conversation(
        conversation_id, delete_clips=delete_clips, delete_spaces=delete_spaces,
        delete_music_videos=delete_music_videos)
    _raise_if_error(result)
    return {"ok": True}


@router.get("/download")
async def download_song(url: str, title: str = ""):
    """Tải một bài của Flow Music thẳng về máy người dùng, tên file theo tiêu đề.

    Phải đi vòng qua agent chứ không dùng `<a download>` được: `audio_url` nằm trên host
    khác, mà thuộc tính `download` bị trình duyệt BỎ QUA khi link trỏ cross-origin — bấm nút
    chỉ mở thêm một tab phát nhạc. Agent tải hộ rồi phát lại dưới dạng attachment.

    Khác `POST /projects/{pid}/music/add`: chỗ đó tải về ĐĨA của agent để đưa vào playlist,
    còn đây không lưu gì cả, chỉ chuyển tiếp cho trình duyệt.
    """
    parsed = urlparse(url)
    # Agent chạy trên máy người dùng và mở cổng 8100 — một endpoint nhận URL tuỳ ý là đường
    # để trang web bất kỳ đọc hộ các dịch vụ đang chạy trên localhost/LAN. Chỉ cho https ra
    # ngoài, chặn tên máy nội bộ.
    if parsed.scheme != "https" or not parsed.hostname:
        raise HTTPException(400, "Chỉ nhận URL https")
    host = parsed.hostname.lower()
    if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"} or host.endswith(".local"):
        raise HTTPException(400, f"Không tải từ địa chỉ nội bộ ({host})")

    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as c:
        resp = await c.get(url)
    if resp.status_code >= 400:
        raise HTTPException(502, f"Tải nhạc thất bại ({resp.status_code})")

    ext = os.path.splitext(parsed.path)[1].lower()
    if ext not in {".mp3", ".m4a", ".wav", ".ogg", ".flac", ".aac"}:
        ext = ".m4a"
    name = re.sub(r'[\/:*?"<>|\r\n\t]+', "", (title or "").strip())[:60] or "flowmusic"
    # Hai lần tên: `filename` phải ASCII thuần (tiêu đề tiếng Việt rơi hết dấu ở đây), còn
    # `filename*` mới giữ nguyên dấu cho trình duyệt nào đọc được — trình duyệt hiện đại ưu
    # tiên bản sau. Bỏ bản ASCII đi thì vài trình duyệt lưu ra tên toàn ký tự %.
    ascii_name = (unicodedata.normalize("NFKD", name)
                  .encode("ascii", "ignore").decode().strip()) or "flowmusic"
    return Response(
        content=resp.content,
        media_type=resp.headers.get("content-type") or "audio/mpeg",
        headers={"Content-Disposition":
                 f'attachment; filename="{ascii_name}{ext}"; '
                 f"filename*=UTF-8''{quote(name + ext)}"},
    )
