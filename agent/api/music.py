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
