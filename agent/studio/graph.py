"""Node-graph executor for the Studio Node Editor (video-app.md §2.9).

A graph is {nodes:[{id,type,data}], edges:[{source,target}]}. We topo-sort, run each
node (mapping to existing Flow/agent ops), and feed each node the merged outputs of its
upstream nodes. The Output node applies the final media to the target shot/entity.

Self-contained (calls flow_client/media_store directly) to avoid importing the router.
"""
import asyncio
import json
import logging
import random

from agent.config import IMAGE_MODELS, VIDEO_POLL_TIMEOUT
from agent.services.flow_client import get_flow_client
from agent.studio import db, media_store, brain, assembler, imgproc, videopoll

logger = logging.getLogger(__name__)


class GraphError(Exception):
    pass


def _topo_sort(nodes: list[dict], edges: list[dict]) -> list[dict]:
    by_id = {n["id"]: n for n in nodes}
    indeg = {n["id"]: 0 for n in nodes}
    adj: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for e in edges:
        s, t = e.get("source"), e.get("target")
        if s in by_id and t in by_id:
            adj[s].append(t)
            indeg[t] += 1
    queue = [nid for nid, d in indeg.items() if d == 0]
    order = []
    while queue:
        nid = queue.pop(0)
        order.append(by_id[nid])
        for nb in adj[nid]:
            indeg[nb] -= 1
            if indeg[nb] == 0:
                queue.append(nb)
    if len(order) != len(nodes):
        raise GraphError("Đồ thị có chu trình (cycle)")
    return order


def _upstream_ids(node_id: str, edges: list[dict]) -> list[str]:
    return [e["source"] for e in edges if e.get("target") == node_id]


def _ancestors(node_id: str, edges: list[dict]) -> set[str]:
    """All nodes that can reach node_id (its upstream chain), including node_id itself."""
    rev: dict[str, list[str]] = {}
    for e in edges:
        rev.setdefault(e.get("target"), []).append(e.get("source"))
    seen: set[str] = set()
    stack = [node_id]
    while stack:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        for s in rev.get(x, []):
            if s:
                stack.append(s)
    return seen


def _descendants(node_id: str, edges: list[dict]) -> set[str]:
    """All nodes reachable FROM node_id (its downstream chain), including node_id itself.
    Used by propagate: regenerating a node should refresh everything it feeds."""
    fwd: dict[str, list[str]] = {}
    for e in edges:
        fwd.setdefault(e.get("source"), []).append(e.get("target"))
    seen: set[str] = set()
    stack = [node_id]
    while stack:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        for t in fwd.get(x, []):
            if t:
                stack.append(t)
    return seen


from agent.config import OMNI_FLASH_MODELS

# Friendly aspect tokens used by the node UI → Flow enums.
_IMG_ASPECT = {"16:9": "IMAGE_ASPECT_RATIO_LANDSCAPE",
               "9:16": "IMAGE_ASPECT_RATIO_PORTRAIT",
               "1:1": "IMAGE_ASPECT_RATIO_SQUARE"}
_VID_ASPECT = {"16:9": "VIDEO_ASPECT_RATIO_LANDSCAPE",
               "9:16": "VIDEO_ASPECT_RATIO_PORTRAIT"}


def _img_model(project: dict, data: dict | None = None) -> str | None:
    name = (data or {}).get("model") or project.get("image_model")
    return IMAGE_MODELS.get(name, name) if name else None


def _img_aspect(project: dict, data: dict | None = None) -> str:
    a = (data or {}).get("aspect")
    if a in _IMG_ASPECT:
        return _IMG_ASPECT[a]
    return (project.get("aspect_ratio") or "").replace(
        "VIDEO_ASPECT_RATIO_", "IMAGE_ASPECT_RATIO_") or "IMAGE_ASPECT_RATIO_LANDSCAPE"


def _omni_duration(project: dict) -> int | None:
    """Độ dài một clip Omni Flash theo ⚙ Cấu hình dự án — `video_model` là "4"/"6"/"8"/"10"
    (hoặc cả model key `abra_r2v_10s`). None khi dự án đang dùng Veo. Cùng luật với
    `_video_engine` bên api/studio.py, để node editor không tự ý chạy một độ dài khác."""
    raw = str(project.get("video_model") or "").strip()
    if raw in OMNI_FLASH_MODELS:
        return int(raw)
    for secs, key in OMNI_FLASH_MODELS.items():
        if raw == key:
            return int(secs)
    return None


