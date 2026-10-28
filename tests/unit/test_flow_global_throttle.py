import asyncio

import pytest

from agent.services import flow_batch as fb
from agent.services import flow_client as fc


@pytest.mark.asyncio
async def test_generation_rpc_is_globally_serialized(monkeypatch):
    monkeypatch.setattr(fc, "FLOW_GENERATION_MAX_CONCURRENT", 1)
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
async def test_unusual_activity_opens_local_circuit_breaker(monkeypatch):
    monkeypatch.setattr(fc, "FLOW_GENERATION_MAX_CONCURRENT", 1)
    monkeypatch.setattr(fc, "FLOW_GENERATION_MIN_INTERVAL_S", 0.0)
    monkeypatch.setattr(fc, "FLOW_UNUSUAL_ACTIVITY_COOLDOWN_S", 120.0)
    client = fc.FlowClient()
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
    second = await client.batch_rpc("b", "y", captcha_action=fb.CAPTCHA_VIDEO)

    assert first["status"] == 200
    assert second["status"] == 429
    assert "local cooldown active" in second["error"]
    assert calls == 1
    assert client.generation_guard_status["cooldown_active"] is True
    assert client.generation_guard_status["last_unusual_activity_rpc"] == "a"


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


async def _unusual(client, monkeypatch):
    async def fake_send(method, params, timeout=300):
        return {"status": 200, "data": "PUBLIC_ERROR_UNUSUAL_ACTIVITY"}

    monkeypatch.setattr(client, "_send", fake_send)
    await client.batch_rpc("a", "x", captcha_action=fb.CAPTCHA_IMAGE)


@pytest.mark.asyncio
async def test_unusual_activity_hold_survives_a_restart(monkeypatch, _generation_hold_path):
    monkeypatch.setattr(fc, "FLOW_GENERATION_MIN_INTERVAL_S", 0.0)
    monkeypatch.setattr(fc, "FLOW_UNUSUAL_ACTIVITY_COOLDOWN_S", 3600.0)
    await _unusual(fc.FlowClient(), monkeypatch)
    assert _generation_hold_path.exists()

    restarted = fc.FlowClient()
    calls = 0

    async def fake_send(method, params, timeout=300):
        nonlocal calls
        calls += 1
        return {"status": 200, "data": "ok"}

    monkeypatch.setattr(restarted, "_send", fake_send)
    result = await restarted.batch_rpc("b", "y", captcha_action=fb.CAPTCHA_VIDEO)
    assert result["status"] == 429 and calls == 0
    status = restarted.generation_guard_status
    assert status["cooldown_reason"] == "unusual_activity"
    assert 3590 < status["cooldown_remaining_s"] <= 3600


def test_expired_or_unreadable_hold_is_ignored(_generation_hold_path):
    _generation_hold_path.write_text('{"until": 1, "reason": "unusual_activity"}')
    assert fc.FlowClient().generation_guard_status["cooldown_active"] is False
    _generation_hold_path.write_text("not json")
    assert fc.FlowClient().generation_guard_status["cooldown_active"] is False


@pytest.mark.asyncio
async def test_clear_lifts_the_hold_and_its_file(monkeypatch, _generation_hold_path):
    monkeypatch.setattr(fc, "FLOW_GENERATION_MIN_INTERVAL_S", 0.0)
    client = fc.FlowClient()
    await _unusual(client, monkeypatch)
    assert client.clear_generation_hold() is True
    assert not _generation_hold_path.exists()
    assert fc.FlowClient().generation_guard_status["cooldown_active"] is False
    assert client.clear_generation_hold() is False


@pytest.mark.asyncio
async def test_hijack_sets_a_short_hold(monkeypatch, _generation_hold_path):
    monkeypatch.setattr(fc, "FLOW_GENERATION_MIN_INTERVAL_S", 0.0)
    client = fc.FlowClient()

    async def fake_send(method, params, timeout=300):
        return {"status": 200, "error": "extension_hijack_detected"}

    monkeypatch.setattr(client, "_send", fake_send)
    result = await client.batch_rpc("a", "x", captcha_action=fb.CAPTCHA_IMAGE)
    assert result["error"].startswith("[HIJACK]")
    status = client.generation_guard_status
    assert status["cooldown_reason"] == "extension_hijack_detected"
    assert 0 < status["cooldown_remaining_s"] <= 30


@pytest.mark.asyncio
async def test_a_shorter_hold_keeps_the_longer_one_and_its_reason(monkeypatch, _generation_hold_path):
    monkeypatch.setattr(fc, "FLOW_GENERATION_MIN_INTERVAL_S", 0.0)
    monkeypatch.setattr(fc, "FLOW_UNUSUAL_ACTIVITY_COOLDOWN_S", 3600.0)
    client = fc.FlowClient()
    await _unusual(client, monkeypatch)
    client._set_generation_hold(30.0, "extension_hijack_detected", "b")
    status = client.generation_guard_status
    assert status["cooldown_reason"] == "unusual_activity"
    assert status["cooldown_remaining_s"] > 3590
    assert fc.FlowClient().generation_guard_status["cooldown_reason"] == "unusual_activity"


@pytest.mark.asyncio
async def test_stream_chat_is_held_like_generation(monkeypatch):
    monkeypatch.setattr(fc, "FLOW_GENERATION_MIN_INTERVAL_S", 0.0)
    monkeypatch.setattr(fc, "FLOW_PROJECT_ID", "p")
    client = fc.FlowClient()
    await _unusual(client, monkeypatch)
    calls = 0

    async def fake_send(method, params, timeout=300):
        nonlocal calls
        calls += 1
        return {"status": 200, "data": "ok"}

    monkeypatch.setattr(client, "_send", fake_send)
    monkeypatch.setattr(client, "_batch_project_id", lambda pid: "p")
    result = await client.stream_chat("hello")
    assert result["status"] == 429 and calls == 0


def test_operation_caches_evict_oldest_first(monkeypatch):
    monkeypatch.setattr(fc, "OPERATION_CACHE_MAX", 3)
    client = fc.FlowClient()
    for i in range(5):
        client._remember_operation(f"op{i}", "p")
    assert list(client._operation_projects) == ["op2", "op3", "op4"]
    client._remember_operation("op2", "p")  # touched again: now newest
    client._remember_operation("op5", "p")
    assert list(client._operation_projects) == ["op4", "op2", "op5"]
