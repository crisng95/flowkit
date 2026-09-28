import asyncio
import json

import pytest

from agent.services import flow_batch as fb
from agent.services import flow_client as fc


@pytest.fixture
def opted_in(monkeypatch, tmp_path):
    monkeypatch.setattr(fc, "FLOW_ENABLE_CAPTCHA_GENERATION", True)
    monkeypatch.setattr(fc, "FLOW_GENERATION_SAFETY_FILE", tmp_path / "hold.json")


@pytest.mark.asyncio
async def test_generation_rpc_is_globally_serialized(monkeypatch, opted_in):
    monkeypatch.setattr(fc, "FLOW_GENERATION_MAX_CONCURRENT", 5)  # legacy override cannot bypass safety cap
    monkeypatch.setattr(fc, "FLOW_GENERATION_MIN_INTERVAL_S", 0.0)
    client = fc.FlowClient()
    active = 0
    max_active = 0

    async def fake_send(method, params, timeout=300):
        nonlocal active, max_active
        assert method == "batch_rpc"
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return {"status": 200, "data": "ok"}

    monkeypatch.setattr(client, "_send", fake_send)
    await asyncio.gather(
        client.batch_rpc("a", "x", captcha_action=fb.CAPTCHA_VIDEO),
        client.batch_rpc("b", "y", captcha_action=fb.CAPTCHA_IMAGE),
    )
    assert max_active == 1


@pytest.mark.asyncio
async def test_unusual_activity_persists_a_safety_hold(monkeypatch, opted_in):
    monkeypatch.setattr(fc, "FLOW_GENERATION_MAX_CONCURRENT", 1)
    monkeypatch.setattr(fc, "FLOW_GENERATION_MIN_INTERVAL_S", 0.0)
    monkeypatch.setattr(fc, "FLOW_UNUSUAL_ACTIVITY_COOLDOWN_S", 120.0)
    client = fc.FlowClient()
    already_running_peer = fc.FlowClient()
    calls = 0

    async def fake_send(method, params, timeout=300):
        nonlocal calls
        calls += 1
        return {
            "status": 200,
            "data": "PUBLIC_ERROR_UNUSUAL_ACTIVITY reCAPTCHA evaluation failed",
        }

    monkeypatch.setattr(client, "_send", fake_send)
    first = await client.batch_rpc("a", "x", captcha_action=fb.CAPTCHA_VIDEO)
    client._generation_unusual_until = 0.0  # timer expiry must not re-open the path
    second = await client.batch_rpc("b", "y", captcha_action=fb.CAPTCHA_VIDEO)
    peer_result = await already_running_peer.batch_rpc("peer", "z", captcha_action=fb.CAPTCHA_VIDEO)
    restarted = fc.FlowClient()
    third = await restarted.batch_rpc("c", "z", captcha_action=fb.CAPTCHA_VIDEO)

    assert first["status"] == 200
    assert second["status"] == 423
    assert peer_result["status"] == 423
    assert third["status"] == 423
    assert "FLOW_ACCOUNT_SAFETY_HOLD" in second["error"]
    assert calls == 1
    assert client.generation_guard_status["safety_hold_active"] is True
    assert client.generation_guard_status["last_unusual_activity_rpc"] == "a"
    assert json.loads(fc.FLOW_GENERATION_SAFETY_FILE.read_text())["reason"] == "PUBLIC_ERROR_UNUSUAL_ACTIVITY"


@pytest.mark.asyncio
async def test_default_off_sends_no_captcha_request(monkeypatch, tmp_path):
    monkeypatch.setattr(fc, "FLOW_ENABLE_CAPTCHA_GENERATION", False)
    monkeypatch.setattr(fc, "FLOW_GENERATION_SAFETY_FILE", tmp_path / "hold.json")
    client = fc.FlowClient()

    async def should_not_send(*_args, **_kwargs):
        raise AssertionError("No CAPTCHA request should reach the extension")

    monkeypatch.setattr(client, "_send", should_not_send)
    result = await client.batch_rpc("image", "x", captcha_action=fb.CAPTCHA_IMAGE)
    assert result["status"] == 423
    assert "FLOW_CAPTCHA_GENERATION_DISABLED" in result["error"]


@pytest.mark.asyncio
async def test_hijack_signal_persists_a_safety_hold(monkeypatch, opted_in):
    client = fc.FlowClient()

    async def fake_send(*_args, **_kwargs):
        return {"status": 403, "error": "[HIJACK] extension_hijack_detected"}

    monkeypatch.setattr(client, "_send", fake_send)
    await client.batch_rpc("video", "x", captcha_action=fb.CAPTCHA_VIDEO)
    assert client.generation_guard_status["safety_hold_reason"] == "extension_hijack_detected"
    assert fc.FlowClient().generation_guard_status["safety_hold_active"] is True


