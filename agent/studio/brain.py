"""The "brain" — wraps the AI-agent CLI (claude / agy) for Studio tasks.

Builds a prompt that demands strict JSON, runs it through /api/agent/run's underlying
handler, then extracts + parses the JSON (tolerant of code fences / surrounding prose).
Retries once on parse failure. See video-app.md §6.
"""
import asyncio
import json
import logging
import math
import os
import re
from pathlib import Path

from fastapi import HTTPException

from agent.api.ai_agent import RunRequest, run_agent
from agent.studio import db, vntext

logger = logging.getLogger(__name__)

# Per-call agent timeout for brain JSON prompts. Must match the CLI ceiling in config
# (AGENT_CLI_TIMEOUT) — a slow agent/model (e.g. antigravity + gemini-flash) can take
# several minutes per scene-plan/beat-split call, so 300s was too tight and tripped 504s.
_AGENT_TIMEOUT = float(os.environ.get("AGENT_CLI_TIMEOUT", "600"))


async def _agent_cfg() -> tuple[str, str | None]:
    """(agent key, model). Model comes from the `agent_model` setting (or env AGENT_MODEL);
    None → let the CLI use its own default. Passing a fast model (e.g. gemini-flash) here
    speeds up every brain call — script/scene/shot generation."""
    settings = await db.kv_get_all()
    agent = settings.get("agent") or "claude"
    model = (settings.get("agent_model") or os.environ.get("AGENT_MODEL") or "").strip() or None
    return agent, model


async def _agent_name() -> str:
    agent, _ = await _agent_cfg()
    return agent


def _extract_json(text: str):
    """Pull the first JSON object/array out of arbitrary model output."""
    if not text:
        raise ValueError("empty agent output")
    # strip ``` fences
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    # fast path
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # balance-scan from the first { or [
    start = min((i for i in (text.find("{"), text.find("[")) if i >= 0), default=-1)
    if start < 0:
        raise ValueError("no JSON found in agent output")
    open_ch = text[start]
    close_ch = "}" if open_ch == "{" else "]"
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return json.loads(text[start:i + 1])
    raise ValueError("unbalanced JSON in agent output")


# ─── Không gọi tên hoạ sĩ / hãng phim ───────────────────────
# Model rất hay "giúp" bằng cách quy phong cách về một cái tên có sẵn ("Makoto Shinkai style",
# "Ghibli style", "Pixar style"). Prompt sinh ra sẽ đi thẳng lên Flow, nên đó là rủi ro bản
# quyền chứ không phải chuyện thẩm mỹ — và cũng thừa: style của dự án đã mô tả đầy đủ bằng
# thuộc tính hình ảnh rồi.
#
# Chặn ở HAI đầu vì mỗi đầu đều thủng: dặn model thì nó vẫn quên, còn lọc không thì lần sau ai
# thêm một cái tên vào danh sách sẽ không hiểu vì sao phải lọc.
NO_NAMED_STYLE_RULE = (
    "\n\nDo NOT introduce a real artist, animation studio, film director or franchise as a "
    "style reference on your own (no \"Ghibli\", \"Makoto Shinkai\", \"Pixar\", \"Disney\", "
    "\"in the style of <person>\", etc.). Describe the look with generic visual attributes "
    "instead — line quality, shading, palette, lighting, lens, mood. The ONE exception: if "
    "the style brief above already names one, keep that name exactly as written."
)

# Chỉ cắt cụm QUY PHONG CÁCH ("X style", "in the style of X", "X-esque"), không cắt mọi lần
# nhắc tên: một truyện lấy bối cảnh công viên Disneyland vẫn được phép nhắc tên nơi đó.
_NAMED = (r"ghibli|studio ghibli|makoto shinkai|shinkai|miyazaki|hayao miyazaki|pixar|disney|"
          r"dreamworks|marvel|greg rutkowski|artgerm|wlop|moebius|akira toriyama|kyoto animation")
_NAMED_STYLE_RE = re.compile(
    rf"(?:\b(?:in|with)\s+(?:the\s+)?(?:style|aesthetic|look)\s+of\s+)?\b(?:{_NAMED})\b"
    rf"(?:[-\s]*(?:style|styled|aesthetic|look|inspired|esque))?",
    re.I)


def named_styles_in(text: str) -> set[str]:
    """Các tên riêng XUẤT HIỆN trong một đoạn text (viết thường), để làm danh sách cho phép."""
    return {m.group(0).lower() for m in re.finditer(_NAMED, text or "", re.I)}


def strip_named_styles(text: str, allow: set[str] | None = None) -> str:
    """Bỏ cụm quy phong cách về tên riêng khỏi text do AI sinh.

    `allow` = các tên NGƯỜI DÙNG đã tự đặt (lấy từ chính prompt gửi đi, nơi chứa style của dự
    án). Chọn "Ghibli style" ở ⚙ Cấu hình là một quyết định có chủ ý — lọc mất là app tự ý đổi
    phong cách của người dùng. Chỉ chặn tên do AI TỰ THÊM."""
    if not text or not _NAMED_STYLE_RE.search(text):
        return text

    def _cut(m: re.Match) -> str:
        if allow and any(a in m.group(0).lower() for a in allow):
            return m.group(0)       # tên của người dùng — giữ nguyên văn
        return ""

    out = _NAMED_STYLE_RE.sub(_cut, text)
    if out == text:
        return text
    # Dọn dấu câu mồ côi do chỗ cắt để lại — không dọn thì prompt đầy ", ." và " ,".
    out = re.sub(r"\s+([,.;:])", r"\1", out)       # "Chibi , a" → "Chibi, a"
    out = re.sub(r",\s*([.;:])", r"\1", out)       # "background, ." → "background."
    out = re.sub(r"(,\s*){2,}", ", ", out)         # ", , ," → ", "
    out = re.sub(r"(^|[.;:])\s*,\s*", r"\1 ", out)  # câu mở đầu bằng dấu phẩy
    out = re.sub(r"\s{2,}", " ", out)
    return out.strip(" ,;")


def _scrub(obj, allow: set[str] | None = None):
    """Áp strip_named_styles lên MỌI chuỗi trong cây JSON model trả về."""
    if isinstance(obj, str):
        return strip_named_styles(obj, allow)
    if isinstance(obj, list):
        return [_scrub(v, allow) for v in obj]
    if isinstance(obj, dict):
        return {k: _scrub(v, allow) for k, v in obj.items()}
    return obj


async def run_json(prompt: str, *, timeout: float = _AGENT_TIMEOUT, retries: int = 2):
    """Run the agent and return parsed JSON. Raises HTTPException(502) on failure.

    Mọi text sinh ra đều đi qua đây, nên đây cũng là chỗ DUY NHẤT lọc tên hoạ sĩ/hãng phim —
    khỏi phải nhớ thêm luật ở từng hàm dựng prompt.

    Tên đã CÓ SẴN trong `prompt` được cho qua: prompt luôn nhúng style của dự án, nên tên nằm
    trong đó là do người dùng tự đặt. Chỉ tên xuất hiện RIÊNG ở phần model trả về mới bị cắt."""
    allow = named_styles_in(prompt)
    if allow:
        logger.info("brain: giữ tên phong cách người dùng đặt: %s", ", ".join(sorted(allow)))
    prompt = prompt + NO_NAMED_STYLE_RULE
    agent, model = await _agent_cfg()
    last_err = None
    for attempt in range(retries + 1):
        nudge = "" if attempt == 0 else "\n\nReturn ONLY valid JSON, no prose, no markdown."
        res = await run_agent(RunRequest(agent=agent, prompt=prompt + nudge, timeout=timeout,
                                         model=model))
        if not res.get("ok"):
            last_err = res.get("stderr") or f"exit {res.get('exit_code')}"
            continue
        try:
            return _scrub(_extract_json(res.get("stdout", "")), allow)
        except ValueError as e:
            last_err = str(e)
            logger.warning("brain JSON parse failed (try %d): %s", attempt, e)
    raise HTTPException(502, f"AI-agent không trả JSON hợp lệ: {last_err}")


async def run_json_valid(prompt: str, validate, *, label: str = "AI",
                         attempts: int = 3, timeout: float = _AGENT_TIMEOUT):
    """run_json that ALSO retries when the reply is valid JSON but fails `validate` (wrong
    shape/semantics — which run_json's parse-only retry can't catch). `validate(data)` returns
    True to accept. Raises HTTPException(502) after all attempts fail, so callers stop silently
    degrading to a worse result and instead surface (or retry) a real failure."""
    last = None
    for attempt in range(attempts):
        try:
            data = await run_json(prompt, timeout=timeout)
            if validate(data):
                return data
            last = "reply failed validation (wrong shape/size)"
            logger.warning("%s try %d: %s", label, attempt + 1, last)
        except HTTPException as e:
            last = e.detail
            logger.warning("%s try %d: %s", label, attempt + 1, last)
        except Exception as e:  # noqa: BLE001 — keep retrying through transient agent errors
            last = str(e)
            logger.warning("%s try %d: %s", label, attempt + 1, last)
        await asyncio.sleep(min(1.0 + attempt, 4.0))
    raise HTTPException(502, f"{label}: AI không trả kết quả hợp lệ sau {attempts} lần thử ({last})")


# ─── Scene parsing (Fountain-ish screenplay → scenes) ───────

_SLUG_RE = re.compile(r"^\s*(INT\.|EXT\.|INT/EXT\.|EXT/INT\.|I/E\.)", re.IGNORECASE)


def parse_scenes(script: str) -> list[dict]:
    """Split a screenplay into scenes on slug lines (INT./EXT. ...).

    Returns [{idx, heading, slug, location_name, body}]. Location = the part of the
    slug between the INT./EXT. prefix and a trailing " - TIME".
    """
    lines = (script or "").splitlines()
    scenes: list[dict] = []
    cur = None
    for ln in lines:
        if _SLUG_RE.match(ln):
            if cur:
                scenes.append(cur)
            heading = ln.strip()
            # location: drop prefix + trailing " - DAY/NIGHT/..."
            loc = _SLUG_RE.sub("", heading).strip(" .-")
            loc = re.split(r"\s+-\s+", loc)[0].strip()
            cur = {"idx": len(scenes), "heading": heading, "slug": heading,
                   "location_name": loc, "body": ""}
        elif cur is not None:
            cur["body"] += ln + "\n"
    if cur:
        scenes.append(cur)
    return scenes


# ─── Prompt composition (style-first + header/footer + culture) ──

