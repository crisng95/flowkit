"""Assistant media provider — routes generation to the AI assistant instead of Google Flow.

Implements the :class:`MediaProvider` interface (see ``provider_base.py``), so
``OperationService`` treats it like any other backend. The transport is the
persistent provider-job queue (``provider_job`` table + ``/api/provider-jobs``
HTTP API):

Producer side (this provider):
    1. ``run(job)`` inserts a QUEUED row into ``provider_job`` with the full
       prompt, orientation, input URLs (``source_url`` / ``start_url`` /
       ``end_url`` / ``extra["reference_urls"]``) and provider-specific params
       in ``extra``.
    2. It then blocks in ``crud.wait_for_provider_job`` until the job reaches
       a terminal status or ``ASSISTANT_PROVIDER_TIMEOUT_S`` elapses.
    3. The terminal row is translated into the same Flow-shaped dict the rest
       of the pipeline parses (``_parsing._extract_media_id`` /
       ``_extract_output_url``), so downstream code never knows which backend
       produced the media.

Worker side (the assistant, or any external agent):
    1. ``GET /api/provider-jobs/wait-next?provider=assistant&worker_id=<id>``
       long-polls for the next claimable job and claims it (lease granted).
    2. ``POST /api/provider-jobs/{id}/heartbeat`` every ~lease_ttl/3 while
       working; ``POST .../progress`` optionally reports progress.
    3. ``POST /api/provider-jobs/{id}/complete`` with a result payload::

           {"output_url": "<file:// or https:// URL of the finished media>",
            "media_id": "<uuid, optional — one is minted when absent>"}

       or ``POST .../fail`` with ``{"error": "..."}``.

A crashed worker's lease expires and the job becomes reclaimable, so jobs are
never stranded. See ``agent/worker/assistant_worker.py`` for a reference
worker implementing this protocol.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from urllib.parse import urlparse

from agent import config
from agent.db import crud
from agent.utils.paths import file_url_to_path
from agent.sdk.services.provider_base import (
    KIND_AUDIO,
    KIND_EDIT_IMAGE,
    KIND_IMAGE,
    KIND_UPSCALE,
    KIND_VIDEO,
    KIND_VIDEO_REFS,
    MediaProvider,
    ProviderCapabilities,
    ProviderJob,
)

logger = logging.getLogger(__name__)


def _image_result(mid: str, url: str) -> dict:
    """Flow-shaped image result so _parsing._extract_media_id/_extract_output_url work."""
    return {
        "data": {
            "media": [
                {
                    "name": mid,
                    "image": {"generatedImage": {"mediaId": mid, "fifeUrl": url}},
                }
            ]
        }
    }


def _video_result(mid: str, url: str) -> dict:
    """Flow-shaped video result so _parsing helpers work."""
    return {
        "data": {
            "operations": [
                {
                    "operation": {
                        "name": mid,
                        "metadata": {"video": {"mediaId": mid, "fifeUrl": url}},
                    },
                    "status": "MEDIA_GENERATION_STATUS_SUCCESSFUL",
                }
            ]
        }
    }


def _audio_result(url: str) -> dict:
    """TTS result: the finished audio URL plus a local path when file://."""
    local = file_url_to_path(url or "")
    local_path = str(local.resolve()) if local is not None else ""
    return {"data": {"url": url, "audio_path": local_path or url}}


