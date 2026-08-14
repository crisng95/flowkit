"""Bản media độ phân giải cao — ảnh (2K/4K) và video (1080p/4K).

Flow chỉ phát bản HD (phân giải thấp) của cả ảnh lẫn video: đủ để xem trong app, KHÔNG đủ
để dựng video truyện hay export sang DaVinci Resolve. Cả hai đều xin bản lớn qua một
endpoint riêng và trần độ phân giải đều phụ thuộc tier tài khoản.

  Ảnh  — `/v1/flow/upsampleImage`, đồng bộ, trả base64 (`encodedImage`), KHÔNG tốn credit.
         TIER_ONE → 2K, TIER_TWO → 4K.
  Video — `video:batchAsyncGenerateVideoUpsampleVideo`, BẤT ĐỒNG BỘ: submit → poll như một
         lượt render (~1 phút/video). TIER_ONE → 1080p, TIER_TWO → 4K. Đo trên tier ONE →
         1080p cũng KHÔNG trừ credit; bản 4K chưa kiểm chứng, có thể tốn.

Bản hi-res lưu cạnh bản HD; `image_path`/`video_path` (bản HD) giữ nguyên nên app vẫn hiển
thị bản nhẹ, chỉ khâu dựng/export mới đọc bản hi-res.
"""
import base64
import binascii
import logging

from agent.config import (
    UPSAMPLE_IMAGE_RESOLUTIONS, UPSAMPLE_IMAGE_DEFAULT,
    UPSAMPLE_VIDEO_RESOLUTIONS, UPSAMPLE_VIDEO_DEFAULT, UPSAMPLE_VIDEO_ORDER,
)
from agent.services.flow_client import get_flow_client
from agent.studio import db, media_store

logger = logging.getLogger(__name__)


def res_for_tier(tier: str) -> str:
    """Độ phân giải cao nhất tier này được phép tải (TIER_ONE → 2K, TIER_TWO → 4K)."""
    return UPSAMPLE_IMAGE_RESOLUTIONS.get(tier or "", UPSAMPLE_IMAGE_DEFAULT)


def res_label(resolution: str) -> str:
    """'UPSAMPLE_IMAGE_RESOLUTION_4K' → '4k' (dùng làm hậu tố tên file + nhãn UI)."""
    return (resolution or "").rsplit("_", 1)[-1].lower() or "hires"


def _encoded_image(payload) -> str | None:
    """Base64 của ảnh đã phóng to trong response (chấp nhận vài biến thể tên khoá)."""
    if isinstance(payload, dict):
        for key in ("encodedImage", "encodedImageBytes", "imageBytes", "encodedMedia"):
            v = payload.get(key)
            if isinstance(v, str) and len(v) > 256:   # bỏ qua chuỗi ngắn (không phải ảnh)
                return v
        for v in payload.values():
            hit = _encoded_image(v)
            if hit:
                return hit
    elif isinstance(payload, list):
        for v in payload:
            hit = _encoded_image(v)
            if hit:
                return hit
    return None


async def fetch(media_id: str, project_id: str, flow_project_id: str,
                tier: str, resolution: str | None = None) -> dict:
    """Gọi upsampleImage rồi lưu ảnh về local. Trả {path, resolution, bytes}.

    Raise RuntimeError kèm lý do đọc được (tiếng Việt) khi hỏng — caller quyết định coi đó
    là lỗi cứng (endpoint thủ công) hay chỉ ghi log (tự động sau khi sinh ảnh).
    """
    target = resolution or res_for_tier(tier)
    client = get_flow_client()
    if not client.connected:
        raise RuntimeError("Extension chưa kết nối")

    res = await client.upscale_image(media_id, flow_project_id,
                                     target_resolution=target, user_paygate_tier=tier)
    if res.get("error"):
        raise RuntimeError(str(res["error"]))
    status = res.get("status")
    if isinstance(status, int) and status >= 400:
        raise RuntimeError(f"Flow trả HTTP {status}")

    b64 = _encoded_image(res.get("data", res))
    if not b64:
        # Không có base64 → thử URL trực tiếp trong response (phòng khi Flow đổi kiểu trả).
        url = media_store.direct_url_in(res.get("data", res))
        if not url:
            raise RuntimeError("Response không có ảnh (encodedImage)")
        web = await media_store.save_from_url(
            f"{media_id}_{res_label(target)}", project_id, "png", url)
        if not web:
            raise RuntimeError("Tải ảnh hi-res về lỗi")
        return {"path": web, "resolution": target, "bytes": 0}

    try:
        data = base64.b64decode(b64, validate=False)
    except (binascii.Error, ValueError) as e:
        raise RuntimeError(f"Base64 hỏng: {e}") from e
    if not data:
        raise RuntimeError("Ảnh hi-res rỗng")

    web = media_store.save_bytes(f"{media_id}_{res_label(target)}", project_id, data)
    return {"path": web, "resolution": target, "bytes": len(data)}


