"""ffmpeg assembly for Flow Studio — normalize shot clips + narration → final.mp4.

Each clip is re-encoded to a uniform format (resolution/fps/audio) so the concat
demuxer can stitch them with -c copy. If a shot has a TTS narration WAV, it becomes
that clip's audio and -shortest trims the clip to the narration (the storytelling
"đọc tới đâu hình tới đó" alignment); otherwise a silent track is added.
"""
import asyncio
import json
import logging
import os
from pathlib import Path

from agent.config import BASE_DIR
from agent.studio import db, hires, media_store

logger = logging.getLogger(__name__)

STUDIO_MEDIA_DIR = Path(os.environ.get("STUDIO_OUT_DIR", BASE_DIR / "studio_media"))


def _local(web_path: str) -> Path:
    """/media/<pid>/<f> → absolute local path."""
    return media_store.MEDIA_DIR / web_path.replace("/media/", "", 1)


def _res(aspect: str, short_side: int = 720) -> tuple[int, int]:
    """Output frame size for a 16:9 project, given the SHORT side (720 = HD default).

    Raised when the sources are hi-res (upsampled stills / upscaled videos) — encoding a
    1080p or 4K source into a 720p frame throws the extra resolution away. See
    `timeline_short_side()` for how it is derived from what the shots actually hold."""
    long_side = round(short_side * 16 / 9 / 2) * 2   # even, ffmpeg/x264 dislikes odd dims
    return ((short_side, long_side) if "PORTRAIT" in (aspect or "")
            else (long_side, short_side))


# Short side of a project's timeline, by what the media actually is.
_SHORT_SIDE_BY_RES = {"VIDEO_RESOLUTION_1080P": 1080, "VIDEO_RESOLUTION_4K": 2160}
# Upsampled stills are 2K/4K, but 1080p is the standard timeline to land them in.
_STILL_SHORT_SIDE = 1080


def timeline_short_side(shots: list[dict]) -> int:
    """720 unless EVERY contributing shot carries a hi-res source, in which case the highest
    resolution they share. A single HD leftover keeps the whole timeline at 720p rather than
    upscaling it on encode — mixing is what makes an export look soft."""
    contributing = [s for s in shots if s.get("video_path") or s.get("image_path")]
    if not contributing:
        return 720
    sides = []
    for s in contributing:
        if s.get("video_path"):
            if not hires.video_path_for(s):
                return 720
            sides.append(_SHORT_SIDE_BY_RES.get(s.get("upscale_res") or "", 1080))
        else:
            if not hires.path_for(s):
                return 720
            sides.append(_STILL_SHORT_SIDE)
    return min(sides)


def shot_video_path(shot: dict) -> Path | None:
    """Local file to BUILD this shot from: the 1080p/4K upscale when it exists and still
    matches the shot's current video, else the HD one. None if neither is on disk."""
    for web in (hires.video_path_for(shot), shot.get("video_path")):
        if web:
            p = _local(web) if web.startswith("/media/") else \
                STUDIO_MEDIA_DIR / web.replace("/studio-media/", "", 1)
            if p.exists() and p.stat().st_size > 0:
                return p
    return None


def shot_image_path(shot: dict) -> Path | None:
    """Local file to BUILD this shot from: the 2K/4K copy when it exists and still matches
    the shot's current image, else the HD one. None if neither is on disk."""
    for web in (hires.path_for(shot), shot.get("image_path")):
        if web:
            p = _local(web)
            if p.exists() and p.stat().st_size > 0:
                return p
    return None


