"""Chapter-final to master-final assembly."""

from __future__ import annotations

from pathlib import Path
import json
import time

from .config import settings
from .media import build_master_manifest, concat_videos, probe_dimensions, probe_duration
from .storage import get_project, insert_artifact, list_completed_chapter_final_artifacts, set_project_master_output
from .upload import download_file, sha256_file, upload_file


def _workspace(project_slug: str) -> Path:
    return Path("/tmp/fk-assembler") / project_slug


def assemble_project(project_id: str) -> dict:
    project = get_project(project_id)
    if not project:
        raise ValueError("Project not found")

    chapter_artifacts = list_completed_chapter_final_artifacts(project_id)
    if not chapter_artifacts:
        raise ValueError("No chapter_final artifacts found")

    workspace = _workspace(project["project_slug"])
    workspace.mkdir(parents=True, exist_ok=True)

    local_files = []
    for artifact in chapter_artifacts:
        destination = workspace / f"chapter_{artifact['chapter_index']:02d}.mp4"
        download_file(artifact["storage_uri"], destination)
        local_files.append(destination)

    final_path = workspace / f"{project['project_slug']}_master_final.mp4"
    concat_videos(local_files, final_path)
    duration = probe_duration(final_path)
    width, height = probe_dimensions(final_path)

    final_key = f"{settings.r2_prefix}/{project['project_slug']}/master/final_45min.mp4"
    final_uri = upload_file(final_path, final_key)
    set_project_master_output(project_id, final_uri)
    insert_artifact(
        project_id=project_id,
        chapter_id=None,
        lane_id=None,
        artifact_type="master_final",
        local_path=str(final_path),
        storage_uri=final_uri,
        checksum_sha256=sha256_file(final_path),
        size_bytes=final_path.stat().st_size,
        duration_seconds=duration,
        width=width,
        height=height,
        artifact_metadata={"chapter_count": len(chapter_artifacts)},
    )

    manifest = build_master_manifest(project, chapter_artifacts, final_uri, duration)
    manifest_path = workspace / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest_key = f"{settings.r2_prefix}/{project['project_slug']}/master/manifest.json"
    manifest_uri = upload_file(manifest_path, manifest_key)
    insert_artifact(
        project_id=project_id,
        chapter_id=None,
        lane_id=None,
        artifact_type="manifest",
        local_path=str(manifest_path),
        storage_uri=manifest_uri,
        checksum_sha256=sha256_file(manifest_path),
        size_bytes=manifest_path.stat().st_size,
        artifact_metadata={"chapter_count": len(chapter_artifacts)},
    )

    return {
        "project_id": project_id,
        "master_output_uri": final_uri,
        "manifest_uri": manifest_uri,
        "duration_seconds": duration,
        "width": width,
        "height": height,
        "chapter_count": len(chapter_artifacts),
    }


def main() -> None:
    print("assembler service running")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
