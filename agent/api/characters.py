from fastapi import APIRouter, HTTPException
from agent.models.character import Character, CharacterCreate, CharacterUpdate
from agent.sdk.persistence.sqlite_repository import SQLiteRepository
from agent.services.event_bus import event_bus
from agent.utils.slugify import slugify

router = APIRouter(prefix="/characters", tags=["characters"])


def _get_repo() -> SQLiteRepository:
    return SQLiteRepository()


@router.post("", response_model=Character)
async def create(body: CharacterCreate):
    repo = _get_repo()
    char = await repo.create_character(**body.model_dump(exclude_none=True))
    await event_bus.emit("character_created", {"id": char.id, "name": char.name})
    return char


@router.get("", response_model=list[Character])
async def list_all():
    repo = _get_repo()
    rows = await repo.list("character", order_by="created_at DESC")
    return [repo._row_to_character(r) for r in rows]


@router.get("/{cid}", response_model=Character)
async def get(cid: str):
    repo = _get_repo()
    c = await repo.get_character(cid)
    if not c:
        raise HTTPException(404, "Character not found")
    return c


@router.patch("/{cid}", response_model=Character)
async def update(cid: str, body: CharacterUpdate):
    repo = _get_repo()
    updates = body.model_dump(exclude_unset=True)
    if "name" in updates:
        updates["slug"] = slugify(updates["name"])
    row = await repo.update("character", cid, **updates)
    if not row:
        raise HTTPException(404, "Character not found")
    char = repo._row_to_character(row)
    await event_bus.emit("character_updated", {"id": char.id, "name": char.name})
    return char


@router.delete("/{cid}")
async def delete(cid: str):
    repo = _get_repo()
    if not await repo.delete_character(cid):
        raise HTTPException(404, "Character not found")
    await event_bus.emit("character_deleted", {"id": cid})
    return {"ok": True}