async def _run(args: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {err.decode('utf-8', 'replace')[-500:]}")


async def probe_duration(path: Path) -> float:
    """Media duration in seconds, or 0.0 if it can't be determined. Never raises — if
    ffprobe isn't installed/on PATH (common on Windows) we degrade to 0 so callers fall
    back to their own timing (e.g. DaVinci export, which doesn't need ffmpeg at all)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    except (FileNotFoundError, NotImplementedError, OSError) as e:
        logger.warning("ffprobe không chạy được (%s) — dùng thời lượng mặc định", e)
        return 0.0
    out, _ = await proc.communicate()
    try:
        return float(out.decode().strip())
    except (ValueError, AttributeError):
        return 0.0


async def _normalize(src: Path, narration: Path | None, out: Path, w: int, h: int) -> None:
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
          f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24")
    args = ["ffmpeg", "-y", "-i", str(src)]
    if narration and narration.exists():
        args += ["-i", str(narration)]
    else:
        args += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    args += [
        "-filter_complex", f"[0:v]{vf}[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "44100", "-shortest", str(out),
    ]
    await _run(args)


async def _image_clip(img: Path, narration: Path | None, out: Path,
                      w: int, h: int, dur: float, ken_burns: bool) -> None:
    """Turn a still shot image into a clip of exactly `dur` seconds (+ narration audio).

    `-loop 1` holds the image; `-t dur` caps the length so it matches the narration
    beat, and the narration (if any) becomes the audio track. With `ken_burns` a slow
    zoom is applied so the slideshow isn't fully static.
    """
    fps = 24
    if ken_burns:
        frames = max(1, int(round(dur * fps)))
        # scale up first so the zoom never reveals padding, then zoompan, then fit canvas.
        vf = (
            f"scale={int(w*1.3)}:{int(h*1.3)}:force_original_aspect_ratio=increase,"
            f"crop={int(w*1.3)}:{int(h*1.3)},"
            f"zoompan=z='min(zoom+0.0007,1.18)':d={frames}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},"
            f"setsar=1,format=yuv420p"
        )
    else:
        vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
              f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p")

    args = ["ffmpeg", "-y", "-loop", "1", "-i", str(img)]
    if narration and narration.exists():
        args += ["-i", str(narration)]
    else:
        args += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    args += [
        "-t", f"{dur:.3f}",
        "-filter_complex", f"[0:v]{vf}[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(fps),
        "-c:a", "aac", "-ar", "44100", "-shortest", str(out),
    ]
    await _run(args)


# Common font locations per-OS so captions work outside Windows too.
_FONT_DIRS = [
    Path("C:/Windows/Fonts"),
    Path("/usr/share/fonts"), Path("/usr/local/share/fonts"),
    Path.home() / ".fonts", Path.home() / ".local/share/fonts",
    Path("/Library/Fonts"), Path("/System/Library/Fonts"), Path.home() / "Library/Fonts",
]
_FONT_FALLBACKS = [
    "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def label_quadrants(src: Path, out: Path, labels: list[str], font: str | None) -> bool:
    """Overlay a label at the bottom of each 2x2 quadrant of an image (used to tag the four
    angles of a location grid: Toàn cảnh / Góc ngược / Trên cao / Cận cảnh). Writes a labeled
    copy to `out`. Returns True on success, False on any failure (caller keeps the original)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        im = Image.open(src).convert("RGB")
        W, H = im.size
        hw, hh = W // 2, H // 2
        draw = ImageDraw.Draw(im, "RGBA")
        size = max(16, W // 38)
        try:
            f = ImageFont.truetype(font, size) if font else ImageFont.load_default()
        except Exception:
            f = ImageFont.load_default()
        for (qx, qy), label in zip([(0, 0), (hw, 0), (0, hh), (hw, hh)], labels):
            if not label:
                continue
            tw = draw.textlength(label, font=f)
            bx = qx + (hw - tw) / 2
            by = qy + hh - size - 16
            pad = 6
            draw.rectangle([bx - pad, by - pad, bx + tw + pad, by + size + pad], fill=(0, 0, 0, 150))
            draw.text((bx, by), label, font=f, fill=(245, 245, 248))
        out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out, "PNG")
        return True
    except Exception:
        return False


def _caption_font(preferred: str | None = None) -> str | None:
    """Resolve a usable .ttf/.otf: explicit choice (path, or a font name found in the font
    dirs) → STUDIO_CAPTION_FONT env → per-OS fallbacks. None if nothing is found."""
    cands: list[str] = []
    if preferred:
        cands.append(preferred)
        if not preferred.lower().endswith((".ttf", ".otf")) or "/" not in preferred.replace("\\", "/"):
            # a bare name like "Arial" — look it up in the font dirs
            for d in _FONT_DIRS:
                if d.exists():
                    for ext in ("ttf", "otf"):
                        cands += [str(p) for p in d.glob(f"**/*{preferred}*.{ext}")]
    if os.environ.get("STUDIO_CAPTION_FONT"):
        cands.append(os.environ["STUDIO_CAPTION_FONT"])
    cands += _FONT_FALLBACKS
    for c in cands:
        if c and Path(c).exists():
            return c
    return None


def list_fonts(limit: int = 300) -> list[dict]:
    """Scan the OS font dirs → [{name, path}] for the caption-font picker."""
    seen: set[str] = set()
    out: list[dict] = []
    for d in _FONT_DIRS:
        if not d.exists():
            continue
        for ext in ("ttf", "otf"):
            for p in sorted(d.glob(f"**/*.{ext}")):
                key = p.stem.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append({"name": p.stem, "path": str(p)})
                if len(out) >= limit:
                    return out
    return out


async def extract_last_frame(video: Path, out_jpg: Path) -> bool:
    """Grab the last frame of a clip as a JPEG (start image for the next chained clip)."""
    try:
        await _run(["ffmpeg", "-y", "-sseof", "-0.2", "-i", str(video),
                    "-frames:v", "1", "-q:v", "2", str(out_jpg)])
        return out_jpg.exists() and out_jpg.stat().st_size > 0
    except RuntimeError as e:
        logger.warning("extract_last_frame failed: %s", e)
        return False


async def apply_bgm(project: dict, final: Path) -> bool:
    """Mix the project's background-music file under the existing audio (narration) of
    `final`, in place. Music is looped to cover the whole video and lowered to
    `bgm_volume`. With ducking on (default), the music auto-dips while the narration
    plays and rises during pauses (sidechaincompress); narration stays at full level.
    No-op if the project has no music. Failures are swallowed so assembly still completes."""
    bgm = (project.get("bgm_path") or "").strip()
    if not bgm:
        return False
    music = Path(bgm)
    if not music.exists():
        logger.warning("bgm file missing, skipping: %s", bgm)
        return False
    try:
        vol = float(project.get("bgm_volume"))
    except (TypeError, ValueError):
        vol = 0.18
    vol = min(max(vol, 0.0), 1.0)
    if vol <= 0:
        return False
    duck = project.get("bgm_duck")
    duck = True if duck is None else bool(duck)
    tmp = final.with_name(f"{final.stem}_bgm.mp4")
    # input 0 = the assembled video (narration), input 1 = looped music (lowered).
    if duck:
        # music is keyed (sidechain) by the narration → dips under speech, returns in pauses.
        filt = (
            f"[1:a]aresample=44100,aformat=channel_layouts=stereo,volume={vol:.3f}[bg];"
            f"[0:a]aresample=44100,aformat=channel_layouts=stereo,asplit=2[n1][n2];"
            f"[bg][n1]sidechaincompress=threshold=0.04:ratio=10:attack=20:release=400[duck];"
            f"[n2][duck]amix=inputs=2:duration=first:normalize=0[a]"
        )
    else:
        filt = (f"[1:a]volume={vol:.3f}[bg];"
                f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]")
    try:
        await _run(["ffmpeg", "-y", "-i", str(final), "-stream_loop", "-1", "-i", str(music),
                    "-filter_complex", filt, "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-ar", "44100", "-shortest", str(tmp)])
    except RuntimeError as e:
        logger.warning("bgm mix failed, keeping video without music: %s", e)
        tmp.unlink(missing_ok=True)
        return False
    tmp.replace(final)
    return True


async def concat_videos(paths: list[Path], out: Path) -> None:
    """Concatenate clips (same codec params from Flow) into one mp4."""
    lst = out.with_name(f"{out.stem}_concat.txt")
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in paths), encoding="utf-8")
    try:
        await _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(out)])
    except RuntimeError:  # params differ → re-encode
        await _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(out)])