# Guard for SHOT FRAME generation. Some entity references are DESIGN SHEETS (character
# turnarounds + expression rows, prop multi-angle sheets). Without this, the model copies
# that sheet layout into the frame. This forces a single coherent photograph. Used only on
# the frame path, never when generating the reference art itself.
#
# Luật tách theo LOẠI ref, vì hai loại cần hai thứ NGƯỢC NHAU: ref nhân vật/đạo cụ chỉ khoá
# danh tính và phải bỏ qua tư thế/khung hình, còn ref bối cảnh thì CHÍNH LÀ nơi chốn, phải
# chép lại trung thành. Bản cũ gộp làm một nên câu "ignore its framing" và nhất là câu "do
# not reproduce any text/labels that appear in the references" (viết để chặn nhãn "Nhìn
# thẳng / Góc 3/4" của sheet) đọc thành luật chung: model được lệnh ĐỔI biển hiệu của con
# phố, và nó đổi — "HIỆU ĐÈN LỒNG HÀNG MÃ" ra thành "PHỞ GIA TRUYỀN", "CÀ PHÊ SỮA ĐÁ" ở 2/3
# lượt đo. Chữ TRONG THẾ GIỚI khác chữ CHÚ THÍCH của bảng sheet; đừng cấm chung.
_SINGLE_FRAME = (
    "Render ONE single unified cinematic frame from a SINGLE camera angle — one continuous "
    "photographic moment, not a composite. Do NOT reproduce any reference-sheet layout: no "
    "grid, no 2x2, no multi-panel or split screen, no collage, no turnaround row, no side-by-"
    "side angles, no plain white reference backdrop.\n\n"
    "CHARACTER and PROP references fix IDENTITY ONLY — face, hair, skin, build, age, costume, "
    "an object's shape and materials. Never swap, blend or mix up faces, hair or costumes "
    "between characters, and do NOT add any extra people who are not named in this shot. They "
    "do NOT dictate POSE: ignore the A-pose/stance, the expression, the gaze direction, the "
    "body orientation, the framing, and — when a reference happens to show more than one "
    "person — the way those people are arranged relative to each other. Pose, angle and "
    "spacing must be invented FRESH for THIS shot's action and camera setup, and must differ "
    "from other shots; characters interact with the scene and each other as the action "
    "demands. Never paste a character in as a rigid cut-out standing the way the reference "
    "shows.\n\n"
    "A character reference also fixes the DRAWING CONVENTION of that face, and that counts as "
    "identity: how large the eyes are as a fraction of the head, the shape of the iris and its "
    "highlights, how far the nose and mouth are simplified, the line weight, the flatness of "
    "the shading. Hold that convention identical in EVERY frame and at EVERY shot size. Do not "
    "drift toward realistic facial proportions merely because the figure is smaller in a wide "
    "shot — the eyes stay the same fraction of the face they occupy in the reference, simply "
    "drawn with fewer pixels. A face with big stylised eyes in the reference and small "
    "naturalistic eyes in the frame is the SAME mistake as changing the hair or the costume.\n\n"
    "A LOCATION reference is the opposite: it IS the place, not a mood board. Reproduce it "
    "faithfully — the same buildings, shopfronts, awnings, goods on display, street furniture, "
    "parked vehicles, foliage, lighting and their arrangement, and the SAME wording on every "
    "sign and banner, spelled the same way. Only the camera angle, the framing and the people "
    "in it may change; never redesign the street, rename the shops or swap in different "
    "businesses.\n\n"
    "Where the WORDS of this prompt describe the place differently from the location reference, "
    "THE REFERENCE WINS. Draw the street that the reference shows and treat the wording as "
    "nothing more than a pointer to which part of it to look at. Phrases naming materials, "
    "colours, architecture or fittings the reference does not have — 'wooden verandas', "
    "'yellow plaster walls', 'flagstone alley', 'tiled eaves' — are to be IGNORED, not built. "
    "A frame that matches every adjective but shows a street nobody can recognise has failed.\n\n"
    "Everything in the frame shares ONE scale, and a person's height is read off the place "
    "around them: a standing adult's head reaches about the top of a shopfront doorway, stays "
    "well below the awning and the first-floor balcony, is roughly three times the height of a "
    "plastic stool, and is a little taller than a market stall. Where two or more people share "
    "the frame, hold their heights in a believable relation to each other as well — one adult "
    "is not half again the height of another, and a seated person's head sits around a standing "
    "person's waist. A figure towering over the doorways, or dwarfed by a stool, is wrong even "
    "when the face and the costume are right.\n\n"
    "Every figure stands IN the place, never pasted on top of it. Their feet — or paws, or an "
    "object's base — meet a surface that actually exists in the frame, at a depth where the "
    "perspective would put a body of that size, and the ground beneath carries the matching "
    "contact shadow plus a reflection when it is wet. Some location references are shot square "
    "on to a frontage and show little ground running away from the camera; in those, put the "
    "figure ON that frontage's pavement — beside a doorway, along the stall line, under the "
    "awning — instead of hovering in the open middle of the image with nothing underneath them, "
    "which reads as a cut-out floating in mid-air.\n\n"
    "Obey the stated weather and time of day physically. In rain, anyone not under an awning, a "
    "roof or an umbrella is visibly getting wet, and the goods, tables and stools a trader would "
    "have moved under cover ARE under cover — never leave someone working calmly at a dry table "
    "in the open during a downpour, and never leave an umbrella raised over someone already "
    "standing under a roof.\n\n"
    "Add no annotations of your own — no captions, view labels, callouts, subtitles or "
    "watermarks. Text that belongs to the world (shop signs, banners, posters) stays, and is "
    "reproduced faithfully from the location reference"
)

# Phần PHỤ của guard trên, CHỈ chèn khi bối cảnh của dự án dùng lưới 4 khung
# (`project.location_frames == 4`). Ở chế độ 1 ảnh thì ảnh bối cảnh vốn đã là một góc máy
# duy nhất nên đoạn này thừa và còn gợi ý sai cho model là có lưới.
_SINGLE_FRAME_GRID = (
    "The location reference is a 2x2 grid of FOUR angles of the place for identity only — PICK "
    "the ONE angle that suits this shot and render it as a single full-frame scene; do NOT "
    "reproduce the grid, the four panels, the split layout or any position labels from it"
)

# Câu về ngôn ngữ của CHỮ nằm TRONG ảnh (biển hiệu, chú thích, nhãn), chèn vào mọi prompt
# ảnh. `{lang}` lấy từ `project.image_text_lang`.
_IMAGE_TEXT = (
    "Any visible text, signs, captions or labels in the image must be written in {lang} "
    "(keep domain-specific foreign terms, e.g. English brand or technical words, in their "
    "original language)"
)

# Bản cho VIDEO. Không dùng chung câu của ảnh được: nói "in the image" với model video thì
# nó hiểu là ảnh tham chiếu, còn chữ MỚI mà nó tự vẽ thêm vào các frame sau (biển hiệu, băng
# rôn, bảng chỉ đường) thì mặc định rơi về tiếng Trung. Nên phải nói rõ "trong video, ở MỌI
# frame" và chặn thẳng các hệ chữ khác.
_VIDEO_TEXT = (
    "Any text visible anywhere in the video — shop signs, banners, posters, street signs, "
    "screens, packaging or handwriting — must be written in {lang}, in EVERY frame and for "
    "the whole clip, including any signage that comes into view as the camera moves. Do NOT "
    "invent signage or lettering in another language or writing system (no Chinese, Japanese "
    "or Korean characters, no Cyrillic, no Arabic script) unless the scene explicitly calls "
    "for it; keep domain-specific foreign terms (English brand or technical words) in their "
    "original language. Add no subtitles, captions, titles or watermarks of your own"
)


def join_blocks(*parts: str) -> str:
    """Nối các khối prompt thành các ĐOẠN riêng, cách nhau một dòng trống.

    Trước đây nối bằng `". "`, nên header dài 6 đoạn, style, mô tả nhân vật và khối JSON 26KB
    dính thành MỘT dòng khổng lồ — model đọc câu style như phần đuôi của câu cuối trong header,
    và chỗ nối sinh ra `".."` khi khối trước đã có dấu chấm. Mỗi thứ một đoạn thì ranh giới
    giữa chúng là ranh giới thật, không phải một dấu chấm giữa biển chữ.

    Khối rỗng bị bỏ qua (không để lại dòng trống thừa)."""
    return "\n\n".join(p for p in (str(x or "").strip() for x in parts) if p)


def compose_prompt(project: dict, body: str, *, include_culture: bool = True,
                   single_frame: bool = False,
                   header: str | None = None, footer: str | None = None,
                   media: str = "image") -> str:
    """Assemble the final image/video prompt for a project.

    Order: [prompt_header] → style (always first of the visual terms) → culture_hint →
    body → [single-frame guard] → [prompt_footer]. `style` leads so the model anchors on it;
    the culture hint (e.g. "Vietnamese folk tale, traditional Vietnamese architecture") keeps
    imagery faithful to the story's origin instead of defaulting to the style's home culture.

    Mỗi khối là một ĐOẠN riêng (`join_blocks`), không dồn thành một dòng.

    `single_frame=True` (shot frames only) appends a guard so the model renders one coherent
    photograph instead of copying the entity reference SHEETS (incl. the 2x2 location grid).

    `header` / `footer` ĐÈ giá trị của dự án khi được truyền (chuỗi rỗng = KHÔNG chèn gì).
    Node editor dùng đường này: ở đó header/footer do node "Prompt header"/"Prompt footer"
    quyết định, không có node thì không chèn — xem agent/studio/graph.py.

    `media="video"` đổi câu cuối sang bản dành cho video ("chữ ở MỌI frame") thay vì bản cho
    ảnh — model video hiểu "in the image" là ảnh tham chiếu nên chữ nó tự vẽ thêm vào clip
    vẫn rơi về tiếng Trung.

    Guard khung đơn và câu về ngôn ngữ chữ là PROMPT NGẦM: xem/chỉnh được trong
    ⚙ Thiết lập dự án → "Prompt ngầm" (PROMPT_DEFAULTS bên dưới).
    """
    style = (project.get("style") or "").strip()
    header = ((project.get("prompt_header") or "") if header is None else header).strip()
    footer = ((project.get("prompt_footer") or "") if footer is None else footer).strip()
    culture = (project.get("culture_hint") or "").strip() if include_culture else ""
    guard = single_frame_guard(project) if single_frame else ""
    return join_blocks(header, style, culture, (body or "").strip(), guard, footer,
                       _text_lang_clause(project, media))


def single_frame_guard(project: dict | None) -> str:
    """Guard khung đơn cho ảnh frame + phần phụ về lưới bối cảnh (chỉ khi dùng lưới 4 khung)."""
    return join_blocks(prompt_part(project, "single_frame"),
                       prompt_part(project, "single_frame_grid")
                       if location_frames(project) == 4 else "")


def _text_lang_clause(project: dict, media: str = "image") -> str:
    """Instruction for the language of any text rendered INSIDE the generated media (signs,
    captions, labels). Domain-specific foreign terms (brand/product/English jargon) stay
    untranslated so they read naturally.

    Ảnh và video dùng HAI khối khác nhau (`image_text` / `video_text`) nhưng chung một ngôn
    ngữ (`project.image_text_lang`)."""
    lang = (project.get("image_text_lang") or "Vietnamese").strip()
    if not lang:
        return ""
    return prompt_part(project, "video_text" if media == "video" else "image_text", lang=lang)


# ─── Prompt templates ───────────────────────────────────────

def script_from_idea_prompt(idea: str, target_duration: int | None,
                            storytelling: bool, style: str, shot_duration: int = 8,
                            language: str = "Vietnamese") -> str:
    budget = ""
    if target_duration:
        shots = max(1, round(target_duration / max(1, shot_duration)))
        words = round(target_duration * 2.5)
        budget = (f"\nTARGET DURATION: {target_duration}s "
                  f"(≈ {shots} shots, ≈ {words} words of narration). "
                  f"Compress or expand the content to fit this length.")
    else:
        budget = "\nNo target duration — keep the full content, natural length."
    mode = ("This is STORYTELLING mode: write a continuous voiceover-driven story; "
            "each scene = one contiguous segment of the content, tied to one location."
            if storytelling else
            "Standard screenplay with dialogue and action.")
    return (
        "You are a professional screenwriter. Write a screenplay in FOUNTAIN format "
        "(scene headings like 'INT. PLACE - DAY', action lines, CHARACTER cues, dialogue).\n"
        f"WRITE THE SCREENPLAY IN {language.upper()}: all action lines, dialogue and "
        f"narration must be in {language}. Keep the FOUNTAIN structural keywords in English "
        "(INT./EXT., DAY/NIGHT, the dual-dialogue caret), but the place name in the scene "
        f"heading should be in {language}. Keep proper nouns and domain-specific foreign "
        "terms (brand/technical/English jargon) in their original language.\n"
        f"Visual style of the film: {style}.\n{mode}{budget}\n\n"
        f"IDEA / CONTENT:\n{idea}\n\n"
        "Also DETECT the cultural origin of this content (which country/era/folk tradition "
        "it belongs to) and return a short ENGLISH `culture_hint` — a comma-separated list of "
        "concrete visual cues that make generated imagery faithful to that origin "
        "(e.g. for a Vietnamese folk tale: 'Vietnamese folk tale, traditional Vietnamese "
        "architecture (nhà tranh, đình làng), áo dài / áo tứ thân clothing, Vietnamese rural "
        "landscape, conical hats'). If the content is culturally neutral, return an empty string.\n\n"
        "Return ONLY JSON: {\"script\": \"<fountain screenplay>\", "
        "\"estimated_duration\": <seconds>, \"culture_hint\": \"<english visual cues or empty>\"}"
    )


def entity_extract_prompt(script: str) -> str:
    return (
        "Extract every distinct ENTITY from this screenplay for an asset library.\n"
        "Three types: 'character' (people/animals), 'location' (places), 'prop' (key objects).\n"
        # Quần áo đang MẶC là một phần của nhân vật, không phải một entity riêng. Tách ra thì
        # sinh hai ảnh tham chiếu cho cùng một thứ — sheet nhân vật đã mặc áo dài, lại thêm
        # một sheet đạo cụ "Áo dài trắng" — và shot nào gọi cả hai thì model dễ vẽ thừa một
        # bộ nữa hoặc vẽ bộ đồ lơ lửng. Đo được: 19 prop là trang phục trên các dự án hiện có.
        "Clothing, footwear and accessories that a character WEARS are part of that "
        "character's own description — never emit them as separate 'prop' entities, even when "
        "the screenplay dwells on them. Only make a prop for an object that is handled, "
        "carried, exchanged, or that appears on its own away from the person wearing it.\n"
        # Cùng luật, chiều bối cảnh: đồ trang trí/hàng hoá làm nên cái nơi ấy đã nằm sẵn
        # trong ảnh bối cảnh. Tách thành prop rồi gọi tên trong shot là đưa cho model MỘT
        # cái đèn lồng anh hùng để dựng vào tiền cảnh một con phố vốn đã treo hàng trăm cái.
        "In the same way, scenery and merchandise that simply FURNISH a place — the lanterns "
        "strung along a lantern street, the tables of a café, the wares on a market stall — "
        "belong to that location's description, not to a prop of their own. A prop earns its "
        "own entity only when a character interacts with it or the story singles it out.\n"
        "A 'character' is ONE SINGLE individual — never a group. If the screenplay refers to "
        "several people with one collective term (a couple, the pair, the parents, the twins, "
        "the children, a family, a crowd, a gang, a team), do NOT make one entity for it: emit "
        "a SEPARATE character entity for each individual you can distinguish, each with its own "
        "singular `name` and its own appearance. Unnamed background crowds are not entities at "
        "all — leave them out. `name` must be singular and refer to one being; never a plural "
        "or collective noun.\n"
        "`name` MUST be the SHORT, single consistent token the screenplay uses to refer to the "
        "entity (e.g. a first name like 'Hùng', not 'Hùng (Phạm Trọng Hùng)'). Do NOT put a "
        "full name, alias or anything in parentheses in `name` — that goes in `description`. "
        "Keep `name` unique; if two characters share a short name, pick distinct short tokens.\n"
        "For each, write a concise visual `description` (you may note the full name/alias here) "
        "and a `ref_prompt` (a vivid image prompt to generate its reference art).\n\n"
        f"SCREENPLAY:\n{script}\n\n"
        "Return ONLY JSON array: "
        "[{\"type\":\"character|location|prop\",\"name\":\"...\",\"description\":\"...\","
        "\"ref_prompt\":\"...\"}]"
    )