async def upscale_shot(shot: dict, project: dict, tier: str,
                       resolution: str | None = None) -> dict:
    """Tải bản hi-res cho ảnh của một shot và ghi vào DB. Raise RuntimeError khi hỏng."""
    media_id = shot.get("image_media_id")
    if not media_id:
        raise RuntimeError("Shot chưa có ảnh")
    out = await fetch(media_id, project["id"], project.get("flow_project_id") or "",
                      tier, resolution)
    # Bản 2K/4K của ảnh CŨ (shot vừa regen ảnh) không ai dùng nữa và nặng vài MB — xoá đi,
    # nếu không mỗi lần regen lại bỏ lại một file mồ côi. Không đụng khi chỉ tải lại cùng ảnh.
    old = shot.get("image_hires_path")
    if old and old != out["path"]:
        f = media_store.MEDIA_DIR / old.replace("/media/", "", 1)
        try:
            f.unlink(missing_ok=True)
        except OSError:
            pass
    await db.update("shot", shot["id"], {
        "image_hires_path": out["path"],
        "image_hires_media_id": media_id,     # bản hi-res thuộc về ảnh HD nào
        "image_hires_res": out["resolution"],
        "updated_at": db.now(),
    })
    return out


def is_stale(shot: dict) -> bool:
    """True khi bản hi-res thiếu HOẶC thuộc về một ảnh CŨ (shot đã regen ảnh sau đó)."""
    if not shot.get("image_hires_path"):
        return True
    return shot.get("image_hires_media_id") != shot.get("image_media_id")


def path_for(shot: dict) -> str | None:
    """Web path của bản hi-res CÒN ĐÚNG với ảnh hiện tại của shot, None nếu không có.

    Dùng ở khâu dựng/export: một bản hi-res cũ (shot đã regen ảnh sau khi upsample) phải bị
    bỏ qua, nếu không video/timeline sẽ dựng bằng ẢNH SAI thay vì ảnh đang hiển thị."""
    return None if is_stale(shot) else shot.get("image_hires_path")


def shot_image(shot: dict) -> str | None:
    """Ảnh dùng để DỰNG shot: bản hi-res nếu còn đúng, không thì bản HD."""
    return path_for(shot) or shot.get("image_path")


# ─── Video (1080p/4K) ───────────────────────────────────────
# Bất đồng bộ: submit rồi poll như một lượt render. Hàm poll do studio.py truyền vào
# (`_poll_video`) để module này không phải import ngược lên tầng API.

# Thứ tự tăng dần — dùng để hạ lựa chọn của người dùng xuống đúng trần của tier. Đọc từ
# config (models.json) chứ không hardcode: Flow mở thêm mức 2K nằm GIỮA 1080p và 4K, mà bảng
# hardcode hai mức thì thêm một mức là phải sửa cả thứ tự lẫn phép cắt danh sách.
_VIDEO_RES_ORDER = list(UPSAMPLE_VIDEO_ORDER)


