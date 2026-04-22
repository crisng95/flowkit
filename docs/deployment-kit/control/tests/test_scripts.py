from pathlib import Path
import socket
import subprocess
import threading


def _wsl_path(path: Path) -> str:
    drive = path.drive.rstrip(":").lower()
    tail = path.as_posix().split(":", 1)[1]
    return f"/mnt/{drive}{tail}"


class _ResetServer:
    def __enter__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(("127.0.0.1", 0))
        self._socket.listen()
        self.port = self._socket.getsockname()[1]
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self

    def _serve(self):
        while self._running:
            try:
                conn, _ = self._socket.accept()
            except OSError:
                return
            conn.close()

    def __exit__(self, exc_type, exc, tb):
        self._running = False
        self._socket.close()
        self._thread.join(timeout=1)
        return False


def test_reset_control_state_script_help():
    script = Path(__file__).resolve().parents[1] / "scripts" / "reset-control-state.sh"

    result = subprocess.run(
        ["bash", _wsl_path(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "POSTGRES_CONTAINER" in result.stdout
    assert "REDIS_CONTAINER" in result.stdout


def test_clean_queue_history_script_help():
    script = Path(__file__).resolve().parents[1] / "scripts" / "clean-queue-history.sh"

    result = subprocess.run(
        ["bash", _wsl_path(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "INCLUDE_DEAD" in result.stdout
    assert "FORCE=0" in result.stdout


def test_create_demo_project_script_help():
    script = Path(__file__).resolve().parents[1] / "scripts" / "create-demo-project.sh"

    result = subprocess.run(
        ["bash", _wsl_path(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "CONTROL_API_URL" in result.stdout
    assert "CHAPTER_COUNT" in result.stdout


def test_start_control_api_script_help():
    script = Path(__file__).resolve().parents[1] / "scripts" / "start-control-api.sh"

    result = subprocess.run(
        ["bash", _wsl_path(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "CONTROL_API_PORT" in result.stdout
    assert "PYTHON_BIN" in result.stdout


def test_start_scheduler_script_help():
    script = Path(__file__).resolve().parents[1] / "scripts" / "start-scheduler.sh"

    result = subprocess.run(
        ["bash", _wsl_path(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "POSTGRES_DSN" in result.stdout
    assert "REDIS_URL" in result.stdout


def test_run_control_demo_script_help():
    script = Path(__file__).resolve().parents[1] / "scripts" / "run-control-demo.sh"

    result = subprocess.run(
        ["bash", _wsl_path(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "START_SERVICES" in result.stdout
    assert "RESET_STATE" in result.stdout
    assert "CONTROL_API_PID_FILE" in result.stdout
    assert "WAIT_FOR_ASSIGNMENTS" in result.stdout


def test_control_service_script_reports_stopped_status():
    script = Path(__file__).resolve().parents[1] / "scripts" / "control-service.sh"

    with subprocess.Popen(
        ["bash", "-lc", "true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ):
        result = subprocess.run(
            [
                "bash",
                "-lc",
                " ".join(
                    [
                        f"RUNTIME_ROOT='{_wsl_path(Path.cwd())}'",
                        "CONTROL_API_URL='http://127.0.0.1:9'",
                        f"'{_wsl_path(script)}'",
                        "status",
                    ]
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 0
    assert '"control_api_running": false' in result.stdout.lower()
    assert '"scheduler_running": false' in result.stdout.lower()


def test_control_service_script_status_handles_connection_reset():
    script = Path(__file__).resolve().parents[1] / "scripts" / "control-service.sh"

    with _ResetServer() as server:
        result = subprocess.run(
            [
                "bash",
                "-lc",
                " ".join(
                    [
                        f"RUNTIME_ROOT='{_wsl_path(Path.cwd())}'",
                        f"CONTROL_API_URL='http://127.0.0.1:{server.port}'",
                        f"'{_wsl_path(script)}'",
                        "status",
                    ]
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 0
    assert '"status": "unreachable"' in result.stdout.lower()


def test_control_service_script_health_handles_connection_reset():
    script = Path(__file__).resolve().parents[1] / "scripts" / "control-service.sh"

    with _ResetServer() as server:
        result = subprocess.run(
            [
                "bash",
                "-lc",
                " ".join(
                    [
                        f"CONTROL_API_URL='http://127.0.0.1:{server.port}'",
                        "WAIT_TIMEOUT_SECONDS='1'",
                        "POLL_INTERVAL_SECONDS='0.1'",
                        f"'{_wsl_path(script)}'",
                        "health",
                    ]
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 1
    assert '"status": "timeout"' in result.stdout.lower()


def test_control_compose_exposes_pythonpath_for_all_python_services():
    compose_file = Path(__file__).resolve().parents[1] / "docker-compose.control.yml"

    content = compose_file.read_text(encoding="utf-8")

    assert "PYTHONPATH: /srv/control" in content
