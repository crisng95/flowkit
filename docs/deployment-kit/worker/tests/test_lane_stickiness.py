from fk_worker import runner


def test_lane_releases_only_after_terminal_chapter_stage():
    assert runner.should_release_lane("CREATE_PROJECT") is False
    assert runner.should_release_lane("GEN_VIDEOS") is False
    assert runner.should_release_lane("UPLOAD_ARTIFACTS") is True


def test_runner_skips_followup_jobs_when_chapter_failed():
    assert runner.should_skip_job({"status": "failed"}, "GEN_REFS") == "Chapter already failed before GEN_REFS"
    assert runner.should_skip_job({"status": "assigned"}, "GEN_REFS") is None


def test_runner_waits_for_prerequisites_before_running_downstream_jobs():
    chapter = {"status": "assigned", "local_flow_project_id": None, "chapter_metadata": {}}
    assert runner.prerequisite_wait_reason(chapter, "CREATE_ENTITIES") == "waiting for CREATE_PROJECT"

    chapter["local_flow_project_id"] = "project-1"
    assert runner.prerequisite_wait_reason(chapter, "CREATE_VIDEO") is None
    assert runner.prerequisite_wait_reason(chapter, "CREATE_SCENES") == "waiting for CREATE_VIDEO"

    chapter["chapter_metadata"] = {"local_video_id": "video-1"}
    assert runner.prerequisite_wait_reason(chapter, "CREATE_SCENES") is None
    assert runner.prerequisite_wait_reason(chapter, "GEN_IMAGES") == "waiting for CREATE_SCENES"

    chapter["chapter_metadata"]["local_scene_ids"] = ["scene-1"]
    assert runner.prerequisite_wait_reason(chapter, "GEN_IMAGES") is None
    assert runner.prerequisite_wait_reason(chapter, "UPLOAD_ARTIFACTS") == "waiting for CONCAT_CHAPTER"
