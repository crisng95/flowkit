"""Google Flow Music (flowmusic.app) endpoints — relay qua cùng 1 extension WS với Flow video.

Khác Flow video: không có API tạo nhạc với tham số cấu trúc. `POST /create-song` là API
tiện dụng bậc cao (gửi prompt → chờ agent phía Google tạo bài → poll → trả audio_url thẳng);
`POST /send-message` là API bậc thấp cho các lượt chat tiếp theo trong 1 conversation (đổi
tỉ lệ video, yêu cầu chỉnh sửa...).
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
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

    ⚠ **~500 credit và 15-30 phút mỗi video** — đắt hơn mọi thứ khác trong Flow Kit gộp lại.
    Endpoint này KHÔNG chờ render xong: nó trả về ngay khi agent phía Flow Music nhận việc.
    Hỏi kết quả bằng `GET /api/music/music-video/{clip_id}`.

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


@router.get("/music-video-job/{job_id}")
async def music_video_job_status(job_id: str):
    """Tiến độ render (phần trăm / thời gian còn lại) theo `job_id` mà
    `POST /create-music-video` trả về. Trả nguyên payload của Flow Music."""
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
