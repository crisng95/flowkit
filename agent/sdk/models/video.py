"""SDK Video domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from agent.sdk.models.base import DomainModel

if TYPE_CHECKING:
    from agent.sdk.models.scene import Scene


@dataclass
class Video(DomainModel):
    """A video (episode) inside a project."""

    _table: str = field(default="video", init=False, repr=False, compare=False)

    project_id: str = ""
    title: str = ""
    description: Optional[str] = None
    display_order: int = 0
    status: str = "DRAFT"
    orientation: Optional[str] = None
    vertical_url: Optional[str] = None
    horizontal_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    resolution: Optional[str] = None
    youtube_id: Optional[str] = None
    privacy: str = "unlisted"
    tags: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # ------------------------------------------------------------------
    # Scene management
    # ------------------------------------------------------------------

    async def add_scene(
        self,
        *,
        prompt: str,
        video_prompt: Optional[str] = None,
        character_names: Optional[list[str]] = None,
        chain_type: str = "ROOT",
        parent_scene_id: Optional[str] = None,
        display_order: Optional[int] = None,
        image_prompt: Optional[str] = None,
    ) -> Scene:
        """Create and persist a new scene in this video. Returns the Scene."""
        from agent.sdk.models.scene import Scene

        if self._repo is None:
            raise RuntimeError("No repository attached — cannot add scene")

        # Auto-assign display_order if not given
        if display_order is None:
            scenes = await self.get_scenes()
            display_order = max((s.display_order for s in scenes), default=-1) + 1

        import json as _json
        import uuid

        scene_id = str(uuid.uuid4())
        row = {
            "id": scene_id,
            "video_id": self.id,
            "display_order": display_order,
            "prompt": prompt,
            "image_prompt": image_prompt,
            "video_prompt": video_prompt,
            "character_names": _json.dumps(character_names) if character_names else None,
            "chain_type": chain_type,
            "parent_scene_id": parent_scene_id,
        }
        await self._repo.insert("scene", row)
        return Scene.from_row({**row, "id": scene_id}, repo=self._repo)

    async def get_scenes(self) -> list[Scene]:
        """Return all scenes for this video, ordered by display_order."""
        from agent.sdk.models.scene import Scene

        if self._repo is None:
            raise RuntimeError("No repository attached — cannot list scenes")
        rows = await self._repo.list("scene", video_id=self.id, order_by="display_order")
        return [Scene.from_row(r, repo=self._repo) for r in rows]

    async def remove_scene(self, scene_id: str) -> None:
        """Delete a scene by id."""
        if self._repo is None:
            raise RuntimeError("No repository attached — cannot remove scene")
        await self._repo.delete("scene", scene_id)

    async def move_scene(self, scene_id: str, new_order: int) -> None:
        """Update a scene's display_order."""
        if self._repo is None:
            raise RuntimeError("No repository attached — cannot move scene")
        await self._repo.update("scene", scene_id, display_order=new_order)