# Per-type reference-image prompt rules (video-app.md §2.2) — clean refs.
# Returns the BODY only; the caller wraps it with style/culture/header/footer via
# compose_prompt() so style always leads the prompt.
_SHEET = {
    # EXACTLY ONE individual per sheet. A description that mentions a partner/group ("một nửa
    # của cặp đôi", "walks with her husband") otherwise makes the model draw BOTH people on the
    # sheet — and then every shot referencing it reproduces that same pair in the same stance,
    # like carrying one statue from frame to frame.
    "character": ("full character reference sheet on a plain solid white background, "
                  "laid out as a single sheet: ONE large detailed upper-body (bust) "
                  "portrait on the left, a row of turnaround views (front, 3/4, side, back) "
                  "in a neutral A-pose, and a separate row of facial EXPRESSION studies "
                  "(neutral, happy, sad, angry, surprised). EXACTLY ONE individual appears on "
                  "this sheet — the same single character in every view. Never draw two or more "
                  "people, never a couple, pair, family or group, even if the description above "
                  "mentions other people (they are separate entities with their own sheets); "
                  "include no companion, partner, child or bystander. No scene, no extra props, "
                  "no ground shadow, studio reference. Do NOT draw any text, titles, captions, "
                  "view labels or watermarks on the sheet — clean art only"),
    # Biến thể MỘT ẢNH của nhân vật (`project.character_one == 1`): KHÔNG bảng, KHÔNG panel.
    #
    # Lý do tồn tại: Flow thay mỗi reference part bằng CHÚ THÍCH TỰ SINH của ảnh đó, nên ảnh
    # ref là bảng sheet thì mọi shot dùng nhân vật ấy đều mở đầu bằng "Character design sheet
    # for a woman ..." — model được bảo vẽ một cái bảng và nó vẽ đúng thế. Ảnh ref là một
    # người đứng trên nền trơn thì chú thích ấy là "a woman in a white ao dai", tức đúng thứ
    # ta muốn nói về nhân vật. Ép luôn TOÀN THÂN + chính diện + nền trơn: đó là ảnh mang nhiều
    # thông tin nhận dạng nhất trong một khung (mặt, dáng, trang phục, giày), và nền trơn để
    # chú thích không lẫn bối cảnh vào.
    "character_one": ("ONE single full-body reference image of the character, front-facing in "
                      "a relaxed neutral pose, the whole body fully visible, looking at the "
                      "camera with a neutral expression, on a plain solid white background. "
                      # `character` gồm CẢ người mọi lứa tuổi LẪN động vật (xem
                      # entity_extract_prompt), nên mẫu không được mặc định là một người trẻ:
                      # câu "adolescent proportions … She stands" từng biến entity Mèo thành
                      # một cô gái và trẻ hoá entity Bà cụ. Tuổi/loài LUÔN lấy từ mô tả, phần
                      # chống chibi chỉ áp cho người.
                      "Species, age and body come from the description above and nothing "
                      "else: an animal is drawn as that animal with its own natural anatomy "
                      "on all fours if that is how it stands, an elderly person is elderly, a "
                      "child is a child. Never turn an animal into a person or a person into "
                      "an animal, and never make the subject younger or older than described. "
                      "When the subject IS human, use realistic human proportions — roughly "
                      "seven to seven and a half heads tall, the head small relative to the "
                      "body — never a chibi, super-deformed, mascot or doll figure, never an "
                      "oversized head, a head as wide as the shoulders or stubby limbs. "
                      "The background is EMPTY WHITE — no street, no "
                      "buildings, no shopfronts, no vehicles, no furniture, no landscape, no "
                      "scenery of any kind, however strongly the text above describes a "
                      "place; any setting mentioned earlier belongs to other images, not to "
                      "this one. NOT a sheet, NOT a grid, no panels, no multi-view "
                      "turnaround, no expression row, no collage, no inset detail boxes. "
                      "EXACTLY ONE individual — never two or more people, never a couple, "
                      "pair, family or group, even if the description above mentions other "
                      "people (they are separate entities with their own images); include no "
                      "companion, partner, child or bystander. Even soft studio lighting, no "
                      "scene, no extra props, no ground shadow. Do NOT draw any text, titles, "
                      "captions, labels or watermarks — clean art only"),
    # Mô tả đạo cụ hầu như luôn kể luôn AI dùng nó và dùng Ở ĐÂU ("vật bất ly thân của Mai",
    # "món quà của bà cụ bán trà", "treo trước cửa hiệu phố Hàng Mã") — và model vẽ ra đúng
    # cảnh đó: entity "Ô" từng ra nguyên một cô gái đang cầm ô đi trong mưa. Bối cảnh và nhân
    # vật đã có câu chặn tương tự trong mẫu của mình; đạo cụ thì thiếu.
    "prop": ("object design sheet, multiple angles (front, 3/4, side, top), single isolated "
             "object on plain solid white background, no background scene, no shadow, "
             "studio product reference. The OBJECT ALONE fills this sheet: no people, no "
             "hands, no character holding, wearing or using it, no shop, street, room, "
             "weather or setting of any kind — ignore every person, place and time of day "
             "named in the description above, they belong to other images and are only "
             "there to say what the object is for. Do NOT draw any text, titles, captions, "
             "view labels or watermarks on the sheet — clean art only"),
    # ONE image = a 2x2 grid of four angles of the same place, in a FIXED quadrant order so
    # we can overlay correct position labels afterwards (Toàn cảnh / Góc ngược / Trên cao /
    # Cận cảnh). The model must not draw its own text. Shots use the single_frame guard to
    # pick one angle instead of copying the grid.
    "location": ("ONE image laid out as a tidy 2x2 grid of FOUR camera angles of the SAME "
                 "place, in this EXACT order: TOP-LEFT a wide establishing shot, TOP-RIGHT the "
                 "reverse angle, BOTTOM-LEFT a high overhead/bird's-eye angle, BOTTOM-RIGHT an "
                 "eye-level closer detail. Consistent architecture, materials, colour and "
                 "lighting across all four panels. The place is COMPLETELY EMPTY — no people, "
                 "no animals (ignore any people mentioned above). Cinematic, deep detail, drawn "
                 "in the SAME visual style stated at the top of this prompt — do NOT switch to "
                 "photorealism unless that style asks for it. Do NOT draw any text, captions, "
                 "labels or watermarks yourself — clean panels only"),
    # Biến thể MỘT ẢNH của bối cảnh (`project.location_frames == 1`): một góc máy duy nhất,
    # không lưới → không có nhãn góc để dán, và shot không phải "chọn một ô" nữa.
    "location_one": ("ONE single establishing view of the place from ONE camera angle — "
                     "a wide, full-frame view that reads the whole space. NOT a grid, NOT a "
                     "2x2 layout, no panels, no split screen, no collage, no multiple angles. "
                     "The view must have DEPTH: the camera looks ALONG the space, not flat at "
                     "one wall of it. Put the ground plane — road, floor, path, water — running "
                     "away from the camera into the distance with a clear vanishing point, and "
                     "let the space continue on BOTH sides of that line, receding and getting "
                     "smaller. A head-on elevation of a single frontage, with everything at one "
                     "distance and no ground leading away, is WRONG: characters placed against "
                     "it look pasted in front of a flat wall with nowhere to stand. There must "
                     "be room in this frame for someone to be near, far, or halfway down it. "
                     "Cinematic, deep detail, consistent architecture, materials, colour and "
                     "lighting, drawn in the SAME visual style stated at the top of this "
                     "prompt — do NOT switch to photorealism unless that style asks for it. "
                     "The place is COMPLETELY EMPTY — no people, no "
                     "animals (ignore any people mentioned above). Do NOT draw any text, "
                     "captions, labels or watermarks — clean image only"),
}

# "Character Production Bible" — sheet nhân vật 13 mục, mặc định MỚI cho `sheet_character`.
#
# Nằm ở file riêng chứ không phải string literal trong đây: nó dài 26KB JSON, nhồi vào brain.py
# thì không ai đọc nổi phần còn lại của module, và nó vốn là thứ người dùng chỉnh (chép nguyên
# văn vào ô ⚙ Thiết lập → 🧩 Prompt ngầm) chứ không phải logic. Gửi lên Flow dưới dạng JSON
# THÔ — model đọc được cấu trúc, và cấu trúc mới là thứ khoá danh tính giữa 13 panel.
#
# Đọc lỗi (thiếu file, JSON hỏng) → rơi về mẫu một-sheet cũ ở `_SHEET["character"]` thay vì
# làm sập cả agent: một sheet nhân vật kém đẹp còn hơn không sinh được ảnh nào.
_BIBLE_FILE = Path(__file__).parent.parent.parent / "presets" / "character-sheet-prompt.json"


def _character_bible() -> str:
    try:
        text = _BIBLE_FILE.read_text(encoding="utf-8").strip()
        json.loads(text)          # chỉ để chắc file không hỏng; gửi đi là bản THÔ
        return text
    except (OSError, ValueError) as e:
        logger.warning("Không đọc được %s (%s) — dùng mẫu sheet nhân vật cũ",
                       _BIBLE_FILE.name, e)
        return ""


# Position labels overlaid on the location grid quadrants (TL, TR, BL, BR), matching the
# order fixed in the _SHEET["location"] prompt above. Chỉ dùng ở chế độ lưới 4 khung.
LOCATION_GRID_LABELS = ["Toàn cảnh", "Góc ngược", "Trên cao", "Cận cảnh"]


def character_one(project: dict | None) -> bool:
    """Ảnh tham chiếu của một NHÂN VẬT là MỘT ẢNH (True) hay bảng sheet nhiều mục (False).

    Mặc định False = giữ bảng "Character Production Bible" 13 mục. Bật lên khi shot bị lây
    layout bảng: chú thích tự sinh của ảnh ref chui vào prompt shot, mà chú thích của một cái
    bảng thì là "character design sheet" — xem `_SHEET["character_one"]`."""
    try:
        return int((project or {}).get("character_one") or 0) == 1
    except (TypeError, ValueError):
        return False


def location_frames(project: dict | None) -> int:
    """Ảnh tham chiếu của một bối cảnh là LƯỚI 4 GÓC MÁY (4, mặc định) hay MỘT ẢNH (1).

    Quyết định ba thứ đi liền nhau: mẫu prompt sinh ảnh bối cảnh, việc dán nhãn 4 ô lên bản
    hiển thị, và đoạn phụ của guard khung đơn khi vẽ frame."""
    try:
        n = int((project or {}).get("location_frames") or 4)
    except (TypeError, ValueError):
        return 4
    return 1 if n == 1 else 4


def ref_image_prompt(entity_type: str, name: str, description: str,
                     project: dict | None = None) -> str:
    """Build the (style-less) body of an entity's reference-art prompt.

    The entity NAME is a LIBRARY LABEL, not art direction, so it is no longer prefixed onto
    the prompt: the model read it as part of the scene description and painted whatever the
    label happened to mention — a location named "DÂY PHƠI VÀ CON PHỐ LÚC RẠNG SÁNG" came back
    with a clothesline hung across the street even when the description said nothing of the
    sort. The name is only used as the body when there is no description at all.

    Mô tả và mẫu sheet là HAI ĐOẠN riêng — mẫu `sheet_character` là khối JSON 26KB, dán nó
    vào sau mô tả bằng một dấu chấm thì chính nó bảo model đọc "character description written
    immediately before this JSON" mà ranh giới lại không nhìn thấy được.

    Luật theo từng loại (sheet nhân vật / đạo cụ / bối cảnh) là PROMPT NGẦM — chỉnh được
    trong ⚙ Thiết lập dự án. Bối cảnh có hai mẫu: lưới 4 khung hoặc một ảnh.
    """
    base = (description or "").strip() or (name or "").strip()
    key = entity_type
    if entity_type == "location" and location_frames(project) == 1:
        key = "location_one"
    elif entity_type == "character" and character_one(project):
        key = "character_one"
    rule = (prompt_part(project, f"sheet_{key}") if f"sheet_{key}" in PROMPT_DEFAULTS
            else "clean reference image")
    return join_blocks(base, rule) if rule else base


