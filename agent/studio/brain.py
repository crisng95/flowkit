"""The "brain" — wraps the AI-agent CLI (claude / agy) for Studio tasks.

Builds a prompt that demands strict JSON, runs it through /api/agent/run's underlying
handler, then extracts + parses the JSON (tolerant of code fences / surrounding prose).
Retries once on parse failure. See video-app.md §6.
"""
import asyncio
import json
import logging
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
    "\n\nNEVER name a real artist, animation studio, film director or franchise as a style "
    "reference (no \"Ghibli\", \"Makoto Shinkai\", \"Pixar\", \"Disney\", \"Marvel\", "
    "\"in the style of <person>\", etc.). Describe the look with generic visual attributes "
    "instead — line quality, shading, palette, lighting, lens, mood."
)

# Chỉ cắt cụm QUY PHONG CÁCH ("X style", "in the style of X", "X-esque"), không cắt mọi lần
# nhắc tên: một truyện lấy bối cảnh công viên Disneyland vẫn được phép nhắc tên nơi đó.
_NAMED = (r"ghibli|studio ghibli|makoto shinkai|shinkai|miyazaki|hayao miyazaki|pixar|disney|"
          r"dreamworks|marvel|greg rutkowski|artgerm|wlop|moebius|akira toriyama|kyoto animation")
_NAMED_STYLE_RE = re.compile(
    rf"(?:\b(?:in|with)\s+(?:the\s+)?(?:style|aesthetic|look)\s+of\s+)?\b(?:{_NAMED})\b"
    rf"(?:[-\s]*(?:style|styled|aesthetic|look|inspired|esque))?",
    re.I)


def strip_named_styles(text: str) -> str:
    """Bỏ mọi cụm quy phong cách về tên riêng khỏi một đoạn text do AI sinh."""
    if not text or not _NAMED_STYLE_RE.search(text):
        return text
    out = _NAMED_STYLE_RE.sub("", text)
    # Dọn dấu câu mồ côi do chỗ cắt để lại — không dọn thì prompt đầy ", ." và " ,".
    out = re.sub(r"\s+([,.;:])", r"\1", out)       # "Chibi , a" → "Chibi, a"
    out = re.sub(r",\s*([.;:])", r"\1", out)       # "background, ." → "background."
    out = re.sub(r"(,\s*){2,}", ", ", out)         # ", , ," → ", "
    out = re.sub(r"(^|[.;:])\s*,\s*", r"\1 ", out)  # câu mở đầu bằng dấu phẩy
    out = re.sub(r"\s{2,}", " ", out)
    return out.strip(" ,;")


def _scrub(obj):
    """Áp strip_named_styles lên MỌI chuỗi trong cây JSON model trả về."""
    if isinstance(obj, str):
        return strip_named_styles(obj)
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items()}
    return obj


