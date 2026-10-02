"""The worker must honour a project's video_model_family.

Before this, the queue path (GENERATE_VIDEO -> FlowProvider._run_video) was
hardwired to Veo; Omni Flash existed only on the ad-hoc /api/flow/generate-video
endpoint, which does not write results back to the scene. A project that
chooses Omni Flash (720p, cheaper, and the only family with r2v / first+last
on the batch transport) must get it through the normal pipeline so review,
concat and retry-repoll keep working unchanged.
"""
from unittest.mock import AsyncMock, patch

import pytest

from agent.sdk.services.flow_provider import FlowProvider
from agent.sdk.services.provider_base import KIND_VIDEO, ProviderJob


def _job(**extra):
    base = {"project_id": "p1", "tier": "PAYGATE_TIER_TWO", "aspect": "VIDEO_ASPECT_RATIO_LANDSCAPE",
            "scene_id": "s1", "start_media_id": "img-1", "end_media_id": None, "request_id": ""}
    base.update(extra)
    return ProviderJob(job_id="j", kind=KIND_VIDEO, prompt="walk", orientation="HORIZONTAL", extra=base)


@pytest.mark.asyncio
async def test_omni_flash_family_routes_to_omni_first_frame():
    client = AsyncMock()
    client.generate_video = AsyncMock()
    submitted = {"data": {"operations": [{"operation": {"name": "op-omni"},
                                          "status": "MEDIA_GENERATION_STATUS_PENDING"}]}}
    with patch("agent.sdk.services.flow_provider.generate_omni_flash_first_frame_video",
               new=AsyncMock(return_value=submitted)) as omni, \
         patch("agent.sdk.services.flow_provider._poll_operations",
               new=AsyncMock(return_value={"data": {"ok": 1}})) as poll:
        result = await FlowProvider(client)._run_video(_job(model_family="omni_flash"))

    client.generate_video.assert_not_called()
    kw = omni.await_args.kwargs
    assert kw["start_image_media_id"] == "img-1"
    assert kw["aspect_ratio"] == "VIDEO_ASPECT_RATIO_LANDSCAPE"
    assert kw["duration_s"] == 8 and kw["resolution"] == "720p"
    assert poll.await_args.args[1][0]["operation"]["name"] == "op-omni"
    assert result == {"data": {"ok": 1}}


@pytest.mark.asyncio
async def test_omni_flash_with_end_frame_uses_first_last():
    client = AsyncMock()
    submitted = {"data": {"operations": [{"operation": {"name": "op-fl"},
                                          "status": "MEDIA_GENERATION_STATUS_PENDING"}]}}
    with patch("agent.sdk.services.flow_provider.generate_omni_flash_first_last_video",
               new=AsyncMock(return_value=submitted)) as fl, \
         patch("agent.sdk.services.flow_provider._poll_operations",
               new=AsyncMock(return_value={"data": {}})):
        await FlowProvider(client)._run_video(_job(model_family="omni_flash", end_media_id="img-2"))
    assert fl.await_args.kwargs["end_image_media_id"] == "img-2"


@pytest.mark.asyncio
async def test_default_family_is_still_veo():
    client = AsyncMock()
    client.generate_video = AsyncMock(
        return_value={"data": {"operations": [{"operation": {"name": "op-veo"}}]}})
    with patch("agent.sdk.services.flow_provider._poll_operations",
               new=AsyncMock(return_value={"data": {}})):
        await FlowProvider(client)._run_video(_job())
    client.generate_video.assert_called_once()


