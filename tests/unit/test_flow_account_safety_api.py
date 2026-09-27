"""A legacy cooldown reset must not reopen CAPTCHA generation after a safety signal."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from agent.api import flow as flow_api


@pytest.mark.asyncio
async def test_clear_hijack_cannot_clear_account_safety_hold(monkeypatch):
    client = SimpleNamespace(generation_guard_status={"safety_hold_active": True})
    monkeypatch.setattr(flow_api, "get_flow_client", lambda: client)

    with pytest.raises(HTTPException) as exc:
        await flow_api.clear_hijack_cooldown()

    assert exc.value.status_code == 409
    assert "FLOW_ACCOUNT_SAFETY_HOLD" in exc.value.detail