def _ff_path(p: str) -> str:
    """Escape a filesystem path for use inside an ffmpeg filtergraph option: forward
    slashes + escaped drive colon (e.g. C:/Fonts/arial.ttf → C\\:/Fonts/arial.ttf),
    otherwise the `:` is read as the option separator."""
    return p.replace("\\", "/").replace(":", "\\:")


def _drawtext_chain(captions: list[dict], font: str, out_dir: Path, tag: str,
                    h: int) -> str:
    """Build a chain of ffmpeg drawtext filters that flash each caption during its window.
    Text is read from a sidecar file (textfile=) to avoid escaping Vietnamese/punctuation."""
    parts = []
    fontposix = _ff_path(font)
    for k, c in enumerate(captions):
        txt = (c.get("text") or "").strip()
        if not txt or c.get("end", 0) <= c.get("start", 0):
            continue
        tf = out_dir / f"cap_{tag}_{k}.txt"
        tf.write_text(txt, encoding="utf-8")
        parts.append(
            f"drawtext=fontfile='{fontposix}':textfile='{_ff_path(str(tf))}'"
            f":enable='between(t,{c['start']:.3f},{c['end']:.3f})'"
            f":fontsize={max(28, int(h*0.055))}:fontcolor=white:borderw=2:bordercolor=black"
            f":box=1:boxcolor=black@0.45:boxborderw=14"
            f":x=(w-text_w)/2:y=h-(text_h*2.2)"
        )
    return ",".join(parts)