# Cinematography spec injected into every shot-creating prompt so each frame's
# `visual_prompt` is a real camera setup, not a vague description. The model must
# make a deliberate choice on every axis below (and vary them across shots so the
# scene doesn't read as one flat angle repeated).
_CINE = (
    "CINEMATOGRAPHY — BOTH the `description` (which generates the still image) and the "
    "`visual_prompt` MUST explicitly specify ALL of these, and ADJACENT frames MUST DIFFER "
    "(never repeat the same shot size AND angle in two consecutive frames) so the scene has "
    "visual rhythm and the cuts don't look like the same shot repeated:\n"
    "  • Shot size / framing: extreme wide, wide/establishing, full, medium, medium close-up, "
    "close-up, or extreme close-up.\n"
    "  • Camera angle & height: eye-level, low angle, high angle, overhead/top-down, dutch "
    "tilt, over-the-shoulder, or POV.\n"
    "  • Lens / focal length & depth of field: e.g. 24mm wide, 35mm, 50mm, 85mm portrait, "
    "135mm telephoto — plus shallow depth of field (soft bokeh background) or deep focus.\n"
    "  • Lighting: scheme and direction (key/fill/back, soft vs hard, Rembrandt, rim/back-"
    "light, silhouette), source (natural daylight, golden hour, moonlight, practical lamps, "
    "firelight), color temperature (warm/cool) and overall contrast.\n"
    "  • Composition & object layout: where each character and prop sits in frame "
    "(foreground / midground / background), rule of thirds, leading lines, symmetry/balance, "
    "headroom and negative space.\n"
    "  • Pose & body language of EVERY character present: stance or posture, what the hands "
    "are doing, head turn and gaze direction, facial expression, and — with two or more people "
    "— how they are placed and turned relative to each other (facing, side by side, one behind, "
    "one reaching toward the other). State this explicitly and CHANGE it between frames; "
    "characters must act out the beat, never stand in the same neutral stance shot after shot "
    "like a statue moved around the set.\n"
    "  • The PLACE is already fixed by its reference image, and that image is the TRUTH about this location, not a starting point to embellish. Say which PART of it the camera is looking at — a doorway, a stall, the kerb, the depth of the street — and do NOT invent architecture or set-dressing the reference does not have: no new buildings, roofs, eaves, gates, shrines, screens or ornament, and nothing borrowed from another country's building tradition. Whatever the place does own stays WHERE the reference puts it: goods and stalls against the frontage, furniture at the pavement edge, the roadway and the walking space left CLEAR. Never move that dressing into the middle of the street, never pile it in front of the sign, pole or landmark that identifies the place, and never multiply it into a heap that was not there. If a character needs to be beside something, move the CHARACTER to it.\n"
    "  • Anchor SCALE against something fixed in the frame, in words: 'her head reaches the top "
    "of the shopfront doorway', 'she stands a head below the awning', 'seated, the elder's head "
    "is level with her waist'. With two people in frame, state their relative heights too. "
    "Without an anchor the image model sizes each figure independently and one of them ends up "
    "towering over the shopfronts. Say what each person is STANDING ON as well — the pavement "
    "outside a named shop, the kerb, the middle of the wet road — so nobody ends up floating in "
    "open space with no ground under them.\n"
    "  • Keep the frame physically possible in the stated weather: in rain, put the people and "
    "the goods that would be under cover under an awning or a roof, and let anyone in the open "
    "be visibly rained on. A trader working calmly at a dry table in a downpour, or a raised "
    "umbrella under a roof, reads as a mistake.\n"
    "  • Name each character ONCE per field. Introduce them with their braced name the first "
    "time they appear in that field and use a pronoun — 'she', 'her', 'the elder', 'the cat' — "
    "for every later mention in the SAME field. Writing the name again in a second sentence "
    "makes the image model draw a SECOND COPY of that person standing beside the first, because "
    "each mention reads to it as another subject to place in the frame.\n"
    "  • Mood / color palette and atmosphere: time of day, weather, haze/fog/dust, "
    "volumetric light, particles — whatever sells the scene's emotion."
)

# Biến thể LIÊN TỤC của khối trên (`project.shot_continuity == 1`).
#
# Bản mặc định ở trên sinh shot cho lối KỂ CHUYỆN: mỗi khung là một bức ảnh minh hoạ cho một
# câu lời đọc, và nó ÉP khung liền kề phải khác nhau. Đem những khung ấy đi dựng video thì mỗi
# clip là một chỗ khác nhau trong cùng một cảnh — nhân vật nhảy từ đầu phố xuống cuối phố, đổi
# hướng đi, đổi phía màn hình — nối lại thành phim thì rời rạc.
#
# Bản này đảo đúng cái luật đó: các khung trong MỘT scene là các lát cắt liên tiếp của MỘT
# hành động trong MỘT không gian, cắt theo ngữ pháp dựng phim thật (đường 180°, quy tắc 30°,
# giao khung ra/vào). Hai bản dùng chung mọi trục kỹ thuật, chỉ khác luật liên khung.
_CINE_CONTINUOUS = (
    "CINEMATOGRAPHY — the frames of ONE scene are consecutive slices of ONE continuous action "
    "in ONE space, cut together as a real film sequence. BOTH the `description` (which "
    "generates the still image) and the `visual_prompt` MUST explicitly specify ALL of the "
    "axes below.\n"
    "CONTINUITY comes first, and it overrides any urge to make neighbouring frames look "
    "different:\n"
    "  • Each frame picks up exactly where the previous one left off — same moment of the "
    "action carried a little further, same time of day, same weather and light, same costume, "
    "same props in the same hands. Nothing resets between frames.\n"
    "  • Hold the 180° line: once the action has a screen direction, keep it. A character "
    "walking left-to-right keeps walking left-to-right in every following frame of the scene; "
    "if they leave frame right, the next frame has them entering from frame left.\n"
    "  • The character's position advances THROUGH the space step by step — a few paces "
    "further along the same street, nearer the same doorway — never teleporting to an "
    "unrelated part of the location between frames.\n"
    "  • Change shot size by AT MOST one step at a time (wide → full → medium → close-up, or "
    "the reverse). Never cut straight from an extreme wide to an extreme close-up. This is a "
    "CEILING on how far a cut may jump, NOT an instruction to change size on every cut: when "
    "the scene's shape asks you to hold one size across several frames, or to keep the camera "
    "in one position and let the subject come toward it, holding the size is CORRECT. Repeating "
    "a shot size is a fault only when nothing else in the frame has moved on.\n"
    "  • When the angle changes, change it by at least 30° so the cut doesn't jitter, but "
    "stay on the SAME side of the action line.\n"
    "  • State in each frame where the subject stands relative to the previous frame, so the "
    "whole scene reads as one walk, one conversation, one gesture — not a gallery of angles.\n"
    "Within that discipline, still specify:\n"
    "  • Shot size / framing: extreme wide, wide/establishing, full, medium, medium close-up, "
    "close-up, or extreme close-up.\n"
    "  • Camera angle & height: eye-level, low angle, high angle, overhead/top-down, dutch "
    "tilt, over-the-shoulder, or POV.\n"
    "  • Lens / focal length & depth of field: e.g. 24mm wide, 35mm, 50mm, 85mm portrait, "
    "135mm telephoto — plus shallow depth of field (soft bokeh background) or deep focus. Keep "
    "one lens language across the scene.\n"
    "  • Lighting: scheme and direction (key/fill/back, soft vs hard, Rembrandt, rim/back-"
    "light, silhouette), source (natural daylight, golden hour, moonlight, practical lamps, "
    "firelight), color temperature (warm/cool) and overall contrast — CONSISTENT across the "
    "whole scene, since it is one continuous moment.\n"
    "  • Composition & object layout: where each character and prop sits in frame "
    "(foreground / midground / background), rule of thirds, leading lines, symmetry/balance, "
    "headroom and negative space.\n"
    "  • Pose & body language of EVERY character present: stance or posture, what the hands "
    "are doing, head turn and gaze direction, facial expression, and — with two or more people "
    "— how they are placed and turned relative to each other. Let it EVOLVE frame to frame as "
    "one continuous movement; never reset to a neutral stance and never repeat the previous "
    "frame's pose unchanged.\n"
    "  • The PLACE is already fixed by its reference image, and that image is the TRUTH about this location, not a starting point to embellish. Say which PART of it the camera is looking at — a doorway, a stall, the kerb, the depth of the street — and do NOT invent architecture or set-dressing the reference does not have: no new buildings, roofs, eaves, gates, shrines, screens or ornament, and nothing borrowed from another country's building tradition. Whatever the place does own stays WHERE the reference puts it: goods and stalls against the frontage, furniture at the pavement edge, the roadway and the walking space left CLEAR. Never move that dressing into the middle of the street, never pile it in front of the sign, pole or landmark that identifies the place, and never multiply it into a heap that was not there. If a character needs to be beside something, move the CHARACTER to it.\n"
    "  • Anchor SCALE against something fixed in the frame, in words: 'her head reaches the top "
    "of the shopfront doorway', 'she stands a head below the awning', 'seated, the elder's head "
    "is level with her waist'. With two people in frame, state their relative heights too. "
    "Without an anchor the image model sizes each figure independently and one of them ends up "
    "towering over the shopfronts. Say what each person is STANDING ON as well — the pavement "
    "outside a named shop, the kerb, the middle of the wet road — so nobody ends up floating in "
    "open space with no ground under them.\n"
    "  • Keep the frame physically possible in the stated weather: in rain, put the people and "
    "the goods that would be under cover under an awning or a roof, and let anyone in the open "
    "be visibly rained on. A trader working calmly at a dry table in a downpour, or a raised "
    "umbrella under a roof, reads as a mistake.\n"
    "  • Name each character ONCE per field. Introduce them with their braced name the first "
    "time they appear in that field and use a pronoun — 'she', 'her', 'the elder', 'the cat' — "
    "for every later mention in the SAME field. Writing the name again in a second sentence "
    "makes the image model draw a SECOND COPY of that person standing beside the first, because "
    "each mention reads to it as another subject to place in the frame.\n"
    "  • Mood / color palette and atmosphere: time of day, weather, haze/fog/dust, "
    "volumetric light, particles — whatever sells the scene's emotion."
)

# ─── Hình dáng scene + chuyển cảnh (chỉ khi bật `shot_continuity`) ──────────
#
# `_CINE_CONTINUOUS` nối các khung TRONG một scene, nhưng không nói gì về việc scene này phải
# KHÁC scene kia. Mà revary / autofill / tách beat đều chạy MỖI SCENE MỘT LƯỢT GỌI AI riêng:
# lượt viết scene 5 không hề nhìn thấy scene 4 đã dựng ra sao. Nên mỗi lượt model lại chọn đúng
# một công thức an toàn nhất — wide → full → medium → close — và 12 scene liền nhau ra y hệt
# nhau. Thêm câu "hãy đa dạng" vào prompt KHÔNG chữa được, vì cái model thiếu là thông tin chứ
# không phải lời nhắc.
#
# Nên việc chọn nằm ở CODE: bốc sẵn một hình dáng theo `scene_idx` rồi đưa THẲNG hình dáng đó
# vào prompt. Hai scene liền nhau không bao giờ trùng, và cả phim đi hết bảng trước khi lặp.
#
# Bảng dài thì KHÔNG tốn gì cả: mỗi lượt gọi AI chỉ nhận đúng MỘT mục, phần còn lại không đi
# lên model. Nên cứ thêm mục mới khi nghĩ ra — dài hơn thì phim lâu lặp lại hơn, thế thôi.
# Thêm thoải mái: `_stride` tự lo điều kiện quét hết bảng, không phải sửa gì thêm.
_SCENE_SHAPES: tuple[tuple[str, str], ...] = (
    ("Detail out",
     "open on the SMALLEST thing in the scene filling the whole frame — a texture, a hand, an "
     "object, water running off an edge — and open up one notch per cut until the last frames "
     "hold the whole place. The widest frame of this scene is its LAST one, not its first"),
    ("Establish in",
     "open on the widest frame of the whole scene and close in one notch per cut, so the "
     "tightest frame lands on the emotional beat and the scene ends there"),
    ("Reveal behind foreground",
     "keep something in the NEAR foreground between lens and subject in every frame — hanging "
     "goods, a rain-blurred awning, passers-by, the edge of a doorway. The subject starts "
     "partly hidden and the foreground clears a little more each cut until the final frame "
     "sees them plainly"),
    ("Travelling follow",
     "hold ONE shot size for most of the scene and travel WITH the subject. The change between "
     "frames comes from what enters and leaves the frame around them and from the camera "
     "drifting 30–45° around them per cut — not from cutting closer. Only the final frame "
     "changes shot size"),
    ("Descend",
     "start high above the action — a rooftop, an upper-floor window, straight down on the wet "
     "street — and step the camera DOWN the building line frame by frame until it reaches "
     "street level, ending at eye level or below"),
    ("Reflection first",
     "play the opening frames in a reflective surface — a rain puddle, shop glass, a metal "
     "tray, a sheet of tin, a lacquered table. The subject exists ONLY as a reflection until "
     "the middle of the scene, where the camera lifts or turns to the direct view for the "
     "closing frames"),
    ("Static frame, moving world",
     "lock ONE wide composition and let the subject move THROUGH it — enter one side, cross, "
     "stop, leave. Two or three frames of this scene keep the EXACT same locked composition at "
     "different moments of that crossing; only the final frame moves in for the reaction"),
    ("Two-hander",
     "build the scene on the relationship between two subjects: open on a two-shot holding "
     "both, then alternate over-the-shoulder singles across the SAME side of the 180° line, "
     "closing back on the two-shot or on the listener's face. If only one figure is present, "
     "make the place the second party — alternate between the subject and the thing they are "
     "looking at, shot and point-of-view reverse"),
    ("Rise",
     "the mirror of a descent: start at ground level — feet, a kerb, water running between "
     "cobbles — and step the camera UP frame by frame, ending high and wide looking out over "
     "the whole place"),
    ("Orbit",
     "the camera arcs steadily around the subject across the scene, each frame a further "
     "30–40° round the SAME circle at roughly the same radius, so the background rotates "
     "behind them while they hold the centre of frame"),
    ("Depth stack",
     "keep the camera in ONE position and change which PLANE of the frame the action lives in: "
     "the subject is deep in the background in the first frame, midground in the next, and "
     "right up against the lens by the last — they come toward the camera through the scene "
     "instead of the camera going to them"),
    ("Insert-punctuated",
     "alternate strictly between wider frames carrying the action and TIGHT INSERTS of what the "
     "hands touch or the eyes land on — an object, a fastening, a coin, a surface. Every other "
     "frame is an insert, and each insert is motivated by the frame before it"),
    ("Off-centre",
     "compose every frame with the subject SMALL and pushed hard to one edge, the place filling "
     "the rest — held consistently to the same side. Only the final frame gives them the centre "
     "of the image"),
    ("Frame within a frame",
     "every shot is composed through something that encloses it — a doorway, an archway, the "
     "gap between hanging goods, a window, a gate, the edge of an umbrella. The enclosing frame "
     "CHANGES each cut but is never absent, and it tightens as the scene goes on"),
)

