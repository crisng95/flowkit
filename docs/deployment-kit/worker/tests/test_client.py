import httpx
import pytest

from fk_worker.client import FlowKitClient


def test_client_raises_useful_error_on_http_failure():
    def handler(request):
        return httpx.Response(503, json={"detail": "Extension not connected"})

    client = FlowKitClient(base_url="http://test")
    client._client = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))

    with pytest.raises(RuntimeError, match="Extension not connected"):
        client.create_project({"name": "Demo"})