async def run_json(prompt: str, *, timeout: float = _AGENT_TIMEOUT, retries: int = 2):
    """Run the agent and return parsed JSON. Raises HTTPException(502) on failure.

    Mọi text sinh ra đều đi qua đây, nên đây cũng là chỗ DUY NHẤT lọc tên hoạ sĩ/hãng phim —
    khỏi phải nhớ thêm luật ở từng hàm dựng prompt."""
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
            return _scrub(_extract_json(res.get("stdout", "")))
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
_SINGLE_FRAME = (
    "Render ONE single unified cinematic frame from a SINGLE camera angle — one continuous "
    "photographic moment, not a composite. The attached reference images (character turnaround "
    "& expression sheets, prop multi-angle sheets, a location establishing shot) are there ONLY "
    "to keep identity, costume, architecture, materials, colour and lighting consistent. Do NOT "
    "reproduce any reference-sheet layout: no grid, no 2x2, no multi-panel or split screen, no "
    "collage, no turnaround row, no side-by-side angles, no plain white reference backdrop. "
    "Each named character must match its OWN reference image in IDENTITY ONLY — face, hair, "
    "skin, build, age and costume — never swap, blend or mix up faces, hair or costumes between "
    "characters, and do NOT add any extra people who are not named in this shot. The reference "
    "does NOT dictate POSE: ignore its A-pose/stance, its expression, its gaze direction, its "
    "body orientation, its framing, and — when a reference happens to show more than one person "
    "— the way those people are arranged relative to each other. Pose, angle and spacing must be "
    "invented FRESH for THIS shot's action and camera setup, and must differ from other shots; "
    "characters interact with the scene and each other as the action demands. Never paste a "
    "character in as a rigid cut-out standing the way the reference sheet shows. Compose THIS "
    "shot at its own specified shot size and camera angle. Render NO text, labels, captions, "
    "annotations, callouts or watermarks, and do not reproduce any text/labels that appear in "
    "the references"
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


def compose_prompt(project: dict, body: str, *, include_culture: bool = True,
                   single_frame: bool = False,
                   header: str | None = None, footer: str | None = None,
                   media: str = "image") -> str:
    """Assemble the final image/video prompt for a project.

    Order: [prompt_header] → style (always first of the visual terms) + culture_hint →
    body → [single-frame guard] → [prompt_footer]. `style` leads so the model anchors on it;
    the culture hint (e.g. "Vietnamese folk tale, traditional Vietnamese architecture") keeps
    imagery faithful to the story's origin instead of defaulting to the style's home culture.

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
    lead = ", ".join(p for p in (style, culture) if p)
    guard = single_frame_guard(project) if single_frame else ""
    parts = [header, lead, (body or "").strip(), guard, footer,
             _text_lang_clause(project, media)]
    return ". ".join(p for p in parts if p)


def single_frame_guard(project: dict | None) -> str:
    """Guard khung đơn cho ảnh frame + phần phụ về lưới bối cảnh (chỉ khi dùng lưới 4 khung)."""
    parts = [prompt_part(project, "single_frame")]
    if location_frames(project) == 4:
        parts.append(prompt_part(project, "single_frame_grid"))
    return ". ".join(p for p in parts if p)


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
    "prop": ("object design sheet, multiple angles (front, 3/4, side, top), single isolated "
             "object on plain solid white background, no background scene, no shadow, "
             "studio product reference. Do NOT draw any text, titles, captions, view labels or "
             "watermarks on the sheet — clean art only"),
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
    Trailing dots are trimmed so the rule doesn't get glued on after ".." either.

    Luật theo từng loại (sheet nhân vật / đạo cụ / bối cảnh) là PROMPT NGẦM — chỉnh được
    trong ⚙ Thiết lập dự án. Bối cảnh có hai mẫu: lưới 4 khung hoặc một ảnh.
    """
    base = ((description or "").strip() or (name or "").strip()).rstrip(" .")
    key = entity_type
    if entity_type == "location" and location_frames(project) == 1:
        key = "location_one"
    rule = (prompt_part(project, f"sheet_{key}") if f"sheet_{key}" in PROMPT_DEFAULTS
            else "clean reference image")
    if not rule:
        return base
    return f"{base}. {rule}" if base else rule


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
    "  • Mood / color palette and atmosphere: time of day, weather, haze/fog/dust, "
    "volumetric light, particles — whatever sells the scene's emotion."
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
    "sheet_prop": _SHEET["prop"],
    "sheet_location": _SHEET["location"],
    "sheet_location_one": _SHEET["location_one"],
    "cine": _CINE,
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


def cine_spec(project: dict | None = None) -> str:
    """Khối CINEMATOGRAPHY chèn vào mọi prompt SINH SHOT (không phải prompt sinh ảnh)."""
    return prompt_part(project, "cine")


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
                               project: dict | None = None) -> str:
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
        "door...\". The shot size AND angle MUST DIFFER from the previous frame's (alternate "
        "wide / medium / close and change the angle/height) so consecutive frames cut together "
        "with rhythm instead of looking like the same shot repeated.\n"
        "- `visual_prompt`: the full camera setup + what is on screen for an image-to-video "
        "model — keep the SAME entity references.\n"
        "- `motion_prompt`: the camera move + the concrete action that happens during the "
        "clip, referencing the SAME entities.\n"
        "- `ref_entity_names`: every entity used in the frame (names WITHOUT braces), and it "
        "MUST include the scene's location.\n"
        f"\n{cine_spec(project)}\n\n{motion_spec(engine, clip_s, project)}\n\n"
        "IMPORTANT: whenever a known entity (character/location/prop) appears in ANY prompt, "
        "wrap its name in curly braces exactly as listed (e.g. {Mai}) so it binds to its "
        "reference image.\n"
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
                         project: dict | None = None) -> str:
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
        "camera angle/height (which MUST DIFFER from the previous beat's — alternate "
        "wide/medium/close and change the angle so beats don't look like one repeated shot), "
        "then the action, e.g. \"At {Làng}, low-angle wide shot, {Tấm} scrubs the porch...\".\n"
        "- `visual_prompt`: the full camera setup + what is on screen (same entity refs).\n"
        "- `motion_prompt`: camera move + action during the clip (same entity refs).\n"
        "- `ref_entity_names`: entity names WITHOUT braces, MUST include the location.\n"
        "- `key_phrases`: 1–3 SHORT punchy phrases taken VERBATIM from this beat's `text` "
        "(the words worth flashing on screen as captions); [] if none.\n\n"
        f"{cine_spec(project)}\n\n{motion_spec(engine, clip_s, project)}\n\n"
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
                        project: dict | None = None) -> str:
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
        "as is — change ONLY the camera so consecutive shots no longer share the same framing.\n"
        f"{loc_line}\n"
        "For EACH shot (same index, same order) return a NEW `description` (image prompt: begin "
        "with the location, then a SPECIFIC shot size + camera angle/height that DIFFERS from the "
        "previous shot, then the SAME action), plus a matching `visual_prompt` and `motion_prompt`. "
        "Wrap EVERY character/location/prop name in curly braces exactly as listed so it binds to "
        "its reference image (a character that acts in the shot MUST be wrapped and present).\n"
        f"\n{cine_spec(project)}\n\n{motion_spec(engine, clip_s, project)}\n\n"
        f"Visual style: {style}.\n\nAVAILABLE ENTITIES:\n{roster}\n\nSHOTS (in order):\n{listing}\n\n"
        "Return ONLY a JSON array with EXACTLY one object per shot, in order: "
        "[{\"idx\":0,\"description\":\"At {Loc}, <distinct shot size+angle>, <same action> {Entity}...\","
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