# Mỗi kiểu chuyển cảnh là MỘT CẶP: `out` cho khung CUỐI scene trước, `in` cho khung ĐẦU scene
# sau. Hai nửa phải khớp nhau thì cắt mới liền — nên chúng nằm chung một mục, đừng tách bảng.
#
# Chú ý kỹ thuật, đây là chỗ dễ làm sai: ảnh tĩnh của shot là KHUNG ĐẦU của clip (image-to-video).
# Nên nửa `out` phải nằm trong `motion_prompt` (mấy giây cuối clip), còn nửa `in` phải nằm ngay
# trong ẢNH TĨNH của shot đầu scene sau. Viết ngược lại thì Flow vẽ vũng nước làm khung cuối rồi
# clip chẳng bao giờ tới đó.
_SCENE_TRANSITIONS: tuple[tuple[str, str, str], ...] = (
    ("Clean exit / clean entry",
     "the subject walks fully OUT of frame past one clearly stated edge and the clip holds a "
     "beat on the emptied street after they have gone",
     "the opening frame is the new place EMPTY, composed and waiting at the same shot size as "
     "the frame that emptied at the end of the previous scene; the subject then walks in from "
     "the OPPOSITE edge with the same gait and the same screen direction"),
    ("Threshold cross",
     "the camera moves with the subject toward a gate, archway, doorway or hanging curtain until "
     "that opening fills the frame and its far side is unreadably dark",
     "the opening frame is the FAR side of that same threshold looking back at it, the subject "
     "coming through into the new place; the camera retreats ahead of them and the threshold "
     "leaves frame"),
    ("Invisible cut behind a mass",
     "the camera tracks steadily sideways and a near foreground mass — a pillar, a tree trunk, a "
     "shuttered stall — slides across the lens and fills the frame completely",
     "the opening frame is filled by an equivalent near mass in the new place; the camera keeps "
     "tracking the SAME direction at the same speed and slides out from behind it into the "
     "scene, so the two clips read as one unbroken move"),
    ("Baton pass",
     "something leaves the frame under its own power in the last seconds — a leaf lifted off, a "
     "drop falling out of frame, smoke drifting off the top edge, a bird crossing out",
     "the opening frame catches a like object ARRIVING in the new place — landing, settling, "
     "drifting in from the same edge it left by — before the camera moves off it into the scene"),
    ("Eyeline turn",
     "the subject turns their head sharply toward a clearly stated off-screen direction, the "
     "clip ending on that look with the thing they are looking at still unseen",
     "the opening frame is what they turned toward, seen from their vantage and on the SAME "
     "side of the line, revealed to be in the new place; the camera then settles out of the "
     "point-of-view into a normal frame"),
    ("Scale nest",
     "the camera pushes INTO one small motif until it fills the frame and loses its scale — a "
     "painted flower, a woven pattern, lettering, a grain of a surface",
     "the opening frame is that SAME motif rendered huge in the new place — the same pattern on "
     "a shopfront, a banner, a wall — and the camera pulls back off it until the new place "
     "resolves around it"),
    ("Overhead lift-off",
     "the camera cranes straight UP off the subject, the clip ending with them a small figure in "
     "the pattern of the wet street seen from far above",
     "the opening frame looks straight DOWN on the new place from that same height, the street "
     "reading as pattern; the camera descends into it until it reaches human scale"),
    ("Ground-plane handoff",
     "the camera tilts DOWN off the subject onto the ground itself — cobbles, wet stone, worn "
     "steps — until the surface and its texture fill the whole frame",
     "the opening frame is that same kind of ground surface in the new place, filling the frame "
     "at the same angle; the camera tilts UP off it to reveal where we now are"),
    ("Graphic match",
     "the last frame settles on ONE simple bold shape held large and centred — a round lamp, a "
     "circle of light on wet stone, the dome of an umbrella, the arc of a roof — and holds it",
     "a DIFFERENT object of the SAME shape, at the same size and the same position in frame as "
     "the shape that closed the previous scene, fills the opening frame; the clip then moves "
     "off it into the new place"),
    ("Object wipe",
     "a solid mass sweeps INTO the lens from one clearly stated side and blacks the frame out "
     "in the final second — a passing vehicle, a hanging bolt of cloth, a wall, someone else's "
     "umbrella crossing close to camera",
     "that same dark mass fills the opening frame edge to edge; it clears the frame in the SAME "
     "direction it entered, wiping the new place into view"),
    ("Push through",
     "the camera pushes FORWARD into something opaque until it fills the frame — a curtain of "
     "rain, steam off a pot, the black mouth of an archway, a beaded doorway, a hanging sheet",
     "the opening frame is inside that same opaque material, close enough to read its texture; "
     "the camera emerges FORWARD out of it into the new place, still moving the same direction"),
    ("Match on action",
     "the clip ends MID-GESTURE, the movement deliberately unfinished — an umbrella half-"
     "raised, a head half-turned, a foot leaving the kerb — with the body at a clearly stated "
     "angle and screen position",
     "the opening frame shows that IDENTICAL gesture at the same body angle, same screen "
     "position and same shot size as the frame that ended the previous scene, now COMPLETING "
     "in the new place"),
    ("Light blow-out",
     "a hard light source sweeps across the lens in the final second and washes the frame out "
     "— a headlight, lightning on wet stone, a sign flaring — until detail is lost",
     "the opening frame is still blown out by that glare, the new place only just emerging from "
     "it; the flare slides out of frame and the place resolves"),
    ("Whip pan",
     "the clip ends mid-whip-pan in one clearly stated direction, the whole frame streaked into "
     "horizontal smears of light",
     "the opening frame is the tail of that same whip — everything smeared in the SAME "
     "direction — settling onto the new place as the pan comes to rest"),
    ("Focus handoff",
     "the clip ends by racking focus OFF the subject onto something in the near foreground — a "
     "raindrop on glass, a strand of hair, a wet railing — until the background is nothing but "
     "soft round bokeh of coloured light",
     "the opening frame is that same field of soft round coloured bokeh, the subject unreadable; "
     "focus racks the other way until the new place sharpens into position"),
    ("Silhouette match",
     "the light behind the subject builds until they are reduced to a flat black silhouette "
     "against a bright field, all detail gone",
     "the opening frame is a DIFFERENT black silhouette in the same position and at the same "
     "size against the same bright field — a lamppost, a gate, another figure — and the light "
     "level then comes down to reveal the new place around it"),
    ("Colour flood",
     "one dominant colour overwhelms the frame in the final second — light through a red lantern, "
     "a wash of green from a sign, a lamp's amber — until the image is that colour and little "
     "else",
     "the opening frame is saturated in that SAME colour; it recedes as the camera moves, and "
     "the new place emerges with the colour surviving only in one motivated source"),
    ("Crowd swallow",
     "a flow of moving people — a press of umbrellas, a crowd crossing — closes over the subject "
     "until they are no longer findable in the frame",
     "the opening frame is that same flow of umbrellas and bodies filling the frame in the new "
     "place; it thins and the subject emerges out of it, facing the same screen direction"),
    ("Glass layering",
     "the camera moves behind glass so the frame carries TWO images at once — what is beyond the "
     "pane and the street reflected on it — with the reflection growing stronger to the end",
     "the opening frame carries that same doubled image in the new place; the reflected layer "
     "fades and the layer beyond the glass becomes the real scene"),
    ("Rain-curtain wipe",
     "a sheet of water crosses the frame in the last second — rain sluicing off an awning, a "
     "wave thrown up by a wheel, a shutter of downpour — and the image goes to broken water",
     "the opening frame is that same sheet of water still falling across the lens; it drops away "
     "and the new place is left clean behind it"),
    ("Reflection tilt",
     "the final seconds tilt DOWN off the subject into water on the ground until the world "
     "exists only as a rippled, half-legible reflection filling the frame — nothing but water, "
     "light and ripple at the end",
     "water on the ground fills the frame and the new place is readable only as a blurred "
     "reflection in it; the clip tilts UP off the water to reveal the place directly, "
     "continuing the previous scene's downward tilt as one unbroken move"),
)

def _stride(n: int, want: int = 3) -> int:
    """Bước nhảy để đi qua bảng `n` mục mà QUÉT HẾT rồi mới quay vòng — tức phải nguyên tố
    cùng nhau với `n`. Trả bước nhỏ nhất từ `want` trở lên thoả điều kiện.

    Tính chứ không chép cứng, vì chép cứng thì thêm một mục vào bảng là hỏng âm thầm: bảng 21
    mục với bước 3 chỉ ghé 7 mục rồi lặp lại từ đầu, nên scene 1 và scene 8 dùng chung một cú
    chuyển cảnh — đúng cái đơn điệu mà cả cơ chế này sinh ra để tránh, và không có gì báo lỗi."""
    for d in range(max(2, want), max(2, want) + n):
        if math.gcd(d, n) == 1:
            return d
    return 1


# Mẫu bọc quanh hình dáng + hai nửa chuyển cảnh đã bốc sẵn. Chỗ trống được `scene_plan()` điền;
# người dùng sửa được phần luật, còn nội dung hai bảng trên nằm trong code (xem docstring).
_SCENE_ARC = (
    "SCENE SHAPE — this is scene {i} of {n}, and each scene of this film is deliberately built "
    "on a DIFFERENT camera idea so the finished cut does not repeat one formula twelve times. "
    "The shape for THIS scene has already been chosen; use it and no other:\n"
    "  ▸ {shape_name}: {shape}.\n"
    "Apply it ON TOP of the continuity rules above, never against them — the shape decides the "
    "ARC of the scene (where it starts, how it develops, where it lands), while continuity still "
    "governs every individual cut: same screen direction, same side of the 180° line, the "
    "subject advancing through the space, no jump between unrelated parts of the location.\n"
    "\n{transitions}"
)

_SCENE_ARC_IN = (
    "SCENE ENTRY — this scene follows \"{prev}\", which ends on exactly this frame:\n"
    "{prev_tail}\n"
    "The FIRST shot of this scene must pick that frame up and complete the hand-off. The "
    "SUGGESTED device for this join is {name}:\n"
    "  ▸ {text}.\n"
    "JUDGE IT AGAINST THE FRAME QUOTED ABOVE before using it, because the device only works if "
    "the geometry allows it — where the subject actually is in that frame and which way they "
    "face, where the camera is and which way it was moving, whether the subject is even present "
    "or moving at all, and what the place physically contains. A hand-off that needs the subject "
    "to walk out of frame is wrong if they are standing still in close-up; one that needs open "
    "sky is wrong under an arcade; one that needs a look off-screen is wrong if nobody is on "
    "screen. If it does not fit, SAY SO in one short clause at the start of the first shot's "
    "`description` and use a device that does fit that frame — matching whatever the previous "
    "frame genuinely leaves you: its last movement, its screen direction, its dominant shape, "
    "its light, or an object it ends on.\n"
    "Whatever device you end up with, the hand-off goes in the `description` and `visual_prompt` "
    "— i.e. IN THE STILL IMAGE ITSELF, because that still is the clip's opening frame — and the "
    "`motion_prompt` moves out of it into the scene within the first two seconds. After that the "
    "shot plays as a normal frame of this scene and obeys the shape above."
)

