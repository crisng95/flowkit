"""
Flow Client — communicates with Google Flow API via Chrome extension WebSocket bridge.

Agent runs a WS server. Extension connects as client. Agent sends API requests,
extension executes them in browser context (residential IP, cookies, reCAPTCHA).
"""
import asyncio
import json
import logging
import re
import time
import uuid
from typing import Optional
from urllib.parse import quote

from agent.config import (
    GOOGLE_FLOW_API, GOOGLE_API_KEY, ENDPOINTS,
    VIDEO_MODELS, UPSCALE_MODELS, IMAGE_MODELS, VIDEO_POLL_TIMEOUT,
    OMNI_FLASH_MODELS, OMNI_FLASH_T2V_MODELS, OMNI_FLASH_VALID_ASPECTS,
    UPSAMPLE_IMAGE_RESOLUTIONS, UPSAMPLE_IMAGE_DEFAULT, UPSAMPLE_IMAGE_TIMEOUT,
    UPSAMPLE_VIDEO_RESOLUTIONS, UPSAMPLE_VIDEO_DEFAULT,
    VEO_LITE_MODELS, VEO_LITE_TIERS, VEO_LITE_DEFAULT_S, VEO_LITE_FRAME_MODELS,
)
from agent.services.headers import random_headers

logger = logging.getLogger(__name__)


