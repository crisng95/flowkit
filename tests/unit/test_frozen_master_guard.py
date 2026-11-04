"""Tests for the frozen Master fail-closed guard."""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD_PATH = REPO_ROOT / "tools" / "frozen_master_guard.py"


@pytest.fixture(scope="module")
def guard_mod():
    spec = importlib.util.spec_from_file_location("frozen_master_guard", GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["frozen_master_guard"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("frozen_master_guard", None)


@pytest.fixture
def frozen_copy(guard_mod, tmp_path):
    """Create a canonical-LF isolated copy for mutation tests."""
    master_src = REPO_ROOT / guard_mod.MASTER_RELATIVE_PATH
    manifest_src = REPO_ROOT / guard_mod.MANIFEST_RELATIVE_PATH

    master_dst = tmp_path / guard_mod.MASTER_RELATIVE_PATH
    manifest_dst = tmp_path / guard_mod.MANIFEST_RELATIVE_PATH
    master_dst.parent.mkdir(parents=True)
    manifest_dst.parent.mkdir(parents=True, exist_ok=True)

    canonical_master = master_src.read_bytes().replace(b"\r\n", b"\n")
    master_dst.write_bytes(canonical_master)
    manifest_dst.write_text(
        manifest_src.read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )
    return tmp_path


def test_real_repository_frozen_baseline_passes(guard_mod):
    result = guard_mod.verify_frozen_baseline(REPO_ROOT)
    assert result.sha256 == guard_mod.EXPECTED_MASTER_SHA256
    assert result.master_path == REPO_ROOT / guard_mod.MASTER_RELATIVE_PATH


def test_isolated_frozen_copy_passes(guard_mod, frozen_copy):
    result = guard_mod.verify_frozen_baseline(frozen_copy)
    assert result.sha256 == guard_mod.EXPECTED_MASTER_SHA256
    assert result.raw_sha256 == guard_mod.EXPECTED_MASTER_SHA256
    assert result.newline_normalized is False


def test_crlf_checkout_of_same_master_passes(guard_mod, frozen_copy):
    master = frozen_copy / guard_mod.MASTER_RELATIVE_PATH
    lf_bytes = master.read_bytes()
    master.write_bytes(lf_bytes.replace(b"\n", b"\r\n"))

    result = guard_mod.verify_frozen_baseline(frozen_copy)

    assert result.sha256 == guard_mod.EXPECTED_MASTER_SHA256
    assert result.raw_sha256 != guard_mod.EXPECTED_MASTER_SHA256
    assert result.newline_normalized is True


def test_missing_master_fails_closed(guard_mod, frozen_copy):
    (frozen_copy / guard_mod.MASTER_RELATIVE_PATH).unlink()
    with pytest.raises(guard_mod.FrozenBaselineError, match="frozen Master is missing"):
        guard_mod.verify_frozen_baseline(frozen_copy)


def test_tampered_master_fails_closed(guard_mod, frozen_copy):
    master = frozen_copy / guard_mod.MASTER_RELATIVE_PATH
    master.write_bytes(master.read_bytes() + b"\nTAMPERED\n")
    with pytest.raises(guard_mod.FrozenBaselineError, match="SHA-256 mismatch"):
        guard_mod.verify_frozen_baseline(frozen_copy)


def test_tampered_crlf_master_still_fails_closed(guard_mod, frozen_copy):
    master = frozen_copy / guard_mod.MASTER_RELATIVE_PATH
    master.write_bytes(master.read_bytes().replace(b"\n", b"\r\n") + b"TAMPERED")
    with pytest.raises(guard_mod.FrozenBaselineError, match="SHA-256 mismatch"):
        guard_mod.verify_frozen_baseline(frozen_copy)


def test_missing_manifest_fails_closed(guard_mod, frozen_copy):
    (frozen_copy / guard_mod.MANIFEST_RELATIVE_PATH).unlink()
    with pytest.raises(guard_mod.FrozenBaselineError, match="freeze manifest is missing"):
        guard_mod.verify_frozen_baseline(frozen_copy)


def test_manifest_declared_sha_must_match(guard_mod, frozen_copy):
    manifest = frozen_copy / guard_mod.MANIFEST_RELATIVE_PATH
    text = manifest.read_text(encoding="utf-8")
    text = text.replace(
        guard_mod.EXPECTED_MASTER_SHA256,
        "0" * 64,
        1,
    )
    manifest.write_text(text, encoding="utf-8")
    with pytest.raises(guard_mod.FrozenBaselineError, match="manifest SHA-256 mismatch"):
        guard_mod.verify_frozen_baseline(frozen_copy)


def test_manifest_declared_path_must_match(guard_mod, frozen_copy):
    manifest = frozen_copy / guard_mod.MANIFEST_RELATIVE_PATH
    text = manifest.read_text(encoding="utf-8")
    text = text.replace(
        guard_mod.MASTER_RELATIVE_PATH.as_posix(),
        "docs/design/canonical/WRONG_MASTER.md",
        1,
    )
    manifest.write_text(text, encoding="utf-8")
    with pytest.raises(guard_mod.FrozenBaselineError, match="Master path mismatch"):
        guard_mod.verify_frozen_baseline(frozen_copy)


def test_manifest_requires_frozen_verdict(guard_mod, frozen_copy):
    manifest = frozen_copy / guard_mod.MANIFEST_RELATIVE_PATH
    text = manifest.read_text(encoding="utf-8").replace(
        guard_mod.FROZEN_VERDICT,
        "MASTER IMPLEMENTATION BASELINE V1 = CANDIDATE",
    )
    manifest.write_text(text, encoding="utf-8")
    with pytest.raises(guard_mod.FrozenBaselineError, match="missing verdict"):
        guard_mod.verify_frozen_baseline(frozen_copy)


def test_cli_exit_codes_are_fail_closed(guard_mod, frozen_copy, capsys):
    assert guard_mod.main(["--repo-root", str(frozen_copy)]) == 0
    out = capsys.readouterr()
    assert "FROZEN_MASTER_GUARD=PASS" in out.out

    master = frozen_copy / guard_mod.MASTER_RELATIVE_PATH
    master.write_bytes(master.read_bytes() + b"tamper")
    assert guard_mod.main(["--repo-root", str(frozen_copy)]) == 1
    out = capsys.readouterr()
    assert "FROZEN_MASTER_GUARD=FAIL" in out.err


def test_cli_reports_newline_normalization(guard_mod, frozen_copy, capsys):
    master = frozen_copy / guard_mod.MASTER_RELATIVE_PATH
    master.write_bytes(master.read_bytes().replace(b"\n", b"\r\n"))

    assert guard_mod.main(["--repo-root", str(frozen_copy)]) == 0
    out = capsys.readouterr()

    assert "FROZEN_MASTER_GUARD=PASS" in out.out
    assert "NEWLINE_NORMALIZED=CRLF_TO_LF" in out.out