_SCENE_ARC_OUT = (
    "SCENE EXIT — this scene is followed by \"{next}\"{next_head}. The LAST shot of this scene "
    "must set up the hand-off into it. The SUGGESTED device for this join is {name}:\n"
    "  ▸ {text}.\n"
    "Again, judge it against where your own last shot actually leaves the subject and the camera "
    "— its shot size, the subject's position and facing, whether they are moving, what is within "
    "reach in the frame. Do not bend the scene to fit the device: if the last shot lands "
    "somewhere that cannot support it, use a device that grows naturally out of that frame "
    "instead, and make sure it is one the NEXT scene can answer in its own opening frame.\n"
    "Whatever device you end up with, the hand-off goes in the `motion_prompt` ONLY, as the "
    "final two seconds of that clip — NOT in the `description`, because the description "
    "generates the clip's FIRST frame and the hand-off belongs at the end."
)

# Dynamic spec injected into every motion-generating prompt. The shot's START FRAME is an
# image-to-video reference that ALREADY locks the static look (shot size, angle, focal
# length, lighting, composition). So the `motion_prompt` must NOT redefine that look — it
# only describes what MOVES over the clip. Re-stating the static framing risks the model
# morphing away from the frame.
_MOTION = (
    "MOTION (image-to-video) — the start frame already fixes the shot size, camera angle, "
    "focal length, lighting and composition. The `motion_prompt` describes ONLY what changes "
    "over time inside that locked frame; do NOT restate or alter the framing/angle/lens:\n"
    "  • Camera movement: type (push-in/dolly, pull-out, pan L/R, tilt up/down, truck, crane "
    "up/down, orbit/arc, handheld, or a static lock-off) + direction + speed (slow & steady "
    "vs brisk & decisive). If the shot is meant to be still, say 'locked-off, no camera move'.\n"
    "  • Focus pull: any rack focus / focus shift from one subject to another during the clip.\n"
    "  • Light & atmosphere over time: light shifting, flicker (fire, neon), drifting "
    "smoke/fog/dust, falling particles, moving shadows.\n"
    "  • Subject motion & pacing: the concrete action and its timing within the clip "
    "(when it starts, how it builds), referencing the SAME entities.\n"
    "  • Continuity: stay within the established frame — the look at the first frame must "
    "match the reference image; only the motion evolves."
)

# Omni Flash reads TIMESTAMP CUES in the prompt: "[00:04] ..." means "from 4s until the next
# cue (or the end), do this". Veo has no such notion, so this block is only ever appended for
# Omni. Without it a 10s Omni clip gets one flat instruction and renders as a single monotonous
# camera move for the whole duration — paying 10 seconds' worth of credits for one beat.
_OMNI_TIMELINE_HEAD = (
    "TIMED BEATS (Omni Flash only) — this clip is {clip_s} seconds long and the model reads "
    "timestamp cues, so write the `motion_prompt` as a SEQUENCE of cues instead of one flat "
    "sentence:\n"
    "  • Format: `[mm:ss] <what happens from this moment until the next cue>`. Always open at "
    "`[00:00]`, then add cues across the clip; the last cue runs to the end.\n"
    "  • Use as MANY cues as the action genuinely warrants — {n_beats} or more for {clip_s}s. "
    "Denser is fine and often better, as long as every cue marks a REAL, distinct change that "
    "can physically happen in the time it is given. Never pad with cues that just restate the "
    "previous beat.\n"
    "  • Make consecutive beats DIFFERENT in kind, not just 'more of the same': e.g. a camera "
    "move, then a subject action, then a light/atmosphere change, then a focus shift or a beat "
    "of stillness. A single push-in held for the whole clip is exactly what to avoid.\n"
    "  • The beats must form ONE continuous take — no cuts, no teleporting; each follows on "
    "physically from the previous.\n"
    "  • Example shape (do not copy the content): `[00:00] locked-off on the puddle, rain "
    "dimpling the surface. [00:03] a slow push-in begins as ripples spread outward. [00:06] a "
    "cyclo rolls through frame behind, its lamp smearing across the water. [00:08] the ripples "
    "settle and the reflection resolves.`"
)


# ─── Prompt ngầm: bảng mặc định + ghi đè theo dự án ─────────
#
# Mọi khối ở đây được CHÈN NGẦM vào prompt mỗi lần chạy — trước đây chỉ nằm trong code nên
# không nhìn thấy và không sửa được. Giờ mỗi khoá `k` có một cột `project.tpl_<k>`:
#   trống  → dùng bản mặc định dưới đây
#   "-"    → TẮT hẳn khối đó (không chèn gì)
#   khác   → dùng nguyên văn của người dùng
# Xem/chỉnh trong ⚙ Thiết lập dự án → nhóm "Prompt ngầm"; mặc định trả về qua
# GET /api/studio/options → `prompt_defaults`.
PROMPT_DEFAULTS: dict[str, str] = {
    "single_frame": _SINGLE_FRAME,
    "single_frame_grid": _SINGLE_FRAME_GRID,
    "image_text": _IMAGE_TEXT,
    "video_text": _VIDEO_TEXT,
    # Bible 13 mục nếu đọc được file preset, không thì mẫu một-sheet cũ.
    "sheet_character": _character_bible() or _SHEET["character"],
    "sheet_character_one": _SHEET["character_one"],
    "sheet_prop": _SHEET["prop"],
    "sheet_location": _SHEET["location"],
    "sheet_location_one": _SHEET["location_one"],
    "cine": _CINE,
    "cine_continuous": _CINE_CONTINUOUS,
    "scene_arc": _SCENE_ARC,
    "scene_arc_in": _SCENE_ARC_IN,
    "scene_arc_out": _SCENE_ARC_OUT,
    "motion": _MOTION,
    "omni_timeline": _OMNI_TIMELINE_HEAD,
}

# Khối nào có chỗ trống {…} phải điền — dùng để cảnh báo trên UI nếu người dùng xoá mất.
PROMPT_PLACEHOLDERS: dict[str, list[str]] = {
    "image_text": ["lang"],
    "video_text": ["lang"],
    "omni_timeline": ["clip_s", "n_beats"],
}


def prompt_part(project: dict | None, key: str, **fmt) -> str:
    """Khối prompt ngầm `key` — bản ghi đè của dự án nếu có, không thì bản mặc định.

    `fmt` điền các chỗ trống {…} của mẫu. Người dùng sửa mẫu mà làm hỏng/xoá mất chỗ trống
    thì trả nguyên văn thay vì nổ KeyError giữa lúc render."""
    raw = ""
    if isinstance(project, dict):
        raw = (project.get(f"tpl_{key}") or "").strip()
    if raw == "-":
        return ""
    text = raw or PROMPT_DEFAULTS.get(key, "")
    if not fmt or not text:
        return text
    try:
        return text.format(**fmt)
    except (KeyError, IndexError, ValueError):
        return text


def default_tpl_row() -> dict[str, str]:
    """Giá trị `tpl_*` cho một dự án MỚI — chép nguyên văn bản mặc định vào DB.

    Cố tình chép chứ không để trống: người dùng phải SỬA được các khối này ngay trong ô thiết
    lập, mà ô trống thì chẳng có gì để sửa. Đánh đổi: dự án cũ giữ bản đã chép, sửa mặc định
    trong code về sau KHÔNG tự lan sang chúng — muốn lấy bản mới thì bấm "Đặt lại" ở từng ô."""
    return {f"tpl_{k}": v for k, v in PROMPT_DEFAULTS.items()}


async def seed_prompt_defaults() -> int:
    """Đổ bản mặc định vào các ô `tpl_*` còn TRỐNG của mọi dự án (chạy lúc khởi động).

    Dự án tạo trước khi có tính năng này — và mỗi khối ngầm thêm mới về sau — đều có ô NULL;
    không bù thì tab Thiết lập hiện ô rỗng, người dùng tưởng là không có gì. Chỉ đụng vào ô
    NULL/rỗng nên không bao giờ ghi đè bản người dùng đã sửa hay đã tắt bằng "-"."""
    cols = [f"tpl_{k}" for k in PROMPT_DEFAULTS]
    where = " OR ".join(f"({c} IS NULL OR {c}='')" for c in cols)
    rows = await db.query_all(f"SELECT id, {', '.join(cols)} FROM project WHERE {where}")
    for r in rows:
        fill = {c: PROMPT_DEFAULTS[c[4:]] for c in cols if not (r.get(c) or "").strip()}
        if fill:
            await db.update("project", r["id"], fill)
    return len(rows)


def shot_continuity(project: dict | None = None) -> bool:
    """Shot trong một scene là chuỗi LIÊN TỤC (True) hay các khung rời để minh hoạ (False).

    Mặc định False = lối kể chuyện: mỗi khung minh hoạ một câu lời đọc, và khối CINEMATOGRAPHY
    ép khung liền kề phải khác nhau cho có nhịp. Đem dựng video thì hỏng — mỗi clip một chỗ
    khác nhau trong cùng một cảnh, nối lại rời rạc. Bật True khi đích đến là VIDEO."""
    try:
        return int((project or {}).get("shot_continuity") or 0) == 1
    except (TypeError, ValueError):
        return False


def cine_spec(project: dict | None = None) -> str:
    """Khối CINEMATOGRAPHY chèn vào mọi prompt SINH SHOT (không phải prompt sinh ảnh).

    Hai bản: rời (kể chuyện) và liên tục (dựng video) — xem `shot_continuity`."""
    return prompt_part(project, "cine_continuous" if shot_continuity(project) else "cine")


def frame_change_rule(project: dict | None = None) -> str:
    """Luật LIÊN KHUNG, nhúng vào phần mô tả `description` của các prompt viết shot.

    Ba prompt (autofill storyboard, tách beat, đổi góc máy) trước đây chép cứng câu "khung sau
    PHẢI KHÁC khung trước" ngay trong phần hướng dẫn từng trường, ngoài khối CINEMATOGRAPHY.
    Bật `shot_continuity` mà không đổi luôn mấy câu này thì prompt tự mâu thuẫn: khối lớn bảo
    nối tiếp, câu nhỏ bảo phải khác — và câu nhỏ đứng ngay cạnh tên trường nên thường thắng."""
    if shot_continuity(project):
        return ("It must CONTINUE the previous frame instead of contrasting with it: hold the "
                "same screen direction and stay on the same side of the 180° line, carry the "
                "subject a few steps further through the SAME space, and move the shot size by "
                "AT MOST one notch (wide → full → medium → close, or the reverse — or hold the "
                "same size, when the scene's shape calls for that) with at least a 30° change "
                "of angle, so the frames cut together as one continuous action")
    return ("The shot size AND angle MUST DIFFER from the previous frame's (alternate wide / "
            "medium / close and change the angle/height) so consecutive frames cut together "
            "with rhythm instead of looking like the same shot repeated")


def scene_arc(project: dict | None, scene_idx: int, n_scenes: int,
              prev_heading: str | None = None, next_heading: str | None = None,
              prev_tail: str = "", next_head: str = "") -> str:
    """Khối HÌNH DÁNG SCENE + CHUYỂN CẢNH cho đúng một scene, bốc sẵn theo `scene_idx`.

    Chỉ có tác dụng khi bật `shot_continuity` — ở lối kể chuyện mỗi khung là một ảnh minh hoạ
    cho một câu lời đọc, ép khung cuối scene thành vũng nước là phá lời đọc.

    Vì sao bốc ở code chứ không nhờ AI đa dạng: mỗi scene là MỘT lượt gọi AI riêng, lượt này
    không thấy lượt kia, nên "hãy làm khác các scene khác" là một câu vô nghĩa với model. Bốc
    theo idx thì hai scene liền nhau chắc chắn khác nhau, và chạy lại cho ra đúng kết quả cũ
    (không phụ thuộc seed) — sửa một scene không làm lệch những scene còn lại.

    Nhưng mục bốc ra chỉ là ĐỀ XUẤT, không phải lệnh. Một cú chuyển có dùng được hay không phụ
    thuộc hình học của khung: nhân vật đang đứng ở đâu, quay mặt hướng nào, máy đang ở đâu và
    vừa di chuyển ra sao, nơi chốn có cái gì. "Đi khuất mép khung" vô nghĩa nếu nhân vật đang
    đứng yên trong cảnh cận; "cẩu vọt lên cao" vô nghĩa dưới mái hiên; "quay theo ánh nhìn" vô
    nghĩa khi trong khung không có ai. Code không biết mấy điều đó — chỉ model, khi đọc khung
    thật, mới biết. Nên `prev_tail` đưa NGUYÊN VĂN khung cuối của scene trước vào prompt và mẫu
    bảo model tự thẩm định rồi đổi sang cú chuyển hợp hơn nếu cần.

    `prev_tail` đọc được là nhờ revary chạy TUẦN TỰ theo thứ tự scene (job batch_size=1): tới
    lượt scene k+1 thì scene k đã viết lại xong, nên đó là khung MỚI chứ không phải khung cũ.

    Kiểu chuyển đánh số theo RANH GIỚI: mục `k` là ranh giới giữa scene k và k+1. Nên lối RA
    của scene k và lối VÀO của scene k+1 luôn đọc trúng cùng một mục — hai nửa của một cú cắt
    phải khớp nhau, nếu tính lệch thì scene trước nhoè xuống nước còn scene sau lại mở bằng
    vệt whip-pan."""
    if not shot_continuity(project):
        return ""
    shape_name, shape = _SCENE_SHAPES[scene_idx % len(_SCENE_SHAPES)]

    def _trans(k: int) -> tuple[str, str, str]:
        return _SCENE_TRANSITIONS[(k * _stride(len(_SCENE_TRANSITIONS))) % len(_SCENE_TRANSITIONS)]

    blocks = []
    if prev_heading:
        name, _out, _in = _trans(scene_idx - 1)
        blocks.append(prompt_part(
            project, "scene_arc_in", prev=prev_heading, name=name, text=_in,
            prev_tail=(prev_tail.strip() or "(that scene's last frame is not written yet — infer "
                       "a plausible ending frame for it from its heading and hand off from that)")))
    if next_heading:
        name, _out, _in = _trans(scene_idx)
        blocks.append(prompt_part(
            project, "scene_arc_out", next=next_heading, name=name, text=_out,
            next_head=(f", which opens on: {next_head.strip().rstrip('.')}"
                       if next_head.strip() else "")))
    return prompt_part(project, "scene_arc",
                       i=scene_idx + 1, n=n_scenes,
                       shape_name=shape_name, shape=shape,
                       transitions=join_blocks(*blocks))


