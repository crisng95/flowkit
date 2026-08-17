"""Export a DaVinci Resolve-compatible timeline (FCP7 XML / xmeml).

References the local shot videos with cumulative in/out points so the user can do
the final edit in Resolve. Frames are computed at a fixed fps from clip durations.
A second video track carries timed keyword captions (FCP7 Text generators) aligned to
when the narration reaches each phrase.
"""
import asyncio
import json
import os
import shutil
from pathlib import Path
from urllib.request import pathname2url
from xml.sax.saxutils import escape

from PIL import Image

from agent.config import BASE_DIR
from agent.studio import assembler, db, hires, media_store

FPS = 24
STUDIO_MEDIA_DIR = Path(os.environ.get("STUDIO_OUT_DIR", BASE_DIR / "studio_media"))


def _alpha(i: int) -> str:
    """0,1,2… → a,b,…,z,aa,ab… — a LETTERS-ONLY id. Media is staged under these names so
    Resolve can't read a digit run in the filename as an image-sequence frame number (UUID
    names like ...eea0e7a3310e.png get collapsed to a phantom '[3310-3621]' sequence)."""
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(97 + r) + s
    return s


async def _resolve_local(web_path, media_id, ext: str, project_id: str):
    """Local file for a shot media; if the cache file is missing, re-download from Flow by
    media_id — a generated shot whose local copy was pruned/never cached still exports."""
    if not web_path:
        return None
    p = assembler._local(web_path)
    if p.exists() and p.stat().st_size > 0:
        return p
    if media_id:
        web = await media_store.ensure_local(media_id, project_id, ext)
        if web:
            p = assembler._local(web)
            if p.exists() and p.stat().st_size > 0:
                return p
    return None


def _stage(src: Path, name: str, dv_dir: Path) -> Path:
    """Hardlink (or copy across volumes) `src` into dv_dir/<name><ext>; return the staged path.
    Lets the timeline reference sequence-safe filenames in one self-contained folder."""
    dst = dv_dir / f"{name}{src.suffix.lower()}"
    try:
        if dst.exists():
            dst.unlink()
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)
    return dst


def _stage_image_jpg(src: Path, name: str, dv_dir: Path) -> Path:
    """Re-encode a still to JPG (flatten alpha) into dv_dir. Resolve reliably imports JPG
    stills but chokes on some PNGs ('media offline'), so storyboard frames are exported as
    JPG. Falls back to a plain hardlink if PIL can't read the source."""
    dst = dv_dir / f"{name}.jpg"
    try:
        with Image.open(src) as im:
            if im.mode != "RGB":
                im = im.convert("RGB")
            im.save(dst, "JPEG", quality=92)
        return dst
    except OSError:
        return _stage(src, name, dv_dir)


def _file_url(p: Path) -> str:
    # Canonical Resolve form: file://localhost/<path>. On Windows pathname2url yields
    # '///D:/...'; the extra slashes (file://localhost///D:/...) trip Resolve's relink, so
    # collapse to a single slash → file://localhost/D:/... (and /home/... on posix).
    return "file://localhost/" + pathname2url(str(p.resolve())).lstrip("/")


