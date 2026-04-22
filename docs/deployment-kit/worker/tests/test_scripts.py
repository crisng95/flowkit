import os
from pathlib import Path
import subprocess
import tempfile


def _wsl_path(path: Path) -> str:
    drive = path.drive.rstrip(":").lower()
    tail = path.as_posix().split(":", 1)[1]
    return f"/mnt/{drive}{tail}"


def test_lane_runner_script_help():
    script = Path(__file__).resolve().parents[1] / "scripts" / "lane-runner.sh"

    result = subprocess.run(
        ["bash", _wsl_path(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "PYTHON_BIN" in result.stdout
    assert "LOG_FILE" in result.stdout


def test_run_worker_demo_script_help():
    script = Path(__file__).resolve().parents[1] / "scripts" / "run-worker-demo.sh"

    result = subprocess.run(
        ["bash", _wsl_path(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "WAIT_FOR_HEALTH" in result.stdout
    assert "RUNNER_PID_FILE" in result.stdout


def test_bootstrap_lane_script_supports_same_vm_lane_overrides():
    script = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap-lane.sh"

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        deploy_root = root / "flowkit-worker-demo-lane-02"
        systemd_dir = root / "systemd"
        systemd_dir.mkdir()
        env = os.environ.copy()
        env.update(
            {
                "DEPLOY_ROOT": _wsl_path(deploy_root),
                "SUDO_BIN": "",
                "SYSTEMCTL_BIN": "true",
                "SYSTEMD_DIR": _wsl_path(systemd_dir),
                "API_PORT_OVERRIDE": "8110",
                "WS_PORT_OVERRIDE": "9232",
                "RUNNER_HEALTH_PORT_OVERRIDE": "18182",
            }
        )

        result = subprocess.run(
            [
                "bash",
                "-lc",
                " ".join(
                    [
                        f"DEPLOY_ROOT='{_wsl_path(deploy_root)}'",
                        "SUDO_BIN=''",
                        "SYSTEMCTL_BIN='true'",
                        f"SYSTEMD_DIR='{_wsl_path(systemd_dir)}'",
                        "API_PORT_OVERRIDE='8110'",
                        "WS_PORT_OVERRIDE='9232'",
                        "RUNNER_HEALTH_PORT_OVERRIDE='18182'",
                        f"'{_wsl_path(script)}'",
                        "lane-02",
                        "flow-account-02",
                    ]
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

        assert result.returncode == 0, result.stderr

        lane_env = (deploy_root / "env" / "lane.env").read_text(encoding="utf-8")
        assert "LANE_ID=lane-02" in lane_env
        assert "FLOW_ACCOUNT_ALIAS=flow-account-02" in lane_env
        assert f"FLOWKIT_ROOT={_wsl_path(deploy_root)}" in lane_env
        assert "API_PORT=8110" in lane_env
        assert "WS_PORT=9232" in lane_env
        assert "RUNNER_HEALTH_PORT=18182" in lane_env
        assert (deploy_root / "docker-compose.worker.yml").exists()
        assert (deploy_root / "Dockerfile.worker").exists()

        agent_service = (systemd_dir / "flowkit-agent-lane-02.service").read_text(encoding="utf-8")
        assert _wsl_path(deploy_root) in agent_service


def test_worker_compose_runs_containers_as_host_user():
    compose_file = Path(__file__).resolve().parents[1] / "docker-compose.worker.yml"

    content = compose_file.read_text(encoding="utf-8")

    assert 'user: "${FLOWKIT_UID:-1000}:${FLOWKIT_GID:-1000}"' in content


def test_bootstrap_lane_script_copies_app_source_when_provided():
    script = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap-lane.sh"

    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        deploy_root = root / "flowkit-worker-demo-lane-02"
        systemd_dir = root / "systemd"
        systemd_dir.mkdir()
        app_source = root / "app-source"
        (app_source / "agent").mkdir(parents=True)
        (app_source / "agent" / "__init__.py").write_text("", encoding="utf-8")
        (app_source / "agent" / "main.py").write_text("print('agent main')\n", encoding="utf-8")
        (app_source / "requirements.txt").write_text("fastapi\n", encoding="utf-8")

        env = os.environ.copy()
        env.update(
            {
                "DEPLOY_ROOT": _wsl_path(deploy_root),
                "APP_SOURCE": _wsl_path(app_source),
                "SUDO_BIN": "",
                "SYSTEMCTL_BIN": "true",
                "SYSTEMD_DIR": _wsl_path(systemd_dir),
            }
        )

        result = subprocess.run(
            [
                "bash",
                "-lc",
                " ".join(
                    [
                        f"DEPLOY_ROOT='{_wsl_path(deploy_root)}'",
                        f"APP_SOURCE='{_wsl_path(app_source)}'",
                        "SUDO_BIN=''",
                        "SYSTEMCTL_BIN='true'",
                        f"SYSTEMD_DIR='{_wsl_path(systemd_dir)}'",
                        f"'{_wsl_path(script)}'",
                        "lane-02",
                        "flow-account-02",
                    ]
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

        assert result.returncode == 0, result.stderr
        assert (deploy_root / "app" / "agent" / "main.py").exists()
        assert (deploy_root / "app" / "requirements.txt").exists()
