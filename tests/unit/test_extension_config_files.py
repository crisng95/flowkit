import json
from pathlib import Path


def test_extension_manifest_has_default_flowkit_config():
    manifest_path = Path(__file__).resolve().parents[2] / "extension" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["flowkit"]["agent_ws_url"] == "ws://127.0.0.1:9222"
    assert manifest["flowkit"]["callback_base_url"] == "http://127.0.0.1:8100"


def test_background_reads_flowkit_config_from_manifest():
    background_path = Path(__file__).resolve().parents[2] / "extension" / "background.js"
    background_source = background_path.read_text(encoding="utf-8")

    assert "chrome.runtime.getManifest()" in background_source
    assert "callback_base_url" in background_source
    assert "agent_ws_url" in background_source
