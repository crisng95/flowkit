import pytest
from fastapi import HTTPException

from agent.api import flow as flow_api


class _StubClient:
    def __init__(self, connected=True, result=None):
        self.connected = connected
        self._result = result or {}

    async def get_credits(self):
        return self._result


@pytest.mark.asyncio
async def test_get_credits_returns_data_even_with_top_level_error(monkeypatch):
    stub = _StubClient(result={
        "error": "UPSTREAM_WARN",
        "data": {
            "userPaygateTier": "PAYGATE_TIER_ONE",
            "remainingCredits": 123,
        },
    })
    monkeypatch.setattr(flow_api, "get_flow_client", lambda: stub)

    result = await flow_api.get_credits()

    assert result["userPaygateTier"] == "PAYGATE_TIER_ONE"
    assert result["remainingCredits"] == 123


@pytest.mark.asyncio
async def test_get_credits_raises_when_only_error_exists(monkeypatch):
    stub = _StubClient(result={"error": "UPSTREAM_FAILED"})
    monkeypatch.setattr(flow_api, "get_flow_client", lambda: stub)

    with pytest.raises(HTTPException) as exc:
        await flow_api.get_credits()

    assert exc.value.status_code == 502
    assert exc.value.detail == "UPSTREAM_FAILED"
