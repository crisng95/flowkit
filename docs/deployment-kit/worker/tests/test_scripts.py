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

        agent_service = (systemd_dir / "flowkit-agent-lane-02.service").read_text(encoding="utf-8")
        assert _wsl_path(deploy_root) in agent_service