@pytest.mark.asyncio
async def test_unreadable_safety_state_fails_closed(monkeypatch, opted_in):
    fc.FLOW_GENERATION_SAFETY_FILE.write_text("{not json", encoding="utf-8")
    client = fc.FlowClient()

    async def should_not_send(*_args, **_kwargs):
        raise AssertionError("Corrupt safety state must not permit generation")

    monkeypatch.setattr(client, "_send", should_not_send)
    result = await client.batch_rpc("image", "x", captcha_action=fb.CAPTCHA_IMAGE)
    assert result["status"] == 423
    assert client.generation_guard_status["safety_hold_reason"] == "unreadable_safety_state"


@pytest.mark.asyncio
async def test_generation_rpc_without_action_never_reaches_extension(monkeypatch, opted_in):
    client = fc.FlowClient()

    async def should_not_send(*_args, **_kwargs):
        raise AssertionError("Missing CAPTCHA action must fail before extension")

    monkeypatch.setattr(client, "_send", should_not_send)
    result = await client.batch_rpc(fb.RPC_UPLOAD_IMAGE, "already-filled")
    assert result == {"status": 400, "error": "CAPTCHA_ACTION_REQUIRED: generation RPC has no CAPTCHA action"}


@pytest.mark.asyncio
async def test_pre_submit_marker_write_failure_sends_nothing(monkeypatch, opted_in):
    client = fc.FlowClient()
    original_open = fc.Path.open

    def fail_safety_write(path, *args, **kwargs):
        if path == fc.FLOW_GENERATION_SAFETY_FILE and args and args[0] == "x":
            raise OSError("simulated unwritable safety state")
        return original_open(path, *args, **kwargs)

    async def should_not_send(*_args, **_kwargs):
        raise AssertionError("No token request may be sent without a durable marker")

    monkeypatch.setattr(fc.Path, "open", fail_safety_write)
    monkeypatch.setattr(client, "_send", should_not_send)
    result = await client.batch_rpc("image", "x", captcha_action=fb.CAPTCHA_IMAGE)
    assert result["status"] == 423
    assert client.generation_guard_status["safety_hold_reason"] == "safety_state_unwritable"


@pytest.mark.asyncio
async def test_failed_hold_write_leaves_inflight_marker_for_restart(monkeypatch, opted_in):
    client = fc.FlowClient()
    original_replace = fc.Path.replace

    def fail_hold_replace(path, target):
        if path.name.endswith(".tmp"):
            raise OSError("simulated failed hold write")
        return original_replace(path, target)

    async def fake_send(*_args, **_kwargs):
        return {"status": 403, "error": "PUBLIC_ERROR_UNUSUAL_ACTIVITY"}

    monkeypatch.setattr(fc.Path, "replace", fail_hold_replace)
    monkeypatch.setattr(client, "_send", fake_send)
    await client.batch_rpc("image", "x", captcha_action=fb.CAPTCHA_IMAGE)
    record = json.loads(fc.FLOW_GENERATION_SAFETY_FILE.read_text())
    assert record["state"] == "inflight"
    assert fc.FlowClient().generation_guard_status["safety_hold_reason"] == "interrupted_generation"


@pytest.mark.asyncio
async def test_hold_latched_during_pacing_wait_prevents_dispatch(monkeypatch, opted_in):
    monkeypatch.setattr(fc, "FLOW_GENERATION_MIN_INTERVAL_S", 3.0)
    client = fc.FlowClient()
    client._generation_last_submit_at = asyncio.get_running_loop().time()

    async def latch_during_wait(_seconds):
        fc.FlowClient()._latch_generation_safety("extension_hijack_detected", "other")

    async def should_not_send(*_args, **_kwargs):
        raise AssertionError("Hold latched during pacing must stop dispatch")

    monkeypatch.setattr(fc.asyncio, "sleep", latch_during_wait)
    monkeypatch.setattr(client, "_send", should_not_send)
    result = await client.batch_rpc("image", "x", captcha_action=fb.CAPTCHA_IMAGE)
    assert result["status"] == 423


@pytest.mark.asyncio
async def test_generic_captcha_error_latches_before_another_request(monkeypatch, opted_in):
    client = fc.FlowClient()
    calls = 0

    async def fake_send(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return {"status": 403, "error": "CAPTCHA_FAILED: no token"}

    monkeypatch.setattr(client, "_send", fake_send)
    first = await client.batch_rpc("image", "x", captcha_action=fb.CAPTCHA_IMAGE)
    second = await client.batch_rpc("image", "y", captcha_action=fb.CAPTCHA_IMAGE)
    assert first["status"] == 403
    assert "FLOW_ACCOUNT_SAFETY_HOLD" in first["error"]
    assert second["status"] == 423
    assert calls == 1


@pytest.mark.asyncio
async def test_non_generation_rpc_bypasses_generation_guard(monkeypatch):
    client = fc.FlowClient()
    client._generation_unusual_until = asyncio.get_running_loop().time() + 60
    calls = 0

    async def fake_send(method, params, timeout=300):
        nonlocal calls
        calls += 1
        return {"status": 200, "data": "metadata"}

    monkeypatch.setattr(client, "_send", fake_send)
    result = await client.batch_rpc("meta", "x")
    assert result["status"] == 200
    assert calls == 1