async def _scene_clip(parts: list[dict], scene: dict, out: Path, w: int, h: int,
                      default_duration: float, ken_burns: bool, font: str | None) -> float:
    """Render ONE scene to `out`: its shot images shown back-to-back over the scene's single
    continuous narration (audio kept whole), with timed keyword captions burned on top."""
    narr = _local(scene["narration_path"]) if scene.get("narration_path") else None
    narr = narr if (narr and narr.exists()) else None
    scene_dur = float(scene.get("narration_duration") or 0)
    if narr and scene_dur <= 0:
        scene_dur = await probe_duration(narr)

    # Each shot's image is shown for its beat's MEASURED narration_duration, so the still lands
    # exactly on its spoken segment (incl. the trailing breathing gap). Fall back to scaling the
    # shot `duration` across the scene only when a beat has no measured time.
    measured = [float(p.get("narration_duration") or 0) for p in parts]
    if all(m > 0 for m in measured):
        durs = measured
    else:
        base = [max(0.5, float(p.get("duration") or default_duration)) for p in parts]
        if scene_dur > 0:                              # scale image windows to cover audio
            s = sum(base) or 1.0
            durs = [d * scene_dur / s for d in base]
        else:
            durs = base

    # The scene WAV is `edge_pad` silence + gapped beats + `edge_pad` silence, so it is longer
    # than the sum of the per-shot beat windows (which exclude those two edge pads). If the image
    # track is shorter than the narration, `-shortest` below would CHOP the tail off the audio —
    # cutting the last spoken word(s) of the scene ("mất từ" at every scene boundary) — and every
    # image would also run ahead of its narration by the leading pad. Absorb the deficit into the
    # image windows: the leading pad onto the FIRST image (so it covers the lead silence and
    # re-aligns every following image with the audio + captions), the rest onto the LAST image.
    if narr and scene_dur > 0 and durs:
        deficit = round(scene_dur - sum(durs), 3)
        if deficit > 0.05:                             # ~2·edge_pad; ignore rounding noise
            head = round(deficit / 2, 3)
            durs = list(durs)
            durs[0] += head
            durs[-1] += deficit - head

    # one silent sub-clip per shot image, then concat → scene video
    tmp = []
    for k, p in enumerate(parts):
        src = shot_image_path(p)
        if not src:
            continue
        sub = out.with_name(f"{out.stem}_s{k}.mp4")
        await _image_clip(src, None, sub, w, h, durs[k], ken_burns)
        tmp.append(sub)
    if not tmp:
        raise RuntimeError("scene không có ảnh hợp lệ")
    lst = out.with_name(f"{out.stem}_list.txt")
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in tmp), encoding="utf-8")
    silent = out.with_name(f"{out.stem}_silent.mp4")
    await _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                "-c", "copy", str(silent)])

    # captions are stored scene-local (already on the scene timeline)
    caps: list[dict] = []
    for p in parts:
        try:
            caps.extend(json.loads(p.get("captions") or "[]"))
        except (json.JSONDecodeError, TypeError):
            pass
    chain = _drawtext_chain(caps, font, out.parent, out.stem, h) if font and caps else ""

    args = ["ffmpeg", "-y", "-i", str(silent)]
    if narr:
        args += ["-i", str(narr)]
    else:
        args += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    if chain:
        args += ["-filter_complex", f"[0:v]{chain}[v]", "-map", "[v]", "-map", "1:a"]
    else:
        args += ["-map", "0:v", "-map", "1:a"]
    args += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-ar", "44100", "-shortest", str(out)]
    await _run(args)
    return await probe_duration(out)