def _srt_ts(sec: float) -> str:
    h = int(sec // 3600); m = int((sec % 3600) // 60)
    s = int(sec % 60); ms = int(round((sec - int(sec)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _clipitem(idx: int, name: str, path: Path, start_f: int, dur_f: int, w: int, h: int) -> str:
    end_f = start_f + dur_f
    return f"""        <clipitem id="clip{idx}">
          <name>{escape(name)}</name>
          <duration>{dur_f}</duration>
          <rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>
          <start>{start_f}</start>
          <end>{end_f}</end>
          <in>0</in>
          <out>{dur_f}</out>
          <file id="file{idx}">
            <name>{escape(path.name)}</name>
            <pathurl>{_file_url(path)}</pathurl>
            <rate><timebase>{FPS}</timebase></rate>
            <duration>{dur_f}</duration>
            <media><video><samplecharacteristics>
              <width>{w}</width><height>{h}</height>
            </samplecharacteristics></video></media>
          </file>
        </clipitem>"""


def _title_item(idx: int, text: str, start_f: int, dur_f: int) -> str:
    """FCP7 'Text' generator clip (Resolve imports these onto a title track)."""
    end_f = start_f + dur_f
    return f"""        <clipitem id="title{idx}">
          <name>{escape(text[:40])}</name>
          <enabled>TRUE</enabled>
          <duration>{dur_f}</duration>
          <rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>
          <start>{start_f}</start>
          <end>{end_f}</end>
          <in>0</in>
          <out>{dur_f}</out>
          <effect>
            <name>Text</name>
            <effectid>Text</effectid>
            <effectcategory>Text</effectcategory>
            <effecttype>generator</effecttype>
            <mediatype>video</mediatype>
            <parameter>
              <parameterid>str</parameterid>
              <name>Text</name>
              <value>{escape(text)}</value>
            </parameter>
          </effect>
        </clipitem>"""


def _audio_item(idx: int, name: str, path: Path, start_f: int, dur_f: int,
                src_in_f: int = 0, file_dur_f: int | None = None,
                file_id: str | None = None, define_file: bool = True) -> str:
    """One audio clipitem. `src_in_f`/`file_dur_f` let several clips play different slices of
    the SAME file (per-beat narration sliced from the scene WAV) — the first shares `file_id`
    with define_file=True, the rest reference it with define_file=False."""
    end_f = start_f + dur_f
    out_f = src_in_f + dur_f
    fdur = file_dur_f if file_dur_f is not None else dur_f
    fid = file_id or f"afile{idx}"
    if define_file:
        file_xml = (f'<file id="{fid}">\n'
                    f'            <name>{escape(path.name)}</name>\n'
                    f'            <pathurl>{_file_url(path)}</pathurl>\n'
                    f'            <rate><timebase>{FPS}</timebase></rate>\n'
                    f'            <duration>{fdur}</duration>\n'
                    f'            <media><audio><channelcount>2</channelcount></audio></media>\n'
                    f'          </file>')
    else:
        file_xml = f'<file id="{fid}"/>'
    return f"""        <clipitem id="aclip{idx}">
          <name>{escape(name)}</name>
          <duration>{dur_f}</duration>
          <rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>
          <start>{start_f}</start>
          <end>{end_f}</end>
          <in>{src_in_f}</in>
          <out>{out_f}</out>
          {file_xml}
          <sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack>
        </clipitem>"""


def _transition_item(start_f: int, end_f: int) -> str:
    """Cross dissolve giữa hai clip kề nhau, kiểu FCP7 (Resolve nhập được).

    `alignment=center`: chỗ cắt nằm GIỮA khoảng [start_f, end_f], nên hai clip hai bên phải
    chờm lên nhau đúng bằng độ dài này — xem `_music_video_track`.
    """
    return f"""        <transitionitem>
          <rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>
          <start>{start_f}</start>
          <end>{end_f}</end>
          <alignment>center</alignment>
          <cutPointTicks>0</cutPointTicks>
          <effect>
            <name>Cross Dissolve</name>
            <effectid>Cross Dissolve</effectid>
            <effectcategory>Dissolve</effectcategory>
            <effecttype>transition</effecttype>
            <mediatype>video</mediatype>
            <wipecode>0</wipecode>
            <wipeaccuracy>100</wipeaccuracy>
            <startratio>0</startratio>
            <endratio>1</endratio>
            <reverse>FALSE</reverse>
          </effect>
        </transitionitem>"""


def _clipitem_slice(idx: int, name: str, path: Path, start_f: int, in_f: int, out_f: int,
                    w: int, h: int, file_id: str, define_file: bool, file_dur_f: int) -> str:
    """Một clipitem đọc ĐOẠN [in_f, out_f) của file. Nhiều vòng lặp của cùng một video dùng
    chung `file_id`: chỉ clip đầu khai `<file>` đầy đủ, các clip sau tham chiếu lại."""
    dur_f = out_f - in_f
    if define_file:
        file_xml = (f'<file id="{file_id}">\n'
                    f'            <name>{escape(path.name)}</name>\n'
                    f'            <pathurl>{_file_url(path)}</pathurl>\n'
                    f'            <rate><timebase>{FPS}</timebase></rate>\n'
                    f'            <duration>{file_dur_f}</duration>\n'
                    f'            <media><video><samplecharacteristics>\n'
                    f'              <width>{w}</width><height>{h}</height>\n'
                    f'            </samplecharacteristics></video></media>\n'
                    f'          </file>')
    else:
        file_xml = f'<file id="{file_id}"/>'
    return f"""        <clipitem id="mv{idx}">
          <name>{escape(name)}</name>
          <duration>{file_dur_f}</duration>
          <rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>
          <start>{start_f}</start>
          <end>{start_f + dur_f}</end>
          <in>{in_f}</in>
          <out>{out_f}</out>
          {file_xml}
        </clipitem>"""


# Độ dài cross dissolve mặc định: 24 khung = 1 giây ở 24fps.
XFADE_F = 24


async def build_music_video(project_id: str, pairs: list[tuple[dict, Path]],
                            xfade_f: int = XFADE_F) -> dict:
    """Timeline Resolve cho video nhạc: mỗi bài một music video, HÌNH LẶP hết bài.

    Khác `build()` (đi theo shot/scene): ở đây hình và tiếng là hai dòng độc lập —
      • dòng TIẾNG: mỗi bài một clip, nối tiếp nhau, cách nhau `project.music_gap`;
      • dòng HÌNH: video của bài lặp lại cho phủ hết bài, mỗi mối nối (giữa hai vòng lặp,
        và giữa hai bài) là một cross dissolve `xfade_f` khung.

    Vì hai clip hình phải CHỜM lên nhau đúng bằng độ dài dissolve, mỗi vòng lặp chỉ đẩy
    timeline đi `Lv - xfade_f` khung chứ không phải `Lv` — không trừ phần chờm này thì hình
    hết trước nhạc đúng `xfade_f × số mối nối` khung.

    `pairs`: [(track_row, đường dẫn music video)] theo thứ tự phát.
    """
    project = await db.query_one("SELECT * FROM project WHERE id=?", (project_id,))
    if not project:
        raise RuntimeError("project not found")
    if not pairs:
        raise RuntimeError("Chưa có bài nào kèm music video")

    w, h = await assembler.probe_size(pairs[0][1])
    if not (w and h):
        w, h = assembler._res(project["aspect_ratio"], 720)
    gap_f = round(float(project.get("music_gap") or 0) * FPS)

    dv_dir = STUDIO_MEDIA_DIR / project_id / "dv_music"
    shutil.rmtree(dv_dir, ignore_errors=True)
    dv_dir.mkdir(parents=True, exist_ok=True)

    # ── Bước 1: mốc thời gian ─────────────────────────────────
    # Dòng tiếng nối tiếp nhau, cách nhau `gap`. Dòng hình chạy LIÊN TỤC, chỉ đổi nguồn: hình
    # của bài k kéo tới đúng lúc bài k+1 bắt đầu, còn hình bài k+1 vào sớm hơn `xfade` khung —
    # nên khi tiếng sang bài mới thì hình đã chuyển xong. Không có khoảng hở nào để dissolve
    # phải hoà vào chỗ trống.
    songs = []
    cursor = 0
    for k, (track, vpath) in enumerate(pairs):
        apath = Path(track["path"])
        song_f = max(1, round(float(track.get("duration") or 0) * FPS))
        if song_f <= 1:
            song_f = max(1, round(await assembler.probe_duration(apath) * FPS))
        vid_f = max(1, round(await assembler.probe_duration(vpath) * FPS))
        songs.append({"track": track, "vpath": vpath, "apath": apath,
                      "astart": cursor, "aend": cursor + song_f, "vid_f": vid_f})
        cursor += song_f + (gap_f if k < len(pairs) - 1 else 0)
    total = songs[-1]["aend"]

    # ── Bước 2: các đoạn hình, có tính phần CHỜM ──────────────
    # Mỗi vòng lặp chỉ đẩy timeline đi `vid_f - xfade` khung chứ không phải `vid_f` — quên trừ
    # phần chờm là hình hết trước nhạc đúng `xfade × số mối nối` khung.
    #
    # Các vòng lặp CHIA ĐỀU chứ không "chạy hết video rồi lấy phần dư": cách chạy-hết để lại
    # một mẩu vụn ở cuối bài (đo thật: 42 khung kẹp giữa hai dissolve — hình vừa hiện đã mờ
    # đi). Số vòng n = ceil((D - X) / (Lv - X)), rồi mỗi vòng dài (D + (n-1)X)/n — luôn ≤ Lv
    # theo đúng công thức, nên không vòng nào đòi nhiều hơn độ dài video có thật.
    spans: list[dict] = []          # {k, start, take, join}
    for k, s in enumerate(songs):
        vstart = s["astart"] - (xfade_f if k else 0)
        vend = songs[k + 1]["astart"] if k + 1 < len(songs) else s["aend"]
        need = vend - vstart
        step = max(1, s["vid_f"] - xfade_f)
        n = max(1, -(-(need - xfade_f) // step))          # ceil
        take = (need + (n - 1) * xfade_f) / n
        pos = vstart
        for j in range(n):
            end = vend if j == n - 1 else round(vstart + (j + 1) * take - j * xfade_f)
            spans.append({"k": k, "start": pos, "take": end - pos, "join": j > 0 or k > 0})
            pos = end - xfade_f

    # ── Bước 3: XML ───────────────────────────────────────────
    video_items: list[str] = []
    audio_items: list[str] = []
    defined: set[int] = set()
    for k, s in enumerate(songs):
        staged_a = _stage(s["apath"], f"song{_alpha(k)}", dv_dir)
        audio_items.append(_audio_item(
            k, s["track"].get("title") or f"Bài {k+1}", staged_a,
            s["astart"], s["aend"] - s["astart"], file_dur_f=s["aend"] - s["astart"]))
    staged_v = {k: _stage(s["vpath"], f"mv{_alpha(k)}", dv_dir) for k, s in enumerate(songs)}
    for idx, sp in enumerate(spans):
        k = sp["k"]
        s = songs[k]
        video_items.append(_clipitem_slice(
            idx, s["track"].get("title") or f"Bài {k+1}", staged_v[k],
            sp["start"], 0, sp["take"], w, h,
            f"mvfile{k}", define_file=k not in defined, file_dur_f=s["vid_f"]))
        defined.add(k)
        if sp["join"]:
            video_items.append(_transition_item(sp["start"], sp["start"] + xfade_f))
    loops_total = len(spans)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="5">
  <sequence id="seq1">
    <name>{escape((project["title"] or "Music video") + " — MV")}</name>
    <duration>{total}</duration>
    <rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>
    <media>
      <video>
        <format><samplecharacteristics>
          <width>{w}</width><height>{h}</height>
          <rate><timebase>{FPS}</timebase></rate>
        </samplecharacteristics></format>
        <track>
{chr(10).join(video_items)}
        </track>
      </video>
      <audio>
        <track>
{chr(10).join(audio_items)}
        </track>
      </audio>
    </media>
  </sequence>
</xmeml>
"""
    out_dir = STUDIO_MEDIA_DIR / project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "music_video_timeline.xml"
    out.write_text(xml, encoding="utf-8")
    return {"path": str(out),
            "web_path": f"/studio-media/{project_id}/music_video_timeline.xml",
            "songs": len(pairs), "clips": loops_total,
            "xfade_frames": xfade_f, "fps": FPS,
            "duration": round(total / FPS, 2), "width": w, "height": h}


DEFAULT_IMG_S = 4.0


async def build(project_id: str) -> dict:
    """Resolve timeline from each shot's VIDEO, or its IMAGE as a still when no video exists
    yet (storytelling: review storyboard images, then edit in Resolve without rendering Flow
    videos). Per scene: video shots use their probed length; image-only scenes scale their
    stills to fill the scene's continuous narration — same timing as 'Tạo video từ ảnh'."""
    project = await db.query_one("SELECT * FROM project WHERE id=?", (project_id,))
    if not project:
        raise RuntimeError("project not found")
    scenes = await db.query_all(
        "SELECT * FROM scene WHERE project_id=? ORDER BY idx", (project_id,))

    # Sequence resolution follows what the shots actually hold: all-hi-res (upsampled stills /
    # upscaled videos) → 1080p or 4K, any HD leftover → 720p. Dropping 2K stills or a 1080p
    # upscale into a 720p sequence would throw away exactly what was paid for.
    all_shots = await db.query_all(
        "SELECT sh.* FROM shot sh JOIN scene sc ON sh.scene_id=sc.id WHERE sc.project_id=?",
        (project_id,))
    w, h = assembler._res(project["aspect_ratio"], assembler.timeline_short_side(all_shots))
    # Stage media under sequence-safe (letters-only) names in one folder next to the XML, so
    # Resolve never mis-reads a UUID's digits as an image-sequence frame range.
    dv_dir = STUDIO_MEDIA_DIR / project_id / "dv_media"
    shutil.rmtree(dv_dir, ignore_errors=True)
    dv_dir.mkdir(parents=True, exist_ok=True)

    items, titles, srt, start_f, total, tnum = [], [], [], 0, 0, 0
    audio_runs = []   # one clip per scene: (narration WAV, scene start_f, scene end_f, lead_f, measured)
    skipped = []      # shots with media in the DB but no usable file (even after re-download)
    i = 0
    for sc in scenes:
        rows = await db.query_all(
            "SELECT * FROM shot WHERE scene_id=? AND "
            "(video_path IS NOT NULL OR image_path IS NOT NULL) ORDER BY idx", (sc["id"],))
        # Resolve each shot to a usable media file: prefer video, else the still image.
        usable = []   # (shot, path, is_image)
        for sh in rows:
            # Prefer the 1080p/4K upscale over the HD render (falls back to re-downloading
            # the HD one by media_id if the local file went missing).
            vp = assembler.shot_video_path(sh) or await _resolve_local(
                sh.get("video_path"), sh.get("video_media_id"), "mp4", project_id)
            if vp:
                usable.append((sh, vp, False))
                continue
            # Prefer the 2K/4K copy; _resolve_local falls back to re-downloading the HD one by
            # media_id if the hi-res file went missing, so the export never breaks over it.
            ip = await _resolve_local(hires.shot_image(sh), sh.get("image_media_id"),
                                      "png", project_id)
            if ip:
                usable.append((sh, ip, True))
            else:
                skipped.append(sh.get("title") or sh["id"])
        if not usable:
            continue

        # Per-shot durations (seconds). Video → its real length; image → the beat's MEASURED
        # narration_duration (so the still lands exactly on its spoken segment). Only when a
        # beat lacks a measured time do we fall back to scaling stills across the scene.
        scene_dur = float(sc.get("narration_duration") or 0)
        if sc.get("narration_path") and scene_dur <= 0:
            np_ = assembler._local(sc["narration_path"])
            if np_.exists():
                scene_dur = await assembler.probe_duration(np_)
        base, have_measured = [], True
        for (sh, path, is_img) in usable:
            if not is_img:
                have_measured = False
                base.append(await assembler.probe_duration(path))
                continue
            nd = float(sh.get("narration_duration") or 0)
            if nd > 0:
                base.append(nd)
            else:
                have_measured = False
                base.append(max(0.5, float(sh.get("duration") or DEFAULT_IMG_S)))
        if have_measured:
            durs = base                                  # measured beats → images sync to audio
        elif scene_dur > 0 and all(is_img for (_, _, is_img) in usable):
            s = sum(base) or 1.0
            durs = [d * scene_dur / s for d in base]
        else:
            durs = base

        scene_start_f = start_f                        # frame where this scene begins
        scene_caps, beat_spans = [], []                # beat_spans: (timeline_start_f, dur_f)
        for (sh, path, is_img), dur_s in zip(usable, durs):
            dur_f = max(1, round(dur_s * FPS))
            name = f"clip{_alpha(i)}"
            staged = await asyncio.to_thread(_stage_image_jpg, path, name, dv_dir) if is_img \
                else _stage(path, name, dv_dir)
            items.append(_clipitem(i, sh.get("title") or f"Shot {i+1}", staged, start_f, dur_f, w, h))
            # 3rd field = this beat's TRUE offset into the scene WAV (shot.start_time, which
            # includes the leading edge-pad silence). The audio slice must read from here, NOT
            # from the cumulative image position (start_f - scene_start_f) which omits that pad.
            src_off_f = round(float(sh.get("start_time") or 0) * FPS)
            beat_spans.append((start_f, dur_f, src_off_f))
            try:
                scene_caps.extend(json.loads(sh.get("captions") or "[]"))
            except (json.JSONDecodeError, TypeError):
                pass
            start_f += dur_f
            total += dur_f
            i += 1
        scene_end_f = start_f

        # Narration audio → ONE continuous clip per scene (not one per beat). Per-beat slicing
        # made every beat a separate clipitem sharing one <file> by empty reference; Resolve
        # mis-imports that (dropping the first word(s) of each beat). A single clip reads the
        # scene WAV from just after its leading edge-pad (so it aligns with the images) to the
        # end of the last beat — its only boundary is the scene start, cushioned by that pad.
        if sc.get("narration_path"):
            lead_f = beat_spans[0][2] if (have_measured and beat_spans) else 0
            audio_runs.append(
                (sc["narration_path"], scene_start_f, scene_end_f, lead_f, have_measured))

        # Captions are timed against the SCENE NARRATION (scene-local seconds), which plays
        # continuously from scene_start_f — NOT against the scaled image-clip starts. Place
        # them absolutely so they stay in sync with the audio (same as the burned-in video).
        # In the per-beat (measured) path the audio slices skip the leading edge-pad, so the
        # narration reaches each phrase `cap_lead_f` frames earlier than its WAV timestamp —
        # subtract that lead so captions land on the audio + images (0 for the continuous path).
        cap_lead_f = beat_spans[0][2] if (have_measured and beat_spans) else 0
        for c in scene_caps:
            cstart, cend = float(c.get("start", 0)), float(c.get("end", 0))
            cs = scene_start_f + round(cstart * FPS) - cap_lead_f
            cd = max(1, round((cend - cstart) * FPS))
            cd = min(cd, max(1, scene_end_f - cs))     # clamp inside the scene span
            if c.get("text") and scene_start_f <= cs < scene_end_f:
                titles.append(_title_item(tnum, c["text"], cs, cd))
                srt.append((cs / FPS, (cs + cd) / FPS, c["text"]))
                tnum += 1

    if not items:
        raise RuntimeError("Chưa có shot nào có ảnh hoặc video để export")

    # narration audio track — ONE fully-defined clip per scene (see the scene loop above for why
    # per-beat slicing was dropped).
    audio_items = []
    aid = 0
    for narr_web, scene_sf, scene_ef, lead_f, measured in audio_runs:
        ap = assembler._local(narr_web)
        if not ap.exists():
            continue
        file_dur_f = max(1, round(await assembler.probe_duration(ap) * FPS))
        staged_ap = _stage(ap, f"narr{_alpha(aid)}", dv_dir)
        if measured:
            # Storytelling: images span scene_dur MINUS the two edge pads, so read the WAV from
            # just after the leading pad (lead_f) for exactly the image span — speech stays under
            # its image and no trailing-pad silence bleeds into the next scene.
            src_in = max(0, lead_f)
            cdur = min(max(1, scene_ef - scene_sf), max(1, file_dur_f - src_in))
        else:
            # Non-measured (e.g. real video shots): play the whole WAV from the scene start.
            src_in = 0
            cdur = file_dur_f
        audio_items.append(_audio_item(
            aid, "narration", staged_ap, scene_sf, cdur, src_in_f=src_in,
            file_dur_f=file_dur_f))
        aid += 1

    # background-music track: the project's music tiled across the whole timeline (Resolve
    # has no loop in XML, so repeat the clip) on its OWN audio track, under the narration.
    bgm_items = []
    bgm = (project.get("bgm_path") or "").strip()
    if bgm and Path(bgm).exists() and total > 0:
        bgm_src = Path(bgm)
        bgm_secs = await assembler.probe_duration(bgm_src)
        if bgm_secs > 0.5:
            bgm_dur_f = max(1, round(bgm_secs * FPS))
            staged_bgm = _stage(bgm_src, "bgmtrack", dv_dir)
            pos, k = 0, 0
            while pos < total and k < 2000:
                seg = min(bgm_dur_f, total - pos)
                bgm_items.append(_audio_item(1000 + k, "bgm", staged_bgm, pos, seg))
                pos += seg
                k += 1

    title_track = f"\n        <track>\n{chr(10).join(titles)}\n        </track>" if titles else ""
    audio_tracks_xml = ""
    if audio_items:
        audio_tracks_xml += f"\n        <track>\n{chr(10).join(audio_items)}\n        </track>"
    if bgm_items:
        audio_tracks_xml += f"\n        <track>\n{chr(10).join(bgm_items)}\n        </track>"
    audio_media = (f"""
      <audio>{audio_tracks_xml}
      </audio>""" if audio_tracks_xml else "")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="5">
  <sequence id="seq1">
    <name>{escape(project["title"] or "Flow Studio")}</name>
    <duration>{total}</duration>
    <rate><timebase>{FPS}</timebase><ntsc>FALSE</ntsc></rate>
    <media>
      <video>
        <format><samplecharacteristics>
          <width>{w}</width><height>{h}</height>
          <rate><timebase>{FPS}</timebase></rate>
        </samplecharacteristics></format>
        <track>
{chr(10).join(items)}
        </track>{title_track}
      </video>{audio_media}
    </media>
  </sequence>
</xmeml>
"""
    out_dir = STUDIO_MEDIA_DIR / project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "timeline.xml"
    out.write_text(xml, encoding="utf-8")

    # Sibling SRT of the keyword captions — Resolve (incl. Free) imports subtitles reliably,
    # whereas FCP7 title generators may be dropped on XML import.
    srt_web = None
    if srt:
        lines = []
        for n, (a, b, txt) in enumerate(srt, 1):
            lines.append(f"{n}\n{_srt_ts(a)} --> {_srt_ts(b)}\n{txt}\n")
        (out_dir / "captions.srt").write_text("\n".join(lines), encoding="utf-8")
        srt_web = f"/studio-media/{project_id}/captions.srt"

    await db.execute("DELETE FROM asset WHERE project_id=? AND kind='davinci_xml'", (project_id,))
    await db.insert("asset", {
        "id": db.new_id(), "project_id": project_id, "kind": "davinci_xml",
        "path": str(out), "meta_json": None, "created_at": db.now()})
    return {"path": str(out), "web_path": f"/studio-media/{project_id}/timeline.xml",
            "clips": len(items), "captions_srt": srt_web, "captions": len(srt),
            "audio_tracks": len(audio_items), "bgm": bool(bgm_items),
            "missing": len(skipped), "missing_titles": skipped[:20]}
