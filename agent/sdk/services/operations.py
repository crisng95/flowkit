"""SDK OperationService — executes media generation operations via providers.

Each method receives loaded data (scene/character dicts), builds a
backend-agnostic :class:`ProviderJob`, resolves the :class:`MediaProvider`
for the request (Google Flow, an AI assistant, or any registered backend),
runs the job, updates the DB, and returns a result dict for processor
status tracking.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING, Optional

from agent.db import crud
from agent.config import DEFAULT_PROVIDER
from agent.sdk.services.registry import ProviderRegistry
from agent.sdk.services.provider_base import (
    KIND_EDIT_IMAGE,
    KIND_IMAGE,
    KIND_UPSCALE,
    KIND_VIDEO,
    KIND_VIDEO_REFS,
    MediaProvider,
    ProviderJob,
)
from agent.utils.slugify import slugify
from agent.worker._parsing import (
    _is_error,
    _is_uuid,
    _extract_media_id,
    _extract_output_url,
)

if TYPE_CHECKING:
    from agent.services.flow_client import FlowClient
    from agent.sdk.persistence.base import Repository

logger = logging.getLogger(__name__)

# Entity types that need landscape (wide) reference images
_LANDSCAPE_ENTITY_TYPES = {"location"}


def _char_matches(c: dict, name_set: set) -> bool:
    """Check if a character matches any name in the set by slug OR display name."""
    slug = c.get("slug") or ""
    name = c.get("name", "")
    return (slug and slug in name_set) or (name and name in name_set)


def _reference_aspect_ratio(entity_type: str) -> str:
    """Pick aspect ratio based on entity type."""
    if entity_type in _LANDSCAPE_ENTITY_TYPES:
        return "IMAGE_ASPECT_RATIO_LANDSCAPE"
    return "IMAGE_ASPECT_RATIO_PORTRAIT"


class OperationService:
    """Executes media generation operations via pluggable MediaProviders.

    Each method builds a backend-agnostic ProviderJob, resolves the provider
    for the request (per-request override, else the DEFAULT_PROVIDER), runs
    the job, updates the database, and returns a result dict (with 'data'
    or 'error').
    """

    def __init__(self, flow_client: FlowClient, repo: Repository,
                 providers: dict[str, MediaProvider] | None = None,
                 registry: ProviderRegistry | None = None):
        self._client = flow_client
        self._repo = repo
        # Provider registry. "flow" wraps the injected FlowClient;
        # "assistant" needs no credentials and is always available.
        # Extra backends (a Sora adapter, a local SDXL worker, …) can be
        # injected here and selected per request.
        self._registry = registry or ProviderRegistry(flow_client, providers)

    @property
    def registry(self) -> ProviderRegistry:
        return self._registry

    @property
    def providers(self) -> dict[str, MediaProvider]:
        return self._registry.providers

    def _resolve_provider(self, name: str | None = None) -> MediaProvider:
        """Resolve a provider by name, falling back to the default."""
        return self._registry.resolve(name)

    async def _run_provider_job(self, job: ProviderJob,
                                provider_name: str | None = None) -> dict:
        """Capability-check then run a job on the resolved provider."""
        provider = self._resolve_provider(provider_name)
        err = provider.check(job)
        if err:
            return {"error": err}
        return await provider.run(job)

    # ------------------------------------------------------------------
    # Scene image operations
    # ------------------------------------------------------------------

    async def generate_scene_image(self, scene: dict, orientation: str,
                                   job_id: str = "",
                                   provider: str | None = None) -> dict:
        """Generate a scene image with reference imageInputs."""
        project = await crud.get_project(scene.get("_project_id", "0"))
        aspect = "IMAGE_ASPECT_RATIO_PORTRAIT" if orientation == "VERTICAL" else "IMAGE_ASPECT_RATIO_LANDSCAPE"
        prompt = scene.get("image_prompt") or scene.get("prompt", "")
        # CONTINUATION scenes: enrich prompt with transformation context
        if scene.get("parent_scene_id") and not scene.get("image_prompt"):
            prompt = _build_continuation_prompt(prompt)
        tier = project.get("user_paygate_tier", "PAYGATE_TIER_TWO") if project else "PAYGATE_TIER_TWO"
        pid = scene.get("_project_id", "0")

        # Resolve character reference media_ids (Flow) and image URLs (assistant)
        char_media_ids = None
        ref_urls: list[str] = []
        ref_names: list[str] = []
        char_names_raw = scene.get("character_names")
        if char_names_raw and pid:
            if isinstance(char_names_raw, str):
                try:
                    char_names_raw = json.loads(char_names_raw)
                except json.JSONDecodeError:
                    char_names_raw = []
            if not isinstance(char_names_raw, list):
                char_names_raw = []
            if char_names_raw:
                project_chars = await crud.get_project_characters(pid)
                valid_ids = []
                missing_refs = []
                char_names_set = set(char_names_raw)
                for c in project_chars:
                    if not _char_matches(c, char_names_set):
                        continue
                    mid = c.get("media_id")
                    if mid:
                        valid_ids.append(mid)
                        ref_names.append(c.get("name", ""))
                        if c.get("reference_image_url"):
                            ref_urls.append(c["reference_image_url"])
                    else:
                        missing_refs.append(c.get("slug") or c["name"])

                if missing_refs:
                    return {"error": f"Waiting for reference images: {', '.join(missing_refs)}"}

                char_media_ids = valid_ids if valid_ids else None
                if char_media_ids:
                    logger.info("Scene %s: using %d reference images",
                                scene.get("id", "?")[:8], len(char_media_ids))

        job = ProviderJob(
            job_id=job_id or uuid.uuid4().hex[:12],
            kind=KIND_IMAGE,
            prompt=prompt,
            orientation=orientation,
            reference_urls=tuple(ref_urls),
            extra={
                # Flow backend knobs
                "project_id": pid,
                "tier": tier,
                "aspect": aspect,
                "character_media_ids": char_media_ids,
                # Assistant / future backends context
                "kind": "image",
                "scene_id": scene.get("id"),
                "project_name": project.get("name") if project else "",
                "display_order": scene.get("display_order", 0),
                "reference_names": ref_names,
            },
        )
        return await self._run_provider_job(job, provider)

    async def edit_scene_image(self, scene: dict, orientation: str,
                               source_media_id: str | None = None,
                               job_id: str = "",
                               provider: str | None = None) -> dict:
        """Edit an existing scene image using IMAGE_INPUT_TYPE_BASE_IMAGE.

        Resolves character refs from scene's character_names and passes them
        as IMAGE_INPUT_TYPE_REFERENCE after the base image. Order:
        [base_image, char_A, char_B, ...] — helps Google Flow detect characters.
        """
        project = await crud.get_project(scene.get("_project_id", "0"))
        aspect = "IMAGE_ASPECT_RATIO_PORTRAIT" if orientation == "VERTICAL" else "IMAGE_ASPECT_RATIO_LANDSCAPE"
        tier = project.get("user_paygate_tier", "PAYGATE_TIER_ONE") if project else "PAYGATE_TIER_ONE"
        pid = scene.get("_project_id", "0")

        src = source_media_id
        orient_prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
        # CONTINUATION scenes always edit from parent's image (that's the
        # whole point of chaining).  Only non-chain scenes edit their own.
        if not src and scene.get("parent_scene_id"):
            parent = await crud.get_scene(scene["parent_scene_id"])
            if parent:
                src = parent.get(f"{orient_prefix}_image_media_id")
        if not src:
            src = scene.get(f"{orient_prefix}_image_media_id")

        # URL form of the source (for URL-based backends like the assistant).
        # source_media_id is a Flow UUID — URL backends need the image URL.
        src_url = None
        if scene.get("parent_scene_id"):
            parent = await crud.get_scene(scene["parent_scene_id"])
            src_url = (parent or {}).get(f"{orient_prefix}_image_url")
        src_url = src_url or scene.get(f"{orient_prefix}_image_url")

        edit_prompt = scene.get("image_prompt") or scene.get("prompt", "")
        # CONTINUATION scenes: enrich prompt with transformation context
        if scene.get("parent_scene_id") and not scene.get("image_prompt"):
            edit_prompt = _build_continuation_prompt(edit_prompt)

        # Resolve character references in both forms (media_ids for Flow,
        # URLs for the assistant).
        char_media_ids = None
        ref_urls: list[str] = []
        char_names_raw = scene.get("character_names")
        if char_names_raw and pid:
            if isinstance(char_names_raw, str):
                try:
                    char_names_raw = json.loads(char_names_raw)
                except json.JSONDecodeError:
                    char_names_raw = []
            if isinstance(char_names_raw, list) and char_names_raw:
                project_chars = await crud.get_project_characters(pid)
                valid_ids = []
                char_names_set = set(char_names_raw)
                for c in project_chars:
                    if _char_matches(c, char_names_set) and c.get("media_id"):
                        valid_ids.append(c["media_id"])
                        if c.get("reference_image_url"):
                            ref_urls.append(c["reference_image_url"])
                char_media_ids = valid_ids if valid_ids else None

        job = ProviderJob(
            job_id=job_id or uuid.uuid4().hex[:12],
            kind=KIND_EDIT_IMAGE,
            prompt=edit_prompt,
            orientation=orientation,
            source_url=src_url,
            reference_urls=tuple(ref_urls),
            extra={
                "project_id": pid,
                "tier": tier,
                "aspect": aspect,
                "source_media_id": src,
                "character_media_ids": char_media_ids,
                "scene_id": scene.get("id"),
                "project_name": project.get("name") if project else "",
                "display_order": scene.get("display_order", 0),
            },
        )
        return await self._run_provider_job(job, provider)

    # ------------------------------------------------------------------
    # Video operations
    # ------------------------------------------------------------------

    async def generate_scene_video(self, scene: dict, orientation: str,
                                   request_id: str = "",
                                   provider: str | None = None) -> dict:
        """Generate video from a scene image (i2v). Submits + polls."""
        prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
        image_media_id = scene.get(f"{prefix}_image_media_id")
        if not image_media_id:
            return {"error": f"No {prefix} image media_id for scene"}

        project = await crud.get_project(scene.get("_project_id", "0"))
        aspect = "VIDEO_ASPECT_RATIO_PORTRAIT" if orientation == "VERTICAL" else "VIDEO_ASPECT_RATIO_LANDSCAPE"
        tier = project.get("user_paygate_tier", "PAYGATE_TIER_TWO") if project else "PAYGATE_TIER_TWO"
        pid = scene.get("_project_id", "0")
        end_id = scene.get(f"{prefix}_end_scene_media_id")
        model_family = (project.get("video_model_family") if project else None) or "veo"

        # Chain scenes with end_image: prefer transition_prompt (describes motion between frames)
        if end_id and scene.get("transition_prompt"):
            base_prompt = scene["transition_prompt"]
        else:
            base_prompt = scene.get("video_prompt") or scene.get("prompt", "")
        prompt = await _build_video_prompt(base_prompt, scene, pid)

        job = ProviderJob(
            job_id=request_id or uuid.uuid4().hex[:12],
            kind=KIND_VIDEO,
            prompt=prompt,
            orientation=orientation,
            start_url=scene.get(f"{prefix}_image_url"),
            end_url=await self._resolve_chain_end_url(scene, prefix),
            extra={
                "project_id": pid,
                "tier": tier,
                "aspect": aspect,
                "scene_id": scene.get("id", ""),
                "start_media_id": image_media_id,
                "end_media_id": end_id,
                "request_id": request_id,
                "model_family": model_family,
                # Per-scene clip length (seconds). Omni Flash honours it (rounded
                # up to 4/6/8/10); Veo ignores it. Lets a scene whose narration
                # outruns the default be rendered longer instead of padded in post.
                "duration_s": scene.get("duration"),
                "project_name": project.get("name") if project else "",
                "display_order": scene.get("display_order", 0),
            },
        )
        return await self._run_provider_job(job, provider)

    async def generate_scene_video_refs(self, scene: dict, orientation: str,
                                        request_id: str = "",
                                        provider: str | None = None) -> dict:
        """Generate video from reference images (r2v). Submits + polls.

        R2V uses any entity images (characters, visual_assets, locations) plus
        scene images as IMAGE_USAGE_TYPE_ASSET references — not just character
        face refs.  Collect all matching entity media_ids and optionally include
        the scene's end_scene image.
        """
        project = await crud.get_project(scene.get("_project_id", "0"))
        aspect = "VIDEO_ASPECT_RATIO_PORTRAIT" if orientation == "VERTICAL" else "VIDEO_ASPECT_RATIO_LANDSCAPE"
        tier = project.get("user_paygate_tier", "PAYGATE_TIER_TWO") if project else "PAYGATE_TIER_TWO"
        pid = scene.get("_project_id", "0")
        prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
        end_id = scene.get(f"{prefix}_end_scene_media_id")

        # Chain scenes with end_image: prefer transition_prompt
        if end_id and scene.get("transition_prompt"):
            base_prompt = scene["transition_prompt"]
        else:
            base_prompt = scene.get("video_prompt") or scene.get("prompt", "")
        prompt = await _build_video_prompt(base_prompt, scene, pid)

        char_names_raw = scene.get("character_names")
        if isinstance(char_names_raw, str):
            try:
                char_names_raw = json.loads(char_names_raw)
            except json.JSONDecodeError:
                char_names_raw = []

        if not pid:
            return {"error": "No project_id for r2v video generation"}

        # Collect up to 3 reference images (API max).  Priority order:
        #   1. end_scene_media_id — chain continuity target (end frame)
        #   2. visual_asset entities — primary objects (vehicles, props)
        #   3. character entities — main character consistency
        # Location entities are excluded — they add generic backgrounds
        # that can re-introduce unwanted visual elements (e.g. buildings
        # removed from a scene).
        _R2V_MAX_REFS = 3
        _R2V_ENTITY_PRIORITY = ("visual_asset", "character")
        ref_ids: list[str] = []
        ref_urls: list[str] = []
        ref_names_r2v: list[str] = []
        seen: set[str] = set()

        # 1. end_scene image (highest priority for chain scenes)
        if end_id and end_id not in seen:
            ref_ids.append(end_id)
            seen.add(end_id)

        # 2-3. Entities by priority: visual_asset first, then character
        if char_names_raw and len(ref_ids) < _R2V_MAX_REFS:
            project_entities = await crud.get_project_characters(pid)
            char_names_set = set(char_names_raw)
            for etype in _R2V_ENTITY_PRIORITY:
                for c in project_entities:
                    if len(ref_ids) >= _R2V_MAX_REFS:
                        break
                    if not _char_matches(c, char_names_set):
                        continue
                    if c.get("entity_type") != etype:
                        continue
                    mid = c.get("media_id")
                    if mid and mid not in seen:
                        ref_ids.append(mid)
                        seen.add(mid)
                        ref_names_r2v.append(c.get("name", ""))
                        if c.get("reference_image_url"):
                            ref_urls.append(c["reference_image_url"])

        job = ProviderJob(
            job_id=request_id or uuid.uuid4().hex[:12],
            kind=KIND_VIDEO_REFS,
            prompt=prompt,
            orientation=orientation,
            start_url=scene.get(f"{prefix}_image_url"),
            reference_urls=tuple(ref_urls),
            extra={
                "project_id": pid,
                "tier": tier,
                "aspect": aspect,
                "scene_id": scene.get("id", ""),
                "ref_media_ids": ref_ids,
                "request_id": request_id,
                "project_name": project.get("name") if project else "",
                "display_order": scene.get("display_order", 0),
                "reference_names": ref_names_r2v,
            },
        )
        return await self._run_provider_job(job, provider)

    async def upscale_scene_video(self, scene: dict, orientation: str,
                                  request_id: str = "",
                                  provider: str | None = None) -> dict:
        """Upscale a completed scene video. Submits + polls.

        If a previous attempt already submitted (op_name saved in DB), skip
        submit and just re-poll — avoids duplicate API calls on retry.
        """
        prefix = "vertical" if orientation == "VERTICAL" else "horizontal"
        video_media_id = scene.get(f"{prefix}_video_media_id")
        if not video_media_id:
            return {"error": f"No {prefix} video media_id for scene"}

        aspect = "VIDEO_ASPECT_RATIO_PORTRAIT" if orientation == "VERTICAL" else "VIDEO_ASPECT_RATIO_LANDSCAPE"
        project = await crud.get_project(scene.get("_project_id", "0"))
        project_slug = slugify(project.get("name", "unnamed")) if project else slugify(scene.get("_project_id", "unnamed"))

        job = ProviderJob(
            job_id=request_id or uuid.uuid4().hex[:12],
            kind=KIND_UPSCALE,
            prompt="",
            orientation=orientation,
            extra={
                "project_id": scene.get("_project_id", "0"),
                "aspect": aspect,
                "scene_id": scene.get("id", ""),
                "video_media_id": video_media_id,
                "request_id": request_id,
                "project_slug": project_slug,
                "display_order": scene.get("display_order", 0),
            },
        )
        return await self._run_provider_job(job, provider)

    # ------------------------------------------------------------------
    # Reference image operations
    # ------------------------------------------------------------------

    async def generate_reference_image(self, char: dict, project_id: str,
                                         job_id: str = "",
                                         provider: str | None = None) -> dict:
        """Generate a reference image for a character/entity.

        Handles fast-path (image exists, just register for a media id) and
        normal path (generate + register). Updates character DB record with
        media_id and reference_image_url. Returns result dict.
        """
        entity_type = char.get("entity_type", "character")
        pid = project_id
        prov = self._resolve_provider(provider)

        # Fast path: image already exists — just needs a provider media id.
        existing_url = char.get("reference_image_url")
        if existing_url and not char.get("media_id"):
            logger.info("%s '%s' already has image, registering with provider '%s'",
                        entity_type, char["name"], prov.name)
            result = await prov.register_existing_image(
                existing_url, name=char.get("name", ""), project_id=pid)
            if not _is_error(result):
                data = result.get("data", {}) or {}
                media = data.get("media") or []
                mid = media[0].get("name") if media else None
                url = data.get("url", existing_url)
                await crud.update_character(char["id"], media_id=mid,
                                            reference_image_url=url)
                logger.info("%s '%s' registered: media_id=%s",
                            entity_type, char["name"], (mid or "?")[:8])
            return result

        # Normal path: generate from scratch.
        prompt = char.get("image_prompt") or f"Character reference: {char['name']}. {char.get('description', '')}"
        project = await crud.get_project(pid) if pid != "0" else None
        tier = project.get("user_paygate_tier", "PAYGATE_TIER_TWO") if project else "PAYGATE_TIER_TWO"
        aspect = _reference_aspect_ratio(entity_type)
        orientation = "VERTICAL" if "PORTRAIT" in aspect else "HORIZONTAL"

        job = ProviderJob(
            job_id=job_id or uuid.uuid4().hex[:12],
            kind=KIND_IMAGE,
            prompt=prompt,
            orientation=orientation,
            extra={
                "kind": "reference_image",
                "project_id": pid,
                "tier": tier,
                "aspect": aspect,
                "entity_name": char["name"],
                "entity_type": entity_type,
                "composition": "portrait full-body, head-to-toe, front-facing, centered"
                if orientation == "VERTICAL"
                else "landscape establishing shot, level horizon, atmospheric",
            },
        )
        result = await self._run_provider_job(job, provider)

        if not _is_error(result):
            output_url = _extract_output_url(result, "GENERATE_IMAGE")
            direct_mid = _extract_media_id(result, "GENERATE_IMAGE")
            if direct_mid and _is_uuid(direct_mid):
                await crud.update_character(char["id"], media_id=direct_mid,
                                            reference_image_url=output_url)
                logger.info("%s '%s' ref image ready (%s): media_id=%s",
                            entity_type, char["name"],
                            aspect.split("_")[-1].lower(), direct_mid)
                return result
            if prov.needs_media_id_registration() and output_url:
                reg = await prov.register_existing_image(
                    output_url, name=char.get("name", ""), project_id=pid)
                if not _is_error(reg):
                    reg_data = reg.get("data", {}) or {}
                    reg_media = reg_data.get("media") or []
                    upload_mid = reg_media[0].get("name") if reg_media else None
                    await crud.update_character(char["id"], media_id=upload_mid,
                                                reference_image_url=output_url)
                    logger.info("%s '%s' ref image uploaded (%s): media_id=%s",
                                entity_type, char["name"],
                                aspect.split("_")[-1].lower(),
                                (upload_mid or "?")[:30])
                    return result
                logger.warning("%s '%s' upload failed, no media_id stored — will retry",
                               entity_type, char["name"])
                return {"error": f"Upload failed for {char['name']} — image generated but could not get UUID media_id"}
            # Provider minted its own id — store whatever we got.
            await crud.update_character(char["id"], media_id=direct_mid,
                                        reference_image_url=output_url)
            logger.info("%s '%s' ref image ready via %s: media_id=%s",
                        entity_type, char["name"], prov.name, (direct_mid or "?")[:8])

        return result

    async def edit_character_image(self, char: dict, project_id: str,
                                   source_media_id: str | None = None,
                                   job_id: str = "",
                                   provider: str | None = None) -> dict:
        """Edit a character/location reference image.

        Resolves the provider for the request and publishes an edit_image
        job; URL-based backends use the character's reference_image_url,
        Flow uses the media_id.
        """
        src = source_media_id or char.get("media_id")
        edit_prompt = char.get("image_prompt") or char.get("description", "")
        aspect = "IMAGE_ASPECT_RATIO_LANDSCAPE" if char.get("entity_type") in ("location",) else "IMAGE_ASPECT_RATIO_PORTRAIT"
        orientation = "VERTICAL" if "PORTRAIT" in aspect else "HORIZONTAL"
        project = await crud.get_project(project_id) if project_id != "0" else None
        tier = project.get("user_paygate_tier", "PAYGATE_TIER_ONE") if project else "PAYGATE_TIER_ONE"

        job = ProviderJob(
            job_id=job_id or uuid.uuid4().hex[:12],
            kind=KIND_EDIT_IMAGE,
            prompt=edit_prompt,
            orientation=orientation,
            source_url=char.get("reference_image_url"),
            extra={
                "project_id": project_id,
                "tier": tier,
                "aspect": aspect,
                "source_media_id": src,
                "entity_name": char.get("name"),
                "entity_type": char.get("entity_type", "character"),
            },
        )
        result = await self._run_provider_job(job, provider)
        if not _is_error(result):
            mid = _extract_media_id(result, "GENERATE_IMAGE")
            url = _extract_output_url(result, "GENERATE_IMAGE")
            await crud.update_character(char["id"], media_id=mid,
                                        reference_image_url=url)
            logger.info("%s '%s' ref image edited via %s: media_id=%s",
                        char.get("entity_type", "character"), char.get("name"),
                        self._resolve_provider(provider).name, (mid or "?")[:8])
        return result

    # ------------------------------------------------------------------
    # Queue-based wrappers (create request in DB for processor pickup)
    # ------------------------------------------------------------------

    async def _resolve_chain_end_url(self, scene: dict, prefix: str) -> str | None:
        """Assistant-mode chaining: find the child scene's image URL for this scene's end frame."""
        video_id = scene.get("video_id")
        if not video_id:
            return None
        try:
            for s in await crud.list_scenes(video_id=video_id):
                if s.get("parent_scene_id") == scene.get("id"):
                    url = s.get(f"{prefix}_image_url")
                    if url:
                        return url
        except Exception as e:
            logger.warning("Could not resolve chain end frame: %s", e)
        return None

    async def _resolve_queue_orientation(self, video_id: str, orientation: str | None) -> str:
        """Resolve orientation for queue methods: explicit > video table > VERTICAL."""
        if orientation:
            return orientation
        video = await crud.get_video(video_id)
        if video and video.get("orientation"):
            return video["orientation"]
        return "VERTICAL"

    async def queue_scene_image(self, scene_id: str, project_id: str,
                                video_id: str, orientation: str | None = None,
                                provider: str | None = None) -> str:
        """Queue a GENERATE_IMAGE request. Returns request id."""
        orientation = await self._resolve_queue_orientation(video_id, orientation)
        row = await crud.create_request(
            req_type="GENERATE_IMAGE", orientation=orientation,
            scene_id=scene_id, project_id=project_id, video_id=video_id,
            provider=provider,
        )
        return row["id"]

    async def queue_edit_scene_image(self, scene_id: str, project_id: str,
                                     video_id: str, orientation: str | None = None,
                                     edit_prompt: str | None = None,
                                     source_media_id: str | None = None,
                                     provider: str | None = None) -> str:
        """Queue an EDIT_IMAGE request. Returns request id."""
        orientation = await self._resolve_queue_orientation(video_id, orientation)
        row = await crud.create_request(
            req_type="EDIT_IMAGE", orientation=orientation,
            scene_id=scene_id, project_id=project_id, video_id=video_id,
            edit_prompt=edit_prompt, source_media_id=source_media_id,
            provider=provider,
        )
        return row["id"]

    async def queue_scene_video(self, scene_id: str, project_id: str,
                                video_id: str, orientation: str | None = None,
                                provider: str | None = None) -> str:
        """Queue a GENERATE_VIDEO request. Returns request id."""
        orientation = await self._resolve_queue_orientation(video_id, orientation)
        row = await crud.create_request(
            req_type="GENERATE_VIDEO", orientation=orientation,
            scene_id=scene_id, project_id=project_id, video_id=video_id,
            provider=provider,
        )
        return row["id"]

    async def queue_scene_video_refs(self, scene_id: str, project_id: str,
                                     video_id: str, orientation: str | None = None,
                                     provider: str | None = None) -> str:
        """Queue a GENERATE_VIDEO_REFS request. Returns request id."""
        orientation = await self._resolve_queue_orientation(video_id, orientation)
        row = await crud.create_request(
            req_type="GENERATE_VIDEO_REFS", orientation=orientation,
            scene_id=scene_id, project_id=project_id, video_id=video_id,
            provider=provider,
        )
        return row["id"]

    async def queue_upscale_video(self, scene_id: str, project_id: str,
                                  video_id: str, orientation: str | None = None,
                                  provider: str | None = None) -> str:
        """Queue an UPSCALE_VIDEO request. Returns request id."""
        orientation = await self._resolve_queue_orientation(video_id, orientation)
        row = await crud.create_request(
            req_type="UPSCALE_VIDEO", orientation=orientation,
            scene_id=scene_id, project_id=project_id, video_id=video_id,
            provider=provider,
        )
        return row["id"]

    async def queue_reference_image(self, character_id: str, project_id: str,
                                provider: str | None = None) -> str:
        """Queue a GENERATE_CHARACTER_IMAGE request. Returns request id."""
        row = await crud.create_request(
            req_type="GENERATE_CHARACTER_IMAGE",
            character_id=character_id, project_id=project_id,
            provider=provider,
        )
        return row["id"]

    async def queue_regenerate_scene_image(self, scene_id: str, project_id: str,
                                           video_id: str, orientation: str | None = None,
                                           provider: str | None = None) -> str:
        """Queue a REGENERATE_IMAGE request (bypasses skip check). Returns request id."""
        orientation = await self._resolve_queue_orientation(video_id, orientation)
        row = await crud.create_request(
            req_type="REGENERATE_IMAGE", orientation=orientation,
            scene_id=scene_id, project_id=project_id, video_id=video_id,
            provider=provider,
        )
        return row["id"]

    async def queue_regenerate_character_image(self, character_id: str, project_id: str,
                                               provider: str | None = None) -> str:
        """Queue a REGENERATE_CHARACTER_IMAGE request (clears existing, regenerates). Returns request id."""
        row = await crud.create_request(
            req_type="REGENERATE_CHARACTER_IMAGE",
            character_id=character_id, project_id=project_id,
            provider=provider,
        )
        return row["id"]

    # Alias used by Character.generate_image()
    async def generate_character_image(self, character_id: str, project_id: str) -> str:
        return await self.queue_reference_image(character_id, project_id)

    async def queue_edit_character_image(self, character_id: str, project_id: str,
                                         edit_prompt: str | None = None,
                                         source_media_id: str | None = None) -> str:
        """Queue an EDIT_CHARACTER_IMAGE request. Returns request id."""
        row = await crud.create_request(
            req_type="EDIT_CHARACTER_IMAGE",
            character_id=character_id, project_id=project_id,
            edit_prompt=edit_prompt, source_media_id=source_media_id,
        )
        return row["id"]

    # Alias used by Character.edit_image()
    async def edit_character_image(self, character_id: str, project_id: str,
                                   edit_prompt: str | None = None,
                                   source_media_id: str | None = None) -> str:
        return await self.queue_edit_character_image(
            character_id, project_id, edit_prompt=edit_prompt,
            source_media_id=source_media_id,
        )


# ------------------------------------------------------------------
# Prompt building (module-level for reuse)
# ------------------------------------------------------------------

async def _build_video_prompt(base_prompt: str, scene: dict, project_id: str | None) -> str:
    """Enhance video prompt with Veo 3 audio instructions and negative prompt."""
    parts = [base_prompt.strip()]

    # Only append voice context when video_prompt contains dialogue (verb-based detection)
    dialogue_verbs = ("says", "whispers", "shouts", "asks", "replies", "murmurs", "exclaims", "gasps", "laughs", "mutters")
    prompt_lower = base_prompt.lower()
    has_dialogue = any(verb in prompt_lower for verb in dialogue_verbs)
    if project_id and has_dialogue:
        char_names_raw = scene.get("character_names")
        if isinstance(char_names_raw, str):
            try:
                char_names_raw = json.loads(char_names_raw)
            except json.JSONDecodeError:
                char_names_raw = []
        if isinstance(char_names_raw, list) and char_names_raw:
            project_chars = await crud.get_project_characters(project_id)
            char_names_set = set(char_names_raw)
            voices = []
            for c in project_chars:
                if _char_matches(c, char_names_set) and c.get("voice_description"):
                    voices.append(f"{c['name']}: {c['voice_description']}")
            if voices:
                parts.append("Character voices: " + ". ".join(voices) + ".")

    # Check project-level audio flags — Veo 3 Audio label format
    allow_music = False
    allow_voice = False
    if project_id:
        project = await crud.get_project(project_id)
        if project:
            if project.get("allow_music"):
                allow_music = True
            if project.get("allow_voice"):
                allow_voice = True

    if not allow_music:
        # Only append if prompt doesn't already have Audio:/Music: labels
        if "audio:" not in prompt_lower and "music:" not in prompt_lower:
            if allow_voice:
                parts.append("Audio: no background music. Keep character dialogue and natural ambient sounds.")
            else:
                parts.append("Audio: natural ambient sounds only, no background music, no narration, no voiceover.")

    # Veo 3 negative prompt — always append unless already present
    if "negative:" not in prompt_lower:
        parts.append("Negative: subtitles, captions, watermark, text on screen, logo, blurry faces, distorted hands.")

    return " ".join(parts)


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_ops: Optional[OperationService] = None


def init_operations(flow_client: FlowClient, repo: Repository) -> OperationService:
    """Initialize the module-level OperationService singleton."""
    global _ops
    _ops = OperationService(flow_client=flow_client, repo=repo)
    return _ops


def get_operations() -> OperationService:
    """Return the initialized OperationService singleton."""
    if _ops is None:
        raise RuntimeError(
            "OperationService not initialized — call init_operations(flow_client, repo) first"
        )
    return _ops