class FlowClient:
    """Sends commands to Chrome extension via WebSocket."""

    def __init__(self):
        self._extension_ws = None  # Set by WS server when extension connects
        self._pending: dict[str, asyncio.Future] = {}
        self._flow_key: Optional[str] = None
        # Tài khoản Google đang đăng nhập Flow trong Chrome ({email, name, picture, sub}).
        # Extension đẩy lên khi kết nối / đổi account; agent không tự suy ra được.
        self._identity: Optional[dict] = None
        # Single-flight queue (video-app.md §9.1): the extension is ONE shared WS channel,
        # so every mutating Flow command (generate / edit / upscale / upload / rename /
        # get-url) is serialized through this lock — only one is in flight at a time. This
        # stops a batch and a manual op (⚡ quick-gen, Node Editor) from interleaving requests
        # and corrupting rate-limit/captcha state. Read-only polls (check-status, credits) opt
        # out (serialize=False) so they don't block submits — they run on their own cadence.
        self._flow_lock = asyncio.Lock()
        # WS stats
        self._ws_connect_count = 0
        self._ws_disconnect_count = 0
        self._ws_connected_at: Optional[float] = None
        self._ws_last_disconnect_at: Optional[float] = None

    def set_extension(self, ws):
        """Called when extension connects via WS."""
        self._extension_ws = ws
        self._ws_connect_count += 1
        self._ws_connected_at = time.time()
        logger.info("Extension connected #%d (waiting for extension_ready/token_captured to sync)", self._ws_connect_count)

    def clear_extension(self):
        """Called when extension disconnects."""
        self._extension_ws = None
        # Identity KHÔNG bị xoá: extension rớt không có nghĩa người dùng đăng xuất, và xoá đi
        # sẽ làm mọi dự án "mất chủ" trong lúc mất kết nối. Extension gửi lại khi nối lại.
        self._ws_disconnect_count += 1
        self._ws_last_disconnect_at = time.time()
        # Cancel all pending futures (copy to avoid RuntimeError on concurrent modification)
        pending_copy = list(self._pending.items())
        count = len(pending_copy)
        for req_id, future in pending_copy:
            if not future.done():
                future.set_exception(ConnectionError("Extension disconnected"))
        self._pending.clear()
        logger.warning("Extension disconnected, cleared %d pending requests", count)

    def set_flow_key(self, key: str):
        self._flow_key = key

    @property
    def connected(self) -> bool:
        return self._extension_ws is not None

    @property
    def identity(self) -> Optional[dict]:
        """Tài khoản Flow đang đăng nhập, hoặc None khi chưa xác định được."""
        return self._identity

    async def fetch_identity(self, refresh: bool = True) -> Optional[dict]:
        """Hỏi extension tài khoản đang đăng nhập (refresh=False → lấy bản extension đang giữ).

        Chỉ dùng khi cần chắc chắn mới nhất (ví dụ ngay trước khi tạo dự án). Luồng thường
        đã có extension tự đẩy `identity` lúc kết nối và mỗi 45 phút."""
        if not self._extension_ws:
            return self._identity
        res = await self._send("get_identity", {"refresh": refresh}, timeout=20, serialize=False)
        data = res.get("result") if isinstance(res, dict) else None
        if isinstance(data, dict) and (data.get("email") or data.get("sub")):
            self._set_identity(data)
        return self._identity

    def _set_identity(self, data: dict) -> None:
        prev = (self._identity or {}).get("email")
        self._identity = data
        if data.get("email") != prev:
            logger.info("Tài khoản Flow: %s", data.get("email") or data.get("sub"))

    @property
    def ws_stats(self) -> dict:
        uptime = None
        if self._ws_connected_at and self.connected:
            uptime = int(time.time() - self._ws_connected_at)
        return {
            "connected": self.connected,
            "connects": self._ws_connect_count,
            "disconnects": self._ws_disconnect_count,
            "uptime_s": uptime,
        }

    async def handle_message(self, data: dict):
        """Handle incoming message from extension."""
        if data.get("type") == "token_captured":
            self._flow_key = data.get("flowKey")
            logger.info("Flow key captured from extension")
            return

        if data.get("type") == "identity":
            ident = data.get("identity") or {}
            if ident.get("email") or ident.get("sub"):
                self._set_identity(ident)
            return

        if data.get("type") == "extension_ready":
            logger.info("Extension ready, flowKey=%s", "yes" if data.get("flowKeyPresent") else "no")
            return

        if data.get("type") == "pong":
            return

        if data.get("type") == "ping":
            # Respond to keepalive
            if self._extension_ws:
                await self._extension_ws.send(json.dumps({"type": "pong"}))
            return

        # Response to a pending request
        req_id = data.get("id")
        if req_id and req_id in self._pending:
            if not self._pending[req_id].done():
                self._pending[req_id].set_result(data)
            return

    async def refresh_project_urls(self, project_id: str) -> dict:
        """Refresh media URLs for a project.

        Note: Google Flow's get_media API returns encoded content (base64),
        not fresh signed URLs. URL refresh requires TRPC intercept from
        the extension when the user opens the project in Chrome.
        The video reviewer falls back to get_media content directly.
        """
        logger.info("URL refresh requested for project %s — TRPC endpoint no longer available, "
                     "use extension passive intercept (open project in Chrome)", project_id[:12])
        return {"refreshed": 0, "found": 0, "note": "TRPC endpoint unavailable. "
                "Video reviewer uses get_media fallback automatically. "
                "For URL refresh, open the project in Google Flow in Chrome."}

    async def _send(self, method: str, params: dict, timeout: float = 300,
                    *, serialize: bool = True) -> dict:
        """Send request to extension and wait for response.

        Always returns a dict. On error, returns {"error": "<reason>"} — callers
        must check result.get("error") or use _is_ws_error() before reading data.
        Never raises; exceptions are caught and returned as error dicts.

        `serialize=True` (default) routes the call through the single-flight lock so it
        does not overlap another Flow command. Read-only polls pass `serialize=False`.
        """
        if not self._extension_ws:
            return {"error": "Extension not connected"}
        if serialize:
            async with self._flow_lock:
                return await self._send_raw(method, params, timeout)
        return await self._send_raw(method, params, timeout)

    async def _send_raw(self, method: str, params: dict, timeout: float) -> dict:
        """Actual send + await of one extension request (no serialization)."""
        if not self._extension_ws:
            return {"error": "Extension not connected"}

        req_id = str(uuid.uuid4())
        future = asyncio.get_running_loop().create_future()
        self._pending[req_id] = future

        try:
            await self._extension_ws.send(json.dumps({
                "id": req_id,
                "method": method,
                "params": params,
            }))
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            return {"error": f"Timeout ({timeout}s) waiting for {method}"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            self._pending.pop(req_id, None)

    def _build_url(self, endpoint_key: str, **kwargs) -> str:
        """Build full API URL.

        The ?key= param is only appended when GOOGLE_API_KEY is set. Auth to
        aisandbox-pa.googleapis.com is carried by the extension's Bearer token,
        so the API key is optional — leave GOOGLE_API_KEY empty to omit it.
        """
        path = ENDPOINTS[endpoint_key].format(**kwargs)
        url = f"{GOOGLE_FLOW_API}{path}"
        if GOOGLE_API_KEY:
            sep = "&" if "?" in path else "?"
            url = f"{url}{sep}key={GOOGLE_API_KEY}"
        return url

    def _client_context(self, project_id: str, user_paygate_tier: str = "PAYGATE_TIER_TWO") -> dict:
        """Build clientContext with recaptcha placeholder."""
        return {
            "projectId": str(project_id),
            "recaptchaContext": {
                "applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB",
                "token": "",  # Extension injects real token
            },
            "sessionId": f";{int(time.time() * 1000)}",
            "tool": "PINHOLE",
            "userPaygateTier": user_paygate_tier,
        }

    # ─── High-level API Methods ──────────────────────────────

    async def create_project(self, project_title: str, tool_name: str = "PINHOLE") -> dict:
        """Create a project on Google Flow via tRPC endpoint.

        Returns the full response including projectId.
        """
        url = "https://labs.google/fx/api/trpc/project.createProject"
        body = {"json": {"projectTitle": project_title, "toolName": tool_name}}

        return await self._send("trpc_request", {
            "url": url,
            "method": "POST",
            "headers": {
                "content-type": "application/json",
                "accept": "*/*",
            },
            "body": body,
        }, timeout=30)


    async def delete_project(self, project_id: str) -> dict:
        """Create a project on Google Flow via tRPC endpoint.

        Returns the full response including projectId.
        """
        url = "https://labs.google/fx/api/trpc/project.deleteProject"
        body = {"json": {"projectToDeleteId": project_id}}

        return await self._send("trpc_request", {
            "url": url,
            "method": "POST",
            "headers": {
                "content-type": "application/json",
                "accept": "*/*",
            },
            "body": body,
        }, timeout=30)


    async def get_project(self, project_id: str) -> dict:
        """Create a project on Google Flow via tRPC endpoint.

        Returns the full response including projectId.
        """
        input_data = json.dumps({"json": {"projectId": project_id}})
        url = f"https://labs.google/fx/api/trpc/project.getProjectContents?input={quote(input_data)}"
        #url = f"https://labs.google/fx/api/trpc/flow.projectInitialData?input={quote(input_data)}"

        return await self._send("trpc_request", {
            "url": url,
            "method": "GET",
            "headers": {
                "content-type": "application/json",
                "accept": "*/*",
            },
        }, timeout=30)


    async def get_projects(self) -> dict:
        """Create a project on Google Flow via tRPC endpoint.

        Returns the full response including projectId.
        """
        input_data = json.dumps({"json":{"pageSize":20,"toolName":"PINHOLE","cursor":None},"meta":{"values":{"cursor":["undefined"]}}})
        url = f"https://labs.google/fx/api/trpc/project.searchUserProjects?input={quote(input_data)}"

        return await self._send("trpc_request", {
            "url": url,
            "method": "GET",
            "headers": {
                "content-type": "application/json",
                "accept": "*/*",
            },
        }, timeout=30)

    async def get_direct_media(self, primary_media_id: str) -> dict:
        """Get media URL redirect."""
        url = f"https://labs.google/fx/api/trpc/media.getMediaUrlRedirect?name={primary_media_id}"

        return await self._send("trpc_request", {
            "url": url,
            "method": "GET",
            "headers": {
                "origin": "https://labs.google",
                "accept": "*/*",
            },
        }, timeout=30)

    async def generate_images(self, prompt: str, project_id: str,
                               aspect_ratio: str = "IMAGE_ASPECT_RATIO_PORTRAIT",
                               user_paygate_tier: str = "PAYGATE_TIER_TWO",
                               character_media_ids: list[str] = None,
                               references: list[dict] = None,
                               image_model: str = None,
                               seed: int = None,
                               batch_id: str = None,
                               serialize: bool = True,
                               bind_unreferenced: bool = False,
                               dedupe_refs: bool = False) -> dict:
        """Generate image(s).

        Two ways to attach character/entity references:
        - `references` (preferred): list of {"handle": <name>, "media_id": <uuid>}. The
          prompt may embed entity names in curly braces, e.g. "{Thao} dắt tay {Luong}".
          Each `{handle}` matching a reference is turned into a dedicated
          `{"reference": {"media": {handle, mediaId}}}` part in `structuredPrompt`, so the
          model binds each mention to the right image instead of guessing (avoids mixing up
          entities when several references are passed).
        - `character_media_ids` (legacy): plain list of mediaIds added as imageInputs only;
          the whole prompt stays a single text part.

        `image_model` overrides the image model key (e.g. "GEM_PIX_2", "NARWHAL");
        defaults to NANO_BANANA_PRO.

        `batch_id`: share ONE Flow batch across several calls (pass the same UUID to a group
        of ≤4 gens fired together) — Flow groups them like the web UI's 4-image batch. When
        None, a per-call batch id is used iff there are references (existing behaviour).
        `serialize=False` sends WITHOUT the single-flight lock so a batch's calls actually
        overlap (the whole point of batching); the extension handles each request id + captcha
        independently, so concurrent image gens are safe.

        `bind_unreferenced=True`: a reference the prompt never names still gets its own
        reference part (prepended), instead of riding along as an anonymous `imageInputs`
        entry. An unnamed reference is attached but NOT bound into `structuredPrompt`, and the
        model then largely ignores it — the same failure `edit_image` fixes with its
        `base_part`: the result comes back looking like a fresh, unreferenced generation. Use
        it wherever the caller KNOWS the picture must be conditioned on (the Node Editor wires
        an image in on purpose). Leave it off where references are a candidate pool the prompt
        selects from by name — binding an entity the shot never mentions invites the model to
        paint that character into the frame.

        `dedupe_refs=True`: mỗi ảnh chỉ được bind MỘT lần (lần nhắc đầu tiên) — xem
        `_build_structured_parts`. Bật cho prompt nhắc lại cùng entity nhiều lần (prompt do
        người dùng viết trong Node Editor), không thì Flow trả 400 INVALID_ARGUMENT.

        Response structure:
            data.media[].name = mediaId (used for video gen)
        """
        ts = int(time.time() * 1000)
        ctx = self._client_context(project_id, user_paygate_tier)
        model_key = image_model or IMAGE_MODELS["NANO_BANANA_PRO"]

        if references:
            parts = _build_structured_parts(prompt, references, dedupe=dedupe_refs)
            if bind_unreferenced:
                parts = _bind_unreferenced(parts, references, "generate_images")
            # imageInputs follow the reference order, de-duplicated.
            ref_ids = list(dict.fromkeys(r["media_id"] for r in references))
        else:
            parts = [{"text": prompt}]
            ref_ids = list(dict.fromkeys(character_media_ids or []))

        request_item = {
            "clientContext": {**ctx, "sessionId": f";{ts}"},
            # a fixed seed (project seed-lock) reproduces the same image for the same
            # prompt+refs; None → random per call.
            "seed": (seed % 1000000) if seed is not None else (ts % 1000000),
            "structuredPrompt": {"parts": parts},
            "imageAspectRatio": aspect_ratio,
            "imageModelName": model_key,
        }

        # Add references as imageInputs (reference order)
        if ref_ids:
            request_item["imageInputs"] = [
                {"name": mid, "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE"}
                for mid in ref_ids
            ]
            character_media_ids = ref_ids  # so batch logic below triggers

        # An explicit batch_id (shared across a fired-together group) wins; else fall back to a
        # per-call id when there are references (the pre-batch behaviour).
        effective_batch = batch_id or (f"{uuid.uuid4()}" if character_media_ids else None)
        body = {
            "clientContext": ctx,
            "requests": [request_item],
        }
        if effective_batch:
            body["mediaGenerationContext"] = {"batchId": effective_batch}
            body["useNewMedia"] = True

        url = self._build_url("generate_images", project_id=project_id)
        return await self._send("api_request", {
            "url": url,
            "method": "POST",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "IMAGE_GENERATION",
        }, serialize=serialize)

    async def edit_image(self, prompt: str, source_media_id: str,
                          project_id: str,
                          aspect_ratio: str = "IMAGE_ASPECT_RATIO_PORTRAIT",
                          user_paygate_tier: str = "PAYGATE_TIER_ONE",
                          character_media_ids: list[str] = None,
                          references: list[dict] = None,
                          base_handle: str = "base",
                          bind_unreferenced: bool = False,
                          dedupe_refs: bool = True) -> dict:
        """Edit an existing image using IMAGE_INPUT_TYPE_BASE_IMAGE.

        If character_media_ids is provided, appends them as IMAGE_INPUT_TYPE_REFERENCE
        after the base image. Order: [base_image, char_A, char_B, ...].
        This helps Google Flow detect characters for consistent edits.

        `references` ({"handle", "media_id"}, like generate_images) are extra pictures the
        prompt can address BY NAME: each `{handle}` becomes its own reference part, so an
        instruction such as "thay áo bằng {Áo khoác}" binds that mention to that exact image
        rather than leaving the model to guess which extra input means what. `base_handle`
        names the edited image itself, so the prompt can refer to it too (e.g. "{Ảnh gốc}").

        `bind_unreferenced=True`: reference mà prompt KHÔNG gọi tên vẫn được bind (xem
        `_bind_unreferenced`). Bắt buộc cho Node Editor — người dùng kéo dây ảnh vào node
        "Sửa ảnh" là cố ý, mà prompt sửa ảnh thì hiếm khi viết `{token}` ("xoá cái xe đi"),
        nên không có cờ này thì ảnh chỉ nằm trong `imageInputs` và model bỏ qua.

        `dedupe_refs` mặc định True vì prompt sửa ảnh LUÔN do người dùng viết: gọi `{Áo}` ở
        hai câu là sinh hai reference part cùng mediaId → Flow trả 400 (xem CLAUDE.md).
        """
        ts = int(time.time() * 1000)
        ctx = self._client_context(project_id, user_paygate_tier)

        image_inputs = [
            {"name": source_media_id, "imageInputType": "IMAGE_INPUT_TYPE_BASE_IMAGE"}
        ]
        extra_ids = list(dict.fromkeys(
            [r["media_id"] for r in (references or []) if r.get("media_id")]
            + list(character_media_ids or [])))
        for mid in extra_ids:
            if mid != source_media_id:
                image_inputs.append({"name": mid, "imageInputType": "IMAGE_INPUT_TYPE_REFERENCE"})

        # Bind the source into the structuredPrompt as a reference part (same mechanism as
        # generate_images), not only as a bare BASE_IMAGE input — otherwise the model may not
        # actually condition on the image and the edit comes out as a fresh, unreferenced gen.
        # Named references are then split out of the prompt text the same way.
        #
        # Ảnh nền đi CÙNG các reference khác vào `_build_structured_parts` rồi mới bù ở đầu
        # nếu prompt không nhắc tới nó. Bản cũ dựng part xong mới LỌC BỎ mọi part của ảnh nền
        # — mà lọc một reference part ở GIỮA câu thì hai mảnh text hai bên dính vào nhau thành
        # hai part text liền kề, đúng kiểu vụn part khiến Flow trả 400 (xem CLAUDE.md). Không
        # lọc gì thì không bao giờ đẻ ra chỗ dính đó.
        base_ref = {"handle": base_handle or "base", "media_id": source_media_id}
        parts = _build_structured_parts(prompt, [base_ref] + list(references or []),
                                        dedupe=dedupe_refs)
        if bind_unreferenced and references:
            parts = _bind_unreferenced(parts, references, "edit_image")
        # Bù ảnh nền SAU cùng để nó đứng đầu: đây là tấm đang được SỬA, không phải một ảnh
        # tham chiếu ngang hàng. Prompt có gọi tên nó thì để yên ở chỗ prompt đặt.
        if not any(p.get("reference", {}).get("media", {}).get("mediaId") == source_media_id
                   for p in parts):
            parts = [{"reference": {"media": {"handle": base_ref["handle"],
                                              "mediaId": source_media_id}}}] + parts

        request_item = {
            "clientContext": {**ctx, "sessionId": f";{ts}"},
            "seed": ts % 1000000,
            "structuredPrompt": {"parts": parts},
            "imageAspectRatio": aspect_ratio,
            "imageModelName": IMAGE_MODELS["NANO_BANANA_PRO"],
            "imageInputs": image_inputs,
        }

        body = {
            "clientContext": ctx,
            "mediaGenerationContext": {"batchId": f"{uuid.uuid4()}"},
            "useNewMedia": True,
            "requests": [request_item],
        }

        url = self._build_url("generate_images", project_id=project_id)
        return await self._send("api_request", {
            "url": url,
            "method": "POST",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "IMAGE_GENERATION",
        })

    async def change_display_name(self, media_name_id: str, project_id: str, display_name: str) -> dict:
        """
        Rename a media item.
        Uses the same endpoint as generate_images but with a different payload.
        """
        url = self._build_url("changeDisplayname_media", media_id=media_name_id)
        body = {
            "updateMask": "metadata.displayName",
            "workflow": {
                "name": media_name_id,
                "projectId": project_id,
                "metadata": {
                    "displayName": display_name
                }
            }
        }
        return await self._send("api_request", {
            "url": url,
            "method": "PATCH",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "IMAGE_GENERATION",
        })

    async def change_project_cover(self, project_id: str, media_name_id: str) -> dict:
        """
        Rename a media item.
        Uses the same endpoint as generate_images but with a different payload.
        """
        url = self._build_url("changeProject_cover_image", project_id=project_id)
        body = {
            "thumbnailMediaKey": media_name_id,
        }
        return await self._send("api_request", {
            "url": url,
            "method": "PATCH",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "IMAGE_GENERATION",
        })

    async def generate_video(self, start_image_media_id: str, prompt: str,
                              project_id: str, scene_id: str,
                              aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
                              end_image_media_id: str = None,
                              user_paygate_tier: str = "PAYGATE_TIER_TWO",
                              video_model: str = None,
                              references: list[dict] = None) -> dict:
        """Generate video from start image (i2v).

        Two sub-types:
        - frame_2_video (i2v): startImage only
        - start_end_frame_2_video (i2v_fl): startImage + endImage (for scene chaining)

        `video_model` ép một model key cụ thể thay vì bảng theo tier — đường Veo 3.1 Lite
        dùng nó (xem generate_video_veo_lite). `references` cho phép prompt gọi ảnh start/end
        bằng token `{handle}` như bên r2v; không truyền thì prompt đi nguyên một part text.
        """
        gen_type = "start_end_frame_2_video" if end_image_media_id else "frame_2_video"
        model_key = video_model or VIDEO_MODELS.get(
            user_paygate_tier, {}).get(gen_type, {}).get(aspect_ratio)

        if not model_key:
            return {"error": f"No model for tier={user_paygate_tier} type={gen_type} ratio={aspect_ratio}"}

        # dedupe=True vì cùng lý do như r2v: nhắc lại một ảnh ở nhiều câu sinh nhiều reference
        # part trỏ cùng mediaId → Flow 400 INVALID_ARGUMENT (xem CLAUDE.md).
        parts = (_build_structured_parts(prompt, references, dedupe=True)
                 if references else [{"text": prompt}])

        request = {
            "aspectRatio": aspect_ratio,
            "seed": int(time.time()) % 10000,
            "textInput": {"structuredPrompt": {"parts": parts}},
            "videoModelKey": model_key,
            "startImage": {"mediaId": start_image_media_id},
            "metadata": {"sceneId": scene_id},
        }

        if end_image_media_id:
            request["endImage"] = {"mediaId": end_image_media_id}

        endpoint_key = "generate_video_start_end" if end_image_media_id else "generate_video"
        body = {
            "mediaGenerationContext": {"batchId": f"{uuid.uuid4()}"},
            "clientContext": self._client_context(project_id, user_paygate_tier),
            "requests": [request],
            "useV2ModelConfig": True,
        }

        url = self._build_url(endpoint_key)
        return await self._send("api_request", {
            "url": url,
            "method": "POST",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "VIDEO_GENERATION",
        }, timeout=60)  # Submit only — polling is separate

    async def generate_video_from_references(self, reference_media_ids: list[str],
                                              prompt: str, project_id: str, scene_id: str,
                                              aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
                                              user_paygate_tier: str = "PAYGATE_TIER_TWO",
                                              references: list[dict] = None,
                                              video_model: str = None) -> dict:
        """Generate video from multiple reference images (r2v).

        Uses referenceImages instead of startImage — the model composes
        a video from all provided reference character images.

        Args:
            reference_media_ids: List of character media_ids (from uploadImage)
        """
        gen_type = "reference_frame_2_video"
        model_key = video_model or VIDEO_MODELS.get(user_paygate_tier, {}).get(gen_type, {}).get(aspect_ratio)

        if not model_key:
            return {"error": f"No model for tier={user_paygate_tier} type={gen_type} ratio={aspect_ratio}"}

        # Like generate_images: prompt may embed entity names as "{handle}" so each mention
        # binds to its own reference image instead of being mixed up. referenceImages follow
        # the reference order, de-duplicated.
        #
        # dedupe ở đây LUÔN bật, khác generate_images (nơi nó là tuỳ chọn). Prompt timeline của
        # một clip gọi lại cùng một frame ở nhiều mốc thời gian là chuyện bình thường, mà mỗi
        # lần nhắc không dedupe là một reference part — đủ nhiều thì Flow trả 400
        # INVALID_ARGUMENT (xem CLAUDE.md). Bind lần thứ hai của cùng một ảnh không thêm gì.
        if references:
            parts = _build_structured_parts(prompt, references, dedupe=True)
            ref_ids = list(dict.fromkeys(r["media_id"] for r in references))
        else:
            parts = [{"text": prompt}]
            ref_ids = list(dict.fromkeys(reference_media_ids or []))

        request = {
            "aspectRatio": aspect_ratio,
            "seed": int(time.time()) % 10000,
            "textInput": {"structuredPrompt": {"parts": parts}},
            "videoModelKey": model_key,
            "metadata": {},
        }
        # Không ảnh nào ⇒ bỏ hẳn field thay vì gửi mảng rỗng. Nhưng đừng trông vào đó để làm
        # text-to-video: model r2v BẮT BUỘC có ảnh, đo trên `abra_r2v_4s` bỏ referenceImages
        # ra thì Flow trả 400 INVALID_ARGUMENT. Đường chỉ-có-prompt là endpoint + bảng key
        # khác hẳn, xem `_generate_video_text_omni`.
        if ref_ids:
            request["referenceImages"] = [
                {"mediaId": mid, "imageUsageType": "IMAGE_USAGE_TYPE_ASSET"}
                for mid in ref_ids
            ]

        body = {
            "mediaGenerationContext": {
                "batchId": f"{uuid.uuid4()}",
                "audioFailurePreference": "BLOCK_SILENCED_VIDEOS",
            },
            "clientContext": self._client_context(project_id, user_paygate_tier),
            "requests": [request],
            "useV2ModelConfig": True,
        }

        url = self._build_url("generate_video_references")
        return await self._send("api_request", {
            "url": url,
            "method": "POST",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "VIDEO_GENERATION",
        }, timeout=60)

    async def generate_video_omni(self, prompt: str, project_id: str,
                                   reference_media_ids: list[str],
                                   duration_s: int = 8,
                                   aspect_ratio: str = "VIDEO_ASPECT_RATIO_LANDSCAPE",
                                   user_paygate_tier: str = "PAYGATE_TIER_ONE",
                                   references: list[dict] = None) -> dict:
        """Generate video with Google's **Omni Flash** model.

        Aspect must be PORTRAIT or LANDSCAPE. Supports `{handle}` references in the prompt
        (structuredPrompt parts).

        Ảnh tham chiếu là TUỲ CHỌN, nhưng KHÔNG phải "cùng request, bỏ trống ảnh": có ảnh và
        không ảnh là hai đường khác hẳn nhau.
          • có ảnh  → `abra_r2v_{4,6,8,10}s` + batchAsyncGenerateVideoReferenceImages
          • chỉ text → `abra_t2v_{4,6,8,10}s` + batchAsyncGenerateVideoText
        Gửi key r2v mà bỏ `referenceImages` đi thì Flow trả 400 INVALID_ARGUMENT (đã đo trên
        `abra_r2v_4s`), nên đừng "sửa" bằng cách thả ảnh ra khỏi request r2v.
        """
        if aspect_ratio not in OMNI_FLASH_VALID_ASPECTS:
            return {"error": f"Omni Flash không hỗ trợ aspect {aspect_ratio} "
                             f"(chỉ PORTRAIT/LANDSCAPE)"}
        if not (reference_media_ids or references):
            return await self._generate_video_text_omni(
                prompt=prompt, project_id=project_id, duration_s=duration_s,
                aspect_ratio=aspect_ratio, user_paygate_tier=user_paygate_tier)

        model_key = OMNI_FLASH_MODELS.get(str(duration_s))
        if not model_key:
            return {"error": f"Omni Flash không có model cho duration={duration_s}s "
                             f"(hỗ trợ: {', '.join(OMNI_FLASH_MODELS)})"}

        # Body r2v giống hệt — chỉ khác videoModelKey. Tái dùng để DRY.
        return await self.generate_video_from_references(
            reference_media_ids=reference_media_ids,
            prompt=prompt,
            project_id=project_id,
            scene_id="",
            aspect_ratio=aspect_ratio,
            user_paygate_tier=user_paygate_tier,
            references=references,
            video_model=model_key,
        )

    async def _generate_video_text_omni(self, prompt: str, project_id: str,
                                        duration_s: int = 8,
                                        aspect_ratio: str = "VIDEO_ASPECT_RATIO_LANDSCAPE",
                                        user_paygate_tier: str = "PAYGATE_TIER_ONE") -> dict:
        """Omni Flash text-to-video: không ảnh nào, chỉ prompt.

        Endpoint + bảng key riêng (xem generate_video_omni). Body giống r2v trừ việc KHÔNG có
        `referenceImages`; `structuredPrompt` chỉ một part text — không có ảnh thì cũng không
        có `{handle}` nào để bind.
        """
        model_key = OMNI_FLASH_T2V_MODELS.get(str(duration_s))
        if not model_key:
            return {"error": f"Omni Flash (text-to-video) không có model cho "
                             f"duration={duration_s}s "
                             f"(hỗ trợ: {', '.join(OMNI_FLASH_T2V_MODELS)})"}

        body = {
            "mediaGenerationContext": {
                "batchId": f"{uuid.uuid4()}",
                "audioFailurePreference": "BLOCK_SILENCED_VIDEOS",
            },
            "clientContext": self._client_context(project_id, user_paygate_tier),
            "requests": [{
                "aspectRatio": aspect_ratio,
                "textInput": {"structuredPrompt": {"parts": [{"text": prompt}]}},
                "videoModelKey": model_key,
                "seed": int(time.time()) % 10000,
                "metadata": {},
            }],
            "useV2ModelConfig": True,
        }
        return await self._send("api_request", {
            "url": self._build_url("generate_video_text"),
            "method": "POST",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "VIDEO_GENERATION",
        }, timeout=60)   # Submit only — polling is separate

    async def generate_video_veo_lite(self, prompt: str, project_id: str,
                                       scene_id: str = "",
                                       start_media_id: str = None,
                                       end_media_id: str = None,
                                       reference_media_ids: list[str] = None,
                                       references: list[dict] = None,
                                       duration_s: int = VEO_LITE_DEFAULT_S,
                                       aspect_ratio: str = "VIDEO_ASPECT_RATIO_LANDSCAPE",
                                       user_paygate_tier: str = "PAYGATE_TIER_TWO") -> dict:
        """**Veo 3.1 Lite [Lower Priority]** — 0 credit, chỉ tài khoản Gemini Ultra.

        Cùng ba endpoint như Veo thường, chỉ khác `videoModelKey`; kiểu sinh suy ra từ ảnh
        được truyền vào (không có cờ riêng để hai chỗ gọi không lệch nhau):

        - start + end  → nội suy hai khung (`veo_3_1_interpolation_lite_low_priority`)
        - chỉ start    → i2v (`veo_3_1_i2v_lite_low_priority`)
        - có reference → "inference" r2v (`veo_3_1_r2v_lite_low_priority`)
        - KHÔNG ảnh nào → text-to-video (`veo_3_1_t2v_lite_low_priority`), endpoint riêng
          `batchAsyncGenerateVideoText` — xem `_generate_video_text_veo_lite`. Đừng dựng lại
          hàng rào "cần ít nhất 1 ảnh": Flow UI vẫn tạo được video Lite chỉ từ prompt.

        `duration_s` CHỈ có nghĩa với kiểu nội suy (4/6/8s) và đi vào MODEL KEY chứ không
        phải một field riêng — hệt Omni Flash. Inference/i2v thì Flow cứng 8s nên tham số bị
        bỏ qua thay vì đổi sang một model không tồn tại.

        Lite xếp hàng ưu tiên thấp nên clip lâu hơn Veo trả tiền — người gọi cứ chờ theo
        VIDEO_POLL_TIMEOUT như thường, đừng bỏ cuộc sớm.
        """
        if user_paygate_tier not in VEO_LITE_TIERS:
            return {"error": "Veo 3.1 Lite chỉ có trên tài khoản Gemini Ultra "
                             f"({'/'.join(sorted(VEO_LITE_TIERS))}); tài khoản này là "
                             f"{user_paygate_tier}"}
        if start_media_id and end_media_id:
            gen_type = "start_end_frame_2_video"
            # Độ dài nằm trong key; số lạ rơi về bản 8s mặc định thay vì dựng một key bịa ra.
            model_key = (VEO_LITE_FRAME_MODELS.get(str(duration_s))
                         or VEO_LITE_MODELS.get(gen_type))
        elif start_media_id:
            gen_type = "frame_2_video"
            model_key = VEO_LITE_MODELS.get(gen_type)
        else:
            # Không ảnh nào ⇒ text-to-video, KHÔNG phải r2v thiếu ảnh: gửi key r2v mà bỏ
            # `referenceImages` đi thì Flow trả 400 (đo trên bảng Omni, cùng khuôn request).
            gen_type = ("reference_frame_2_video"
                        if (reference_media_ids or references) else "text_2_video")
            model_key = VEO_LITE_MODELS.get(gen_type)
        if not model_key:
            return {"error": f"Veo 3.1 Lite không có model cho kiểu {gen_type}"}

        if gen_type == "text_2_video":
            return await self._generate_video_text_veo_lite(
                prompt=prompt, project_id=project_id, aspect_ratio=aspect_ratio,
                user_paygate_tier=user_paygate_tier)

        if gen_type == "reference_frame_2_video":
            return await self.generate_video_from_references(
                reference_media_ids=reference_media_ids or [],
                prompt=prompt, project_id=project_id, scene_id=scene_id,
                aspect_ratio=aspect_ratio, user_paygate_tier=user_paygate_tier,
                references=references, video_model=model_key)

        return await self.generate_video(
            start_image_media_id=start_media_id, prompt=prompt, project_id=project_id,
            scene_id=scene_id, aspect_ratio=aspect_ratio,
            end_image_media_id=end_media_id, user_paygate_tier=user_paygate_tier,
            video_model=model_key, references=references)

    async def _generate_video_text_veo_lite(
            self, prompt: str, project_id: str,
            aspect_ratio: str = "VIDEO_ASPECT_RATIO_LANDSCAPE",
            user_paygate_tier: str = "PAYGATE_TIER_TWO") -> dict:
        """Veo 3.1 Lite text-to-video: không ảnh nào, chỉ prompt.

        Khuôn request bắt tận tay trên Flow UI (`video:batchAsyncGenerateVideoText`, key
        `veo_3_1_t2v_lite_low_priority`). Khác đường r2v/i2v ở ba chỗ, tất cả đều bắt buộc:
        endpoint riêng, model key riêng, và `outputSpec.resolution` — Flow UI luôn gửi
        720P cho đường này.

        Độ dài Flow cứng 8s (không có bảng key theo giây như nội suy), nên hàm không nhận
        `duration_s` thay vì nhận rồi lặng lẽ bỏ qua. `structuredPrompt` chỉ một part text:
        không có ảnh thì cũng chẳng có `{handle}` nào để bind.
        """
        model_key = VEO_LITE_MODELS.get("text_2_video")
        if not model_key:
            return {"error": "Veo 3.1 Lite không có model text-to-video"}

        body = {
            "mediaGenerationContext": {
                "batchId": f"{uuid.uuid4()}",
                "audioFailurePreference": "BLOCK_SILENCED_VIDEOS",
            },
            "clientContext": self._client_context(project_id, user_paygate_tier),
            "requests": [{
                "outputSpec": {"resolution": "VIDEO_RESOLUTION_720P"},
                "aspectRatio": aspect_ratio,
                "textInput": {"structuredPrompt": {"parts": [{"text": prompt}]}},
                "videoModelKey": model_key,
                "seed": int(time.time()) % 100000,
                "metadata": {},
            }],
            "useV2ModelConfig": True,
        }
        return await self._send("api_request", {
            "url": self._build_url("generate_video_text"),
            "method": "POST",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "VIDEO_GENERATION",
        }, timeout=60)   # Submit only — polling is separate

    async def upscale_video(self, media_id: str, scene_id: str,
                             aspect_ratio: str = "VIDEO_ASPECT_RATIO_PORTRAIT",
                             resolution: str = None,
                             project_id: str = "",
                             user_paygate_tier: str = "PAYGATE_TIER_ONE",
                             workflow_id: str = None) -> dict:
        """Submit a video upsample (async — poll with check_video_status like a normal gen).

        The generated video is only HD; this re-renders it at a higher resolution. The
        ceiling is tier-bound — TIER_ONE tops out at 1080p, only TIER_TWO reaches 4K — so an
        omitted `resolution` is derived from `user_paygate_tier`. Asking for 4K on TIER_ONE
        is rejected by Flow, so callers should let the tier decide.

        `workflow_id` (the source video's workflow) attaches the upsample to that same Flow
        workflow, which is how the web UI does it — the result shows up on the existing item
        instead of as a detached one. The operation returned is named `<mediaId>_upsampled`.
        """
        target = resolution or UPSAMPLE_VIDEO_RESOLUTIONS.get(
            user_paygate_tier, UPSAMPLE_VIDEO_DEFAULT)
        model_key = UPSCALE_MODELS.get(target, "veo_3_1_upsampler_1080p")

        request = {
            "aspectRatio": aspect_ratio,
            "resolution": target,
            "seed": int(time.time()) % 100000,
            "metadata": {"workflowId": workflow_id} if workflow_id else {"sceneId": scene_id},
            "videoInput": {"mediaId": media_id},
            "videoModelKey": model_key,
        }

        body = {
            "mediaGenerationContext": {
                "batchId": f"{uuid.uuid4()}",
                "audioFailurePreference": "BLOCK_SILENCED_VIDEOS",
            },
            "clientContext": self._client_context(project_id, user_paygate_tier),
            "requests": [request],
            "useV2ModelConfig": True,
        }

        url = self._build_url("upscale_video")
        return await self._send("api_request", {
            "url": url,
            "method": "POST",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "VIDEO_GENERATION",
        }, timeout=60)

    async def upscale_image(self,
        media_id: str,
        project_id: str,
        target_resolution: str = None,
        user_paygate_tier: str = "PAYGATE_TIER_ONE") -> dict:
        """Upsample an image to 2K/4K and get the bytes back.

        Flow only serves the low-res (HD) copy through the normal media URL; this endpoint
        returns the high-resolution render inline as base64 (`encodedImage` in the response).
        The ceiling is tier-bound — TIER_ONE → 2K, TIER_TWO → 4K — so when `target_resolution`
        is omitted it is derived from `user_paygate_tier` (see UPSAMPLE_IMAGE_RESOLUTIONS).
        """
        target = target_resolution or UPSAMPLE_IMAGE_RESOLUTIONS.get(
            user_paygate_tier, UPSAMPLE_IMAGE_DEFAULT)

        body = {
            "clientContext": {
                "projectId": project_id,
                "recaptchaContext": {
                    "applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB",
                    "token": "",  # Extension injects real token
                },
                "sessionId": f";{int(time.time() * 1000)}",
                "tool": "PINHOLE",
                "userPaygateTier": user_paygate_tier,
            },
            "mediaId": media_id,
            "targetResolution": target,
        }

        url = self._build_url("upscale_image")
        return await self._send("api_request", {
            "url": url,
            "method": "POST",
            "headers": random_headers(),
            "body": body,
            "captchaAction": "IMAGE_GENERATION",
        }, timeout=UPSAMPLE_IMAGE_TIMEOUT)

    async def check_video_status(self, media: list[dict]) -> dict:
        """Trạng thái render của các media video. `media` = [{"name": <mediaId>,
        "projectId": <flowProjectId>}].

        Contract MỚI của `video:batchCheckAsyncVideoGenerationStatus` (Flow đã đổi): trước
        đây body là `{"operations":[{"operation":{"name":...},"sceneId":...}]}` và trả
        `operations[]` kèm `metadata.video.fifeUrl`. Shape cũ giờ bị từ chối 400
        INVALID_ARGUMENT với MỌI operation — đó là lý do cả render video lẫn upscale đều
        "chạy xong trên Flow mà không lấy về được".

        Response: `{"media":[{name, projectId, workflowId, mediaMetadata:{mediaStatus:{
        mediaGenerationStatus, error, failureReasons}}, video:{...}}], remainingCredits}`.
        KHÔNG còn URL trong response — xong rồi thì phải resolve riêng
        (media_store.resolve_url → media.getMediaUrlRedirect).
        """
        body = {"media": media}
        url = self._build_url("check_video_status")
        return await self._send("api_request", {
            "url": url,
            "method": "POST",
            "headers": random_headers(),
            "body": body,
        }, timeout=30, serialize=False)  # poll is read-only → must not block submits (§9.1)

    async def get_credits(self) -> dict:
        """Get user credits and tier."""
        url = self._build_url("get_credits")
        return await self._send("api_request", {
            "url": url,
            "method": "GET",
            "headers": random_headers(),
        }, timeout=15, serialize=False)  # lightweight read (StatusPills) → don't block submits

    async def validate_media_id(self, media_id: str) -> bool:
        """Check if a mediaId is still valid.

        Production calls: GET /v1/media/{mediaId}?key=...&clientContext.tool=PINHOLE
        Returns True on 200, False otherwise.
        """
        # result = await self.get_media(media_id)
        # status = result.get("status", 500)
        # return isinstance(status, int) and status == 200
        result = await self.get_direct_media(media_id)
        return result.get("redirected", False)

    async def get_media(self, media_id: str) -> dict:
        """Fetch media metadata from Google Flow.

        Returns the raw API response which contains a fresh signed URL
        in data.fifeUrl or data.servingUri.
        """
        url = f"{GOOGLE_FLOW_API}/v1/media/{media_id}?key={GOOGLE_API_KEY}&clientContext.tool=PINHOLE"
        return await self._send("api_request", {
            "url": url,
            "method": "GET",
            "headers": random_headers(),
        }, timeout=15)

    async def upload_image(self, image_base64: str, mime_type: str = "image/jpeg",
                            project_id: str = "", file_name: str = "image.jpg") -> dict:
        """Upload an image for use as start/end frame.

        Uses /v1/flow/uploadImage endpoint.
        Response: {media: {name: "uuid", ...}, workflow: {...}}
        We store media.name as the mediaId for video generation.
        """
        body = {
            "clientContext": {
                "projectId": project_id,
                "tool": "PINHOLE",
            },
            "fileName": file_name,
            "imageBytes": image_base64,
            "isHidden": False,
            "isUserUploaded": True,
            "mimeType": mime_type,
        }

        url = self._build_url("upload_image")
        result = await self._send("api_request", {
            "url": url,
            "method": "POST",
            "headers": random_headers(),
            "body": body,
        }, timeout=60)

        # Extract media.name for convenience (used as mediaId in video gen)
        if not _is_ws_error(result):
            data = result.get("data", {})
            if isinstance(data, dict):
                media = data.get("media", {})
                if isinstance(media, dict) and media.get("name"):
                    result["_mediaId"] = media["name"]

        return result


def _is_ws_error(result: dict) -> bool:
    return bool(result.get("error")) or (isinstance(result.get("status"), int) and result["status"] >= 400)


_REF_TOKEN_RE = re.compile(r"\{([^{}]+)\}")
_ALIAS_RE = re.compile(r"^(.*?)\s*\((.*)\)\s*$")


def _handle_aliases(handle: str) -> list[str]:
    """Aliases a `{token}` may use for an entity whose name carries a parenthetical, e.g.
    "Hùng (Phạm Trọng Hùng)" → ["Hùng (Phạm Trọng Hùng)", "Hùng", "Phạm Trọng Hùng"]. Lets
    a prompt bind with the short name OR the full name, not only the verbatim entity name."""
    h = (handle or "").strip()
    out = [h]
    m = _ALIAS_RE.match(h)
    if m:
        if m.group(1).strip():
            out.append(m.group(1).strip())
        if m.group(2).strip():
            out.append(m.group(2).strip())
    return out


def _bind_unreferenced(parts: list[dict], references: list[dict],
                       who: str = "") -> list[dict]:
    """Thêm reference part (ở ĐẦU) cho các ảnh mà prompt không gọi tên.

    Ảnh chỉ nằm trong `imageInputs` mà không có part nào trong `structuredPrompt` thì model
    gần như bỏ qua — kết quả trông như một lượt sinh mới, chẳng liên quan ảnh đưa vào. Chỉ
    dùng khi người gọi BIẾT ảnh phải được điều kiện hoá (Node Editor kéo dây vào là cố ý);
    đừng dùng nơi references là kho ứng viên để prompt tự chọn theo tên.

    `bound` lớn dần trong vòng lặp: hai reference cùng mediaId (kho ứng viên hay gặp) chỉ được
    thêm MỘT part, không thì chính cái bind bù này lại đẻ ra đúng kiểu part trùng gây 400."""
    bound = {p["reference"]["media"]["mediaId"] for p in parts if "reference" in p}
    extra: list[dict] = []
    for r in references or []:
        mid = r.get("media_id")
        if not mid or mid in bound:
            continue
        bound.add(mid)
        extra.append({"reference": {"media": {"handle": r.get("handle") or "image",
                                              "mediaId": mid}}})
    if extra:
        logger.info("%s: bind %d reference chưa được prompt gọi tên (%s)",
                    who or "flow", len(extra),
                    ", ".join(p["reference"]["media"]["handle"] for p in extra))
    return extra + parts


def _build_structured_parts(prompt: str, references: list[dict],
                            dedupe: bool = False) -> list[dict]:
    """Build Google Flow `structuredPrompt.parts` by splitting `{handle}` tokens.

    Each `{handle}` in `prompt` that matches a reference's `handle` becomes a dedicated
    reference part `{"reference": {"media": {"handle", "mediaId"}}}`; surrounding text
    becomes `{"text": ...}` parts. This binds each entity mention to its own image so the
    model doesn't mix up references. Curly braces are used (not square brackets) to avoid
    clashing with control tokens like timestamps `[00:05]`. Unknown `{tokens}` are kept as
    literal text (braces stripped). Falls back to a single text part when no token matches.

    A reference's handle also binds via its aliases (short/full name around a parenthetical),
    so an extracted name like "Hùng (Phạm Trọng Hùng)" binds from {Hùng} too.

    `dedupe=True`: bind mỗi ẢNH đúng MỘT lần, ở lần nhắc đầu tiên; các lần sau thành chữ
    thường như token lạ. Bắt buộc cho prompt nhắc lại cùng một entity nhiều lần — một trang
    storyboard 6 panel gọi `{Phố Hàng Mã}` ở cả 6 panel sinh ra 6 reference part trỏ CÙNG một
    mediaId trong khi `imageInputs` chỉ có một mục, và Flow trả 400 INVALID_ARGUMENT (đã đo:
    6 part/1 ảnh → 400; bind một lần → chạy, cùng độ dài prompt). Hai reference part cho cùng
    một ảnh vốn cũng chẳng nói thêm gì cho model: nó chỉ cần biết ảnh này TÊN gì, một lần.
    """
    # exact handles first (priority), then aliases that don't shadow a real handle
    handle_to_id = {r["handle"].strip(): r["media_id"] for r in (references or [])}
    for r in references or []:
        for alias in _handle_aliases(r["handle"])[1:]:
            handle_to_id.setdefault(alias, r["media_id"])
    parts: list[dict] = []
    pos = 0
    bound: set[str] = set()      # mediaId đã có reference part (chỉ dùng khi dedupe)

    def push_text(s: str):
        """Nối vào part text liền trước thay vì tạo part mới.

        Mỗi token KHÔNG bind (token lạ, hoặc ảnh đã bind rồi khi dedupe) cắt đoạn văn làm đôi;
        nếu mỗi mảnh thành một part riêng thì một prompt nhiều token biến structuredPrompt
        thành hàng chục mảnh text vụn liền kề — Flow trả 400 INVALID_ARGUMENT. Đã đo trên trang
        storyboard 6 panel: 30 token → 37 part → 400; gộp lại còn 8 part → chạy, cùng nguyên
        văn prompt ấy. Các mảnh liền kề vốn chỉ là một đoạn văn bị chẻ ra, gộp lại không đổi
        nghĩa gì."""
        if not s:
            return
        if parts and "text" in parts[-1]:
            parts[-1]["text"] += s
        else:
            parts.append({"text": s})

    for m in _REF_TOKEN_RE.finditer(prompt):
        handle = m.group(1).strip()
        mid = handle_to_id.get(handle)
        if mid and not (dedupe and mid in bound):
            push_text(prompt[pos:m.start()])
            parts.append({"reference": {"media": {"handle": handle, "mediaId": mid}}})
            bound.add(mid)
            pos = m.end()
        else:
            # token lạ — hoặc ảnh đã bind rồi — giữ làm chữ thường, bỏ ngoặc
            push_text(prompt[pos:m.start()] + handle)
            pos = m.end()

    push_text(prompt[pos:])
    return parts or [{"text": prompt}]


# Singleton
_client: Optional[FlowClient] = None


def get_flow_client() -> FlowClient:
    global _client
    if _client is None:
        _client = FlowClient()
    return _client
