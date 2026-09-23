"""Video review engine — frame extraction + Claude Vision analysis.

Two analysis backends:
  1. CLI subprocess (claude/agy/codex, default) — no API key needed, uses contact sheets
  2. Anthropic SDK (if ANTHROPIC_API_KEY set) — direct API, individual frames
"""
import asyncio
import base64
import functools
import json
import logging
import os
import re
import subprocess
import tempfile
import shutil
from pathlib import Path

import ssl

import aiohttp
import certifi

from agent import config
from agent.config import (
    ANTHROPIC_API_KEY,
    REVIEW_MODEL,
    REVIEW_FPS_LIGHT,
    REVIEW_FPS_DEEP,
    REVIEW_MAX_FRAMES,
    REVIEW_CLI_TIMEOUT_S,
    REVIEW_SHEET_COLS,
    REVIEW_SHEET_ROWS,
)
from agent.db.crud import list_scenes, get_project_characters
from agent.models.review import DimensionScores, SceneReview, SegmentScore, VideoError, VideoReview
from agent.services.cli_providers import (  # noqa: F401  (PROVIDER_BINARIES re-exported)
    PROVIDER_BINARIES,
    resolve_role,
)

logger = logging.getLogger(__name__)


# ─── Scoring helpers ─────────────────────────────────────────

_WEIGHTS = {
    "character_consistency": 0.25,
    "prompt_adherence": 0.20,
    "motion_quality": 0.20,
    "visual_fidelity": 0.15,
    "temporal_coherence": 0.10,
    "composition": 0.10,
}


def _compute_overall(dims: dict) -> float:
    return round(sum(dims[k] * w for k, w in _WEIGHTS.items()), 2)


def _verdict(score: float) -> str:
    if score >= 9.0:
        return "excellent"
    if score >= 7.5:
        return "good"
    if score >= 6.0:
        return "acceptable"
    if score >= 4.0:
        return "poor"
    return "unusable"


def _fix_guide(dims: dict, errors: list) -> str:
    """Generate fix guide based on lowest dimension and critical error patterns."""
    critical_types = set()
    for err in errors:
        if err.severity == "CRITICAL":
            desc = err.description.lower()
            if "drift" in desc or "morph" in desc or "limb" in desc or "breed" in desc:
                critical_types.add("drift")
            if "swap" in desc or "wrong character" in desc:
                critical_types.add("breed_swap")
            if "count" in desc or "number of character" in desc:
                critical_types.add("count")
            if "logo" in desc or "brand" in desc:
                critical_types.add("logo")
            if "role" in desc or "wrong action" in desc:
                critical_types.add("role")
        elif err.severity == "HIGH":
            desc = err.description.lower()
            if "reverse" in desc:
                critical_types.add("reverse")

    if critical_types:
        hints = []
        if "drift" in critical_types:
            hints.append("simplify prompt, add 'steady camera, minimal movement'")
        if "breed_swap" in critical_types:
            hints.append("use stronger color contrast between characters")
        if "count" in critical_types:
            hints.append("make ONE character dominant, others in background")
        if "logo" in critical_types:
            hints.append("add 'no brand logos, no text' to prompt")
        if "role" in critical_types:
            hints.append("rewrite prompt to clarify which character does which action")
        if "reverse" in critical_types:
            hints.append("regenerate video (reverse motion is random, retry may fix)")
        return "REGENERATE_IMAGE then GENERATE_VIDEO: " + "; ".join(hints)

    lowest = min(dims, key=dims.get)
    guides = {
        "character_consistency": "Check character references, consider EDIT_IMAGE with closer framing",
        "prompt_adherence": "Rewrite scene prompt to be more specific, then REGENERATE_IMAGE",
        "motion_quality": "Regenerate video (motion artifacts are random, retry may fix)",
        "visual_fidelity": "Consider UPSCALE_VIDEO or REGENERATE_IMAGE with better lighting",
        "temporal_coherence": "Regenerate video, check scene lighting consistency",
        "composition": "Edit video_prompt camera directions, then regenerate",
    }
    return guides[lowest]


# ─── Frame extraction ─────────────────────────────────────────

_ssl_ctx = ssl.create_default_context(cafile=certifi.where())


class _URLExpiredError(Exception):
    """Raised when a GCS signed URL returns 400 (expired)."""


async def _download_video(url: str, dest: Path) -> None:
    """Download video from URL to local path. Raises _URLExpiredError on 400."""
    conn = aiohttp.TCPConnector(ssl=_ssl_ctx)
    async with aiohttp.ClientSession(connector=conn) as session:
        async with session.get(url) as resp:
            if resp.status == 400:
                raise _URLExpiredError(f"URL expired (400): {url[:80]}")
            resp.raise_for_status()
            with open(dest, "wb") as f:
                async for chunk in resp.content.iter_chunked(65536):
                    f.write(chunk)


