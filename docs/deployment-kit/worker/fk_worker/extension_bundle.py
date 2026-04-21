"""Helpers for rendering lane-specific Chrome extension bundles."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil


@dataclass(frozen=True)
class LanePorts:
    api_port: int
    ws_port: int
    health_port: int


def _lane_number(lane_id: str) -> int:
    match = re.fullmatch(r"lane-(\d+)", lane_id)
    if not match:
        raise ValueError(f"Unsupported lane id: {lane_id}")
    return int(match.group(1))


def demo_ports_for_lane(lane_id: str) -> LanePorts:
    lane_number = _lane_number(lane_id)
    offset = lane_number - 1
    return LanePorts(
        api_port=8100 + (offset * 10),
        ws_port=9222 + (offset * 10),
        health_port=18180 + lane_number,
    )


def _host_permissions_with_callback(manifest: dict, callback_base_url: str) -> list[str]:
    callback_permission = f"{callback_base_url}/*"
    existing = manifest.get("host_permissions", [])
    preserved = [
        permission
        for permission in existing
        if not re.fullmatch(r"http://127\.0\.0\.1:\d+/\*", permission)
    ]
    if callback_permission not in preserved:
        preserved.append(callback_permission)
    return preserved


def render_extension_bundle(
    source_dir: Path,
    output_dir: Path,
    lane_id: str,
    api_host: str,
    api_port: int,
    ws_host: str,
    ws_port: int,
) -> dict[str, str]:
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)
    manifest_path = source_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Extension manifest not found: {manifest_path}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(source_dir, output_dir)

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    callback_base_url = f"http://{api_host}:{api_port}"
    flowkit = {
        **manifest.get("flowkit", {}),
        "agent_ws_url": f"ws://{ws_host}:{ws_port}",
        "callback_base_url": callback_base_url,
    }

    manifest["name"] = f"{manifest.get('name', 'Flow Kit')} ({lane_id})"
    manifest["flowkit"] = flowkit
    manifest["host_permissions"] = _host_permissions_with_callback(manifest, callback_base_url)

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "lane_id": lane_id,
        "output_dir": str(output_dir),
        "agent_ws_url": flowkit["agent_ws_url"],
        "callback_base_url": flowkit["callback_base_url"],
    }
