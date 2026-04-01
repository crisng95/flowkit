from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from agent.models.request import Request, RequestCreate
from agent.models.enums import StatusType
from agent.db import crud

router = APIRouter(prefix="/requests", tags=["requests"])


class RequestUpdate(BaseModel):
    status: Optional[StatusType] = None
    media_id: Optional[str] = None
    output_url: Optional[str] = None
    error_message: Optional[str] = None
    request_id: Optional[str] = None


@router.post("", response_model=Request)
async def create(body: RequestCreate):
    data = body.model_dump(exclude_none=True)
    data["req_type"] = data.pop("type")
    return await crud.create_request(**data)


@router.get("", response_model=list[Request])
async def list_all(scene_id: str = None, status: str = None):
    return await crud.list_requests(scene_id=scene_id, status=status)


@router.get("/pending", response_model=list[Request])
async def list_pending():
    return await crud.list_pending_requests()


@router.get("/{rid}", response_model=Request)
async def get(rid: str):
    r = await crud.get_request(rid)
    if not r:
        raise HTTPException(404, "Request not found")
    return r


@router.patch("/{rid}", response_model=Request)
async def update(rid: str, body: RequestUpdate):
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(400, "No fields to update")
    r = await crud.update_request(rid, **data)
    if not r:
        raise HTTPException(404, "Request not found")
    return r