class AssistantProvider(MediaProvider):
    """Publishes generation jobs to the provider-job queue and awaits a worker."""

    name = "assistant"
    display_name = "Assistant (Pax)"
    capabilities = ProviderCapabilities(
        generate_image=True,
        edit_image=True,
        generate_video_i2v=True,
        generate_video_r2v=True,
        upscale=False,  # the assistant cannot upscale video
        generate_audio=True,  # TTS via provider-job queue
        max_concurrent=config.ASSISTANT_MAX_CONCURRENT,
        cooldown_s=config.ASSISTANT_COOLDOWN_S,
    )

    def is_available(self) -> bool:
        """The assistant bridge needs no credentials or Chrome — always up."""
        return True

    def __init__(self) -> None:
        self.timeout_s = config.ASSISTANT_PROVIDER_TIMEOUT_S
        self.poll_s = config.ASSISTANT_PROVIDER_POLL_S

    # ── MediaProvider interface ──

    async def run(self, job: ProviderJob) -> dict:
        """Publish one provider job and wait for an external worker to finish it."""
        if job.kind == KIND_EDIT_IMAGE:
            if not job.source_url:
                return {"error": "No source image to edit — generate a scene image first"}
        elif job.kind == KIND_AUDIO:
            if not (job.prompt or "").strip():
                return {"error": "No text to synthesize — TTS prompt is empty"}
        elif job.kind in (KIND_VIDEO, KIND_VIDEO_REFS):
            prefix = "vertical" if job.orientation == "VERTICAL" else "horizontal"
            if job.kind == KIND_VIDEO_REFS:
                # Degrade gracefully: r2v with no refs becomes plain i2v off
                # the scene image. Fail only when there is nothing to
                # generate from.
                if not job.reference_urls and not job.start_url:
                    return {"error": "No valid reference images for r2v"}
            elif not job.start_url:
                return {"error": f"No {prefix} image for scene"}
        elif job.kind not in (KIND_IMAGE, KIND_AUDIO):
            return {"error": f"AssistantProvider: unknown job kind '{job.kind}'"}

        payload_extra = dict(job.extra or {})
        payload_extra["reference_urls"] = list(job.reference_urls)

        await crud.create_provider_job(
            provider=self.name,
            kind=job.kind,
            prompt=job.prompt,
            orientation=job.orientation,
            source_url=job.source_url,
            start_url=job.start_url,
            end_url=job.end_url,
            extra=payload_extra,
            job_id=job.job_id,
        )
        logger.info("Assistant provider: job %s (%s) queued — waiting for worker",
                    job.job_id[:12], job.kind)

        final = await crud.wait_for_provider_job(
            job.job_id, timeout_s=self.timeout_s, poll_interval_s=self.poll_s)
        if final is None:
            logger.error("Assistant provider: job %s timed out after %ds",
                         job.job_id[:12], self.timeout_s)
            return {"error": f"Assistant provider timeout: no worker completed job "
                             f"{job.job_id[:12]} after {self.timeout_s}s"}

        status = final.get("status")
        if status == "SUCCEEDED":
            try:
                result = json.loads(final.get("result") or "{}")
            except (json.JSONDecodeError, TypeError):
                result = {}
            url = result.get("output_url", "")
            mid = result.get("media_id") or str(uuid.uuid4())
            logger.info("Assistant provider: job %s completed (media_id=%s)",
                        job.job_id[:12], mid[:8])
            if job.kind in (KIND_VIDEO, KIND_VIDEO_REFS):
                return _video_result(mid, url)
            if job.kind == KIND_AUDIO:
                return _audio_result(url)
            return _image_result(mid, url)
        if status == "CANCELLED":
            return {"error": f"Assistant provider job {job.job_id[:12]} was cancelled"}
        return {"error": final.get("error_message") or
                f"Assistant provider job {job.job_id[:12]} failed"}

    def check(self, job: ProviderJob) -> str | None:
        if job.kind == KIND_UPSCALE:
            # Keep the historical message — worker/tests match on it.
            return "UPSCALE_VIDEO is not supported by the assistant media provider"
        return super().check(job)

    def needs_media_id_registration(self) -> bool:
        # The assistant mints UUID media_ids itself (_image_result /
        # _video_result) — no upload-back step needed.
        return False

    async def register_existing_image(
        self, url: str, *, name: str = "", project_id: str = ""
    ) -> dict:
        """Mint a UUID media_id for an already-existing local image."""
        local = file_url_to_path(url)
        if local is None:
            local = Path(url)
        if not local.is_file():
            return {"error": f"AssistantProvider: local image not found for '{name}': {url}"}
        mid = str(uuid.uuid4())
        canonical = "file://" + str(local.resolve())
        logger.info("AssistantProvider: registered existing image '%s' → media_id=%s",
                    name, mid[:8])
        return {"data": {"media": [{"name": mid}], "url": canonical}}
