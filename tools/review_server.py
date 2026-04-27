"""Mini server for Scene Review Board.

Serves:
  - /                  -> review_board.html
  - /api/feedback      -> GET/POST feedback JSON (persisted to disk)
  - /videos/<file>     -> local scene videos
  - /api/scenes        -> proxy to main API (fresh scene data)
"""

import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import urllib.request

API_BASE = "http://127.0.0.1:8100"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8200

TOOLS_DIR = Path(__file__).parent
PROJECT_ROOT = TOOLS_DIR.parent
REVIEW_DIR = PROJECT_ROOT / "output"

FEEDBACK_FILE = TOOLS_DIR / "review_feedback.json"


def _resolve_video_dir():
    """Resolve the per-request video dir from the active project.

    Priority within the active project's output folder:
      1. review_full/ (if exists and has scene_*.mp4)
      2. raw/        (fallback for projects that haven't built review_full)
      3. None        (no videos to serve)
    """
    try:
        with urllib.request.urlopen(f"{API_BASE}/api/active-project", timeout=5) as r:
            active = json.loads(r.read())
        pid = active.get("project_id")
        if not pid:
            return None
        with urllib.request.urlopen(f"{API_BASE}/api/projects/{pid}/output-dir", timeout=5) as r:
            out = json.loads(r.read())
        out_path = out.get("path")
        if not out_path:
            return None
        proj_dir = (PROJECT_ROOT / out_path).resolve()
        for sub in ("review_full", "raw"):
            d = proj_dir / sub
            if d.exists() and any(d.glob("scene_*.mp4")):
                return d
    except Exception:
        return None
    return None


class ReviewHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Serve the HTML board
        if path in ("/", "/index.html", "/review_board.html"):
            self._serve_file(TOOLS_DIR / "review_board.html", "text/html")
            return

        # Serve local videos
        if path.startswith("/videos/"):
            fname = path[len("/videos/"):]
            vdir = _resolve_video_dir()
            if vdir:
                fpath = vdir / fname
                if fpath.exists():
                    self._serve_file(fpath, "video/mp4")
                    return
            self.send_error(404, f"Video not found: {fname}")
            return

        # Feedback GET
        if path == "/api/feedback":
            data = {}
            if FEEDBACK_FILE.exists():
                data = json.loads(FEEDBACK_FILE.read_text())
            self._json_response(data)
            return

        # Proxy scenes from main API
        if path == "/api/scenes":
            qs = parsed.query
            try:
                url = f"{API_BASE}/api/scenes?{qs}"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    body = resp.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_error(502, f"API proxy error: {e}")
            return

        # Video dir listing (for mapping scene_id -> file)
        if path == "/api/video-files":
            vdir = _resolve_video_dir()
            files = []
            if vdir:
                files = sorted(f.name for f in vdir.glob("scene_*.mp4"))
            self._json_response({"dir": str(vdir) if vdir else None, "files": files})
            return

        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/feedback":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                FEEDBACK_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
                self._json_response({"ok": True, "saved": str(FEEDBACK_FILE)})
            except Exception as e:
                self.send_error(400, str(e))
            return

        self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json_response(self, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, fpath, content_type):
        try:
            data = fpath.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(data))
            self.send_header("Access-Control-Allow-Origin", "*")
            if content_type == "video/mp4":
                self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, format, *args):
        # Quieter logging
        if "/api/feedback" in str(args) or "/videos/" in str(args):
            return
        super().log_message(format, *args)


if __name__ == "__main__":
    print(f"Review Board Server")
    print(f"  Board:    http://localhost:{PORT}")
    print(f"  API:      {API_BASE}")
    print(f"  Videos:   {_resolve_video_dir() or 'NOT FOUND (will resolve per-request from active project)'}")
    print(f"  Feedback: {FEEDBACK_FILE}")
    server = HTTPServer(("127.0.0.1", PORT), ReviewHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
