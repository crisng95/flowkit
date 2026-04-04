"""SDK Project domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from agent.sdk.models.base import DomainModel

if TYPE_CHECKING:
    from agent.sdk.models.character import Character
    from agent.sdk.models.video import Video
    from agent.sdk.repository import Repository


@dataclass
class Project(DomainModel):
    """Top-level project container."""

    _table: str = field(default="project", init=False, repr=False, compare=False)

    name: str = ""
    description: Optional[str] = None
    story: Optional[str] = None
    thumbnail_url: Optional[str] = None
    language: str = "en"
    status: str = "ACTIVE"
    user_paygate_tier: str = "PAYGATE_TIER_ONE"
    material: Optional[str] = None
    narrator_voice: Optional[str] = None
    narrator_ref_audio: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # ------------------------------------------------------------------
    # Class-level constructors
    # ------------------------------------------------------------------

    @classmethod
    async def get(cls, project_id: str, *, repo: Repository) -> Project:
        """Load a project by id."""
        row = await repo.get("project", project_id)
        if row is None:
            raise LookupError(f"Project {project_id} not found")
        return cls(**{k: v for k, v in row.items() if not k.startswith("_")}, _repo=repo)

    @classmethod
    async def create(
        cls,
        *,
        repo: Repository,
        name: str,
        description: Optional[str] = None,
        story: Optional[str] = None,
        language: str = "en",
        user_paygate_tier: str = "PAYGATE_TIER_ONE",
    ) -> Project:
        """Insert a new project row and return a Project instance."""
        import uuid

        pid = str(uuid.uuid4())
        row = {
            "id": pid,
            "name": name,
            "description": description,
            "story": story,
            "language": language,
            "user_paygate_tier": user_paygate_tier,
        }
        await repo.insert("project", row)
        return cls(id=pid, name=name, description=description, story=story,
                   language=language, user_paygate_tier=user_paygate_tier, _repo=repo)

    # ------------------------------------------------------------------
    # Character / entity helpers
    # ------------------------------------------------------------------

    async def add_character(self, character_id: str) -> None:
        """Link an existing character/entity to this project."""
        if self._repo is None:
            raise RuntimeError("No repository attached")
        await self._repo.insert(
            "project_character",
            {"project_id": self.id, "character_id": character_id},
        )

    async def get_characters(self) -> list[Character]:
        """Return all characters/entities linked to this project."""
        from agent.sdk.models.character import Character

        if self._repo is None:
            raise RuntimeError("No repository attached")
        rows = await self._repo.list_project_characters(self.id)
        return [Character(**{k: v for k, v in r.items() if not k.startswith("_")}, _repo=self._repo, _project=self) for r in rows]

    async def get_character(self, name: str) -> Optional[Character]:
        """Find a single character/entity by name within this project."""
        chars = await self.get_characters()
        for c in chars:
            if c.name == name:
                return c
        return None

    # ------------------------------------------------------------------
    # Video helpers
    # ------------------------------------------------------------------

    async def add_video(
        self,
        *,
        title: str,
        description: Optional[str] = None,
        display_order: int = 0,
    ) -> Video:
        """Create a new video under this project."""
        from agent.sdk.models.video import Video
        import uuid

        if self._repo is None:
            raise RuntimeError("No repository attached")

        vid = str(uuid.uuid4())
        row = {
            "id": vid,
            "project_id": self.id,
            "title": title,
            "description": description,
            "display_order": display_order,
        }
        await self._repo.insert("video", row)
        return Video(id=vid, project_id=self.id, title=title,
                     description=description, display_order=display_order, _repo=self._repo)

    async def get_videos(self) -> list[Video]:
        """Return all videos for this project, ordered by display_order."""
        from agent.sdk.models.video import Video

        if self._repo is None:
            raise RuntimeError("No repository attached")
        rows = await self._repo.list("video", project_id=self.id, order_by="display_order")
        return [Video(**{k: v for k, v in r.items() if not k.startswith("_")}, _repo=self._repo) for r in rows]