def _cap_for(tier: str) -> str:
    """Trần của tier, đã kẹp vào danh sách mức đang có (cấu hình lệch không làm nổ index)."""
    cap = UPSAMPLE_VIDEO_RESOLUTIONS.get(tier or "", UPSAMPLE_VIDEO_DEFAULT)
    return cap if cap in _VIDEO_RES_ORDER else _VIDEO_RES_ORDER[-1]


def video_res_for_tier(tier: str, prefer: str | None = None) -> str:
    """Độ phân giải upscale sẽ dùng.

    Trần theo tier (ONE → 1080p, TWO → 4K). `prefer` là lựa chọn của dự án: tier TWO có thể
    cố tình lấy 1080p hay 2K cho file nhẹ + rẻ hơn thay vì luôn 4K. Lựa chọn CAO HƠN trần bị
    hạ xuống trần thay vì gửi đi rồi để Flow từ chối."""
    cap = _cap_for(tier)
    if not prefer or prefer not in _VIDEO_RES_ORDER:
        return cap
    return min(prefer, cap, key=_VIDEO_RES_ORDER.index)


def video_res_choices(tier: str) -> list[str]:
    """Các mức người dùng được chọn ở tier này (mọi mức ≤ trần)."""
    return _VIDEO_RES_ORDER[:_VIDEO_RES_ORDER.index(_cap_for(tier)) + 1]


def video_res_label(resolution: str) -> str:
    """'VIDEO_RESOLUTION_1080P' → '1080p' (hậu tố tên file + nhãn nút trong UI)."""
    return (resolution or "").rsplit("_", 1)[-1].lower() or "hires"


def video_upscalable(shot: dict) -> bool:
    """Chỉ upscale được video là MỘT media Flow.

    Shot chained (beat dài hơn một clip) được ghép cục bộ từ nhiều sub-clip và `video_path`
    trỏ vào /studio-media/, còn `video_media_id` chỉ là clip ĐẦU — upscale nó sẽ trả về mỗi
    clip đầu, mất phần sau. Những shot này phải bỏ qua, không phải "chưa upscale"."""
    if not shot.get("video_media_id"):
        return False
    return (shot.get("video_path") or "").startswith("/media/")


def video_is_stale(shot: dict) -> bool:
    """True khi bản upscale thiếu HOẶC thuộc về một video CŨ (shot đã render lại video)."""
    if not shot.get("upscale_path"):
        return True
    return shot.get("upscale_media_id") != shot.get("video_media_id")


def video_path_for(shot: dict) -> str | None:
    """Web path bản upscale CÒN ĐÚNG với video hiện tại của shot, None nếu không có."""
    return None if video_is_stale(shot) else shot.get("upscale_path")


def shot_video(shot: dict) -> str | None:
    """Video dùng để GHÉP/EXPORT shot: bản upscale nếu còn đúng, không thì bản HD."""
    return video_path_for(shot) or shot.get("video_path")


def _upsample_operation(data: dict) -> tuple[str | None, str | None]:
    """(operation name, generation status) từ response upsample video.

    Flow trả HAI shape khác nhau và cả hai đều hợp lệ:
      • lần đầu (PENDING)  → operations[0].operation.name
      • video ĐÃ upscale rồi (SUCCESSFUL ngay, không tính credit lại)
                           → operations[0].mediaGenerationId, không có .operation
    Cả hai đều tên `<mediaId>_upsampled`; media[0].name là chốt chặn cuối.
    """
    ops = (data or {}).get("operations") or []
    op = ops[0] if ops else {}
    name = ((op.get("operation") or {}).get("name")
            or op.get("mediaGenerationId")
            or ((data.get("media") or [{}])[0]).get("name"))
    return name, op.get("status")