async def assemble_from_images(project_id: str, ken_burns: bool = True,
                               default_duration: float = 4.0,
                               caption_font: str | None = None) -> dict:
    """Build ONE long video from the shot IMAGES, grouped BY SCENE.

    Storytelling (§2.6): each scene has ONE continuous narration (kept whole for emotional
    flow); its shot images play back-to-back to cover that audio ("đọc tới đâu hình tới
    đó"), with timed keyword captions burned on. Scenes without narration fall back to each
    shot's `duration`. Scene clips concat into studio_media/<pid>/final.mp4 — no Flow video.
    """
    project = await db.query_one("SELECT * FROM project WHERE id=?", (project_id,))
    if not project:
        raise RuntimeError("project not found")
    scenes = await db.query_all(
        "SELECT * FROM scene WHERE project_id=? ORDER BY idx", (project_id,))
    out_dir = STUDIO_MEDIA_DIR / project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    font = _caption_font(caption_font)

    # Resolve every scene's usable shots first, so the output resolution can be decided from
    # what the stills actually are: all-2K/4K sources → render 1080p, else keep 720p.
    per_scene, usable = [], []
    for si, sc in enumerate(scenes):
        parts = await db.query_all(
            "SELECT * FROM shot WHERE scene_id=? AND image_path IS NOT NULL ORDER BY idx",
            (sc["id"],))
        parts = [p for p in parts if shot_image_path(p)]
        if not parts:
            continue
        usable.extend(parts)
        per_scene.append((si, sc, parts))
    # stills only here — ignore any video the shots may also have
    w, h = _res(project["aspect_ratio"],
                timeline_short_side([{**p, "video_path": None} for p in usable]))

    clip_paths, total = [], 0.0
    for si, sc, parts in per_scene:
        out = out_dir / f"scene{si:03d}.mp4"
        total += await _scene_clip(parts, sc, out, w, h, default_duration, ken_burns, font)
        clip_paths.append(out)

    if not clip_paths:
        raise RuntimeError("Chưa có shot nào có ảnh để ghép")

    list_file = out_dir / "concat_images.txt"
    list_file.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in clip_paths), encoding="utf-8")
    final = out_dir / "final.mp4"
    await _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
                "-c", "copy", str(final)])
    bgm = await apply_bgm(project, final)

    duration = await probe_duration(final)
    await db.execute("DELETE FROM asset WHERE project_id=? AND kind='final_video'", (project_id,))
    await db.insert("asset", {
        "id": db.new_id(), "project_id": project_id, "kind": "final_video",
        "path": str(final), "meta_json": None, "created_at": db.now()})
    web = f"/studio-media/{project_id}/final.mp4"
    return {"final_path": str(final), "web_path": web, "clips": len(clip_paths),
            "duration": duration, "mode": "images", "bgm": bgm}


async def assemble(project_id: str) -> dict:
    """Concat all shot videos (in scene/shot order) → studio_media/<pid>/final.mp4."""
    project = await db.query_one("SELECT * FROM project WHERE id=?", (project_id,))
    if not project:
        raise RuntimeError("project not found")
    shots = await db.query_all(
        "SELECT sh.* FROM shot sh JOIN scene sc ON sh.scene_id=sc.id "
        "WHERE sc.project_id=? AND sh.video_path IS NOT NULL ORDER BY sc.idx, sh.idx",
        (project_id,))
    if not shots:
        raise RuntimeError("Chưa có shot nào có video để ghép")

    out_dir = STUDIO_MEDIA_DIR / project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    w, h = _res(project["aspect_ratio"], timeline_short_side(shots))

    norm_paths = []
    for i, sh in enumerate(shots):
        # Bản upscale 1080p/4K nếu còn đúng với video hiện tại, không thì bản HD. (Cũng xử lý
        # được video chained nằm trong /studio-media/ — _local chỉ hiểu /media/.)
        src = shot_video_path(sh)
        if not src:
            continue
        narr = _local(sh["narration_path"]) if sh.get("narration_path") else None
        out = out_dir / f"norm{i:03d}.mp4"
        await _normalize(src, narr, out, w, h)
        norm_paths.append(out)

    if not norm_paths:
        raise RuntimeError("Không có clip hợp lệ để ghép")

    list_file = out_dir / "concat.txt"
    list_file.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in norm_paths), encoding="utf-8")
    final = out_dir / "final.mp4"
    await _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
                "-c", "copy", str(final)])
    bgm = await apply_bgm(project, final)

    duration = await probe_duration(final)
    # record asset
    await db.execute("DELETE FROM asset WHERE project_id=? AND kind='final_video'", (project_id,))
    await db.insert("asset", {
        "id": db.new_id(), "project_id": project_id, "kind": "final_video",
        "path": str(final), "meta_json": None, "created_at": db.now()})
    web = f"/studio-media/{project_id}/final.mp4"
    return {"final_path": str(final), "web_path": web, "clips": len(norm_paths),
            "duration": duration, "bgm": bgm}
