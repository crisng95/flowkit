"""Abstract Repository interface for the SDK persistence layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from agent.sdk.models.character import Character
from agent.sdk.models.project import Project
from agent.sdk.models.scene import Scene
from agent.sdk.models.video import Video


class Repository(ABC):
    """Abstract base for all SDK persistence backends.

    Provides both high-level typed methods (get_project, save_project, …)
    and low-level generic dispatchers (get, list, insert, update, delete,
    list_project_characters) that domain models call directly.
    """

    # ------------------------------------------------------------------
    # Generic low-level interface (called by domain model methods)
    # ------------------------------------------------------------------

    @abstractmethod
    async def get(self, table: str, pk: str) -> Optional[dict[str, Any]]:
        """Return one row as a dict, or None if not found."""

    @abstractmethod
    async def list(self, table: str, **filters: Any) -> list[dict[str, Any]]:
        """Return rows matching *filters*.

        Supports an optional ``order_by`` keyword that is NOT a column filter
        but controls the ORDER BY clause.
        """

    @abstractmethod
    async def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        """Insert *row* into *table* and return the inserted row."""

    @abstractmethod
    async def update(self, table: str, pk: str, **kwargs: Any) -> Optional[dict[str, Any]]:
        """Update columns for the row identified by *pk* in *table*."""

    @abstractmethod
    async def delete(self, table: str, pk: str) -> bool:
        """Delete the row identified by *pk* from *table*. Returns True if deleted."""

    @abstractmethod
    async def list_project_characters(self, project_id: str) -> list[dict[str, Any]]:
        """Return all character rows linked to *project_id*."""

    # ------------------------------------------------------------------
    # Typed Project methods
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_project(self, project_id: str) -> Optional[Project]:
        """Return a Project by id, or None."""

    @abstractmethod
    async def save_project(self, project: Project) -> None:
        """Persist changes on an existing Project."""

    @abstractmethod
    async def create_project(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        story: Optional[str] = None,
        language: str = "en",
        user_paygate_tier: str = "PAYGATE_TIER_ONE",
        id: Optional[str] = None,
    ) -> Project:
        """Insert a new project row and return the Project."""

    @abstractmethod
    async def delete_project(self, project_id: str) -> bool:
        """Delete a project by id. Returns True if deleted."""

    # ------------------------------------------------------------------
    # Typed Character methods
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_character(self, character_id: str) -> Optional[Character]:
        """Return a Character by id, or None."""

    @abstractmethod
    async def save_character(self, character: Character) -> None:
        """Persist changes on an existing Character."""

    @abstractmethod
    async def create_character(
        self,
        *,
        name: str,
        entity_type: str = "character",
        description: Optional[str] = None,
        image_prompt: Optional[str] = None,
        voice_description: Optional[str] = None,
        reference_image_url: Optional[str] = None,
        media_id: Optional[str] = None,
    ) -> Character:
        """Insert a new character row and return the Character."""

    @abstractmethod
    async def delete_character(self, character_id: str) -> bool:
        """Delete a character by id. Returns True if deleted."""

    @abstractmethod
    async def get_project_characters(self, project_id: str) -> list[Character]:
        """Return all Characters linked to a project."""

    @abstractmethod
    async def link_character_to_project(self, project_id: str, character_id: str) -> bool:
        """Link a character to a project. Returns True on success."""

    @abstractmethod
    async def unlink_character_from_project(self, project_id: str, character_id: str) -> bool:
        """Unlink a character from a project. Returns True if removed."""

    # ------------------------------------------------------------------
    # Typed Video methods
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_video(self, video_id: str) -> Optional[Video]:
        """Return a Video by id, or None."""

    @abstractmethod
    async def save_video(self, video: Video) -> None:
        """Persist changes on an existing Video."""

    @abstractmethod
    async def create_video(
        self,
        *,
        project_id: str,
        title: str,
        description: Optional[str] = None,
        display_order: int = 0,
        orientation: Optional[str] = None,
    ) -> Video:
        """Insert a new video row and return the Video."""

    @abstractmethod
    async def delete_video(self, video_id: str) -> bool:
        """Delete a video by id. Returns True if deleted."""

    @abstractmethod
    async def list_videos(self, project_id: str) -> list[Video]:
        """Return all Videos for a project, ordered by display_order."""

    # ------------------------------------------------------------------
    # Typed Scene methods
    # ------------------------------------------------------------------

    @abstractmethod
    async def get_scene(self, scene_id: str) -> Optional[Scene]:
        """Return a Scene by id, or None."""

    @abstractmethod
    async def save_scene(self, scene: Scene) -> None:
        """Persist changes on an existing Scene."""

    @abstractmethod
    async def create_scene(
        self,
        *,
        video_id: str,
        display_order: int,
        prompt: str,
        image_prompt: Optional[str] = None,
        video_prompt: Optional[str] = None,
        character_names: Optional[list[str]] = None,
        parent_scene_id: Optional[str] = None,
        chain_type: str = "ROOT",
        source: str = "root",
    ) -> Scene:
        """Insert a new scene row and return the Scene."""

    @abstractmethod
    async def delete_scene(self, scene_id: str) -> bool:
        """Delete a scene by id. Returns True if deleted."""

    @abstractmethod
    async def list_scenes(self, video_id: str) -> list[Scene]:
        """Return all Scenes for a video, ordered by display_order."""

    # ------------------------------------------------------------------
    # Generic typed dispatchers
    # ------------------------------------------------------------------

    async def save(self, model: Any) -> None:
        """Dispatch save() to the typed method matching model's _table."""
        table = getattr(model, "_table", None)
        if table == "project":
            await self.save_project(model)
        elif table == "character":
            await self.save_character(model)
        elif table == "video":
            await self.save_video(model)
        elif table == "scene":
            await self.save_scene(model)
        else:
            raise ValueError(f"No typed save() for table {table!r}")

    async def reload(self, model: Any) -> None:
        """Dispatch reload() by fetching the row and updating model fields."""
        table = getattr(model, "_table", None)
        row = await self.get(table, model.id)
        if row is None:
            raise LookupError(f"{table} {model.id} not found")
        for k, v in row.items():
            if hasattr(model, k) and not k.startswith("_"):
                object.__setattr__(model, k, v)
