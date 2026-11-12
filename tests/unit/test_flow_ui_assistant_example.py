"""Cover the example's handoff from the existing assistant producer."""
from argparse import Namespace
import asyncio
import json
from pathlib import Path

import pytest

from agent.db import crud
from agent.sdk.services.assistant_provider import AssistantProvider
from agent.sdk.services.provider_base import KIND_VIDEO, ProviderJob
from examples.flow_ui_assistant import worker


async def test_example_reads_an_assistant_video_job(test_db):
    config = json.loads((Path(__file__).resolve().parents[2]
                         / "examples/flow_ui_assistant/config.example.json").read_text(encoding="utf-8"))
    first, last = config["assets"]
    provider = AssistantProvider()
    provider.timeout_s, provider.poll_s = 3, 0.01
    generation = asyncio.create_task(provider.run(ProviderJob(
        job_id="flow-ui-example",
        kind=KIND_VIDEO,
        prompt="Turn towards camera.",
        start_url="file:///tmp/first.png",
        end_url="file:///tmp/last.png",
        extra={"project_id": config["project_id"], "model_family": "omni_flash",
               "start_media_id": first, "end_media_id": last, "duration_s": 4},
    )))
    try:
        for _ in range(100):
            row = await crud.get_provider_job("flow-ui-example")
            if row:
                break
            await asyncio.sleep(0.01)
        assert row is not None
        row = {**row, "extra": json.loads(row["extra"])}  # HTTP queue serialization
        prepared = worker.browser_job(row, config)
        assert (prepared["extra"]["start_asset"], prepared["extra"]["end_asset"]) == (
            "first-frame.png", "last-frame.png")
        with pytest.raises(ValueError, match="both scene frame URLs"):
            worker.browser_job({**row, "end_url": None}, config)
        await crud.claim_provider_job(row["id"], "example-test")
        await crud.complete_provider_job(row["id"], "example-test", {"output_url": "file:///tmp/test.mp4"})
        result = await generation
        assert result["data"]["operations"][0]["operation"]["metadata"]["video"]["fifeUrl"] == "file:///tmp/test.mp4"
    finally:
        if not generation.done():
            generation.cancel()
            await asyncio.gather(generation, return_exceptions=True)


def test_submit_intent_is_one_shot_even_if_progress_request_fails(tmp_path, monkeypatch):
    lease = tmp_path / "job.json"
    lease.write_text(json.dumps({"worker_id": "owned", "job": {}}), encoding="utf-8")
    called = []

    def queue_call(_api, path, body=None):
        if path == "job":
            return {"status": "CLAIMED", "claimed_by": "owned", "retry_count": 1, "progress": 0}
        called.append((path, body))
        raise OSError("progress request outcome unknown")

    monkeypatch.setattr(worker, "queue_call", queue_call)
    args = Namespace(api="", state_dir=tmp_path, action="mark-submit", job_id="job")
    with pytest.raises(OSError, match="outcome unknown"):
        worker.run(args)
    with pytest.raises(FileExistsError):
        worker.run(args)
    assert len(called) == 1
