import pytest

from agent import main as agent_main


class _StubClient:
    def __init__(self, flow_key=None):
        self._flow_key = flow_key
        self.set_extension_calls = 0
        self.clear_extension_calls = 0

    def set_extension(self, websocket):
        self.set_extension_calls += 1

    def clear_extension(self):
        self.clear_extension_calls += 1

    async def handle_message(self, data):
        return None


class _FakeWebSocket:
    def __init__(self):
        self.remote_address = ("127.0.0.1", 12345)
        self.sent = []

    async def send(self, payload):
        self.sent.append(payload)

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


@pytest.mark.asyncio
async def test_ws_handler_seeds_known_flow_token(monkeypatch):
    stub = _StubClient(flow_key="ya29.test-token")
    ws = _FakeWebSocket()
    monkeypatch.setattr(agent_main, "get_flow_client", lambda: stub)
    monkeypatch.setattr(agent_main, "_CALLBACK_SECRET", "secret-123")

    await agent_main.ws_handler(ws)

    assert stub.set_extension_calls == 1
    assert stub.clear_extension_calls == 1
    assert len(ws.sent) == 2
    assert '"type": "callback_secret"' in ws.sent[0]
    assert '"secret": "secret-123"' in ws.sent[0]
    assert '"type": "seed_token"' in ws.sent[1]
    assert '"flowKey": "ya29.test-token"' in ws.sent[1]


@pytest.mark.asyncio
async def test_ws_handler_skips_seed_when_no_known_token(monkeypatch):
    stub = _StubClient(flow_key=None)
    ws = _FakeWebSocket()
    monkeypatch.setattr(agent_main, "get_flow_client", lambda: stub)
    monkeypatch.setattr(agent_main, "_CALLBACK_SECRET", "secret-123")

    await agent_main.ws_handler(ws)

    assert len(ws.sent) == 1
    assert '"type": "callback_secret"' in ws.sent[0]
