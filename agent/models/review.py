"""Pydantic models for video review results."""
from pydantic import BaseModel
from typing import Optional


class SegmentScore(BaseModel):
    time_range: str
    score: float


class VideoError(BaseModel):
    severity: str  # CRITICAL / HIGH / MINOR
    time_range: str
    description: str

    def format(self) -> str:
        return f"[{self.severity}] {self.time_range}: {self.description}"


class DimensionScores(BaseModel):
    character_consistency: float
    prompt_adherence: float
    motion_quality: float
    visual_fidelity: float
    temporal_coherence: float
    composition: float


class SceneReview(BaseModel):
    scene_id: str
    overall_score: float
    verdict: str  # excellent / good / acceptable / poor / unusable
    dimensions: DimensionScores
    errors: list[VideoError]
    usable_segments: list[SegmentScore]
    fix_guide: str
    frames_analyzed: int
    fps_used: float
    has_critical_errors: bool = False


class VideoReview(BaseModel):
    video_id: str
    project_id: str
    mode: str  # light / deep
    orientation: str
    overall_score: float
    verdict: str
    scene_reviews: list[SceneReview]
    scenes_reviewed: int
    scenes_skipped: int  # no video yet