def motion_spec(engine: str = "veo", clip_s: int = 8,
                project: dict | None = None) -> str:
    """Khối hướng dẫn viết `motion_prompt`, có thêm phần mốc thời gian khi engine là Omni.

    `n_beats` chỉ là SÀN gợi ý (≈1 mốc / 2s), không phải trần — Omni nhận bao nhiêu mốc cũng
    được miễn là hợp logic, nên prompt khuyến khích dày hơn nếu hành động xứng đáng."""
    motion = prompt_part(project, "motion")
    if engine != "omni":
        return motion
    timeline = prompt_part(project, "omni_timeline",
                           clip_s=clip_s, n_beats=max(3, round(clip_s / 2)))
    return "\n\n".join(p for p in (motion, timeline) if p)


def storyboard_autofill_prompt(scene_heading: str, scene_body: str,
                               entities: list[dict], style: str,
                               n_frames: int | None = None,
                               location: str | None = None,
                               engine: str = "veo", clip_s: int = 8,
                               project: dict | None = None, arc: str = "") -> str:
    roster = "\n".join(
        f"- {{{e['name']}}} ({e['type']}): {e.get('description') or ''}" for e in entities
    ) or "(none)"
    locations = [e["name"] for e in entities if e.get("type") == "location"]
    if location:
        loc_line = (
            f"This scene takes place at ONE fixed location: {{{location}}}. EVERY frame is at "
            f"this SAME place — begin each `description` with {{{location}}}, use ONLY "
            f"{{{location}}} and NO other location anywhere, and put {{{location}}} (and no "
            "other place) in ref_entity_names. Do NOT invent or switch to any other location."
        )
    elif locations:
        loc_line = (
            "The location entities available are: "
            + ", ".join("{" + n + "}" for n in locations)
            + ". Pick the single location this scene happens at and use ONLY it in every frame."
        )
    else:
        loc_line = (
            "No location entity exists yet — invent a consistent place name and wrap it in "
            "curly braces, reusing the SAME name for every frame of this scene."
        )
    count = f"about {n_frames} frames" if n_frames else "as many frames as the action needs (2–6)"
    return (
        "Break this scene into storyboard FRAMES (still shots). Every frame in this scene "
        "happens at ONE shared location.\n"
        f"{loc_line}\n\n"
        "For each frame return:\n"
        "- `title`: short label.\n"
        "- `description`: a vivid image-generator prompt that MUST begin by naming the "
        "location, then a SPECIFIC shot size + camera angle/height for THIS frame, then the "
        "action — e.g. \"At {Khu rừng}, low-angle medium close-up, {Mai} opens the wooden "
        "door...\". " + frame_change_rule(project) + ".\n"
        "- `visual_prompt`: the full camera setup + what is on screen for an image-to-video "
        "model — keep the SAME entity references.\n"
        "- `motion_prompt`: the camera move + the concrete action that happens during the "
        "clip, referencing the SAME entities.\n"
        "- `ref_entity_names`: every entity used in the frame (names WITHOUT braces), and it "
        "MUST include the scene's location.\n"
        f"\n{join_blocks(cine_spec(project), arc, motion_spec(engine, clip_s, project))}\n\n"
        "IMPORTANT: when a known entity (character/location/prop) appears in a prompt, wrap its "
        "name in curly braces exactly as listed (e.g. {Mai}) so it binds to its reference image "
        "— but name it ONCE per field and use a pronoun afterwards; see the naming rule above.\n"
        f"Visual style: {style}. Produce {count}.\n\n"
        f"AVAILABLE ENTITIES:\n{roster}\n\n"
        f"SCENE: {scene_heading}\n{scene_body}\n\n"
        "Return ONLY JSON array: [{\"title\":\"...\",\"description\":\"At {Location}, "
        "<angle>, ... {Entity} ...\",\"visual_prompt\":\"...\",\"motion_prompt\":\"...\","
        "\"ref_entity_names\":[\"Location\",\"Entity\"]}]"
    )


# A terminator (.!?…) ends a sentence ONLY when followed by whitespace or end-of-string
# (optionally after closing quotes/brackets). A '.' glued to the next char — a filename
# "ACC_REPORT...2047.zip", a decimal, a version, a glued abbreviation — is NOT a boundary,
# so the sentence is never cut mid-token. Newlines always break.
_SENT_RE = re.compile(r".*?(?:[.!?…]+[\"'’”\)\]]*(?=\s|$)|\n|$)", re.S)


def _sentences(text: str) -> list[str]:
    # Drop fragments with no readable word (a standalone "◆", a row of bullets) so decoration
    # never becomes its own contiguous part → its own beat → a wasted shot + 0.8s of noise.
    return [s.strip() for s in _SENT_RE.findall(text or "")
            if s.strip() and vntext.has_words(s)]


def partition_text(text: str, n: int) -> list[str]:
    """Split `text` into up to `n` contiguous, VERBATIM parts on sentence boundaries,
    balanced by length. Storytelling reads the user's ORIGINAL input — so every word is
    kept, in order: concatenating the parts back gives the whole source (only inter-
    sentence whitespace is normalized to single spaces). Never rewrites or drops content."""
    text = (text or "").strip()
    if not text:
        return []
    sents = _sentences(text)
    if not sents:
        return [text]
    n = max(1, min(n, len(sents)))
    if n == 1:
        return [" ".join(sents)]
    total = sum(len(s) for s in sents) or 1
    target = total / n
    parts: list[str] = []
    cur: list[str] = []
    acc = 0
    for i, s in enumerate(sents):
        cur.append(s)
        acc += len(s)
        opened = len(parts)
        sents_left = len(sents) - i - 1
        slots_left = n - opened - 1               # parts still to open after this one
        # must close now if we have to reserve ≥1 sentence for every remaining slot
        must_close = sents_left <= slots_left
        if opened < n - 1 and (acc >= target * (opened + 1) or must_close):
            parts.append(" ".join(cur))
            cur = []
    if cur:
        parts.append(" ".join(cur))
    return parts


_CLAUSE_RE = re.compile(r"(?<=[,;:—–])\s+")     # split points inside an over-long sentence


def _split_long_sentence(sent: str, max_words: int) -> list[str]:
    """Split ONE over-long sentence into ≤max_words pieces at clause boundaries (, ; : — –),
    hard word-splitting any clause that is still too long. Verbatim (only whitespace
    normalized), so the pieces concatenate back to the sentence."""
    out: list[str] = []
    for cl in _CLAUSE_RE.split(sent):
        words = cl.split()
        if len(words) <= max_words:
            out.append(cl)
        else:                                   # a single clause too long → hard word-split
            for k in range(0, len(words), max_words):
                out.append(" ".join(words[k:k + max_words]))
    return out or [sent]


# Vietnamese narration rate of the TTS voice, words per second. Measured over 95 built scenes
# (words ÷ scene WAV duration, incl. its pauses): ~3.4 for the continuous-read v2 takes. The old
# 2.5 under-counted by ~35%, which inflated every duration estimate → too many beats, and made a
# "10s" chunk actually run ~7s. Override with FLOWKIT_WORDS_PER_SEC.
WORDS_PER_SEC = float(os.environ.get("FLOWKIT_WORDS_PER_SEC", "3.4"))


def chunk_by_duration(text: str, max_secs: float = 10.0, min_secs: float = 8.0,
                      wps: float = WORDS_PER_SEC) -> list[str]:
    """Split `text` into contiguous, VERBATIM chunks that each AIM for the [min_secs, max_secs]
    band of narration — one shot (and so one generated image) per chunk.

    Sentences are the base unit; a sentence longer than the budget is further split at CLAUSE
    boundaries (, ; : —) then by word count. Pieces are then PACKED to FILL the band: a chunk is
    only closed once it has reached `min_secs` worth of words, so we stop emitting the swarm of
    3–5s shots that made the image count explode. When a piece would overflow `max_secs` while
    the chunk is still under the minimum, we keep whichever choice lands nearer the band's middle.
    A tiny trailing chunk is folded back into the previous one rather than left as a stray shot.

    Concatenating the chunks back gives the whole text (whitespace normalized) — never rewrites
    or drops content."""
    text = (text or "").strip()
    if not text:
        return []
    max_words = max(3, round(max_secs * wps))
    min_words = max(2, min(round(min_secs * wps), max_words))
    target_words = (min_words + max_words) // 2
    pieces: list[str] = []
    for s in _sentences(text):
        if len(s.split()) <= max_words:
            pieces.append(s)
        else:
            pieces.extend(_split_long_sentence(s, max_words))
    out: list[str] = []
    cur: list[str] = []
    cur_w = 0
    for p in pieces:
        w = len(p.split())
        if cur and cur_w + w > max_words:
            # Over the cap. Close only if the chunk already fills the band, or if closing lands
            # strictly nearer the target than overflowing would — otherwise keep packing (a
            # slightly long shot beats a stray 3s one, and ties favour packing).
            if cur_w >= min_words or abs(cur_w - target_words) < abs(cur_w + w - target_words):
                out.append(" ".join(cur))
                cur, cur_w = [], 0
        cur.append(p)
        cur_w += w
    if cur:
        # A trailing chunk under the minimum reads as a stray short shot. Fold it into the
        # previous one when that stays within a reasonable overshoot; else keep it standalone.
        prev_w = len(out[-1].split()) if out else 0
        if out and cur_w < min_words and prev_w + cur_w <= round(max_words * 1.25):
            out[-1] = f"{out[-1]} {' '.join(cur)}"
        else:
            out.append(" ".join(cur))
    return out or [text]


async def align_source_to_scenes(source: str, scenes: list[dict]) -> list[str]:
    """Assign the original SOURCE prose to scenes BY CONTENT (not by equal length). Each scene
    gets a contiguous, verbatim block of source sentences that matches its location heading /
    action, in order; together the slices cover the whole source with no gaps or overlaps.
    Returns one slice per scene (len == len(scenes)).

    Robust by construction: the AI only picks the sentence index where each scene ENDS, and we
    slice on those boundaries — so the text is never paraphrased and the union is always the
    complete source. Falls back to length-balanced partition_text if the AI reply is unusable."""
    sents = _sentences(source)
    n = len(scenes)
    total = len(sents)
    if n <= 0:
        return []
    if n == 1 or total <= 1:
        return [" ".join(sents)] + [""] * (n - 1)
    if total <= n:                                   # fewer sentences than scenes → one each
        return [sents[i] if i < total else "" for i in range(n)]

    numbered = "\n".join(f"[{i + 1}] {s}" for i, s in enumerate(sents))
    scene_lines = "\n".join(
        f"- Scene {i + 1}: {sc.get('heading') or ''} :: {((sc.get('action') or '')[:200])}"
        for i, sc in enumerate(scenes))
    prompt = (
        "You align an original SOURCE narration to a list of SCENES. The SOURCE below is split "
        "into NUMBERED sentences. Each scene covers a CONTIGUOUS block of sentences IN ORDER; "
        "together the scenes MUST cover EVERY sentence with no gaps or overlaps. Using each "
        "scene's location heading and action summary, keep every sentence with the scene whose "
        "LOCATION/EVENT it actually describes (a change of place starts a new scene's block).\n\n"
        f"Return ONLY a JSON array of {n} integers: the 1-based index of the LAST sentence of "
        f"each scene. Values MUST be strictly increasing and the final value MUST equal {total}."
        f"\n\nSCENES:\n{scene_lines}\n\nSOURCE SENTENCES:\n{numbered}"
    )
    def _ok(data):
        try:
            return len(data) == n and all(isinstance(int(x), int) for x in data)
        except Exception:  # noqa: BLE001
            return False

    try:
        raw = await run_json_valid(prompt, _ok, label="Căn nội dung→scene")
        ends = [int(x) for x in raw]
    except Exception as e:  # noqa: BLE001 — exhausted retries → safe length-based fallback
        logger.warning("source→scene align failed after retries (%s) — dùng chia đều", e)
        return partition_text(source, n)
    # sanitize: clamp into range, force strictly-increasing, ≥1 sentence per scene, last=total
    fixed: list[int] = []
    prev = 0
    for i, e in enumerate(ends):
        lo = prev + 1                                # ≥1 sentence after the previous scene
        hi = total - (n - 1 - i)                     # leave ≥1 sentence for each remaining scene
        e = max(lo, min(e, hi))
        fixed.append(e)
        prev = e
    fixed[-1] = total
    out, start = [], 0
    for e in fixed:
        out.append(" ".join(sents[start:e]))
        start = e
    return out


