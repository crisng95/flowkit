"""Offline regressions for persistent review sheet directory setup."""

import pytest

from agent.services import video_reviewer


@pytest.mark.asyncio
async def test_failed_video_fetch_does_not_leave_empty_scene_directory(tmp_path, monkeypatch):
    async def no_video(*args, **kwargs):
        raise ValueError("No source video")

    monkeypatch.setattr(video_reviewer, "_fetch_scene_video", no_video)
    with pytest.raises(ValueError, match="No source video"):
        await video_reviewer.prepare_review_sheets(
            {"id": "missing-scene"}, [], "light", "VERTICAL", tmp_path
        )

    assert not (tmp_path / "missing-scene").exists()
