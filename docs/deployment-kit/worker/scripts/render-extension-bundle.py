#!/usr/bin/env python3
"""Render a lane-specific unpacked extension copy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
WORKER_ROOT = SCRIPT_DIR.parent
REPO_ROOT = WORKER_ROOT.parents[2]
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from fk_worker.extension_bundle import demo_ports_for_lane, render_extension_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane-id", required=True, help="Lane id, for example lane-02")
    parser.add_argument(
        "--source-dir",
        default=str(REPO_ROOT / "extension"),
        help="Source unpacked extension directory",
    )
    parser.add_argument("--output-dir", required=True, help="Rendered unpacked extension directory")
    parser.add_argument("--api-host", default="127.0.0.1", help="HTTP callback host")
    parser.add_argument("--ws-host", default="127.0.0.1", help="WebSocket host")
    parser.add_argument("--api-port", type=int, help="HTTP callback port")
    parser.add_argument("--ws-port", type=int, help="WebSocket port")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ports = demo_ports_for_lane(args.lane_id)
    result = render_extension_bundle(
        source_dir=Path(args.source_dir),
        output_dir=Path(args.output_dir),
        lane_id=args.lane_id,
        api_host=args.api_host,
        api_port=args.api_port or ports.api_port,
        ws_host=args.ws_host,
        ws_port=args.ws_port or ports.ws_port,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