def scene_plan_prompt(voiceover: str, entities: list[dict], style: str,
                      location: str | None = None) -> str:
    """Read the WHOLE scene first and produce a short shot PLAN, so the shots that follow are
    coherent (a real scene) instead of a random jumble of solo shots. Identifies who is
    physically present + where (blocking) and a camera coverage strategy. Small JSON output."""
    roster = "\n".join(
        f"- {e['name']} ({e['type']}): {e.get('description') or ''}" for e in entities
    ) or "(none)"
    return (
        "You are a film director. Read this ENTIRE scene voiceover and return a SHORT plan so "
        "the storyboard shots stay coherent — same place, same people, consistent spatial "
        "relationships — instead of disconnected solo shots.\n"
        f"Location: {location or 'one consistent place (name it)'}. Visual style: {style}.\n"
        f"AVAILABLE ENTITIES:\n{roster}\n\nVOICEOVER:\n{voiceover}\n\n"
        "Return ONLY JSON:\n"
        "{\n"
        '  "present": ["names of entities PHYSICALLY in this scene"],\n'
        '  "blocking": "one sentence: where each person/object is and their spatial relation",\n'
        '  "coverage": "one sentence: how to shoot it — e.g. establishing wide, then '
        'over-the-shoulder between the two speakers, reaction close-ups, inserts of the screen"\n'
        "}"
    )


def scene_segment_prompt(voiceover: str, entities: list[dict], style: str,
                         location: str | None = None, target_beats: int | None = None,
                         plan: dict | None = None,
                         engine: str = "veo", clip_s: int = 8,
                         project: dict | None = None, arc: str = "") -> str:
    """Split an ALREADY-WRITTEN scene voiceover into visual BEATS. Each beat's `text` is a
    verbatim CONTIGUOUS slice of the voiceover (in order, concatenating back to the whole),
    so each beat's share of the audio time can be derived from its word count. Also pick the
    key phrases to flash on screen when the narration reaches them."""
    roster = "\n".join(
        f"- {{{e['name']}}} ({e['type']}): {e.get('description') or ''}" for e in entities
    ) or "(none)"
    locations = [e["name"] for e in entities if e.get("type") == "location"]
    if location:
        loc_line = (
            f"This scene is at ONE fixed location: {{{location}}}. EVERY beat is at this SAME "
            f"place — begin each `description` with {{{location}}}, use ONLY {{{location}}} and "
            f"NO other location, and put {{{location}}} (and no other place) in ref_entity_names."
        )
    elif locations:
        loc_line = (
            "Location entities available: " + ", ".join("{" + n + "}" for n in locations)
            + ". Every beat is at the ONE location of this scene; use ONLY that one."
        )
    else:
        loc_line = (
            "No location entity yet — invent ONE consistent place name in curly braces and "
            "reuse it for every beat."
        )
    count_line = (
        f"Aim for ABOUT {target_beats} beats — each on-screen image should last 8–10 seconds of "
        "narration. That is fresh enough to keep the viewer engaged, while each beat costs one "
        "generated image, so do NOT over-split. Split at natural sentence/clause boundaries; a "
        "beat is usually 2–3 sentences. Avoid beats shorter than ~8 seconds: merge a short "
        "thought into its neighbour rather than emitting a tiny beat."
        if target_beats else
        "Each beat should cover one on-screen moment worth 8–10 seconds of narration (usually "
        "2–3 sentences). Each beat costs one generated image, so avoid tiny beats — merge a "
        "short thought into its neighbour instead of over-splitting."
    )
    plan_line = ""
    if plan and (plan.get("blocking") or plan.get("coverage")):
        present = ", ".join(plan.get("present") or [])
        plan_line = (
            "SCENE PLAN — OBEY IT so the beats form ONE coherent scene, not disconnected solo "
            "shots:\n"
            + (f"- People present the WHOLE scene: {present}. Keep them consistent; do NOT drop "
               "a present person or invent someone not listed.\n" if present else "")
            + (f"- Blocking / space: {plan['blocking']}\n" if plan.get("blocking") else "")
            + (f"- Camera coverage: {plan['coverage']}\n" if plan.get("coverage") else "")
            + "Establish the space early, then VARY framing across beats (wide → medium → "
            "over-the-shoulder → reaction/insert) while respecting who is where. In a dialogue, "
            "alternate over-the-shoulder + reaction shots of BOTH speakers — never a random "
            "string of one-person shots.\n\n"
        )
    return (
        "Split this scene VOICEOVER into visual BEATS (one beat = one on-screen moment). "
        "Do NOT rewrite the narration — each beat's `text` MUST be a verbatim, contiguous "
        "slice of the voiceover, and the slices in order MUST concatenate back to the whole "
        "voiceover (no gaps, no overlaps).\n"
        f"{count_line}\n"
        f"{plan_line}"
        f"{loc_line}\n\n"
        "For each beat return:\n"
        "- `text`: the verbatim voiceover slice for this beat.\n"
        "- `beat_action`: the concrete action happening on screen.\n"
        "- `description`: image prompt beginning with the location then a SPECIFIC shot size + "
        "camera angle/height, then the action, e.g. \"At {Làng}, low-angle wide shot, {Tấm} "
        "scrubs the porch...\". " + frame_change_rule(project) + ".\n"
        "- `visual_prompt`: the full camera setup + what is on screen (same entity refs).\n"
        "- `motion_prompt`: camera move + action during the clip (same entity refs).\n"
        "- `ref_entity_names`: entity names WITHOUT braces, MUST include the location.\n"
        "- `key_phrases`: 1–3 SHORT punchy phrases taken VERBATIM from this beat's `text` "
        "(the words worth flashing on screen as captions); [] if none.\n\n"
        f"{join_blocks(cine_spec(project), arc, motion_spec(engine, clip_s, project))}\n\n"
        f"Wrap known entity names in curly braces. Visual style: {style}.\n\n"
        f"AVAILABLE ENTITIES:\n{roster}\n\nVOICEOVER:\n{voiceover}\n\n"
        "Return ONLY JSON array: [{\"text\":\"...\",\"beat_action\":\"...\","
        "\"description\":\"At {Loc}, <angle>, ...\",\"visual_prompt\":\"...\","
        "\"motion_prompt\":\"...\",\"ref_entity_names\":[\"Loc\"],\"key_phrases\":[\"...\"]}]"
    )


def beat_parts_prompt(beat_action: str, motion_prompt: str, n_parts: int,
                      clip_s: int = 8, engine: str = "veo",
                      project: dict | None = None) -> str:
    """A beat's video is longer than one clip (~clip_s s) → split into `n_parts` continuous
    sub-clips. Each sub-clip starts from the previous one's last frame (chained), so the
    motion must flow on. Returns a continuation motion prompt for each part."""
    return (
        f"This action lasts longer than one {clip_s}-second video clip, so it is rendered as "
        f"{n_parts} consecutive sub-clips that play back-to-back as ONE continuous shot. Each "
        "sub-clip begins on the LAST frame of the previous one, so the motion must continue "
        "smoothly without resetting or repeating.\n\n"
        f"FULL ACTION: {beat_action}\nFULL MOTION: {motion_prompt}\n\n"
        f"Write {n_parts} motion prompts, one per sub-clip in order, each describing only the "
        f"portion of the action in that ~{clip_s}s window (continuous, no repetition).\n\n"
        f"{motion_spec(engine, clip_s, project)}\n\n"
        "Return ONLY JSON: {\"parts\":[{\"part_idx\":0,\"motion_prompt\":\"...\"}, ...]}"
    )


def revary_shots_prompt(shots: list[dict], entities: list[dict], style: str,
                        location: str | None = None,
                        engine: str = "veo", clip_s: int = 8,
                        project: dict | None = None, arc: str = "") -> str:
    """Rewrite the CAMERA work of EXISTING shots without changing the story, order, count or
    per-shot action — only pick fresh, distinct angles so consecutive shots differ. Fast path
    to fix monotonous framing (and the location) without re-segmenting or re-running TTS."""
    roster = "\n".join(
        f"- {{{e['name']}}} ({e['type']}): {e.get('description') or ''}" for e in entities
    ) or "(none)"
    listing = "\n".join(
        f"{i}. {((s.get('beat_action') or s.get('narrator_text') or s.get('description') or '') or '').strip()[:300]}"
        for i, s in enumerate(shots))
    loc_line = (
        f"This scene is at ONE fixed location: {{{location}}}. EVERY shot's `description` MUST "
        f"begin with {{{location}}} and use ONLY this place — no other location anywhere.\n"
        if location else ""
    )
    return (
        f"An existing storyboard scene has {len(shots)} shots, in order, listed below by their "
        "action. Keep the story, the ORDER, the NUMBER of shots and each shot's action EXACTLY "
        "as is — change ONLY the camera.\n"
        f"{loc_line}\n"
        "For EACH shot (same index, same order) return a NEW `description` (image prompt: begin "
        "with the location, then a SPECIFIC shot size + camera angle/height, then the SAME "
        "action; " + frame_change_rule(project) + "), plus a matching `visual_prompt` and "
        "`motion_prompt`. "
        "Wrap each character/location/prop name in curly braces exactly as listed so it binds to "
        "its reference image (a character that acts in the shot MUST be wrapped and present) — "
        "but name it ONCE per field and use a pronoun afterwards; see the naming rule above.\n"
        f"\n{join_blocks(cine_spec(project), arc, motion_spec(engine, clip_s, project))}\n\n"
        f"Visual style: {style}.\n\nAVAILABLE ENTITIES:\n{roster}\n\nSHOTS (in order):\n{listing}\n\n"
        "Return ONLY a JSON array with EXACTLY one object per shot, in order: "
        "[{\"idx\":0,\"description\":\"At {Loc}, <shot size+angle>, <same action> {Entity}...\","
        "\"visual_prompt\":\"...\",\"motion_prompt\":\"...\"}]"
    )


def shot_prompts_prompt(description: str, style: str,
                        engine: str = "veo", clip_s: int = 8,
                        project: dict | None = None) -> str:
    return (
        "For this storyboard frame, write two prompts for an image-to-video model:\n"
        "- `visual_prompt`: the full camera setup + what is on screen.\n"
        "- `motion_prompt`: the camera move + the action that happens during the clip "
        "(concrete, e.g. 'the fox steps onto the ice, camera slowly pushes in').\n"
        f"\n{cine_spec(project)}\n\n{motion_spec(engine, clip_s, project)}\n\n"
        f"Visual style: {style}.\n\n"
        f"FRAME: {description}\n\n"
        "Return ONLY JSON: {\"visual_prompt\":\"...\",\"motion_prompt\":\"...\"}"
    )


def narrator_prompt(description: str, language: str = "Vietnamese") -> str:
    return (
        f"Write ONE short {language} narrator line (voiceover) for this shot — natural, "
        "spoken, 1–2 sentences, no stage directions.\n\n"
        f"SHOT: {description}\n\n"
        "Return ONLY JSON: {\"narrator_text\":\"...\"}"
    )


def seo_prompt(title: str, script: str, language: str = "Vietnamese") -> str:
    return (
        f"Create YouTube metadata in {language} for this video, plus a thumbnail image "
        "prompt (English).\n\n"
        f"WORKING TITLE: {title}\nSCRIPT:\n{script[:2000]}\n\n"
        "Return ONLY JSON: {\"title\":\"...\",\"description\":\"...\",\"tags\":[\"...\"],"
        "\"thumbnail_prompt\":\"...\"}"
    )


def edit_script_prompt(script: str, instruction: str, style: str,
                       language: str = "Vietnamese") -> str:
    return (
        "You are editing a FOUNTAIN screenplay. Apply the user's instruction and return "
        "the FULL updated screenplay (keep fountain format, scene headings 'INT./EXT.').\n"
        f"Keep the screenplay written in {language} (action lines, dialogue, narration), "
        "unless the instruction explicitly asks for another language.\n"
        f"Film style: {style}.\n\n"
        f"CURRENT SCREENPLAY:\n{script}\n\n"
        f"INSTRUCTION:\n{instruction}\n\n"
        "Return ONLY JSON: {\"script\": \"<updated fountain screenplay>\"}"
    )
