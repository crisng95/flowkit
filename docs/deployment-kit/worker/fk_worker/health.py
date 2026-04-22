"""Very small HTTP health server for the lane-runner."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread

from .config import settings
from .state import RunnerStateStore


class _HealthHandler(BaseHTTPRequestHandler):
    state_store: RunnerStateStore | None = None

    def do_GET(self):  # noqa: N802
        if self.path not in ("/health", "/ready"):
            self.send_response(404)
            self.end_headers()
            return

        state = self.state_store.snapshot() if self.state_store else {}
        ready = bool(state.get("api_reachable")) and state.get("status") != "starting"
        if self.path == "/ready" and not ready:
            self.send_response(503)
        else:
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(state).encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A003
        return


def start_health_server(state_store: RunnerStateStore) -> Thread:
    _HealthHandler.state_store = state_store
    server = ThreadingHTTPServer((settings.runner_health_host, settings.runner_health_port), _HealthHandler)
    thread = Thread(target=server.serve_forever, name=f"{settings.lane_id}-health", daemon=True)
    thread.start()
    return thread
