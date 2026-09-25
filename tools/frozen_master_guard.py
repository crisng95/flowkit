#!/usr/bin/env python3
"""Fail-closed guard for the frozen AI Film Studio Master baseline.

This module intentionally performs read-only verification.  The frozen Master
is a design authority; implementation code may depend on it but must not
silently update it.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

EXPECTED_MASTER_SHA256 = (
    "1ff9383d713dfaab309d3f36cc83cf05e8932c1bc07f68682e2e12a488c77287"
)
MASTER_RELATIVE_PATH = Path(
    "docs/design/canonical/MASTER_AI_FILM_STUDIO_FINAL_IMPLEMENTATION_BASELINE_V1.md"
)
MANIFEST_RELATIVE_PATH = Path(
    "docs/design/canonical/MASTER_AI_FILM_STUDIO_IMPLEMENTATION_BASELINE_V1_FREEZE_MANIFEST.md"
)
FROZEN_VERDICT = "MASTER IMPLEMENTATION BASELINE V1 = FROZEN"


class FrozenBaselineError(RuntimeError):
    """Raised when the frozen baseline cannot be proven intact."""


@dataclass(frozen=True)
class FrozenBaselineResult:
    repo_root: Path
    master_path: Path
    manifest_path: Path
    sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FrozenBaselineError(f"{label} is missing: {path}")


def _manifest_declared_path(text: str) -> str:
    match = re.search(r"(?m)^Path:\s*\n\s*`([^`]+)`\s*$", text)
    if not match:
        raise FrozenBaselineError("freeze manifest does not declare the frozen Master Path")
    return match.group(1).replace("\\", "/")


def _manifest_declared_sha(text: str) -> str:
    match = re.search(
        r"(?mi)^Frozen SHA-256:\s*\n\s*`([0-9a-f]{64})`\s*$",
        text,
    )
    if not match:
        raise FrozenBaselineError("freeze manifest does not declare Frozen SHA-256")
    return match.group(1).lower()


def verify_frozen_baseline(repo_root: Path | str) -> FrozenBaselineResult:
    """Verify the exact frozen Master and freeze-manifest contract.

    The check is deliberately stricter than simply finding the expected hash
    somewhere in the manifest.  It parses the manifest's declared Path and
    Frozen SHA-256 fields and requires the frozen verdict.
    """

    root = Path(repo_root).resolve()
    master_path = root / MASTER_RELATIVE_PATH
    manifest_path = root / MANIFEST_RELATIVE_PATH

    _require_file(master_path, "frozen Master")
    _require_file(manifest_path, "freeze manifest")

    actual_sha = _sha256(master_path)
    if actual_sha != EXPECTED_MASTER_SHA256:
        raise FrozenBaselineError(
            "frozen Master SHA-256 mismatch: "
            f"expected {EXPECTED_MASTER_SHA256}, got {actual_sha}"
        )

    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise FrozenBaselineError(
            f"freeze manifest is not valid UTF-8: {manifest_path}"
        ) from exc

    declared_path = _manifest_declared_path(manifest_text)
    expected_path = MASTER_RELATIVE_PATH.as_posix()
    if declared_path != expected_path:
        raise FrozenBaselineError(
            "freeze manifest Master path mismatch: "
            f"expected {expected_path}, got {declared_path}"
        )

    declared_sha = _manifest_declared_sha(manifest_text)
    if declared_sha != EXPECTED_MASTER_SHA256:
        raise FrozenBaselineError(
            "freeze manifest SHA-256 mismatch: "
            f"expected {EXPECTED_MASTER_SHA256}, got {declared_sha}"
        )

    if FROZEN_VERDICT not in manifest_text:
        raise FrozenBaselineError(
            f"freeze manifest is missing verdict: {FROZEN_VERDICT}"
        )

    return FrozenBaselineResult(
        repo_root=root,
        master_path=master_path,
        manifest_path=manifest_path,
        sha256=actual_sha,
    )


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify the frozen AI Film Studio Master baseline."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_default_repo_root(),
        help="Repository root. Defaults to the parent of tools/.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = verify_frozen_baseline(args.repo_root)
    except FrozenBaselineError as exc:
        print("FROZEN_MASTER_GUARD=FAIL", file=sys.stderr)
        print(f"ERROR={exc}", file=sys.stderr)
        return 1

    print("FROZEN_MASTER_GUARD=PASS")
    print(f"MASTER={result.master_path.relative_to(result.repo_root).as_posix()}")
    print(f"SHA256={result.sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
