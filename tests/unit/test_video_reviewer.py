"""Integration-style tests for agent/services/video_reviewer.py's
_create_contact_sheets: real ffmpeg frame extraction + REVIEW_MAX_FRAMES cap +
chunking into contact sheets. No mocking of ffmpeg subprocess calls here —
these tests generate a real short synthetic video and verify the chunking
math against real ffmpeg output.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from agent.services.video_reviewer import _create_contact_sheets


@pytest.fixture(scope="module")
def synthetic_video():
    """A real ~2-second synthetic test video generated once for this test module."""
    tmp_dir = tempfile.mkdtemp()
    video_path = Path(tmp_dir) / "synthetic.mp4"
    ffmpeg_cmd = "ffmpeg"
    import shutil
    if not shutil.which("ffmpeg"):
        try:
            import imageio_ffmpeg
            ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
    try:
        result = subprocess.run(
            [ffmpeg_cmd, "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=30",
             str(video_path)],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        pytest.skip("ffmpeg not found in PATH")
    if result.returncode != 0:
        pytest.skip(f"ffmpeg unavailable or failed to generate test video: {result.stderr[-300:]}")
    yield video_path


class TestCreateContactSheetsChunking:
    def test_2s_video_at_4fps_produces_correct_sheet_count(self, synthetic_video):
        # 2s * 4fps = 8 frames -> ceil(8/9) = 1 sheet
        with tempfile.TemporaryDirectory() as out_dir:
            sheets, total_frames, _timestamped = _create_contact_sheets(str(synthetic_video), 4, out_dir)
            assert total_frames == 8
            assert len(sheets) == 1
            assert all(s.exists() and s.stat().st_size > 0 for s in sheets)

    def test_2s_video_at_8fps_produces_correct_sheet_count(self, synthetic_video):
        # 2s * 8fps = 16 frames -> ceil(16/9) = 2 sheets
        with tempfile.TemporaryDirectory() as out_dir:
            sheets, total_frames, _timestamped = _create_contact_sheets(str(synthetic_video), 8, out_dir)
            assert total_frames == 16
            assert len(sheets) == 2
            assert all(s.exists() and s.stat().st_size > 0 for s in sheets)

    def test_review_max_frames_caps_total_and_sheet_count(self, synthetic_video, monkeypatch):
        import agent.services.video_reviewer as vr
        monkeypatch.setattr(vr, "REVIEW_MAX_FRAMES", 5)
        with tempfile.TemporaryDirectory() as out_dir:
            sheets, total_frames, _timestamped = _create_contact_sheets(str(synthetic_video), 8, out_dir)
            # 16 natural frames capped to 5 -> ceil(5/9) = 1 sheet
            assert total_frames == 5
            assert len(sheets) == 1

    def test_downsampling_selects_correct_nonconsecutive_frames_across_chunks(
        self, synthetic_video, monkeypatch
    ):
        """The single most important correctness property of this function: after
        REVIEW_MAX_FRAMES downsampling, each chunk must be tiled from the CORRECT
        (possibly non-contiguous) subset of frames, not a contiguous slice of the
        original numbering. A naive -start_number/-frames:v approach against the
        original frame_%04d.jpg sequence would silently tile the wrong frames here.
        """
        import agent.services.video_reviewer as vr

        # 2s * 30fps = 60 natural frames; capping to 20 spans 3 chunks (ceil(20/9)=3)
        # and is genuinely non-contiguous (step = 60/20 = 3.0, picks frames 0,3,6,...).
        monkeypatch.setattr(vr, "REVIEW_MAX_FRAMES", 20)
        out_dir = tempfile.mkdtemp()
        try:
            sheets, total_frames, _timestamped = _create_contact_sheets(str(synthetic_video), 30, out_dir)
            assert total_frames == 20
            assert len(sheets) == 3

            all_frames = sorted((Path(out_dir) / "frames").glob("frame_*.jpg"))
            assert len(all_frames) == 60
            step = len(all_frames) / 20
            expected_selection = [all_frames[int(i * step)] for i in range(20)]

            per_sheet = 9
            for sheet_idx, start in enumerate(range(0, 20, per_sheet)):
                expected_chunk = expected_selection[start:start + per_sheet]
                chunk_dir = Path(out_dir) / f"_chunk_{sheet_idx:02d}"
                symlinks = sorted(chunk_dir.glob("f_*.jpg"))
                assert len(symlinks) == len(expected_chunk)
                for link, expected_target in zip(symlinks, expected_chunk):
                    assert link.resolve() == expected_target.resolve(), (
                        f"chunk {sheet_idx} symlink {link.name} points to "
                        f"{link.resolve()}, expected {expected_target.resolve()}"
                    )
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    @pytest.mark.parametrize(
        "chunk_size,expected_cols,expected_rows",
        [
            (1, 1, 1), (2, 2, 1), (3, 3, 1), (4, 2, 2), (5, 1, 5),
            (6, 3, 2), (7, 1, 7), (8, 2, 4), (9, 3, 3),
        ],
    )
    def test_partial_trailing_chunk_uses_zero_waste_layout(
        self, synthetic_video, monkeypatch, chunk_size, expected_cols, expected_rows
    ):
        """Every possible chunk size (1-9) must produce a tile grid with EXACTLY that
        many cells -- zero unfilled cells. A layout with any unfilled cell renders that
        cell as a solid color block (not blank), which vision models can and do misread
        as a defect in the source video (confirmed via a live review call during
        development: a 3x2 layout with 1 blank cell out of 6 was enough to trigger a
        fabricated "HIGH severity" corruption finding). Asserting the EXACT output
        dimensions (not just "smaller than the old fixed 3x3") is what catches a
        regression to a min/ceil-style approximate shrink that still leaves waste for
        some chunk sizes (e.g. size 4 under min(4,3)=3,ceil(4/3)=2 gives 3x2=6 cells,
        2 wasted -- this exact regression was caught by this test during development).
        """
        import agent.services.video_reviewer as vr

        monkeypatch.setattr(vr, "REVIEW_MAX_FRAMES", chunk_size)
        out_dir = tempfile.mkdtemp()
        try:
            sheets, total_frames, _timestamped = _create_contact_sheets(str(synthetic_video), 30, out_dir)
            assert total_frames == chunk_size
            try:
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0",
                     "-show_entries", "stream=width,height", "-of", "csv=p=0", str(sheets[0])],
                    capture_output=True, text=True,
                )
                if probe.returncode != 0:
                    raise FileNotFoundError
                width, height = (int(x) for x in probe.stdout.strip().split(","))
            except (FileNotFoundError, ValueError):
                from PIL import Image
                with Image.open(sheets[0]) as im:
                    width, height = im.size
            frame_w, frame_h = 320, 240  # scale=320:-1 applied to the 320x240 synthetic_video
            assert (width, height) == (expected_cols * frame_w, expected_rows * frame_h), (
                f"chunk_size={chunk_size}: expected a {expected_cols}x{expected_rows} "
                f"zero-waste layout ({expected_cols*frame_w}x{expected_rows*frame_h}), "
                f"got {width}x{height} -- some cells are unfilled/wasted"
            )
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# review_scene_video :: what a malformed CLI answer is allowed to become
# ---------------------------------------------------------------------------

class TestReviewScoringRefusesAFabricatedScore:
    """Every field of DimensionScores has a 5.0 default, so an answer carrying
    no `dimensions` used to become a complete, plausible review — 5.0 across
    the board, verdict "poor", zero errors — indistinguishable from a real
    verdict on a mediocre video. That is the same class of bug as a CLI
    returning an empty response on a zero exit code, and it has to fail loudly
    instead.
    """

    @staticmethod
    def _patched(monkeypatch, analysis):
        import agent.services.video_reviewer as vr

        async def fake_download(url, dest):
            Path(dest).write_bytes(b"not really a video")

        def fake_sheets(video_path, fps, out_dir):
            sheet = Path(out_dir) / "sheet_00.jpg"
            sheet.write_bytes(b"jpeg")
            return [sheet], 9, True

        async def fake_analyze(sheets, n_frames, fps, scene, timestamped=None, role=None):
            return analysis

        monkeypatch.setattr(vr, "ANTHROPIC_API_KEY", "")
        monkeypatch.setattr(vr, "_download_video", fake_download)
        monkeypatch.setattr(vr, "_create_contact_sheets", fake_sheets)
        monkeypatch.setattr(vr, "_analyze_cli", fake_analyze)
        return vr

    SCENE = {"id": "s1", "vertical_video_url": "https://example.test/v.mp4",
             "prompt": "p", "video_prompt": "vp", "character_names": "[]"}

    @pytest.mark.asyncio
    async def test_an_answer_with_no_dimensions_raises(self, monkeypatch):
        vr = self._patched(monkeypatch, {"errors": [], "usable_segments": []})
        with pytest.raises(RuntimeError, match="no dimensions"):
            await vr.review_scene_video(dict(self.SCENE), [])

    @pytest.mark.asyncio
    async def test_an_empty_dimensions_object_raises(self, monkeypatch):
        vr = self._patched(monkeypatch, {"dimensions": {}, "errors": []})
        with pytest.raises(RuntimeError, match="no dimensions"):
            await vr.review_scene_video(dict(self.SCENE), [])

    @pytest.mark.asyncio
    async def test_a_partial_dimensions_object_still_defaults(self, monkeypatch):
        """A model that scored some axes and not others is answering, just
        incompletely — that is worth keeping, unlike one that answered nothing.
        """
        vr = self._patched(monkeypatch, {
            "dimensions": {"character_consistency": 9.0}, "errors": [], "usable_segments": []})
        review = await vr.review_scene_video(dict(self.SCENE), [])
        assert review.dimensions.character_consistency == 9.0
        assert review.dimensions.motion_quality == 5.0  # the documented default

    GOOD_DIMS = {"character_consistency": 9.0, "prompt_adherence": 9.0,
                 "motion_quality": 9.0, "visual_fidelity": 9.0,
                 "temporal_coherence": 9.0, "composition": 9.0}

    @pytest.mark.asyncio
    async def test_a_near_miss_key_keeps_the_critical_instead_of_dropping_it(self, monkeypatch):
        """`timeRange` for `time_range` used to drop the whole entry, and what
        drops with it is usually CRITICAL — the one severity that caps
        character_consistency at 3.0 and forces the verdict below acceptable.
        An unusable video came back clean over a camelCase key.

        The entry is repaired rather than refused: the model found the defect
        and said so, it just spelled one field name oddly. Failing the scene
        here would throw away a correct finding.
        """
        vr = self._patched(monkeypatch, {
            "dimensions": dict(self.GOOD_DIMS),
            "errors": [{"severity": "CRITICAL", "timeRange": "3s-5s",
                        "description": "the dog becomes a cat"}],
            "usable_segments": [],
        })
        review = await vr.review_scene_video(dict(self.SCENE), [])

        assert [e.severity for e in review.errors] == ["CRITICAL"]
        assert review.errors[0].time_range == "3s-5s"
        assert review.has_critical_errors is True
        assert review.dimensions.character_consistency == 3.0
        assert review.overall_score <= 5.9

    @pytest.mark.asyncio
    async def test_a_missing_time_range_is_repaired_not_refused(self, monkeypatch):
        """Losing a timestamp costs the reader context; it cannot move a score.
        Same placeholder the legacy plain-string path has always used."""
        vr = self._patched(monkeypatch, {
            "dimensions": dict(self.GOOD_DIMS),
            "errors": [{"severity": "MINOR", "description": "candle count drifts"}],
            "usable_segments": [],
        })
        review = await vr.review_scene_video(dict(self.SCENE), [])
        assert review.errors[0].time_range == "?"
        assert review.errors[0].description == "candle count drifts"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("severity", [None, "", "SEVERE", "MAJOR", "Critical character drift"])
    async def test_an_unrecognisable_severity_fails_the_scene(self, monkeypatch, severity):
        """The asymmetry that makes the rest safe. `has_critical_errors`, the
        character_consistency cap and `_fix_guide` all branch on this exact
        string, so a severity outside {CRITICAL, HIGH, MINOR} silently disables
        all three — the model flagged something and the score does not show it.
        Unlike a missing timestamp, there is no safe default: we do not know
        whether the video passed."""
        entry = {"time_range": "3s-5s", "description": "character morphs"}
        if severity is not None:
            entry["severity"] = severity
        vr = self._patched(monkeypatch, {
            "dimensions": dict(self.GOOD_DIMS), "errors": [entry], "usable_segments": []})
        with pytest.raises(RuntimeError, match="no usable severity"):
            await vr.review_scene_video(dict(self.SCENE), [])

    @pytest.mark.asyncio
    async def test_an_unreadable_segment_is_dropped_not_raised(self, monkeypatch):
        """A lost segment errs toward "less usable footage", which cannot turn
        a bad video into a good score the way a lost CRITICAL can — so it is a
        drop, not a failure. It is still logged."""
        vr = self._patched(monkeypatch, {
            "dimensions": dict(self.GOOD_DIMS),
            "errors": [],
            "usable_segments": [
                {"time_range": "0s-4s", "score": 8.0},
                {"time_range": "4s-8s"},          # no score — unreadable
                {"timeRange": "0s-2s", "score": 7.0},  # near-miss key — repaired
                "not even a dict",
            ],
        })
        review = await vr.review_scene_video(dict(self.SCENE), [])
        assert [(s.time_range, s.score) for s in review.usable_segments] == [
            ("0s-4s", 8.0), ("0s-2s", 7.0)]

    @pytest.mark.asyncio
    async def test_a_well_formed_critical_still_caps_the_score(self, monkeypatch):
        """The other half of the same property: a CRITICAL that IS readable
        must go on capping the score, so the strictness above is not covering
        for a parser that stopped working."""
        vr = self._patched(monkeypatch, {
            "dimensions": {"character_consistency": 9.0, "prompt_adherence": 9.0,
                           "motion_quality": 9.0, "visual_fidelity": 9.0,
                           "temporal_coherence": 9.0, "composition": 9.0},
            "errors": [{"severity": "critical", "time_range": "3s-5s",
                        "description": "the dog becomes a cat"}],
            "usable_segments": [],
        })
        review = await vr.review_scene_video(dict(self.SCENE), [])
        assert review.has_critical_errors is True
        assert review.dimensions.character_consistency == 3.0
        assert review.overall_score <= 5.9
        assert review.verdict in ("poor", "unusable")

    @pytest.mark.asyncio
    async def test_a_plain_string_error_is_still_accepted(self, monkeypatch):
        """The documented legacy shape. Strictness must not break it."""
        vr = self._patched(monkeypatch, {
            "dimensions": {"character_consistency": 8.0},
            "errors": ["camera drifts after 4s"],
            "usable_segments": [],
        })
        review = await vr.review_scene_video(dict(self.SCENE), [])
        assert [e.description for e in review.errors] == ["camera drifts after 4s"]
        assert review.errors[0].severity == "HIGH"


# ---------------------------------------------------------------------------
# drawtext: the probe is an optimisation, not a correctness check
# ---------------------------------------------------------------------------

class TestDrawtextRuntimeFallback:
    def test_extraction_retries_without_drawtext_when_the_filter_fails(
        self, synthetic_video, monkeypatch
    ):
        """`ffmpeg -filters` proves drawtext is compiled in, not that it can
        render. A build with libfreetype but no resolvable font lists the
        filter and then dies on "Cannot find a valid font for the family Sans"
        — the original symptom again, on a box where the probe says everything
        is fine. One retry makes the probe an optimisation.

        The failure is forced through `_frame_filter` rather than by trusting
        this machine's ffmpeg, so the retry is exercised on a runner that has a
        working drawtext as well as on one that has none.
        """
        import agent.services.video_reviewer as vr

        seen = []

        def fake_filter(fps, drawtext=None):
            seen.append(drawtext)
            chain = f"fps={fps},scale=320:-1"
            return chain + ",definitely_not_a_real_filter" if drawtext else chain

        monkeypatch.setattr(vr, "_has_drawtext", lambda: True)
        monkeypatch.setattr(vr, "_frame_filter", fake_filter)

        with tempfile.TemporaryDirectory() as out_dir:
            sheets, total_frames, timestamped = vr._create_contact_sheets(
                str(synthetic_video), 4, out_dir)

            assert seen == [True, False]     # tried timestamped, then fell back
            assert timestamped is False      # and says so, rather than guessing
            assert total_frames == 8
            assert len(sheets) == 1 and sheets[0].stat().st_size > 0

    def test_a_failure_unrelated_to_drawtext_is_not_retried_away(
        self, synthetic_video, monkeypatch
    ):
        """The retry exists for one cause. A genuinely broken input must still
        surface as an error instead of being masked by a second attempt."""
        import agent.services.video_reviewer as vr

        monkeypatch.setattr(vr, "_has_drawtext", lambda: False)
        with tempfile.TemporaryDirectory() as out_dir:
            with pytest.raises(RuntimeError, match="Frame extraction failed"):
                vr._create_contact_sheets(str(Path(out_dir) / "nope.mp4"), 4, out_dir)


# ---------------------------------------------------------------------------
# one review, one provider
# ---------------------------------------------------------------------------

class TestRoleIsPinnedForTheWholeReview:
    @pytest.mark.asyncio
    async def test_the_role_is_resolved_once_and_reused_for_every_scene(self, monkeypatch):
        """Each scene awaits a download, an executor hop and a subprocess, so
        the loop yields repeatedly — and providers.json is documented as safe
        to hand-edit while a dashboard GET hot-reloads it. Resolving per scene
        let scenes 4..N run on a different backend than scenes 1..3, and
        `overall_score` then averages two of them with no record of which
        produced what.
        """
        import agent.services.video_reviewer as vr

        scenes = [{"id": f"s{i}", "vertical_video_url": f"https://example.test/{i}.mp4"}
                  for i in range(3)]

        async def fake_list_scenes(vid):
            return scenes

        async def fake_characters(pid):
            return []

        resolved = []

        def fake_resolve(role_name):
            resolved.append(role_name)
            return {"provider": "claude", "model": "sonnet", "effort": "high"}

        seen_roles = []

        async def fake_scene_review(scene, characters, **kwargs):
            seen_roles.append(kwargs.get("role"))
            return vr.SceneReview(
                scene_id=scene["id"], overall_score=8.0, verdict="good",
                dimensions=vr.DimensionScores(
                    character_consistency=8.0, prompt_adherence=8.0, motion_quality=8.0,
                    visual_fidelity=8.0, temporal_coherence=8.0, composition=8.0),
                errors=[], usable_segments=[], fix_guide="", frames_analyzed=9, fps_used=4.0)

        monkeypatch.setattr(vr, "list_scenes", fake_list_scenes)
        monkeypatch.setattr(vr, "get_project_characters", fake_characters)
        monkeypatch.setattr(vr, "resolve_role", fake_resolve)
        monkeypatch.setattr(vr, "review_scene_video", fake_scene_review)

        review = await vr.review_video("v1", "p1")

        assert resolved == ["video_review"]          # once, not once per scene
        assert len(seen_roles) == 3
        assert all(r == {"provider": "claude", "model": "sonnet", "effort": "high"}
                   for r in seen_roles)
        assert review.scenes_reviewed == 3
