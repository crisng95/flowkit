import json
from pathlib import Path

from fk_worker.extension_bundle import demo_ports_for_lane, render_extension_bundle


def test_demo_ports_for_lane_02_match_same_vm_handoff():
    ports = demo_ports_for_lane("lane-02")

    assert ports.api_port == 8110
    assert ports.ws_port == 9232
    assert ports.health_port == 18182


def test_render_extension_bundle_writes_lane_specific_manifest(tmp_path):
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    source_dir.mkdir()
    (source_dir / "background.js").write_text("console.log('ok');", encoding="utf-8")
    (source_dir / "content.js").write_text("console.log('content');", encoding="utf-8")
    (source_dir / "manifest.json").write_text(
        json.dumps(
            {
                "manifest_version": 3,
                "name": "Flow Kit",
                "host_permissions": [
                    "https://labs.google/*",
                    "https://aisandbox-pa.googleapis.com/*",
                    "http://127.0.0.1:8100/*",
                ],
            }
        ),
        encoding="utf-8",
    )

    render_extension_bundle(
        source_dir=source_dir,
        output_dir=output_dir,
        lane_id="lane-02",
        api_host="127.0.0.1",
        api_port=8110,
        ws_host="127.0.0.1",
        ws_port=9232,
    )

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["name"] == "Flow Kit (lane-02)"
    assert manifest["flowkit"]["agent_ws_url"] == "ws://127.0.0.1:9232"
    assert manifest["flowkit"]["callback_base_url"] == "http://127.0.0.1:8110"
    assert "http://127.0.0.1:8110/*" in manifest["host_permissions"]
    assert "http://127.0.0.1:8100/*" not in manifest["host_permissions"]
