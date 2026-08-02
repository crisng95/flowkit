"""Ai đang đăng nhập Flow — và dự án nào thuộc về ai.

Flow gắn MỌI thứ vào tài khoản Google đang đăng nhập trong Chrome: project, media, credit.
`media_id` do account A sinh ra thì token của account B không resolve được, nên dự án trong
studio.db bắt buộc phải mang chủ sở hữu. Không có nó, đổi account là thấy một danh sách dự
án dùng được một nửa: ảnh đã cache trên đĩa vẫn xem được, còn mọi thao tác gọi Flow (sinh
ảnh/video, upscale, refresh URL) đều hỏng với lỗi khó hiểu.

Danh tính do extension cung cấp (background.js, mục "Account identity") và đẩy lên agent qua
WebSocket; module này lưu lại vào bảng `account`, trả lời "tài khoản hiện tại là ai" và "dự
án này có phải của họ không".

Chưa xác định được tài khoản (extension tắt, chưa đăng nhập, fetch lỗi) → `current()` trả
None và phía gọi mở cửa: thà hiện tất cả kèm cảnh báo còn hơn khoá người dùng khỏi chính dữ
liệu của họ vì extension rớt.
"""
import logging
import time
from typing import Optional

from agent.services.flow_client import get_flow_client
from agent.studio import db

logger = logging.getLogger(__name__)

# Extension tự đẩy identity lúc kết nối và mỗi 45 phút, nên agent gần như luôn có sẵn. Chỉ
# khi CHƯA có gì mới hỏi ngược lại extension — và giãn ra để một loạt request song song
# không biến thành một loạt round-trip WS.
_PROBE_COOLDOWN = 30.0
_last_probe = 0.0
_cache: dict = {"row": None, "ts": 0.0}
_CACHE_TTL = 15.0


def _account_id(ident: dict) -> Optional[str]:
    """Khoá tài khoản = email viết thường (người đọc hiểu ngay); `sub` chỉ dùng khi không có
    email — tokeninfo đôi khi chỉ trả `sub`."""
    email = (ident.get("email") or "").strip().lower()
    if email:
        return email
    sub = (ident.get("sub") or "").strip()
    return f"sub:{sub}" if sub else None


async def _upsert(ident: dict) -> Optional[dict]:
    aid = _account_id(ident)
    if not aid:
        return None
    ts = db.now()
    row = await db.query_one("SELECT * FROM account WHERE id=?", (aid,))
    fields = {
        "email": (ident.get("email") or "").strip().lower() or None,
        "name": ident.get("name"),
        "picture": ident.get("picture"),
        "sub": ident.get("sub"),
        "last_seen_at": ts,
    }
    if row:
        # Ảnh đại diện / tên có thể vắng khi identity đến từ tokeninfo — đừng ghi đè bằng None.
        upd = {k: v for k, v in fields.items() if v is not None or k == "last_seen_at"}
        await db.update("account", aid, upd)
    else:
        await db.insert("account", {"id": aid, "created_at": ts, **fields})
        _multi.update(value=None, ts=0.0)     # có thêm account → tính lại đường tắt một-account
        logger.info("Tài khoản Flow mới: %s", aid)
    return await db.query_one("SELECT * FROM account WHERE id=?", (aid,))


async def _adopt_orphan_projects(account_id: str) -> int:
    """Dự án tạo từ trước khi có phân tài khoản (account_id NULL) về tay tài khoản ĐẦU TIÊN
    được nhận diện — chính là người đã tạo chúng, vì trước đó app chỉ phục vụ một account.
    Chạy đúng một lần; các account nhận diện sau không được vơ vét nữa."""
    if await db.kv_get("account_orphans_adopted"):
        return 0
    rows = await db.query_all("SELECT id FROM project WHERE account_id IS NULL")
    if rows:
        await db.execute("UPDATE project SET account_id=? WHERE account_id IS NULL", (account_id,))
        logger.info("Gán %d dự án chưa có chủ cho %s", len(rows), account_id)
    await db.kv_set("account_orphans_adopted", account_id)
    return len(rows)


async def current(probe: bool = True) -> Optional[dict]:
    """Tài khoản Flow đang đăng nhập (một dòng bảng `account`), None nếu chưa xác định được."""
    global _last_probe
    now = time.monotonic()
    client = get_flow_client()
    ident = client.identity
    # Cache chỉ dùng lại khi extension VẪN báo đúng tài khoản đó — đổi account trong Chrome
    # phải ăn ngay, không đợi hết TTL rồi mới đổi danh sách dự án.
    if (_cache["row"] and now - _cache["ts"] < _CACHE_TTL
            and (not ident or _account_id(ident) == _cache["row"]["id"])):
        return _cache["row"]

    if not ident and probe and client.connected and now - _last_probe > _PROBE_COOLDOWN:
        _last_probe = now
        try:
            ident = await client.fetch_identity()
        except Exception as e:                       # extension lỗi → coi như chưa xác định
            logger.warning("Không hỏi được tài khoản từ extension: %s", e)
    if not ident:
        return None

    row = await _upsert(ident)
    if row:
        await _adopt_orphan_projects(row["id"])
        _cache.update(row=row, ts=now)
    return row


async def current_id(probe: bool = True) -> Optional[str]:
    row = await current(probe=probe)
    return row["id"] if row else None


def invalidate() -> None:
    _cache.update(row=None, ts=0.0)
    _multi.update(value=None, ts=0.0)


_multi: dict = {"value": None, "ts": 0.0}


async def multi_account() -> bool:
    """Máy này đã từng thấy nhiều hơn một tài khoản Flow chưa?

    Chỉ khi có nhiều tài khoản thì việc canh chủ sở hữu mới có việc để làm — trường hợp một
    account (gần như tất cả người dùng) đi đường tắt này và không phải truy vấn gì thêm."""
    now = time.monotonic()
    if _multi["value"] is not None and now - _multi["ts"] < 60:
        return _multi["value"]
    rows = await db.query_all("SELECT id FROM account LIMIT 2")
    val = len(rows) > 1
    _multi.update(value=val, ts=now)
    return val


async def owner_label(account_id: str) -> str:
    """Tên hiển thị của chủ sở hữu cho thông báo lỗi."""
    row = await db.query_one("SELECT * FROM account WHERE id=?", (account_id,))
    return (row or {}).get("email") or account_id


async def list_accounts() -> list[dict]:
    return await db.query_all("SELECT * FROM account ORDER BY last_seen_at DESC")
