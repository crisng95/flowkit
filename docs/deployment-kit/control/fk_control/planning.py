"""Pure planning helpers for project/chapter/lane orchestration."""

from dataclasses import dataclass
from math import floor
import re

from .contracts import build_job_envelope


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return value or "untitled"


def split_duration(total_seconds: int, chapter_count: int) -> list[int]:
    base = floor(total_seconds / chapter_count)
    remainder = total_seconds % chapter_count
    return [base + (1 if i < remainder else 0) for i in range(chapter_count)]


def build_chapter_rows(project_slug: str, total_seconds: int, chapter_count: int) -> list[dict]:
    durations = split_duration(total_seconds, chapter_count)
    return [
        {
            "chapter_index": i + 1,
            "chapter_slug": f"{project_slug}_chapter_{i+1:02d}",
            "title": f"{project_slug.replace('_', ' ').title()} - Chapter {i+1:02d}",
            "target_duration_seconds": durations[i],
            "target_scene_count": max(1, round(durations[i] / 8)),
        }
        for i in range(chapter_count)
    ]


@dataclass(frozen=True)
class LaneScore:
    lane_id: str
    credits_last_seen: int
    token_age_seconds: int | None


def choose_best_lane(lanes: list[LaneScore]) -> str | None:
    if not lanes:
        return None
    ranked = sorted(
        lanes,
        key=lambda lane: (
            -(lane.credits_last_seen or 0),
            lane.token_age_seconds if lane.token_age_seconds is not None else 10**9,
            lane.lane_id,
        ),
    )
    return ranked[0].lane_id


def _chapter_story_seed(chapter_context: dict) -> str:
    return (
        chapter_context.get("synopsis")
        or chapter_context.get("source_brief")
        or chapter_context.get("chapter_title")
        or chapter_context.get("source_title")
        or "Untitled chapter"
    )


def _chapter_anchor_name(chapter_context: dict) -> str:
    title = chapter_context.get("chapter_title") or "Chapter"
    return f"{title} Anchor"


def _build_scene_payloads(chapter_context: dict) -> list[dict]:
    scene_count = max(1, int(chapter_context.get("target_scene_count") or 1))
    chapter_title = chapter_context.get("chapter_title") or "Untitled chapter"
    story_seed = _chapter_story_seed(chapter_context)
    anchor_name = _chapter_anchor_name(chapter_context)
    scenes = []
    for index in range(scene_count):
        beat = index + 1
        scenes.append(
            {
                "display_order": index,
                "prompt": f"{chapter_title}. Beat {beat:02d}/{scene_count}. {story_seed}",
                "video_prompt": f"Cinematic motion for {chapter_title}. Beat {beat:02d}/{scene_count}. {story_seed}",
                "character_names": [anchor_name],
                "chain_type": "ROOT" if index == 0 else "CONTINUATION",
            }
        )
    return scenes


def build_chapter_job_plan(
    project_id: str,
    chapter_id: str,
    lane_id: str,
    trace_id: str,
    chapter_context: dict | None = None,
) -> list[dict[str, str]]:
    chapter_context = chapter_context or {}
    chapter_title = chapter_context.get("chapter_title") or f"Chapter {chapter_id}"
    source_title = chapter_context.get("source_title") or f"Project {project_id}"
    story_seed = _chapter_story_seed(
        {
            **chapter_context,
            "chapter_title": chapter_title,
            "source_title": source_title,
        }
    )
    material_id = chapter_context.get("material_id") or "realistic"
    anchor_name = _chapter_anchor_name({"chapter_title": chapter_title})
    specs = [
        (
            "CREATE_PROJECT",
            100,
            3,
            {
                "name": chapter_title,
                "description": f"{source_title} / {chapter_title}",
                "story": story_seed,
                "material": material_id,
                "tool_name": "PINHOLE",
                "allow_music": False,
                "allow_voice": False,
            },
        ),
        (
            "CREATE_ENTITIES",
            95,
            2,
            {
                "entities": [
                    {
                        "name": anchor_name,
                        "entity_type": "visual_asset",
                        "description": story_seed,
                        "image_prompt": f"Reference visual for {chapter_title}. {story_seed}",
                    }
                ]
            },
        ),
        (
            "CREATE_VIDEO",
            90,
            2,
            {
                "title": chapter_title,
                "description": story_seed,
                "orientation": "VERTICAL",
            },
        ),
        (
            "CREATE_SCENES",
            85,
            2,
            {
                "scenes": _build_scene_payloads(
                    {
                        **chapter_context,
                        "chapter_title": chapter_title,
                        "source_title": source_title,
                        "target_scene_count": chapter_context.get("target_scene_count") or 1,
                    }
                )
            },
        ),
        ("GEN_REFS", 80, 2, {}),
        ("GEN_IMAGES", 75, 3, {"orientation": "VERTICAL"}),
        ("GEN_VIDEOS", 70, 2, {"orientation": "VERTICAL"}),
        ("CONCAT_CHAPTER", 50, 2, {"orientation": "VERTICAL"}),
        ("UPLOAD_ARTIFACTS", 40, 3, {}),
    ]
    return [
        build_job_envelope(
            job_type=job_type,
            project_id=project_id,
            chapter_id=chapter_id,
            lane_id=lane_id,
            payload=payload,
            priority=priority,
            max_attempts=max_attempts,
            trace_id=trace_id,
            idempotency_key=f"chapter:{chapter_id}:{job_type.lower()}:v1",
        )
        for job_type, priority, max_attempts, payload in specs
    ]
