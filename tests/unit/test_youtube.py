"""Unit tests for youtube/upload.py and youtube/auth.py."""
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from youtube.upload import (
    auto_schedule,
    detect_video_type,
    load_channel_rules,
    validate_upload,
)


def test_load_channel_rules_fallback():
    rules = load_channel_rules("non_existent_channel_xyz")
    assert "upload_rules" in rules
    assert "shorts" in rules["upload_rules"]
    assert rules["timezone"] == "Asia/Ho_Chi_Minh"


def test_load_channel_rules_from_disk(tmp_path, monkeypatch):
    from youtube import auth

    monkeypatch.setattr(auth, "CHANNELS_DIR", tmp_path)
    chan_dir = tmp_path / "custom_chan"
    chan_dir.mkdir()
    custom_rules = {
        "upload_rules": {
            "shorts": {"max_per_day": 5, "optimal_times": ["08:00"]},
            "long": {"max_per_day": 2, "optimal_times": ["20:00"]},
        },
        "timezone": "UTC",
    }
    (chan_dir / "channel_rules.json").write_text(
        json.dumps(custom_rules), encoding="utf-8"
    )

    rules = load_channel_rules("custom_chan")
    assert rules["upload_rules"]["shorts"]["max_per_day"] == 5
    assert rules["timezone"] == "UTC"


def test_detect_video_type_short():
    with patch("youtube.upload._probe_video", return_value=(45.0, 1080, 1920)):
        vtype, orient = detect_video_type("test.mp4")
        assert vtype == "short"
        assert orient == "vertical"


def test_detect_video_type_long():
    with patch("youtube.upload._probe_video", return_value=(120.0, 1920, 1080)):
        vtype, orient = detect_video_type("test.mp4")
        assert vtype == "long"
        assert orient == "horizontal"


def test_validate_upload_avoid_hours():
    # 03:00 is in default avoid_hours (0..5)
    avoid_dt = datetime(2026, 9, 22, 3, 0, tzinfo=timezone.utc)
    ok, reason = validate_upload("chan1", avoid_dt, is_short=True)
    assert not ok
    assert "avoid_hours" in reason


def test_validate_upload_valid_slot():
    valid_dt = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)
    with patch("youtube.upload.load_upload_history", return_value=[]):
        ok, reason = validate_upload("chan1", valid_dt, is_short=True)
        assert ok
        assert reason == "OK"


def test_auto_schedule_generates_slots():
    start_dt = datetime(2026, 9, 22, 6, 0, tzinfo=timezone.utc)
    with patch("youtube.upload.load_upload_history", return_value=[]):
        slots = auto_schedule("chan1", count=3, is_short=True, start_from=start_dt)
        assert len(slots) == 3
        # Should start from the first optimal time >= 6:00 (which is 07:00, 12:00, 17:00)
        assert "07:00:00" in slots[0]
        assert "12:00:00" in slots[1]
        assert "17:00:00" in slots[2]
