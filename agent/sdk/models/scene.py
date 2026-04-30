"""SDK Scene domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from agent.sdk.models.base import DomainModel
from agent.sdk.models.media import MediaAsset, OrientationSlot, GenerationResult


def _slot_from_row(row: dict[str, Any], prefix: str) -> OrientationSlot:
    """Build an OrientationSlot from a flat DB row using *prefix* (vertical/horizontal)."""
    return OrientationSlot(
        image=MediaAsset(
            media_id=row.get(f"{prefix}_image_media_id"),
            url=row.get(f"{prefix}_image_url"),
            status=row.get(f"{prefix}_image_status", "PENDING"),
        ),
        video=MediaAsset(
            media_id=row.get(f"{prefix}_video_media_id"),
            url=row.get(f"{prefix}_video_url"),
            status=row.get(f"{prefix}_video_status", "PENDING"),
        ),
        upscale=MediaAsset(
            media_id=row.get(f"{prefix}_upscale_media_id"),
            url=row.get(f"{prefix}_upscale_url"),
            status=row.get(f"{prefix}_upscale_status", "PENDING"),
        ),
        end_scene_media_id=row.get(f"{prefix}_end_scene_media_id"),
    )


@dataclass
class Scene(DomainModel):
    """A single scene inside a video."""

    _table: str = field(default="scene", init=False, repr=False, compare=False)

    video_id: str = ""
    display_order: int = 0
    prompt: Optional[str] = None
    image_prompt: Optional[str] = None
    video_prompt: Optional[str] = None
    transition_prompt: Optional[str] = None
    narrator_text: Optional[str] = None
    character_names: Optional[list[str]] = field(default=None)
    parent_scene_id: Optional[str] = None
    chain_type: str = "ROOT"
    source: Optional[str] = "root"

    vertical: OrientationSlot = field(default_factory=OrientationSlot)
    horizontal: OrientationSlot = field(default_factory=OrientationSlot)

    trim_start: Optional[float] = None
    trim_end: Optional[float] = None
    duration: Optional[float] = None

    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # ------------------------------------------------------------------
    # Construction from flat DB row
    # ------------------------------------------------------------------

    @classmethod
    def from_row(cls, row: dict[str, Any], repo: Any = None) -> Scene:
        """Create a Scene from a flat DB/API row, inflating OrientationSlots."""
        import json as _json

        names_raw = row.get("character_names")
        if isinstance(names_raw, str):
            try:
                names_raw = _json.loads(names_raw)
            except (ValueError, TypeError):
                names_raw = None

        return cls(
            id=row.get("id", ""),
            video_id=row.get("video_id", ""),
            display_order=row.get("display_order", 0),
            prompt=row.get("prompt"),
            image_prompt=row.get("image_prompt"),
            video_prompt=row.get("video_prompt"),
            transition_prompt=row.get("transition_prompt"),
            narrator_text=row.get("narrator_text"),
            character_names=names_raw,
            parent_scene_id=row.get("parent_scene_id"),
            chain_type=row.get("chain_type", "ROOT"),
            source=row.get("source", "root"),
            vertical=_slot_from_row(row, "vertical"),
            horizontal=_slot_from_row(row, "horizontal"),
            trim_start=row.get("trim_start"),
            trim_end=row.get("trim_end"),
            duration=row.get("duration"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            _repo=repo,
        )

    def to_operation_dict(self, project_id: str) -> dict:
        """Convert to the flat dict that OperationService direct methods expect."""
        import json as _json
        d = {
            "id": self.id,
            "video_id": self.video_id,
            "display_order": self.display_order,
            "prompt": self.prompt,
            "image_prompt": self.image_prompt,
            "video_prompt": self.video_prompt,
            "transition_prompt": self.transition_prompt,
            "character_names": _json.dumps(self.character_names) if isinstance(self.character_names, list) else self.character_names,
            "parent_scene_id": self.parent_scene_id,
            "chain_type": self.chain_type,
            "source": self.source,
            "_project_id": project_id,
        }
        # Flatten OrientationSlot fields
        for prefix, slot in [("vertical", self.vertical), ("horizontal", self.horizontal)]:
            d[f"{prefix}_image_media_id"] = slot.image.media_id
            d[f"{prefix}_image_url"] = slot.image.url
            d[f"{prefix}_image_status"] = slot.image.status
            d[f"{prefix}_video_media_id"] = slot.video.media_id
            d[f"{prefix}_video_url"] = slot.video.url
            d[f"{prefix}_video_status"] = slot.video.status
            d[f"{prefix}_upscale_media_id"] = slot.upscale.media_id
            d[f"{prefix}_upscale_url"] = slot.upscale.url
            d[f"{prefix}_upscale_status"] = slot.upscale.status
            d[f"{prefix}_end_scene_media_id"] = slot.end_scene_media_id
        return d

    # ------------------------------------------------------------------
    # Generation helpers
    # ------------------------------------------------------------------

    async def generate_image(
        self,
        *,
        orientation: str = "VERTICAL",
        project_id: str,
        video_id: Optional[str] = None,
    ) -> str:
        """Submit a GENERATE_IMAGE request. Returns the request id."""
        from agent.sdk.services.operations import get_operations

        ops = get_operations()
        return await ops.queue_scene_image(
            scene_id=self.id,
            project_id=project_id,
            video_id=video_id or self.video_id,
            orientation=orientation,
        )

    async def edit_image(
        self,
        edit_prompt: str,
        *,
        orientation: str = "VERTICAL",
        project_id: str,
        video_id: Optional[str] = None,
        source_media_id: Optional[str] = None,
    ) -> str:
        """Submit an EDIT_IMAGE request for this scene. Returns the request id."""
        from agent.sdk.services.operations import get_operations

        slot = self.vertical if orientation == "VERTICAL" else self.horizontal
        ops = get_operations()
        return await ops.queue_edit_scene_image(
            scene_id=self.id,
            project_id=project_id,
            video_id=video_id or self.video_id,
            orientation=orientation,
            edit_prompt=edit_prompt,
            source_media_id=source_media_id or slot.image.media_id,
        )

    async def generate_video(
        self,
        *,
        orientation: str = "VERTICAL",
        project_id: str,
        video_id: Optional[str] = None,
    ) -> str:
        """Submit a GENERATE_VIDEO request. Returns the request id."""
        from agent.sdk.services.operations import get_operations

        ops = get_operations()
        return await ops.queue_scene_video(
            scene_id=self.id,
            project_id=project_id,
            video_id=video_id or self.video_id,
            orientation=orientation,
        )

    async def upscale_video(
        self,
        *,
        orientation: str = "VERTICAL",
        project_id: str,
        video_id: Optional[str] = None,
    ) -> str:
        """Submit a local upscale request. Returns the request id."""
        from agent.sdk.services.operations import get_operations

        ops = get_operations()
        return await ops.queue_upscale_video(
            scene_id=self.id,
            project_id=project_id,
            video_id=video_id or self.video_id,
            orientation=orientation,
        )

    # ------------------------------------------------------------------
    # Direct execution (calls FlowClient directly, returns result)
    # ------------------------------------------------------------------

    async def execute_generate_image(
        self,
        *,
        orientation: str = "VERTICAL",
        project_id: str,
    ) -> GenerationResult:
        """Generate scene image directly (blocking). Returns GenerationResult."""
        from agent.sdk.services.operations import get_operations
        from agent.sdk.services.result_handler import parse_result, apply_scene_result

        ops = get_operations()
        raw = await ops.generate_scene_image(self.to_operation_dict(project_id), orientation)
        result = parse_result(raw, "GENERATE_IMAGE")
        if result.success:
            await apply_scene_result(self.id, "GENERATE_IMAGE", orientation, result)
            slot = self.vertical if orientation == "VERTICAL" else self.horizontal
            slot.image.media_id = result.media_id
            slot.image.url = result.url
            slot.image.status = "COMPLETED"
            slot.video = MediaAsset()
            slot.upscale = MediaAsset()
        return result

    async def execute_edit_image(
        self,
        edit_prompt: str,
        *,
        orientation: str = "VERTICAL",
        project_id: str,
        source_media_id: Optional[str] = None,
    ) -> GenerationResult:
        """Edit scene image directly (blocking). Returns GenerationResult."""
        from agent.sdk.services.operations import get_operations
        from agent.sdk.services.result_handler import parse_result, apply_scene_result

        ops = get_operations()
        scene_dict = self.to_operation_dict(project_id)
        slot = self.vertical if orientation == "VERTICAL" else self.horizontal
        src = source_media_id or slot.image.media_id
        raw = await ops.edit_scene_image(scene_dict, orientation, source_media_id=src)
        result = parse_result(raw, "EDIT_IMAGE")
        if result.success:
            await apply_scene_result(self.id, "EDIT_IMAGE", orientation, result)
            slot.image.media_id = result.media_id
            slot.image.url = result.url
            slot.image.status = "COMPLETED"
            slot.video = MediaAsset()
            slot.upscale = MediaAsset()
        return result

    async def execute_generate_video(
        self,
        *,
        orientation: str = "VERTICAL",
        project_id: str,
    ) -> GenerationResult:
        """Generate video from scene image directly (blocking, polls). Returns GenerationResult."""
        from agent.sdk.services.operations import get_operations
        from agent.sdk.services.result_handler import parse_result, apply_scene_result

        ops = get_operations()
        raw = await ops.generate_scene_video(self.to_operation_dict(project_id), orientation)
        result = parse_result(raw, "GENERATE_VIDEO")
        if result.success:
            await apply_scene_result(self.id, "GENERATE_VIDEO", orientation, result)
            slot = self.vertical if orientation == "VERTICAL" else self.horizontal
            slot.video.media_id = result.media_id
            slot.video.url = result.url
            slot.video.status = "COMPLETED"
            slot.upscale = MediaAsset()
        return result

    async def execute_generate_video_refs(
        self,
        *,
        orientation: str = "VERTICAL",
        project_id: str,
    ) -> GenerationResult:
        """Generate video from references directly (blocking, polls). Returns GenerationResult."""
        from agent.sdk.services.operations import get_operations
        from agent.sdk.services.result_handler import parse_result, apply_scene_result

        ops = get_operations()
        raw = await ops.generate_scene_video_refs(self.to_operation_dict(project_id), orientation)
        result = parse_result(raw, "GENERATE_VIDEO_REFS")
        if result.success:
            await apply_scene_result(self.id, "GENERATE_VIDEO_REFS", orientation, result)
            slot = self.vertical if orientation == "VERTICAL" else self.horizontal
            slot.video.media_id = result.media_id
            slot.video.url = result.url
            slot.video.status = "COMPLETED"
            slot.upscale = MediaAsset()
        return result

    async def execute_upscale_video(
        self,
        *,
        orientation: str = "VERTICAL",
        project_id: str,
    ) -> GenerationResult:
        """Upscale scene video directly (blocking, polls). Returns GenerationResult."""
        from agent.sdk.services.operations import get_operations
        from agent.sdk.services.result_handler import parse_result, apply_scene_result

        ops = get_operations()
        raw = await ops.upscale_scene_video(self.to_operation_dict(project_id), orientation)
        result = parse_result(raw, "UPSCALE_VIDEO")
        if result.success:
            await apply_scene_result(self.id, "UPSCALE_VIDEO", orientation, result)
            slot = self.vertical if orientation == "VERTICAL" else self.horizontal
            slot.upscale.media_id = result.media_id
            slot.upscale.url = result.url
            slot.upscale.status = "COMPLETED"
        return result
