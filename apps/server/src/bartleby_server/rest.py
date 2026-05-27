"""The ``/api/v1`` REST router. Each handler is a thin call into ``NoteService``;
core models are used as response models so OpenAPI is generated from them.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from bartleby_core import LinkService, Note, NoteCreate, NoteService

from .schemas import LinkCreate, NoteListResponse, SearchResponse
from .service import get_link_service, get_service

router = APIRouter(prefix="/api/v1")

ServiceDep = Annotated[NoteService, Depends(get_service)]
LinkServiceDep = Annotated[LinkService, Depends(get_link_service)]


@router.post("/notes", status_code=201, response_model=Note, responses={200: {"model": Note}})
async def create_note(data: NoteCreate, response: Response, service: ServiceDep) -> Note:
    note, created = service.create(data)
    response.status_code = 201 if created else 200
    return note


@router.post("/links", status_code=201, response_model=Note, responses={200: {"model": Note}})
async def create_link(
    data: LinkCreate, response: Response, service: LinkServiceDep
) -> Note:
    note, created = await service.create_from_link(
        url=str(data.url),
        tags=data.tags,
        title_override=data.title,
        idempotency_key=data.idempotency_key,
    )
    response.status_code = 201 if created else 200
    return note


@router.get("/notes", response_model=NoteListResponse)
async def list_notes(
    service: ServiceDep,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None),
    tag: str | None = Query(None),
) -> NoteListResponse:
    items, next_cursor = service.list_notes(tag=tag, limit=limit, cursor=cursor)
    return NoteListResponse(items=items, next_cursor=next_cursor)


@router.get("/notes/{note_id}", response_model=Note)
async def get_note(note_id: str, service: ServiceDep) -> Note:
    return service.get(note_id)


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: str, service: ServiceDep) -> Response:
    service.delete(note_id)
    return Response(status_code=204)


@router.post("/notes/{note_id}/restore", response_model=Note)
async def restore_note(note_id: str, service: ServiceDep) -> Note:
    return service.restore(note_id)


@router.get("/search", response_model=SearchResponse)
async def search(
    service: ServiceDep,
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    tag: str | None = Query(None),
) -> SearchResponse:
    return SearchResponse(items=service.search(q, tag=tag, limit=limit))


@router.get("/trash", response_model=NoteListResponse)
async def list_trash(
    service: ServiceDep,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None),
) -> NoteListResponse:
    items, next_cursor = service.list_trash(limit=limit, cursor=cursor)
    return NoteListResponse(items=items, next_cursor=next_cursor)