async def upscale_video(shot: dict, project: dict, tier: str, poll,
                        resolution: str | None = None) -> dict:
    """Submit upsample cho video của shot, chờ xong, tải về và ghi DB.

    `poll(client, media_id, flow_project_id, timeout)` → URL video hoặc None
    (studio._poll_video). Raise RuntimeError kèm lý do khi hỏng.
    """
    media_id = shot.get("video_media_id")
    if not media_id:
        raise RuntimeError("Shot chưa có video")
    if not video_upscalable(shot):
        raise RuntimeError("Shot ghép từ nhiều clip (chained) — Flow không upscale được "
                           "video ghép cục bộ")
    target = resolution or video_res_for_tier(tier, project.get("upscale_res"))
    client = get_flow_client()
    if not client.connected:
        raise RuntimeError("Extension chưa kết nối")

    res = await client.upscale_video(
        media_id=media_id, scene_id=shot["id"], aspect_ratio=project["aspect_ratio"],
        resolution=target, project_id=project.get("flow_project_id") or "",
        user_paygate_tier=tier, workflow_id=shot.get("video_workflow_id"))
    if res.get("error"):
        raise RuntimeError(str(res["error"]))
    status = res.get("status")
    if isinstance(status, int) and status >= 400:
        raise RuntimeError(f"Flow trả HTTP {status}")

    op_name, gen_status = _upsample_operation(res.get("data", res))
    if not op_name:
        raise RuntimeError("Flow không trả operation cho upscale")
    if gen_status and "FAIL" in gen_status:
        raise RuntimeError(f"Flow báo upscale hỏng ({gen_status})")

    # Bản upscale là một media riêng tên `<mediaId>_upsampled`; poll theo đúng tên đó.
    url = await poll(client, op_name, project.get("flow_project_id") or "", 600)
    if not url:
        raise RuntimeError("Upscale chưa xong trong thời gian chờ")

    # Tên file mang op_name (<media_id>_upsampled) nên bản upscale không đè lên bản HD.
    web = await media_store.save_from_url(op_name, project["id"], "mp4", url)
    if not web:
        raise RuntimeError("Tải video upscale về lỗi")

    old = shot.get("upscale_path")
    if old and old != web:
        f = media_store.MEDIA_DIR / old.replace("/media/", "", 1)
        try:
            f.unlink(missing_ok=True)
        except OSError:
            pass
    await db.update("shot", shot["id"], {
        "upscale_path": web, "upscale_url": url,
        "upscale_media_id": media_id, "upscale_res": target,
        "updated_at": db.now(),
    })
    return {"path": web, "url": url, "resolution": target}


async def auto_upscale_video(shot: dict, project: dict, tier: str, poll) -> None:
    """Hook chạy sau khi render xong video shot, khi dự án bật 'tự upscale video'.
    Best-effort: hỏng chỉ ghi log (video HD đã lưu), tải bù được sau."""
    if not project.get("auto_upscale_video"):
        return
    try:
        out = await upscale_video(shot, project, tier, poll)
        logger.info("upscale %s cho shot %s", video_res_label(out["resolution"]),
                    (shot.get("title") or shot["id"])[:20])
    except Exception as e:  # noqa: BLE001 — không bao giờ chặn luồng render
        logger.warning("upscale video hỏng cho shot %s: %s",
                       (shot.get("title") or shot["id"])[:20], e)


async def auto_upscale_shot(shot: dict, project: dict, tier: str) -> None:
    """Hook chạy sau khi sinh ảnh shot, khi dự án bật 'tự tải ảnh 2K/4K'. Best-effort:
    lỗi upsample KHÔNG được làm hỏng lượt sinh ảnh (ảnh HD đã lưu xong), chỉ ghi log —
    có thể tải bù sau bằng nút 'Tải ảnh 2K/4K' hoặc job cả dự án."""
    if not project.get("auto_hires"):
        return
    try:
        out = await upscale_shot(shot, project, tier)
        logger.info("hi-res %s cho shot %s (%.1f MB)", res_label(out["resolution"]),
                    (shot.get("title") or shot["id"])[:20], out["bytes"] / 1e6)
    except Exception as e:  # noqa: BLE001 — không bao giờ chặn luồng sinh ảnh
        logger.warning("tải ảnh hi-res hỏng cho shot %s: %s",
                       (shot.get("title") or shot["id"])[:20], e)
