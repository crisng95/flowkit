"""SQLiteRepository — wraps agent.db.crud for SDK persistence."""

from __future__ import annotations

import json
from typing import Any, Optional

import agent.db.crud as crud

from agent.sdk.models.character import Character
from agent.sdk.models.project import Project
from agent.sdk.models.scene import Scene
from agent.sdk.models.video import Video
from agent.sdk.persistence.base import Repository


class SQLiteRepository(Repository):
    """Concrete repository backed by the SQLite DB via agent.db.crud."""

    # ------------------------------------------------------------------
    # Row → model converters
    # ------------------------------------------------------------------

    def _row_to_project(self, row: dict[str, Any]) -> Project:
        return Project(
            id=row.get("id", ""),
            name=row.get("name", ""),
            description=row.get("description"),
            story=row.get("story"),
            thumbnail_url=row.get("thumbnail_url"),
            language=row.get("language", "en"),
            status=row.get("status", "ACTIVE"),
            user_paygate_tier=row.get("user_paygate_tier", "PAYGATE_TIER_ONE"),
            material=row.get("material"),
            narrator_voice=row.get("narrator_voice"),
            narrator_ref_audio=row.get("narrator_ref_audio"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            _repo=self,
        )

    def _row_to_character(self, row: dict[str, Any]) -> Character:
        return Character(
            id=row.get("id", ""),
            name=row.get("name", ""),
            entity_type=row.get("entity_type", "character"),
            description=row.get("description"),
            image_prompt=row.get("image_prompt"),
            voice_description=row.get("voice_description"),
            reference_image_url=row.get("reference_image_url"),
            media_id=row.get("media_id"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            _repo=self,
        )

    def _row_to_video(self, row: dict[str, Any]) -> Video:
        return Video(
            id=row.get("id", ""),
            project_id=row.get("project_id", ""),
            title=row.get("title", ""),
            description=row.get("description"),
            display_order=row.get("display_order", 0),
            status=row.get("status", "DRAFT"),
            vertical_url=row.get("vertical_url"),
            horizontal_url=row.get("horizontal_url"),
            thumbnail_url=row.get("thumbnail_url"),
            duration=row.get("duration"),
            resolution=row.get("resolution"),
            youtube_id=row.get("youtube_id"),
            privacy=row.get("privacy", "unlisted"),
            tags=row.get("tags"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            _repo=self,
        )

    def _row_to_scene(self, row: dict[str, Any]) -> Scene:
        """Map a flat DB row (18 orientation columns) to a Scene with nested OrientationSlots."""
        return Scene.from_row(row, repo=self)

    def _scene_to_updates(self, scene: Scene) -> dict[str, Any]:
        """Flatten a Scene's OrientationSlots back to DB column names."""
        updates: dict[str, Any] = {
            "prompt": scene.prompt,
            "image_prompt": scene.image_prompt,
            "video_prompt": scene.video_prompt,
            "character_names": json.dumps(scene.character_names) if scene.character_names is not None else None,
            "chain_type": scene.chain_type,
            "source": scene.source,
            "display_order": scene.display_order,
            "trim_start": scene.trim_start,
            "trim_end": scene.trim_end,
            "duration": scene.duration,
            # Vertical
            "vertical_image_url": scene.vertical.image.url,
            "vertical_image_media_id": scene.vertical.image.media_id,
            "vertical_image_status": scene.vertical.image.status,
            "vertical_video_url": scene.vertical.video.url,
            "vertical_video_media_id": scene.vertical.video.media_id,
            "vertical_video_status": scene.vertical.video.status,
            "vertical_upscale_url": scene.vertical.upscale.url,
            "vertical_upscale_media_id": scene.vertical.upscale.media_id,
            "vertical_upscale_status": scene.vertical.upscale.status,
            "vertical_end_scene_media_id": scene.vertical.end_scene_media_id,
            # Horizontal
            "horizontal_image_url": scene.horizontal.image.url,
            "horizontal_image_media_id": scene.horizontal.image.media_id,
            "horizontal_image_status": scene.horizontal.image.status,
            "horizontal_video_url": scene.horizontal.video.url,
            "horizontal_video_media_id": scene.horizontal.video.media_id,
            "horizontal_video_status": scene.horizontal.video.status,
            "horizontal_upscale_url": scene.horizontal.upscale.url,
            "horizontal_upscale_media_id": scene.horizontal.upscale.media_id,
            "horizontal_upscale_status": scene.horizontal.upscale.status,
            "horizontal_end_scene_media_id": scene.horizontal.end_scene_media_id,
        }
        return {k: v for k, v in updates.items() if v is not None or k.endswith("_media_id") or k.endswith("_url") or k.endswith("_status")}

    # ------------------------------------------------------------------
    # Generic low-level interface
    # ------------------------------------------------------------------

    async def get(self, table: str, pk: str) -> Optional[dict[str, Any]]:
        return await crud._get(table, "id", pk)

    async def list(self, table: str, **filters: Any) -> list[dict[str, Any]]:
        order_by = filters.pop("order_by", None)
        from agent.db.schema import get_db
        db = await get_db()
        where_parts = [f"{k}=?" for k in filters]
        params = list(filters.values())
        q = f"SELECT * FROM {table}"
        if where_parts:
            q += " WHERE " + " AND ".join(where_parts)
        if order_by:
            q += f" ORDER BY {order_by}"
        cur = await db.execute(q, params)
        return [dict(r) for r in await cur.fetchall()]

    async def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        from agent.db.schema import get_db, _db_lock
        db = await get_db()
        cols = list(row.keys())
        placeholders = ",".join("?" for _ in cols)
        col_str = ",".join(cols)
        async with _db_lock:
            await db.execute(
                f"INSERT OR IGNORE INTO {table} ({col_str}) VALUES ({placeholders})",
                list(row.values()),
            )
            await db.commit()
        pk = row.get("id")
        if pk:
            return await crud._get(table, "id", pk) or row
        return row

    async def update(self, table: str, pk: str, **kwargs: Any) -> Optional[dict[str, Any]]:
        return await crud._update(table, "id", pk, **kwargs)

    async def delete(self, table: str, pk: str) -> bool:
        return await crud._delete(table, "id", pk)

    async def list_project_characters(self, project_id: str) -> list[dict[str, Any]]:
        return await crud.get_project_characters(project_id)

    # ------------------------------------------------------------------
    # Typed Project methods
    # ------------------------------------------------------------------

    async def get_project(self, project_id: str) -> Optional[Project]:
        row = await crud.get_project(project_id)
        return self._row_to_project(row) if row else None

    async def save_project(self, project: Project) -> None:
        await crud.update_project(
            project.id,
            name=project.name,
            description=project.description,
            story=project.story,
            thumbnail_url=project.thumbnail_url,
            language=project.language,
            status=project.status,
            user_paygate_tier=project.user_paygate_tier,
        )

    async def create_project(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        story: Optional[str] = None,
        language: str = "en",
        user_paygate_tier: str = "PAYGATE_TIER_ONE",
        id: Optional[str] = None,
        material: Optional[str] = None,
    ) -> Project:
        row = await crud.create_project(
            name=name,
            description=description,
            story=story,
            language=language,
            user_paygate_tier=user_paygate_tier,
            id=id,
            material=material,
        )
        return self._row_to_project(row)

    async def delete_project(self, project_id: str) -> bool:
        return await crud.delete_project(project_id)

    # ------------------------------------------------------------------
    # Typed Character methods
    # ------------------------------------------------------------------

    async def get_character(self, character_id: str) -> Optional[Character]:
        row = await crud.get_character(character_id)
        return self._row_to_character(row) if row else None

    async def save_character(self, character: Character) -> None:
        await crud.update_character(
            character.id,
            name=character.name,
            entity_type=character.entity_type,
            description=character.description,
            image_prompt=character.image_prompt,
            voice_description=character.voice_description,
            reference_image_url=character.reference_image_url,
            media_id=character.media_id,
        )

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
        row = await crud.create_character(
            name=name,
            entity_type=entity_type,
            description=description,
            image_prompt=image_prompt,
            voice_description=voice_description,
            reference_image_url=reference_image_url,
            media_id=media_id,
        )
        return self._row_to_character(row)

    async def delete_character(self, character_id: str) -> bool:
        return await crud.delete_character(character_id)

    async def get_project_characters(self, project_id: str) -> list[Character]:
        rows = await crud.get_project_characters(project_id)
        return [self._row_to_character(r) for r in rows]

    async def link_character_to_project(self, project_id: str, character_id: str) -> bool:
        return await crud.link_character_to_project(project_id, character_id)

    async def unlink_character_from_project(self, project_id: str, character_id: str) -> bool:
        return await crud.unlink_character_from_project(project_id, character_id)

    # ------------------------------------------------------------------
    # Typed Video methods
    # ------------------------------------------------------------------

    async def get_video(self, video_id: str) -> Optional[Video]:
        row = await crud.get_video(video_id)
        return self._row_to_video(row) if row else None

    async def save_video(self, video: Video) -> None:
        await crud.update_video(
            video.id,
            title=video.title,
            description=video.description,
            display_order=video.display_order,
            status=video.status,
            vertical_url=video.vertical_url,
            horizontal_url=video.horizontal_url,
            thumbnail_url=video.thumbnail_url,
            duration=video.duration,
            resolution=video.resolution,
            youtube_id=video.youtube_id,
            privacy=video.privacy,
            tags=video.tags,
        )

    async def create_video(
        self,
        *,
        project_id: str,
        title: str,
        description: Optional[str] = None,
        display_order: int = 0,
    ) -> Video:
        row = await crud.create_video(
            project_id=project_id,
            title=title,
            description=description,
            display_order=display_order,
        )
        return self._row_to_video(row)

    async def delete_video(self, video_id: str) -> bool:
        return await crud.delete_video(video_id)

    async def list_videos(self, project_id: str) -> list[Video]:
        rows = await crud.list_videos(project_id)
        return [self._row_to_video(r) for r in rows]

    # ------------------------------------------------------------------
    # Typed Scene methods
    # ------------------------------------------------------------------

    async def get_scene(self, scene_id: str) -> Optional[Scene]:
        row = await crud.get_scene(scene_id)
        return self._row_to_scene(row) if row else None

    async def save_scene(self, scene: Scene) -> None:
        updates = self._scene_to_updates(scene)
        await crud.update_scene(scene.id, **updates)

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
        row = await crud.create_scene(
            video_id=video_id,
            display_order=display_order,
            prompt=prompt,
            image_prompt=image_prompt,
            video_prompt=video_prompt,
            character_names=character_names,
            parent_scene_id=parent_scene_id,
            chain_type=chain_type,
            source=source,
        )
        return self._row_to_scene(row)

    async def delete_scene(self, scene_id: str) -> bool:
        return await crud.delete_scene(scene_id)

    async def list_scenes(self, video_id: str) -> list[Scene]:
        rows = await crud.list_scenes(video_id)
        return [self._row_to_scene(r) for r in rows]