async def _download_via_get_media(media_id: str, dest: Path) -> None:
    """Re-fetch a clip through the media record when its stored url has expired.

    The two transports answer differently: the batch path hands back a freshly
    signed url to download, the legacy REST path inlined the bytes as base64.
    Try the url first, fall back to the encoded content.
    """
    from agent.services.flow_client import get_flow_client

    client = get_flow_client()
    result = await client.get_media(media_id)
    if result.get("error"):
        raise ValueError(f"get_media failed for {media_id}: {result['error']}")

    data = result.get("data", result)
    if not isinstance(data, dict):
        raise ValueError(f"Unreadable get_media response for {media_id}")

    video = data.get("video") if isinstance(data.get("video"), dict) else {}
    image = data.get("image") if isinstance(data.get("image"), dict) else {}

    url = video.get("fifeUrl") or data.get("fifeUrl")
    if url:
        await _download_video(url, dest)
        logger.info("Downloaded %s via a freshly signed url", media_id[:12])
        return

    encoded = video.get("encodedVideo") or image.get("encodedImage") or data.get("encodedVideo")
    if not encoded:
        raise ValueError(f"No video url or encoded content in get_media response for {media_id}")

    video_bytes = base64.standard_b64decode(encoded)
    with open(dest, "wb") as f:
        f.write(video_bytes)
    logger.info("Downloaded %s via get_media (%d bytes)", media_id[:12], len(video_bytes))


