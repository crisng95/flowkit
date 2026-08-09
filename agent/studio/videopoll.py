"""Chờ một media video render xong trên Flow — MỘT bản dùng chung cho mọi đường render.

Trước đây `api/studio.py` và `studio/graph.py` mỗi nơi giữ một bản `_poll_video` riêng, nên
khi Flow đổi contract của `video:batchCheckAsyncVideoGenerationStatus` thì phải sửa hai chỗ
(và bản trong graph.py còn lệch timeout 240s so với 420s). Tất cả giờ đi qua đây.

Contract hiện tại (xem flow_client.check_video_status):
  request  {"media": [{"name": <mediaId>, "projectId": <flowProjectId>}]}
  response {"media": [{... mediaMetadata.mediaStatus.mediaGenerationStatus ...}]}

Trạng thái quan trọng:
  MEDIA_GENERATION_STATUS_SUCCESSFUL → xong; URL KHÔNG nằm trong response, phải resolve
                                       riêng qua media_store.resolve_url
  MEDIA_GENERATION_STATUS_FAILED     → hỏng hẳn (vd PROMINENT_PERSON); dừng ngay thay vì
                                       chờ hết giờ rồi mới báo
  còn lại (PENDING/ACTIVE/…)         → đang render, chờ tiếp
"""
import asyncio
import logging
import time as _t

from agent.config import VIDEO_POLL_TIMEOUT
from agent.studio import media_store

logger = logging.getLogger(__name__)

_SUCCESS = "MEDIA_GENERATION_STATUS_SUCCESSFUL"
_FAILED = "MEDIA_GENERATION_STATUS_FAILED"


class VideoFailed(Exception):
    """Flow báo lượt render HỎNG HẲN (lọc nội dung, lỗi model…) — chờ thêm vô ích."""


def _status_of(item: dict) -> tuple[str, str]:
    """(mediaGenerationStatus, lý do đọc được) từ một phần tử `media[]`."""
    st = ((item.get("mediaMetadata") or {}).get("mediaStatus") or {})
    reasons = st.get("failureReasons") or []
    why = ", ".join(str(r) for r in reasons) or (st.get("error") or {}).get("message") or ""
    return st.get("mediaGenerationStatus") or "", why


async def poll_video(client, media_id: str, project_id: str,
                     timeout: float | None = None, interval: float = 8) -> str | None:
    """Chờ tới khi `media_id` render xong → URL tải về. None nếu hết giờ (Flow VẪN đang
    render — người gọi không được submit lại). Raise VideoFailed khi Flow báo hỏng hẳn.

    `project_id` là flow_project_id (UUID dự án trên Flow), không phải id dự án nội bộ.
    """
    deadline = _t.monotonic() + (timeout or VIDEO_POLL_TIMEOUT)
    while _t.monotonic() < deadline:
        await asyncio.sleep(interval)
        st = await client.check_video_status([{"name": media_id, "projectId": project_id}])
        data = st.get("data", st)
        if not isinstance(data, dict):
            continue
        items = data.get("media") or []
        if not items:
            logger.warning("poll %s: response không có media (%s)", media_id[:8],
                           str(data)[:200])
            continue
        status, why = _status_of(items[0])
        if status == _FAILED:
            raise VideoFailed(why or "Flow báo render hỏng")
        if status != _SUCCESS:
            continue
        # Xong rồi nhưng response không kèm URL → resolve. Signed URL đôi khi chưa sẵn ngay
        # sau khi status chuyển SUCCESSFUL, nên thử lại vài nhịp trước khi bỏ cuộc.
        url = await media_store.resolve_url(media_id)
        if url:
            return url
        logger.info("poll %s: SUCCESSFUL nhưng chưa resolve được URL, thử lại", media_id[:8])
    return None
