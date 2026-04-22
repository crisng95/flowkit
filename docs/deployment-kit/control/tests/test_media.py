from pathlib import Path

from fk_control.media import build_master_manifest, concat_lines


def test_concat_lines():
    paths = [Path("/tmp/ch1.mp4"), Path("/tmp/ch2.mp4")]
    lines = concat_lines(paths)
    assert lines[0].startswith("file '")
    assert lines[1].startswith("file '")
    assert lines[0].endswith("ch1.mp4'")
    assert lines[1].endswith("ch2.mp4'")


def test_build_master_manifest():
    project = {
        "id": "project-1",
        "project_slug": "project_x",
        "source_title": "Project X",
        "target_duration_seconds": 2700,
    }
    chapters = [
        {"chapter_id": "ch-1", "chapter_index": 1, "storage_uri": "s3://bucket/ch1.mp4"},
        {"chapter_id": "ch-2", "chapter_index": 2, "storage_uri": "s3://bucket/ch2.mp4"},
    ]
    manifest = build_master_manifest(project, chapters, "s3://bucket/master.mp4", 2700.0)
    assert manifest["project_slug"] == "project_x"
    assert manifest["master_output_uri"] == "s3://bucket/master.mp4"
    assert manifest["chapters"][0]["chapter_index"] == 1