def _ffmpeg_bin() -> str:
    env_bin = os.environ.get("FFMPEG_BIN")
    if env_bin:
        return env_bin
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _extract_frames(video_path: str, fps: float, out_dir: str) -> list:
    """Extract frames as JPEGs using ffmpeg. Returns sorted list of frame paths."""
    cmd = [
        _ffmpeg_bin(), "-y", "-i", video_path,
        "-vf", f"fps={fps},scale=640:-1",
        "-q:v", "4",
        f"{out_dir}/frame_%04d.jpg",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed: {result.stderr[-500:]}")
    return sorted(Path(out_dir).glob("frame_*.jpg"))


def _frame_to_base64(path: Path) -> str:
    return base64.standard_b64encode(path.read_bytes()).decode()


@functools.lru_cache(maxsize=1)
def _has_drawtext() -> bool:
    """Whether this ffmpeg build carries the `drawtext` filter.

    Homebrew's ffmpeg 8.x is built without libfreetype, so `drawtext` is simply
    absent and any filter chain naming it aborts with "No such filter:
    'drawtext'". That took down the whole review path, not just the timestamps
    it was there to draw. Probe once and degrade to untimestamped frames.
    """
    try:
        out = subprocess.run(
            [_ffmpeg_bin(), "-hide_banner", "-filters"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning("Could not list ffmpeg filters (%s) — assuming no drawtext", e)
        return False
    present = re.search(r"^\s*\S+\s+drawtext\s", out.stdout, re.MULTILINE) is not None
    if not present:
        logger.warning(
            "ffmpeg has no drawtext filter (no libfreetype) — contact sheets will "
            "carry no burned-in timestamps; the vision prompt compensates by "
            "describing frame order and interval instead"
        )
    return present


def _frame_filter(fps: float, drawtext: bool | None = None) -> str:
    """Filter chain for contact-sheet frames, timestamped where ffmpeg allows."""
    if drawtext is None:
        drawtext = _has_drawtext()
    chain = f"fps={fps},scale=320:-1"
    if drawtext:
        chain += (
            ",drawtext=text='%{pts\\:hms}':x=5:y=5:fontsize=14:"
            "fontcolor=white:borderw=1:bordercolor=black"
        )
    return chain


def _create_contact_sheets(
    video_path: str, fps: float, out_dir: str
) -> tuple[list[Path], int, bool]:
    """Extract all frames and tile them into REVIEW_SHEET_COLSxREVIEW_SHEET_ROWS sheets.

    Returns (sheet_paths in chronological order, total_frames after any
    REVIEW_MAX_FRAMES cap, whether the frames carry burned-in timestamps).

    The caller is told what actually happened rather than re-deriving it from
    `_has_drawtext()`: extraction can fall back to untimestamped frames at
    runtime even on a build that lists the filter, and `_analyze_cli` has to
    word the prompt for the sheets it really got.
    """
    frames_dir = Path(out_dir) / "frames"
    frames_dir.mkdir(exist_ok=True)

    def _extract(with_drawtext: bool):
        return subprocess.run(
            [
                _ffmpeg_bin(), "-y", "-i", video_path,
                "-vf", _frame_filter(fps, with_drawtext),
                "-q:v", "2",
                f"{frames_dir}/frame_%04d.jpg",
            ],
            capture_output=True, text=True,
        )

    timestamped = _has_drawtext()
    result = _extract(timestamped)
    if result.returncode != 0 and timestamped:
        # The probe proves drawtext is compiled in, not that it can render. An
        # ffmpeg with libfreetype but no resolvable font lists the filter and
        # then dies on "Cannot find a valid font for the family Sans" — the
        # original symptom all over again, on a box where the probe says
        # everything is fine. One retry makes the probe an optimisation rather
        # than a load-bearing correctness check.
        tail = (result.stderr or "").strip().splitlines()
        logger.warning(
            "Frame extraction failed with drawtext (%s) — retrying untimestamped",
            tail[-1] if tail else "no stderr",
        )
        timestamped = False
        result = _extract(False)
    if result.returncode != 0:
        raise RuntimeError(f"Frame extraction failed: {result.stderr[-500:]}")

    frames = sorted(frames_dir.glob("frame_*.jpg"))
    if len(frames) > REVIEW_MAX_FRAMES:
        step = len(frames) / REVIEW_MAX_FRAMES
        frames = [frames[int(i * step)] for i in range(REVIEW_MAX_FRAMES)]

    per_sheet = REVIEW_SHEET_COLS * REVIEW_SHEET_ROWS
    sheets = []
    for sheet_idx, start in enumerate(range(0, len(frames), per_sheet)):
        chunk = frames[start:start + per_sheet]
        chunk_dir = Path(out_dir) / f"_chunk_{sheet_idx:02d}"
        chunk_dir.mkdir(exist_ok=True)
        for i, frame_path in enumerate(chunk, start=1):
            target_link = chunk_dir / f"f_{i:04d}.jpg"
            try:
                os.symlink(frame_path.resolve(), target_link)
            except OSError:
                shutil.copy2(frame_path.resolve(), target_link)
        output = Path(out_dir) / f"sheet_{sheet_idx:02d}.jpg"
        # Pick the largest divisor of the chunk size (up to REVIEW_SHEET_COLS) as the
        # column count, so every cell in the tile is filled — zero unfilled cells for any
        # chunk size. A fixed/undersized-but-not-exact layout leaves unfilled cells
        # rendered as a solid color block (not blank), which vision models can and do
        # misread as a defect in the source video (confirmed via a live review call).
        cols_eff = max(c for c in range(1, REVIEW_SHEET_COLS + 1) if len(chunk) % c == 0)
        rows_eff = len(chunk) // cols_eff
        tile_cmd = [
            _ffmpeg_bin(), "-y",
            "-i", f"{chunk_dir}/f_%04d.jpg",
            "-vf", f"tile={cols_eff}x{rows_eff}:nb_frames={len(chunk)}",
            "-q:v", "2", str(output),
        ]
        result = subprocess.run(tile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Contact sheet tiling failed: {result.stderr[-500:]}")
        sheets.append(output)

    return sheets, len(frames), timestamped


# ─── Claude Vision analysis ───────────────────────────────────

_VISION_PROMPT = """\
You are an expert AI video quality reviewer analyzing {n_frames} frames at {fps}fps from an 8-second AI-generated video.{sheet_note}

SCENE IMAGE PROMPT: {prompt}
SCENE VIDEO PROMPT: {video_prompt}
EXPECTED CHARACTERS: {character_names}

== SCORING DIMENSIONS (0.0-10.0 each) ==
1. character_consistency - Do characters match references? Stable species/breed/limb count/clothing?
2. prompt_adherence - Does video match prompt? Correct characters, actions, roles?
3. motion_quality - Smooth motion? No jitter/reverse motion/teleportation?
4. visual_fidelity - Clear resolution? No artifacts/blur/brand logos?
5. temporal_coherence - Consistent lighting/shadows/background/scale across frames?
6. composition - Framing matches camera directions? Good depth/balance?

== ERROR DETECTION RUBRIC ==
Classify each error by severity tier:

CRITICAL (auto-score affected dimension 0-3):
1. Character Drift -- character morphs mid-video (extra limbs, breed changes, bipedal to quadruped). Very common after 3-4s.
2. Breed Swap -- similar characters get swapped (Doberman to Rottweiler, wrong character in wrong role).
3. Role Reversal -- wrong character performs the action (villain wins instead of hero). ~50% of fight scenes.
4. Brand Logo -- AI generates real brand logos (FENDI, Gucci, Nike, etc.). Legal liability.
5. Character Count -- rendered count differs from requested count.

HIGH (score affected dimension 4-6):
6. Camera Drift -- sudden unwanted zoom, rotation, or angle shift. ~60% of videos after 4s.
7. Object Morph -- held items change shape (envelope becomes clutch, phone becomes tablet).
8. Reverse Motion -- character does action then undoes it (steps forward then back). ~30%.
9. Human Hands -- anthropomorphic/animal characters get human hands or fingers.
10. Scale Break -- characters suddenly giant or tiny relative to environment.

MINOR (score affected dimension 7-8, still acceptable):
11. Prop Count -- small props change count (3 candles become 4).
12. Clothing Detail -- texture shift (matte becomes glossy).
13. Background Blur -- signage becomes garbled text.
14. Accessory Change -- small accessories appear/disappear.

== INSTRUCTIONS ==
- For each error found, include: severity, time_range (e.g. "3s-5s"), and description.
- Identify usable_segments: continuous segments free of CRITICAL or HIGH errors.
- If ANY CRITICAL error is present, character_consistency must be 3.0 or below.

Return ONLY valid JSON (no markdown):
{{
  "dimensions": {{"character_consistency": N, "prompt_adherence": N, "motion_quality": N, "visual_fidelity": N, "temporal_coherence": N, "composition": N}},
  "errors": [
    {{"severity": "CRITICAL|HIGH|MINOR", "time_range": "Xs-Ys", "description": "what happened"}},
    ...
  ],
  "usable_segments": [{{"time_range": "Xs-Ys", "score": N}}, ...]
}}"""


def _parse_character_names(scene: dict) -> list[str]:
    names = scene.get("character_names")
    if not names:
        return []
    try:
        return json.loads(names) if isinstance(names, str) else list(names)
    except (json.JSONDecodeError, TypeError):
        return []


def _build_prompt(n_frames: int, fps: float, n_sheets: int, scene: dict) -> str:
    sheet_note = (
        f" The frames are provided across {n_sheets} sequential contact sheets "
        f"(each fully packed, up to {REVIEW_SHEET_COLS}x{REVIEW_SHEET_ROWS} cells — the last sheet "
        f"may use a different grid shape to fit its frame count exactly, in chronological order — "
        f"sheet 1 is earliest, sheet {n_sheets} is latest)."
        if n_sheets > 1 else ""
    )
    return _VISION_PROMPT.format(
        n_frames=n_frames,
        fps=fps,
        sheet_note=sheet_note,
        prompt=scene.get("prompt") or "",
        video_prompt=scene.get("video_prompt") or "",
        character_names=", ".join(_parse_character_names(scene)) or "none specified",
    )


# Model answers stray on field *names* far more often than on values. These are
# the near-misses worth absorbing; anything outside the map is left alone and
# judged on its merits below. Keys are compared with underscores stripped and
# lowercased, so `timeRange` and `time_range` land on the same entry.
_ERROR_KEY_ALIASES = {
    "timerange": "time_range",
    "time": "time_range",
    "desc": "description",
    "level": "severity",
}
_SEGMENT_KEY_ALIASES = {
    "timerange": "time_range",
    "time": "time_range",
}
_SEVERITIES = ("CRITICAL", "HIGH", "MINOR")


def _normalise_keys(entry: dict, aliases: dict) -> dict:
    """Rename near-miss keys onto the names the rubric asked for."""
    return {
        aliases.get(str(k).replace("_", "").lower(), k): v
        for k, v in entry.items()
    }


def _parse_json_response(raw: str) -> dict:
    """Extract JSON from a response that may contain markdown fences."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    # Also try to find JSON object in free text
    raw = raw.strip()
    if not raw.startswith("{"):
        start = raw.find("{")
        if start >= 0:
            raw = raw[start:]
    return json.loads(raw)


# ─── Backend 1: CLI providers (default, no API key needed) ───

# PROVIDER_BINARIES and resolve_role are imported from agent.services.cli_providers,
# which is where everything the three CLIs disagree about now lives.


async def _communicate_with_timeout(proc, provider: str) -> tuple:
    try:
        return await asyncio.wait_for(proc.communicate(), timeout=REVIEW_CLI_TIMEOUT_S)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise RuntimeError(f"{provider} CLI timed out after {REVIEW_CLI_TIMEOUT_S}s")


async def _spawn_and_check(args: tuple, provider: str) -> bytes:
    # stdin is closed deliberately. All three CLIs read piped stdin when it is
    # not a terminal and append it to the prompt — codex says so in its own
    # --help ("stdin is appended as a `<stdin>` block"). Under uvicorn stdin is
    # whatever the launching shell handed down, which is nothing we want in a
    # vision prompt.
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await _communicate_with_timeout(proc, provider)
    if proc.returncode != 0:
        # Both streams. claude puts the readable sentence on stdout ("There's an
        # issue with the selected model (...)") and buries the machine tag under
        # paragraphs of unrelated context advice on stderr; codex is the other
        # way round. Tail-slice each, because the useful part is always last.
        detail = stderr.decode()[-500:]
        out = stdout.decode().strip()
        if out:
            detail = f"{detail} | stdout: {out[-300:]}"
        raise RuntimeError(f"{provider} CLI failed (rc={proc.returncode}): {detail}")
    return stdout


def _model_effort_args(model: str | None, effort: str | None) -> list:
    """claude and agy happen to spell these the same way; codex does not."""
    args = []
    if model:
        args += ["--model", model]
    if effort:
        args += ["--effort", effort]
    return args


async def _run_claude_cli(
    prompt: str,
    *,
    model: str | None = None,
    effort: str | None = None,
    add_dirs: tuple = (),
) -> str:
    args = ["claude", "-p", prompt, "--allowedTools", "Read", "--output-format", "text"]
    for d in add_dirs:
        args += ["--add-dir", str(d)]
    args += _model_effort_args(model, effort)
    stdout = await _spawn_and_check(tuple(args), "claude")
    return stdout.decode()


# agy is agentic: handed a bare file path it reaches for a shell command to look
# at the file, headless mode cannot prompt for that permission, so the tool is
# auto-denied and the run returns an empty response on a *zero* exit code.
# Pointing it at its own file-reading tool is what makes the read happen
# unprivileged — verified against agy 1.2.7. The remedy agy itself suggests in
# that error, --dangerously-skip-permissions, auto-approves every tool including
# arbitrary shell commands, for a job whose whole need is reading three JPEGs.
_AGY_READ_STEER = (
    "Use your file-reading tool to read the image file(s). "
    "Do NOT run any shell command."
)


def _parse_agy_envelope(raw: str) -> str:
    """Pull the answer out of `agy --output-format json`, or explain the silence."""
    raw = raw.strip()
    if not raw:
        raise RuntimeError("agy CLI returned no output")
    try:
        env = json.loads(raw)
    except json.JSONDecodeError:
        # Permission refusals and startup errors arrive as bare prose on a zero
        # exit code, so _spawn_and_check never sees them. They land here.
        raise RuntimeError(f"agy CLI returned non-JSON output: {raw[:300]}")
    if not isinstance(env, dict):
        raise RuntimeError(f"agy CLI returned unexpected JSON: {raw[:300]}")

    response = (env.get("response") or "").strip()
    denied = env.get("denied_actions") or []
    if denied:
        # Any denial at all, answer or no answer. The prompt tells agy to read
        # the sheets with its file-reading tool and run no shell command, so a
        # denial means the steering did not hold — and the prompt also carries
        # the full scoring rubric, the scene's image prompt, its video prompt
        # and the character names. That is more than enough for a plausible
        # review written entirely from the text, without the images ever being
        # looked at. A denial plus a confident answer is the more dangerous of
        # the two cases, not the safer one.
        #
        # status stays "SUCCESS" here, which is why this is caught by name
        # rather than by the status field.
        names = ", ".join(
            str(d.get("display_name") or d.get("action"))
            for d in denied if isinstance(d, dict)
        )
        raise RuntimeError(
            f"agy CLI had tools auto-denied headlessly ({names or denied}) — "
            f"its {len(response)}-character answer cannot be trusted to have "
            f"come from the images"
        )
    status = env.get("status")
    if status is not None and status != "SUCCESS":
        raise RuntimeError(f"agy CLI reported status={status!r}: {raw[:300]}")
    if not response:
        raise RuntimeError("agy CLI returned an empty response")
    return response


async def _run_agy_cli(
    prompt: str,
    *,
    model: str | None = None,
    effort: str | None = None,
    add_dirs: tuple = (),
) -> str:
    # --print-timeout is set just inside our own wait_for so agy gets to finish
    # and report on its own terms rather than being SIGKILLed with its answer
    # still buffered. Left unset it defaults to 0, meaning "wait forever".
    print_timeout = max(10, int(REVIEW_CLI_TIMEOUT_S) - 5)
    args = [
        "agy", "-p", prompt,
        "--output-format", "json",
        "--print-timeout", f"{print_timeout}s",
    ]
    for d in add_dirs:
        args += ["--add-dir", str(d)]
    if model and effort:
        # agy's slugs carry the effort (gemini-3.8-flash-low), so the pair is
        # rejected unless it is redundant. The API refuses to store both; this
        # covers a hand-edited providers.json, which is supported.
        logger.warning(
            "Dropping effort %r — agy model %r already names its effort", effort, model
        )
        effort = None
    args += _model_effort_args(model, effort)
    stdout = await _spawn_and_check(tuple(args), "agy")
    return _parse_agy_envelope(stdout.decode())


async def _run_codex_cli(
    prompt: str,
    contact_sheets: list,
    *,
    model: str | None = None,
    effort: str | None = None,
) -> str:
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        out_path = Path(tmp.name)
    try:
        # read-only, not --dangerously-bypass-approvals-and-sandbox: -i hands
        # codex the image bytes directly, so the run needs no filesystem write
        # and no shell at all. read-only still implies approval:never, so it
        # cannot hang waiting for a prompt. --skip-git-repo-check keeps the run
        # working if the server is ever started outside a git checkout.
        args = ["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only"]
        for sheet in contact_sheets:
            args += ["-i", str(sheet)]
        args += ["-o", str(out_path)]
        if model:
            args += ["-m", model]
        if effort:
            # codex has no --effort; reasoning level is a config override, and
            # -c parses its value as TOML, hence the quotes around the string.
            args += ["-c", f'model_reasoning_effort="{effort}"']
        args.append(prompt)
        await _spawn_and_check(tuple(args), "codex")
        answer = out_path.read_text(encoding="utf-8").strip()
        if not answer:
            raise RuntimeError(
                "codex CLI exited cleanly but wrote no answer to its output file"
            )
        return answer
    finally:
        out_path.unlink(missing_ok=True)


async def _analyze_cli(
    contact_sheets: list[Path],
    n_frames: int,
    fps: float,
    scene: dict,
    timestamped: bool | None = None,
    role: dict | None = None,
) -> dict:
    """Analyze contact sheets via the CLI provider configured for video_review.

    `role` is passed in by a multi-scene review so every scene runs on the same
    backend — see `review_video`.
    """
    if timestamped is None:
        timestamped = _has_drawtext()
    n_sheets = len(contact_sheets)
    base_prompt = _build_prompt(n_frames, fps, n_sheets, scene)

    if role is None:
        role = resolve_role("video_review")
    provider = role["provider"]
    logger.info(
        "Calling %s CLI for vision analysis (%d frames, %d sheets, model=%s, effort=%s, timestamps=%s)",
        provider, n_frames, n_sheets,
        role["model"] or "default", role["effort"] or "default", timestamped,
    )

    if timestamped:
        stamp_note = "with timestamps"
    else:
        # Without burned-in timestamps the model still has to answer in
        # time_range, so hand it the arithmetic instead of the labels.
        stamp_note = (
            f"without timestamps — frames run left to right then top to bottom, "
            f"one every {1 / fps:.2f}s, so frame N starts at (N-1)*{1 / fps:.2f}s"
        )

    if n_sheets == 1:
        sheet_intro = f"It is a contact sheet of {n_frames} video frames at {fps}fps {stamp_note}."
    else:
        sheet_intro = (
            f"These are {n_sheets} sequential contact sheets covering {n_frames} video frames "
            f"at {fps}fps {stamp_note}, in chronological order (sheet 1 is earliest)."
        )

    if provider == "codex":
        full_prompt = f"{sheet_intro}\n\n{base_prompt}"
        raw = await _run_codex_cli(
            full_prompt, contact_sheets, model=role["model"], effort=role["effort"]
        )
    else:
        if n_sheets == 1:
            read_instruction = f"Read the image at {contact_sheets[0]}."
        else:
            sheet_list = ", ".join(str(s) for s in contact_sheets)
            read_instruction = f"Read the images at: {sheet_list}, in that order."
        if provider == "agy":
            read_instruction = f"{read_instruction} {_AGY_READ_STEER}"
        full_prompt = f"{read_instruction} {sheet_intro}\n\n{base_prompt}"
        # The sheets live in a TemporaryDirectory outside the server's cwd;
        # naming it keeps the read inside a workspace the CLI was told about.
        add_dirs = tuple(sorted({str(Path(s).parent) for s in contact_sheets}))
        runner = {"claude": _run_claude_cli, "agy": _run_agy_cli}[provider]
        raw = await runner(
            full_prompt, model=role["model"], effort=role["effort"], add_dirs=add_dirs
        )
    return _parse_json_response(raw)


# ─── Backend 2: Anthropic SDK (when API key is set) ──────────

async def _analyze_sdk(
    frames: list,
    fps: float,
    scene: dict,
    characters: list,
) -> dict:
    """Send individual frames to Claude Vision via Anthropic SDK."""
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    character_names = _parse_character_names(scene)
    # SDK path sends individual frames, not tiled sheets; n_sheets=1 renders no sheet_note.
    prompt_text = _build_prompt(len(frames), fps, 1, scene)

    content = []
    for char in characters:
        slug = char.get("slug") or ""
        name = char.get("name", "")
        if char.get("reference_image_url") and ((slug and slug in character_names) or (name and name in character_names)):
            content.append({"type": "text", "text": f"Character reference -- {char['name']}:"})
            content.append({"type": "image", "source": {"type": "url", "url": char["reference_image_url"]}})
    if content:
        content.append({"type": "text", "text": "Video frames to analyze:"})

    for frame_path in frames:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": _frame_to_base64(frame_path)},
        })
    content.append({"type": "text", "text": prompt_text})

    response = await client.messages.create(
        model=REVIEW_MODEL, max_tokens=1024,
        messages=[{"role": "user", "content": content}],
    )
    return _parse_json_response(response.content[0].text)


# ─── Public API ───────────────────────────────────────────────

async def review_scene_video(
    scene: dict,
    characters: list,
    mode: str = "light",
    orientation: str = "VERTICAL",
    project_id: str = None,
    role: dict | None = None,
) -> SceneReview:
    """Review a single scene's video via frame extraction + Claude Vision.

    `role` pins the provider/model/effort. `review_video` resolves it once and
    passes it down; a single-scene call resolves it here.
    """
    fps = REVIEW_FPS_DEEP if mode == "deep" else REVIEW_FPS_LIGHT

    orient_prefix = "vertical" if orientation.upper() == "VERTICAL" else "horizontal"
    video_url = scene.get(f"{orient_prefix}_video_url")

    if not video_url:
        raise ValueError(f"No video URL found for scene {scene['id']} ({orientation})")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        video_path = tmp_path / "scene.mp4"

        logger.info("Downloading video for scene %s from %s", scene["id"], video_url[:80])
        try:
            await _download_video(video_url, video_path)
        except (_URLExpiredError, Exception) as e:
            # URL expired or download failed — fall back to get_media API
            media_id = scene.get(f"{orient_prefix}_video_media_id")
            if not media_id:
                raise ValueError(f"No media_id to refresh URL for scene {scene['id']}")
            logger.info("URL download failed for scene %s (%s), fetching via get_media %s",
                        scene["id"], type(e).__name__, media_id[:12])
            await _download_via_get_media(media_id, video_path)

        if ANTHROPIC_API_KEY:
            # SDK path: individual frames
            logger.info("Extracting frames at %sfps (SDK mode)", fps)
            frames = await asyncio.get_event_loop().run_in_executor(
                None, _extract_frames, str(video_path), fps, tmp
            )
            if not frames:
                raise RuntimeError(f"No frames extracted from scene {scene['id']}")
            if len(frames) > REVIEW_MAX_FRAMES:
                step = len(frames) / REVIEW_MAX_FRAMES
                frames = [frames[int(i * step)] for i in range(REVIEW_MAX_FRAMES)]
            n_frames = len(frames)
            logger.info("Analyzing %d frames via Anthropic SDK", n_frames)
            result = await _analyze_sdk(frames, fps, scene, characters)
        else:
            # CLI path: contact sheets (no API key needed)
            logger.info("Creating contact sheets at %sfps (CLI mode)", fps)
            contact_sheets, n_frames, timestamped = await asyncio.get_event_loop().run_in_executor(
                None, _create_contact_sheets, str(video_path), fps, tmp
            )
            if not contact_sheets or not all(s.exists() for s in contact_sheets):
                raise RuntimeError(f"Contact sheets not created for scene {scene['id']}")
            logger.info("Analyzing %d frames across %d sheets via CLI provider", n_frames, len(contact_sheets))
            result = await _analyze_cli(
                contact_sheets, n_frames, fps, scene,
                timestamped=timestamped, role=role,
            )

    # Parse structured errors with severity.
    #
    # The three fields are NOT equal, so they are not treated equally. Only
    # `severity` can change the outcome: CRITICAL is what caps
    # character_consistency at 3.0 and forces the score below "acceptable".
    # This block used to require all three keys exactly and silently drop any
    # entry that missed one, so a model writing `timeRange` turned "this video
    # is unusable" into a clean pass. Now a missing time_range or description
    # is repaired and logged — losing those costs the reader context, not the
    # verdict — while an unrecognisable severity fails the scene, because at
    # that point we genuinely do not know whether the video passed.
    errors = []
    repaired_fields = 0
    for e in result.get("errors") or []:
        if isinstance(e, str):
            # Legacy shape: a bare sentence, no severity to lose.
            errors.append(VideoError(severity="HIGH", time_range="?", description=e))
            continue
        if not isinstance(e, dict):
            raise RuntimeError(
                f"review answer had an unreadable error entry: {str(e)[:200]}"
            )

        entry = _normalise_keys(e, _ERROR_KEY_ALIASES)
        severity = str(entry.get("severity", "")).strip().upper()
        if severity not in _SEVERITIES:
            raise RuntimeError(
                f"review answer had an error entry with no usable severity "
                f"(expected one of {list(_SEVERITIES)}): {str(e)[:200]}"
            )

        time_range = entry.get("time_range")
        if not isinstance(time_range, str) or not time_range.strip():
            time_range = "?"  # the same placeholder the legacy string path uses
            repaired_fields += 1
        description = entry.get("description")
        if not isinstance(description, str) or not description.strip():
            description = "(no description given)"
            repaired_fields += 1

        errors.append(VideoError(
            severity=severity, time_range=time_range, description=description,
        ))

    has_critical = any(e.severity == "CRITICAL" for e in errors)

    dims_raw = result.get("dimensions") or {}
    if not isinstance(dims_raw, dict) or not dims_raw:
        # Every field below has a 5.0 default, so an answer with no dimensions
        # at all becomes a complete, plausible review: 5.0 across the board,
        # verdict "poor", no errors. That is a fabricated score wearing the
        # shape of a real one, and it reads as a bad video rather than a failed
        # review. Refuse it — review_video logs and skips the scene.
        raise RuntimeError(
            f"{'CLI' if not ANTHROPIC_API_KEY else 'SDK'} answer had no dimensions: "
            f"{str(result)[:300]}"
        )

    dims = DimensionScores(
        character_consistency=float(dims_raw.get("character_consistency", 5.0)),
        prompt_adherence=float(dims_raw.get("prompt_adherence", 5.0)),
        motion_quality=float(dims_raw.get("motion_quality", 5.0)),
        visual_fidelity=float(dims_raw.get("visual_fidelity", 5.0)),
        temporal_coherence=float(dims_raw.get("temporal_coherence", 5.0)),
        composition=float(dims_raw.get("composition", 5.0)),
    )

    # Enforce: any CRITICAL error caps character_consistency at 3.0
    if has_critical and dims.character_consistency > 3.0:
        dims = dims.model_copy(update={"character_consistency": 3.0})

    dims_dict = dims.model_dump()
    overall = _compute_overall(dims_dict)

    # Force score cap when critical errors present (verdict must be poor or unusable)
    if has_critical and overall > 5.9:
        overall = 5.9

    # A segment that cannot be read is dropped rather than raised on: losing one
    # errs toward "less usable footage", which cannot turn a bad video into a
    # good score the way a lost CRITICAL can. It is still logged — the absence
    # of any signal is what kept the error-entry version of this invisible.
    usable_segments = []
    dropped_segments = 0
    for seg in result.get("usable_segments") or []:
        if not isinstance(seg, dict):
            dropped_segments += 1
            continue
        norm = _normalise_keys(seg, _SEGMENT_KEY_ALIASES)
        try:
            score = float(norm["score"])
        except (KeyError, TypeError, ValueError):
            dropped_segments += 1
            continue
        time_range = norm.get("time_range")
        usable_segments.append(SegmentScore(
            time_range=time_range if isinstance(time_range, str) and time_range.strip() else "?",
            score=score,
        ))

    if repaired_fields or dropped_segments:
        logger.warning(
            "Scene %s: review answer needed repair — %d error field(s) defaulted, "
            "%d usable segment(s) unreadable",
            scene["id"], repaired_fields, dropped_segments,
        )

    return SceneReview(
        scene_id=scene["id"],
        overall_score=overall,
        verdict=_verdict(overall),
        dimensions=dims,
        errors=errors,
        usable_segments=usable_segments,
        fix_guide=_fix_guide(dims_dict, errors),
        frames_analyzed=n_frames,
        fps_used=fps,
        has_critical_errors=has_critical,
    )


async def review_video(
    video_id: str,
    project_id: str,
    mode: str = "light",
    orientation: str = "VERTICAL",
    scene_ids: list[str] | None = None,
) -> VideoReview:
    """Review all scenes (or a subset by scene_ids) in a video."""
    scenes = await list_scenes(video_id)
    if scene_ids:
        id_set = set(scene_ids)
        scenes = [s for s in scenes if s["id"] in id_set]
    characters = await get_project_characters(project_id)

    # Resolved once, for the whole review. Each scene awaits a download, an
    # executor hop and a subprocess, so the loop below yields repeatedly — and
    # providers.json is documented as safe to hand-edit, while a dashboard GET
    # hot-reloads it. Resolving per scene let scenes 4..N run on a different
    # backend than scenes 1..3, and `overall_score` then averages two of them
    # with no record of which produced what.
    role = resolve_role("video_review")
    logger.info(
        "Reviewing %s on %s (model=%s, effort=%s)",
        video_id, role["provider"], role["model"] or "default", role["effort"] or "default",
    )

    orient_prefix = "vertical" if orientation.upper() == "VERTICAL" else "horizontal"

    scene_reviews = []
    skipped = 0

    for scene in scenes:
        video_url = scene.get(f"{orient_prefix}_video_url")
        if not video_url:
            logger.info("Skipping scene %s -- no %s video", scene["id"], orientation)
            skipped += 1
            continue

        try:
            review = await review_scene_video(
                scene, characters, mode=mode, orientation=orientation,
                project_id=project_id, role=role,
            )
            scene_reviews.append(review)
        except Exception as e:
            logger.error("Failed to review scene %s: %s", scene["id"], e)
            skipped += 1

    overall = round(sum(r.overall_score for r in scene_reviews) / len(scene_reviews), 2) if scene_reviews else 0.0

    return VideoReview(
        video_id=video_id,
        project_id=project_id,
        mode=mode,
        orientation=orientation,
        overall_score=overall,
        verdict=_verdict(overall),
        scene_reviews=scene_reviews,
        scenes_reviewed=len(scene_reviews),
        scenes_skipped=skipped,
    )
