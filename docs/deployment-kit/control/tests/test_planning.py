from fk_control.planning import LaneScore, build_chapter_job_plan, build_chapter_rows, choose_best_lane, split_duration


def test_split_duration_keeps_total():
    parts = split_duration(2700, 10)
    assert len(parts) == 10
    assert sum(parts) == 2700


def test_build_chapter_rows_sets_scene_targets():
    rows = build_chapter_rows("project_x", 900, 3)
    assert rows[0]["chapter_slug"] == "project_x_chapter_01"
    assert rows[0]["target_scene_count"] > 0


def test_choose_best_lane_prefers_more_credits_then_younger_token():
    lanes = [
        LaneScore("lane-02", credits_last_seen=100, token_age_seconds=30),
        LaneScore("lane-01", credits_last_seen=200, token_age_seconds=300),
        LaneScore("lane-03", credits_last_seen=200, token_age_seconds=20),
    ]
    assert choose_best_lane(lanes) == "lane-03"


def test_build_chapter_job_plan_has_expected_stage_order():
    jobs = build_chapter_job_plan("project-1", "chapter-1", "lane-01", "trace-1")
    assert jobs[0]["job_type"] == "CREATE_PROJECT"
    assert jobs[-1]["job_type"] == "UPLOAD_ARTIFACTS"
    assert all(job["lane_id"] == "lane-01" for job in jobs)


def test_build_chapter_job_plan_contains_runnable_payloads():
    jobs = build_chapter_job_plan(
        "project-1",
        "chapter-1",
        "lane-01",
        "trace-1",
        {
            "source_title": "Master Title",
            "source_brief": "A short chapter brief.",
            "chapter_title": "Chapter 01",
            "target_scene_count": 3,
            "material_id": "realistic",
        },
    )

    create_project = jobs[0]
    create_entities = jobs[1]
    create_video = jobs[2]
    create_scenes = jobs[3]
    gen_images = jobs[5]

    assert '"name":"Chapter 01"' in create_project["payload_json"]
    assert '"material":"realistic"' in create_project["payload_json"]
    assert '"entities":' in create_entities["payload_json"]
    assert '"title":"Chapter 01"' in create_video["payload_json"]
    assert create_scenes["payload_json"].count('"display_order"') == 3
    assert '"chain_type":"ROOT"' in create_scenes["payload_json"]
    assert '"chain_type":"CONTINUATION"' in create_scenes["payload_json"]
    assert '"orientation":"VERTICAL"' in gen_images["payload_json"]