@pytest.mark.asyncio
async def test_generate_scene_video_passes_project_family():
    """operations.generate_scene_video reads the project's family into job.extra."""
    from agent.sdk.services.operations import OperationService

    captured = {}

    async def fake_run(self, job, provider=None):
        captured.update(job.extra)
        return {"data": {}}

    scene = {"id": "s1", "_project_id": "p1", "horizontal_image_media_id": "img-1",
             "horizontal_image_url": "file:///x.png", "video_prompt": "walk", "display_order": 1}
    with patch("agent.sdk.services.operations.crud") as crud, \
         patch("agent.sdk.services.operations._build_video_prompt", new=AsyncMock(return_value="p")), \
         patch.object(OperationService, "_run_provider_job", fake_run), \
         patch.object(OperationService, "_resolve_chain_end_url", new=AsyncMock(return_value=None)):
        crud.get_project = AsyncMock(return_value={"user_paygate_tier": "PAYGATE_TIER_TWO",
                                                   "video_model_family": "omni_flash"})
        await OperationService.__new__(OperationService).generate_scene_video(scene, "HORIZONTAL")
    assert captured["model_family"] == "omni_flash"


@pytest.mark.asyncio
async def test_project_update_persists_video_model_family(test_db):
    """crud._update whitelists columns; the new one must be allowed or PATCH is a silent no-op."""
    from agent.db import crud

    p = await crud.create_project("x")
    assert p["video_model_family"] == "veo"
    row = await crud._update("project", "id", p["id"], video_model_family="omni_flash")
    assert row["video_model_family"] == "omni_flash"


def test_flow_provider_rate_limits_come_from_env(monkeypatch):
    """A session that fires generates every 10s trips Flow's UNUSUAL_ACTIVITY guard;
    operators must be able to slow the worker without editing code."""
    import importlib
    from agent import config
    monkeypatch.setenv("FLOW_MAX_CONCURRENT", "1")
    monkeypatch.setenv("FLOW_COOLDOWN_S", "45")
    importlib.reload(config)
    import agent.sdk.services.flow_provider as fp
    importlib.reload(fp)
    try:
        assert fp.FlowProvider.capabilities.max_concurrent == 1
        assert fp.FlowProvider.capabilities.cooldown_s == 45.0
    finally:
        monkeypatch.delenv("FLOW_MAX_CONCURRENT"); monkeypatch.delenv("FLOW_COOLDOWN_S")
        importlib.reload(config); importlib.reload(fp)


@pytest.mark.asyncio
async def test_generate_scene_video_passes_scene_duration_for_omni():
    """scene.duration (seconds) must reach the Omni Flash call so a scene whose
    narration outruns the 8s default can be rendered at 10s instead of being
    padded with a frozen last frame in post."""
    from agent.sdk.services.operations import OperationService

    captured = {}

    async def fake_run(self, job, provider=None):
        captured.update(job.extra)
        return {"data": {}}

    scene = {"id": "s1", "_project_id": "p1", "horizontal_image_media_id": "img-1",
             "horizontal_image_url": "file:///x.png", "video_prompt": "walk", "display_order": 1,
             "duration": 10}
    with patch("agent.sdk.services.operations.crud") as crud, \
         patch("agent.sdk.services.operations._build_video_prompt", new=AsyncMock(return_value="p")), \
         patch.object(OperationService, "_run_provider_job", fake_run), \
         patch.object(OperationService, "_resolve_chain_end_url", new=AsyncMock(return_value=None)):
        crud.get_project = AsyncMock(return_value={"user_paygate_tier": "PAYGATE_TIER_TWO",
                                                   "video_model_family": "omni_flash"})
        await OperationService.__new__(OperationService).generate_scene_video(scene, "HORIZONTAL")
    assert captured["duration_s"] == 10


@pytest.mark.asyncio
async def test_omni_flash_rounds_duration_up_to_supported_step():
    """Omni Flash only accepts 4/6/8/10s; a 8.8s request must become 10, never 8."""
    client = AsyncMock()
    submitted = {"data": {"operations": [{"operation": {"name": "op"}, "status": "MEDIA_GENERATION_STATUS_PENDING"}]}}
    with patch("agent.sdk.services.flow_provider.generate_omni_flash_first_frame_video",
               new=AsyncMock(return_value=submitted)) as omni, \
         patch("agent.sdk.services.flow_provider._poll_operations", new=AsyncMock(return_value={"data": {}})):
        await FlowProvider(client)._run_video(_job(model_family="omni_flash", duration_s=8.8))
    assert omni.await_args.kwargs["duration_s"] == 10
