from fk_control.dashboard import build_queue_sections


def test_build_queue_sections_hides_zero_depth_noise_by_default():
    sections = build_queue_sections(
        {
            "chapters:pending": 0,
            "lane:01:jobs": 0,
            "lane:01:dead": 0,
            "lane:01:jobs:pending": 0,
            "lane:01:jobs:lag": 0,
            "lane:01:jobs:stream_depth": 11,
            "lane:02:jobs": 3,
            "lane:02:dead": 1,
        }
    )

    assert [row["key"] for row in sections["default"]] == [
        "chapters:pending",
        "lane:02:jobs",
        "lane:02:dead",
    ]
    assert "lane:01:dead" not in [row["key"] for row in sections["default"]]
    assert "lane:01:jobs:stream_depth" in [row["key"] for row in sections["debug"]]
