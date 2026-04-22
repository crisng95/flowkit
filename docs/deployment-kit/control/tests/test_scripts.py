from pathlib import Path
import subprocess


def _wsl_path(path: Path) -> str:
    drive = path.drive.rstrip(":").lower()
    tail = path.as_posix().split(":", 1)[1]
    return f"/mnt/{drive}{tail}"


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


def test_control_compose_exposes_pythonpath_for_all_python_services():
    compose_file = Path(__file__).resolve().parents[1] / "docker-compose.control.yml"

    content = compose_file.read_text(encoding="utf-8")

    assert "PYTHONPATH: /srv/control" in content