def _vid_aspect(project: dict, data: dict | None = None) -> str:
    a = (data or {}).get("aspect")
    if a in _VID_ASPECT:
        return _VID_ASPECT[a]
    return project.get("aspect_ratio") or "VIDEO_ASPECT_RATIO_LANDSCAPE"


_GRAPH_IMG_RETRIES = 3
_GRAPH_VID_RETRIES = 2

# Node types that PRODUCE media (so they support lock/reuse + refresh on propagate). The
# local-processing ones (filter/text/upscale/blend) run with Pillow then re-upload to Flow.
_GEN_TYPES = ("image", "editImage", "removebg", "replacebg", "video",
              "filter", "text", "upscale", "blend", "crop", "vignette", "border",
              "colorgrade", "collage", "watermark")
_LOCAL_TYPES = ("filter", "text", "upscale", "blend", "crop", "vignette", "border",
                "colorgrade", "collage", "watermark")


def _deep_find(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _deep_find(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _deep_find(v, key)
            if r is not None:
                return r
    return None


def _block_reason(payload):
    for k in ("raiFilteredReason", "filteredReason", "raiFilterReason", "blockReason"):
        v = _deep_find(payload, k)
        if v:
            return str(v)
    return None


def _generated_media_id(payload, exclude=None):
    """The GENERATED image id from a generate/edit response. An edit passes the source as a
    BASE_IMAGE input and Flow echoes it back in `media`, so we scan ALL items for a
    generatedImage.mediaId and skip the source (`exclude`) — taking media[0] blindly would
    return the input image. Falls back to a raw media `name` if no generatedImage is present."""
    media = payload.get("media") or []
    found = []
    for m in media:
        if not isinstance(m, dict):
            continue
        mid = ((m.get("image") or {}).get("generatedImage") or {}).get("mediaId")
        if mid and mid != exclude:
            found.append(mid)
    if found:
        return found[-1]            # the generated result comes after any echoed inputs
    for m in media:                 # fallback: first raw media id that isn't the source
        name = m.get("name") if isinstance(m, dict) else None
        if name and name != exclude:
            return name
    return None


def _gen_media_item(payload, exclude=None):
    """The `media` item that holds the GENERATED image (same selection as _generated_media_id)
    — so its direct URL can be read for a resolve-free download. {} if none."""
    media = payload.get("media") or []
    chosen = {}
    for m in media:
        if not isinstance(m, dict):
            continue
        mid = ((m.get("image") or {}).get("generatedImage") or {}).get("mediaId")
        if mid and mid != exclude:
            chosen = m                  # last generated item wins (result after echoed inputs)
    return chosen


async def _img_gen_retry(call, pid, exclude=None):
    """Run an image-producing Flow call, VERIFY a media was made + downloaded, and retry
    on content-policy blocks / transient failures. Returns (media_id, web_path). `exclude`
    is the edit's source id, skipped so the result isn't the (echoed) input image."""
    last = ""
    for attempt in range(_GRAPH_IMG_RETRIES):
        res = await call()
        if res.get("error"):
            last = str(res["error"])
        else:
            p = res.get("data", res)
            mid = _generated_media_id(p, exclude)
            if mid:
                # download via the direct URL in the gen response when present (no rate-limited
                # resolve), else fall back to get_direct_media with retries
                url = media_store.direct_url_in(_gen_media_item(p, exclude))
                web = await media_store.save_media(mid, pid, "png", url)
                if web:
                    return mid, web
                last = "tải ảnh lỗi"
            else:
                last = _block_reason(p) or "Flow không trả media (có thể bị chặn)"
        if attempt < _GRAPH_IMG_RETRIES - 1:
            await asyncio.sleep(random.uniform(2, 5))
    raise GraphError(f"Tạo ảnh thất bại sau {_GRAPH_IMG_RETRIES} lần: {last}")


async def _load_local_image(media_id: str, pid: str):
    """Open a media's local file as a PIL image (downloading from Flow first if needed).
    Ext-robust via media_store.find_local (png/jpg/webp)."""
    from PIL import Image
    p = media_store.find_local(media_id, pid)
    if not p:
        web = await media_store.ensure_local(media_id, pid)
        p = media_store.find_local(media_id, pid) if web else None
    if not p:
        raise GraphError("Không tải được ảnh nguồn để xử lý")
    return await asyncio.to_thread(lambda: Image.open(p).convert("RGB"))


async def _save_and_upload(img, pid: str, flow_pid: str) -> tuple[str, str]:
    """Save a processed PIL image locally AND upload it to Flow → (media_id, web). Uploading
    keeps the chain alive: a locally-filtered image still gets a Flow media_id so downstream
    edit/video/output nodes (and 'Áp dụng') keep working."""
    import base64
    import io

    def _encode():
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()

    raw = await asyncio.to_thread(_encode)
    res = await get_flow_client().upload_image(
        base64.b64encode(raw).decode(), mime_type="image/png",
        project_id=flow_pid, file_name="node.png")
    if res.get("error"):
        raise GraphError(f"Upload ảnh đã xử lý lên Flow lỗi: {res['error']}")
    mid = res.get("_mediaId") or _generated_media_id(res.get("data", res))
    if not mid:
        raise GraphError("Flow không trả media_id cho ảnh đã xử lý")
    rel = f"{pid}/{mid}.png"
    dest = media_store.MEDIA_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(dest.write_bytes, raw)
    return mid, f"/media/{rel}"


async def _run_local_node(t: str, data: dict, inp: dict, pid: str):
    """Produce a PIL image for a local-processing node (filter/text/upscale/blend) from its
    upstream image(s). Raises GraphError with a clear message if inputs are missing."""
    # multi-input nodes read the distinct upstream images (in connection order)
    if t in ("blend", "watermark", "collage"):
        seen: list[str] = []
        for r in inp.get("references", []):
            mid = r.get("media_id")
            if mid and mid not in seen:
                seen.append(mid)
        if t == "collage":
            if len(seen) < 2:
                raise GraphError("Node Ghép lưới cần ít nhất 2 ảnh đầu vào.")
            imgs = [await _load_local_image(m, pid) for m in seen]
            return await asyncio.to_thread(imgproc.collage, imgs, data)
        if len(seen) < 2:
            raise GraphError(
                "Node Ghép/Blend cần 2 ảnh đầu vào." if t == "blend"
                else "Node Watermark cần 2 ảnh: nối ảnh nền TRƯỚC, logo SAU.")
        a = await _load_local_image(seen[0], pid)
        b = await _load_local_image(seen[1], pid)
        fn = imgproc.blend if t == "blend" else imgproc.watermark
        return await asyncio.to_thread(fn, a, b, data)

    src = inp.get("media_id")
    if not src:
        raise GraphError(f"Node '{t}' cần 1 ảnh đầu vào (nối từ Nguồn ảnh / Tạo ảnh).")
    img = await _load_local_image(src, pid)
    if t == "filter":
        return await asyncio.to_thread(imgproc.apply_filter, img, data)
    if t == "upscale":
        return await asyncio.to_thread(imgproc.upscale, img, data)
    if t == "crop":
        return await asyncio.to_thread(imgproc.crop, img, data)
    if t == "vignette":
        return await asyncio.to_thread(imgproc.vignette, img, data)
    if t == "border":
        return await asyncio.to_thread(imgproc.border, img, data)
    if t == "colorgrade":
        return await asyncio.to_thread(imgproc.color_grade, img, data)
    if t == "text":
        font = await asyncio.to_thread(assembler._caption_font)
        return await asyncio.to_thread(imgproc.overlay_text, img, data, font)
    raise GraphError(f"Loại node cục bộ không hỗ trợ: {t}")


async def _vid_gen_retry(submit, scene_key, pid, kind: str = "shot", flow_pid: str = ""):
    """Submit a video, poll, download — verify the clip exists and retry on failure.
    Returns (media_id, web_path).

    Hết giờ chờ thì KHÔNG submit lại: Flow vẫn đang render bản đã tính tiền, gửi lại chỉ tốn
    thêm credit cho bản thứ hai rồi bỏ rơi cả hai. Operation được ghi vào `shot.operation_json`
    để nút 'Lấy lại video' kéo bản đang render về (giống đường _render_clip bên api/studio)."""
    client = get_flow_client()
    last = ""
    for attempt in range(_GRAPH_VID_RETRIES):
        res = await submit()
        if res.get("error"):
            last = str(res["error"])
        else:
            p = res.get("data", res)
            mid = (p.get("media") or [{}])[0].get("name")
            if not mid:
                last = _block_reason(p) or "Flow không trả media"
            else:
                try:
                    url = await videopoll.poll_video(client, mid, flow_pid)
                except videopoll.VideoFailed as ex:
                    # Hỏng hẳn (lọc nội dung…) → thử lại luôn, đừng ghi operation treo.
                    last = f"Flow báo hỏng: {ex}"
                    if attempt < _GRAPH_VID_RETRIES - 1:
                        await asyncio.sleep(random.uniform(5, 10))
                    continue
                if url:
                    web = await media_store.save_from_url(mid, pid, "mp4", url)
                    if web:
                        return mid, web
                    # Clip đã xong trên Flow nhưng tải hỏng — vẫn là bản đã trả tiền, ghi lại
                    # operation rồi dừng thay vì render thêm một bản nữa.
                    await _remember_pending(kind, scene_key, p, mid)
                    raise GraphError(
                        "Video đã render xong trên Flow nhưng tải về lỗi — bấm 'Lấy lại video'.")
                await _remember_pending(kind, scene_key, p, mid)
                raise GraphError(
                    f"Video vẫn đang render trên Flow (quá {VIDEO_POLL_TIMEOUT:.0f}s chờ). "
                    f"KHÔNG tạo lại (tránh tốn credit lần nữa) — bấm 'Lấy lại video' để lấy "
                    f"bản đang render về.")
        if attempt < _GRAPH_VID_RETRIES - 1:
            await asyncio.sleep(random.uniform(5, 10))
    raise GraphError(f"Tạo video thất bại sau {_GRAPH_VID_RETRIES} lần: {last}")


async def _remember_pending(kind: str, shot_id: str, payload: dict, media_id: str) -> None:
    """Ghi lượt render đang treo vào shot.operation_json — đúng shape mà
    POST /shots/{id}/video/resume đọc, nên nút 'Lấy lại video' dùng được cho cả node editor."""
    if kind != "shot":
        return
    wf = (payload.get("workflows") or [{}])[0]
    try:
        await db.update("shot", shot_id, {
            "operation_json": json.dumps({
                "media_id": media_id,
                "workflow_id": wf.get("name"),
                "primary_media_id": (wf.get("metadata") or {}).get("primaryMediaId"),
                "submitted_at": db.now()}),
            "updated_at": db.now()})
    except Exception as ex:  # noqa: BLE001
        logger.warning("không ghi được operation_json cho shot %s: %s", shot_id, ex)


def _handle_of(data: dict, fallback: str) -> str:
    """The `{token}` this node's image binds to inside a downstream prompt.

    Every image-producing node can carry a user-typed `handle` ("định danh"): writing
    `{handle}` in a prompt then turns that exact image into its own reference part of the
    structuredPrompt (see flow_client._build_structured_parts), so the model knows WHICH
    role the picture plays instead of receiving an anonymous pile of reference images.
    Braces are stripped — the token in the prompt supplies them."""
    h = str(data.get("handle") or "").replace("{", "").replace("}", "").strip()
    return h or fallback


def _reuse_locked(data: dict, ext: str, handle: str, force: bool = False):
    """Stored output of a gen node, to skip regenerating it. Reused when the node is locked
    (so a full run keeps media the user is happy with) OR `force` (a per-node gen: only the
    requested node regenerates, its upstream gen nodes keep their existing images). Else None."""
    mid = data.get("result_media_id")
    if (data.get("locked") or force) and mid:
        return {"media_id": mid, "web": data.get("result_web"), "ext": ext, "handle": handle,
                "_reused": True}
    return None


async def run_graph(graph: dict, target: dict, project: dict, kind: str,
                    only_node: str | None = None, propagate: bool = False) -> dict:
    """Execute the graph; return {media_id, image_path|video_path} of the Output.

    only_node: when set, run only that node + its upstream chain and return its media
    (no Output node required, target not modified) — used by the per-node "⚡ tạo nhanh".
    propagate: with only_node, ALSO regenerate everything DOWNSTREAM of it (the "⏬ cập nhật
    xuôi dòng" button) so a change to one node flows through the whole chain.

    Reuse rules (so iterating one node doesn't re-roll the rest):
    - full run (no only_node): a gen node reuses its stored result iff LOCKED.
    - per-node run: nodes being refreshed (only_node + its descendants when propagating)
      regenerate unless locked; every other node needed only as INPUT reuses its stored
      result. The explicitly-requested only_node always regenerates (lock ignored)."""
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    if not nodes:
        raise GraphError("Đồ thị rỗng")
    if only_node and not any(n.get("id") == only_node for n in nodes):
        raise GraphError("Không tìm thấy node cần tạo")
    client = get_flow_client()
    if not client.connected:
        raise GraphError("Extension chưa kết nối")

    outputs: dict[str, dict] = {}        # node_id -> output dict
    pid = project["id"]
    flow_pid = project["flow_project_id"]
    final = None
    # refresh = nodes that should regenerate; allowed = refresh ∪ all their inputs (ancestors).
    refresh: set[str] | None = None
    allowed: set[str] | None = None
    if only_node:
        refresh = _descendants(only_node, edges) if propagate else {only_node}
        allowed = set()
        for r in refresh:
            allowed |= _ancestors(r, edges)   # pull in side-inputs of refreshed nodes too

    def merged_inputs(nid):
        """Collect from upstream nodes: text, reference images (refs + any source/generated
        media), the best start image for i2v, and the latest produced media of ANY kind
        (so an Output node can pick up an image OR a video result)."""
        text = None
        refs: list[dict] = []
        start = None
        start_ext = "png"
        result = result_web = None
        result_ext = "png"
        for up in _upstream_ids(nid, edges):
            o = outputs.get(up, {})
            if o.get("text"):
                text = o["text"]
            for r in o.get("references", []):
                refs.append(r)
            if o.get("media_id"):
                refs.append({"handle": o.get("handle", "source"), "media_id": o["media_id"]})
                result = o["media_id"]
                result_ext = o.get("ext", "png")
                result_web = o.get("web")
                if o.get("ext", "png") != "mp4":   # only images can be a start frame
                    start = o["media_id"]
                    start_ext = o.get("ext", "png")
        seen, uniq = set(), []
        for r in refs:
            if r.get("media_id") and r["media_id"] not in seen:
                uniq.append(r)
                seen.add(r["media_id"])
        return {"text": text, "references": uniq[:10], "media_id": start, "ext": start_ext,
                "result": result, "result_ext": result_ext, "result_web": result_web}

    for node in _topo_sort(nodes, edges):
        t = node.get("type")
        data = node.get("data") or {}
        nid = node["id"]
        if allowed is not None and nid not in allowed:
            continue  # per-node run: only this node + its upstream chain
        inp = merged_inputs(nid)

        # Decide whether this gen-like node reuses its stored result or regenerates.
        #  - full run: reuse iff locked.
        #  - per-node run: a node being REFRESHED regenerates (unless locked); the
        #    requested only_node always regenerates; any other node (needed only as input)
        #    reuses. See run_graph docstring.
        if t in _GEN_TYPES and nid != only_node:
            ext = "mp4" if t == "video" else "png"
            handle = _handle_of(data, "video" if t == "video" else "image")
            if allowed is None:                       # full run
                force = False
            elif refresh and nid in refresh:          # being refreshed → reuse only if locked
                force = bool(data.get("locked"))
            else:                                     # input-only ancestor → always reuse
                force = True
            reused = _reuse_locked(data, ext, handle, force=force)
            if reused:
                if not reused.get("web") and reused.get("media_id"):
                    reused["web"] = await media_store.ensure_local(
                        reused["media_id"], pid, reused["ext"])
                outputs[nid] = reused
                continue

        if t == "prompt":
            outputs[nid] = {"text": data.get("text", "")}

        elif t == "source":
            # A source node bound to an entity (entity_id) must use the entity's CURRENT image,
            # so regenerating that entity propagates into the graph instead of using the stale
            # media_id snapshotted when the node was created. Plain (uploaded) sources keep their
            # stored media_id.
            mid = data.get("media_id")
            web = data.get("web")
            eid = data.get("entity_id")
            auto = data.get("label") or "source"
            if eid:
                ent = await db.query_one(
                    "SELECT name, media_id, image_path FROM entity WHERE id=?", (eid,))
                if ent and ent.get("media_id"):
                    mid, web = ent["media_id"], ent.get("image_path")
                    auto = ent.get("name") or auto
            # An explicit "định danh" wins over the auto label, so an uploaded picture (whose
            # label is just a filename) can be addressed as {Áo khoác} from the prompt.
            handle = _handle_of(data, auto)
            if not web and mid:
                web = await media_store.ensure_local(mid, pid)
            outputs[nid] = {"media_id": mid, "web": web, "ext": "png", "handle": handle}

        elif t == "refs":
            ids = data.get("entity_ids") or []
            rows = await db.query_all("SELECT * FROM entity WHERE project_id=?", (pid,))
            by_id = {r["id"]: r for r in rows}
            refs = [{"handle": by_id[i]["name"], "media_id": by_id[i]["media_id"]}
                    for i in ids if by_id.get(i) and by_id[i].get("media_id")][:10]
            outputs[nid] = {"references": refs}

        elif t == "image":
            body = inp["text"] or data.get("text") or ""
            if kind == "entity" and target.get("type"):
                # Entity reference: apply the SAME per-type sheet rule as quick-gen so a
                # node-built reference matches (e.g. a location comes out as the 2x2 grid,
                # not a single plain view).
                img_prompt = brain.compose_prompt(project, brain.ref_image_prompt(
                    target["type"], target.get("name") or "", body))
            else:
                # Shot frame: single-frame guard (don't copy the location grid layout) so a
                # node-built frame matches the storyboard table.
                img_prompt = brain.compose_prompt(project, body, single_frame=(kind == "shot"))
            mid, web = await _img_gen_retry(lambda: client.generate_images(
                prompt=img_prompt,
                project_id=flow_pid,
                aspect_ratio=_img_aspect(project, data),
                user_paygate_tier=project["paygate_tier"],
                references=inp["references"] or None,
                image_model=_img_model(project, data)), pid)
            outputs[nid] = {"media_id": mid, "web": web, "ext": "png",
                            "handle": _handle_of(data, "image")}

        elif t == "editImage":
            # Which upstream picture is the one being EDITED (the base) vs. the ones merely
            # referenced by name in the prompt. `base_handle` lets the user say so explicitly;
            # otherwise fall back to the last upstream image (previous behaviour).
            src = inp["media_id"]
            want = str(data.get("base_handle") or "").strip()
            if want:
                hit = next((r for r in inp["references"] if r.get("handle") == want), None)
                if hit:
                    src = hit["media_id"]
            if not src:
                raise GraphError("editImage cần ảnh nguồn")
            # The base is named by the handle of the node it came from, so the prompt can
            # address the edited picture itself as well (e.g. "giữ nguyên nền của {Ảnh gốc}").
            base_h = next((r.get("handle") for r in inp["references"]
                           if r.get("media_id") == src and r.get("handle")), None) or "base"
            edit_prompt = inp["text"] or data.get("text") or ""
            logger.info("editImage: source=%s prompt=%r", src, edit_prompt[:80])
            # Everything else feeding this node stays available as a NAMED reference, so a
            # prompt like "mặc {Áo khoác} cho nhân vật" binds that picture to that role
            # instead of arriving as an anonymous extra image.
            extra = [r for r in inp["references"] if r.get("media_id") != src]
            # The edit prompt is used VERBATIM (no compose_prompt wrapping) — the user's exact
            # instruction edits the source. `exclude=src` skips the echoed input so the result
            # is the edited image, not the original.
            mid, web = await _img_gen_retry(lambda: client.edit_image(
                edit_prompt, src, flow_pid,
                aspect_ratio=_img_aspect(project, data),
                user_paygate_tier=project["paygate_tier"],
                references=extra[:9] or None,
                base_handle=base_h), pid, exclude=src)
            outputs[nid] = {"media_id": mid, "web": web, "ext": "png",
                            "handle": _handle_of(data, "image")}

        elif t == "removebg":
            # AI background swap via edit (no extra ML dep). Replaces the background with a
            # clean solid colour, keeping the subject — a preset edit_image instruction.
            src = inp["media_id"]
            if not src:
                raise GraphError("Tách nền cần ảnh nguồn (nối từ Nguồn ảnh / Tạo ảnh).")
            bg = (data.get("bg") or "white").lower()
            bg_desc = {"white": "a plain solid white", "black": "a plain solid black",
                       "green": "a plain solid chroma-key green (#00b140)",
                       "gray": "a plain solid neutral gray"}.get(bg, "a plain solid white")
            prompt = (f"Completely remove and replace the background with {bg_desc} background. "
                      "Keep the main subject perfectly intact with clean, sharp edges; do not "
                      "alter the subject. Studio cut-out look, even lighting, no shadows.")
            mid, web = await _img_gen_retry(lambda: client.edit_image(
                prompt, src, flow_pid, aspect_ratio=_img_aspect(project, data),
                user_paygate_tier=project["paygate_tier"]), pid, exclude=src)
            outputs[nid] = {"media_id": mid, "web": web, "ext": "png",
                            "handle": _handle_of(data, "image")}

        elif t == "replacebg":
            # AI background SWAP with a background IMAGE: composite the subject (1st input) onto
            # the background scene (2nd input) via a 2-reference generate. Order = subject, bg.
            seen_rb: list[dict] = []
            ids_rb: set[str] = set()
            for r in inp["references"]:
                if r.get("media_id") and r["media_id"] not in ids_rb:
                    seen_rb.append({"handle": r.get("handle", "ref"), "media_id": r["media_id"]})
                    ids_rb.add(r["media_id"])
            if len(seen_rb) < 2:
                raise GraphError("Thay nền (ảnh) cần 2 ảnh: chủ thể TRƯỚC, ảnh nền SAU.")
            seen_rb[0]["handle"], seen_rb[1]["handle"] = "subject", "background"
            extra = (inp["text"] or data.get("text") or "").strip()
            rb_prompt = (
                "Composite the SUBJECT from the first reference image onto the BACKGROUND scene "
                "from the second reference image. Keep the subject's identity, pose and colours "
                "intact; match the subject's lighting, perspective and scale to the new "
                "background for a believable result. " + extra).strip()
            # Like editImage: the instruction goes in VERBATIM (no compose_prompt). Style /
            # culture / header / footer would fight the two source pictures and repaint the
            # subject — an edit must only do what it was told.
            mid, web = await _img_gen_retry(lambda: client.generate_images(
                prompt=rb_prompt,
                project_id=flow_pid, aspect_ratio=_img_aspect(project, data),
                user_paygate_tier=project["paygate_tier"],
                references=seen_rb[:10], image_model=_img_model(project, data)), pid)
            outputs[nid] = {"media_id": mid, "web": web, "ext": "png",
                            "handle": _handle_of(data, "image")}

        elif t == "note":
            pass  # a canvas comment/label — produces nothing, ignored by the executor

        elif t == "video":
            body = inp["text"] or data.get("text") or ""
            # Apply the same project-level header/footer/style/culture as the image node,
            # so prompt_header / prompt_footer set in ⚙ Cấu hình dự án actually reach the
            # video model. editImage / replacebg deliberately bypass compose_prompt because
            # they operate verbatim, but a plain "Tạo video" generation should honour the
            # project's visual identity just like "Tạo ảnh".
            prompt = brain.compose_prompt(project, body)
            aspect_v = _vid_aspect(project, data)
            kind_v = (data.get("model") or "omni").lower()
            # Node không tự đặt thời lượng → theo ⚙ Cấu hình dự án. Trước đây node editor
            # cứng 8s nên chọn "Omni Flash 10s" ở cấu hình vẫn ra clip 8s.
            dur_v = int(data.get("duration") or 0) or _omni_duration(project) or 8
            if kind_v == "omni" or kind_v in OMNI_FLASH_MODELS.values():
                ref_ids = [r["media_id"] for r in inp["references"]]
                if not ref_ids and inp["media_id"]:
                    ref_ids = [inp["media_id"]]
                if not ref_ids:
                    raise GraphError("Omni Flash cần ít nhất 1 ảnh tham chiếu/nguồn")
                submit = lambda: client.generate_video_omni(
                    prompt=prompt, project_id=flow_pid, reference_media_ids=ref_ids,
                    duration_s=dur_v, aspect_ratio=aspect_v,
                    user_paygate_tier=project["paygate_tier"],
                    references=inp["references"] or None)
            else:   # Veo i2v — needs a start frame
                if not inp["media_id"]:
                    raise GraphError("Veo i2v cần ảnh start (nối từ Nguồn ảnh / Tạo ảnh)")
                start = inp["media_id"]
                submit = lambda: client.generate_video(
                    start_image_media_id=start, prompt=prompt,
                    project_id=flow_pid, scene_id=target["id"],
                    aspect_ratio=aspect_v, user_paygate_tier=project["paygate_tier"])
            mid, web = await _vid_gen_retry(submit, target["id"], pid, kind, flow_pid)
            outputs[nid] = {"media_id": mid, "web": web, "ext": "mp4",
                            "handle": _handle_of(data, "video")}

        elif t in _LOCAL_TYPES:
            # Local Pillow processing (no AI): filter / text / upscale / blend. Result is
            # re-uploaded to Flow so the chain (→ edit / video / output) keeps a media_id.
            out_img = await _run_local_node(t, data, inp, pid)
            mid, web = await _save_and_upload(out_img, pid, flow_pid)
            outputs[nid] = {"media_id": mid, "web": web, "ext": "png",
                            "handle": _handle_of(data, "image")}

        elif t == "output":
            # The Output node designates the final result: whatever media flows into it.
            if inp["result"]:
                final = {"media_id": inp["result"], "web": inp["result_web"],
                         "ext": inp["result_ext"]}
                outputs[nid] = {"media_id": inp["result"], "web": inp["result_web"],
                                "ext": inp["result_ext"]}

        else:
            logger.warning("Unknown node type: %s", t)

    # node_id -> {web, media_id, ext}; the frontend uses this to fill previews and to
    # remember each gen node's media_id (so a locked node can be reused on the next run).
    node_outputs = {k: {"web": o.get("web"), "media_id": o.get("media_id"),
                        "ext": o.get("ext", "png")}
                    for k, o in outputs.items() if o.get("web")}

    if only_node:
        o = outputs.get(only_node) or {}
        if not o.get("media_id"):
            raise GraphError("Node này không tạo ra ảnh/video")
        return {"media_id": o.get("media_id"), "path": o.get("web"),
                "ext": o.get("ext", "png"), "node_outputs": node_outputs,
                "only_node": only_node}

    if not any(n.get("type") == "output" for n in nodes):
        raise GraphError("Đồ thị phải có node Output để chỉ định kết quả")
    if not final or not final.get("media_id"):
        raise GraphError("Node Output chưa được nối tới một node tạo ảnh/video có kết quả")

    # apply to target
    web = final.get("web") or await media_store.ensure_local(
        final["media_id"], pid, final.get("ext", "png"))
    display_path = web  # what the entity/shot SHOWS (may differ from the raw media, e.g. labels)
    if kind == "entity":
        await db.update("entity", target["id"], {
            "media_id": final["media_id"], "primary_media_id": final["media_id"],
            "image_path": web, "updated_at": db.now()})
        # A location's reference is a 2x2 grid → overlay the position labels for display,
        # same as the quick-gen path (media_id stays the clean grid).
        if target.get("type") == "location" and web:
            src = media_store.MEDIA_DIR / web.replace("/media/", "", 1)
            if src.exists():
                out_rel = f"{pid}/loc_{target['id']}_labeled.png"
                ok = await asyncio.to_thread(
                    assembler.label_quadrants, src, media_store.MEDIA_DIR / out_rel,
                    brain.LOCATION_GRID_LABELS, assembler._caption_font())
                if ok:
                    display_path = f"/media/{out_rel}"
                    await db.update("entity", target["id"], {"image_path": display_path})
    else:
        col = "video" if final.get("ext") == "mp4" else "image"
        await db.update("shot", target["id"], {
            f"{col}_media_id": final["media_id"], f"{col}_primary_id": final["media_id"],
            f"{col}_path": web, "updated_at": db.now(),
            # Video mới đã về ⇒ lượt render treo (nếu có) không còn ý nghĩa.
            **({"operation_json": None} if col == "video" else {})})
    return {"media_id": final["media_id"], "path": web, "ext": final.get("ext", "png"),
            "display_path": display_path, "node_outputs": node_outputs}
