"""The ``/api/v1`` REST router. Each handler is a thin call into ``NoteService``;
core models are used as response models so OpenAPI is generated from them.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response

from engram_core import (
    GraphView,
    LinkService,
    Note,
    NoteCreate,
    NoteService,
    OutgoingLink,
    TagCount,
)

from .errors import PreconditionRequired
from .schemas import (
    AppendRequest,
    LinkCreate,
    NoteListResponse,
    NoteUpdate,
    PatchSectionRequest,
    RestoreRequest,
    SearchResponse,
)
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


@router.post("/notes/restore", response_model=Note)
async def restore_note(data: RestoreRequest, service: ServiceDep) -> Note:
    return service.restore(data.path)


@router.get("/notes/by-title", response_model=Note)
async def get_note_by_title(
    service: ServiceDep, response: Response, title: str = Query(...)
) -> Note:
    note = service.get_by_title(title)
    response.headers["ETag"] = service.get_etag(note.path) or ""
    return note


@router.get("/notes/by-path/{path:path}", response_model=Note)
async def get_note_by_path(path: str, service: ServiceDep, response: Response) -> Note:
    note = service.get(path)
    response.headers["ETag"] = service.get_etag(note.path) or ""
    return note


@router.put("/notes/by-path/{path:path}", response_model=Note)
async def update_note_by_path(
    path: str,
    data: NoteUpdate,
    service: ServiceDep,
    response: Response,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> Note:
    if if_match is None:
        raise PreconditionRequired()
    note = service.update_note(
        path, title=data.title, body=data.body, tags=data.tags, expected_etag=if_match
    )
    response.headers["ETag"] = service.get_etag(note.path) or ""
    return note


@router.delete("/notes/by-path/{path:path}", status_code=204)
async def delete_note_by_path(path: str, service: ServiceDep) -> Response:
    service.delete(path)
    return Response(status_code=204)


@router.post("/notes/append", response_model=Note)
async def append_to_note(data: AppendRequest, service: ServiceDep, response: Response) -> Note:
    note = service.append_to_note(data.path, data.text)
    response.headers["ETag"] = service.get_etag(note.path) or ""
    return note


@router.post("/notes/patch-section", response_model=Note)
async def patch_section(
    data: PatchSectionRequest, service: ServiceDep, response: Response
) -> Note:
    note = service.patch_section(data.path, data.heading, data.content)
    response.headers["ETag"] = service.get_etag(note.path) or ""
    return note


@router.get("/notes/{handle}", response_model=Note)
async def get_note(handle: str, service: ServiceDep) -> Note:
    """Fetch a note by its id alias or a top-level path handle (use
    ``/notes/by-path/{path}`` for nested paths)."""
    return service.get(handle)


@router.delete("/notes/{handle}", status_code=204)
async def delete_note(handle: str, service: ServiceDep) -> Response:
    service.delete(handle)
    return Response(status_code=204)


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


@router.get("/backlinks", response_model=NoteListResponse)
async def backlinks(service: ServiceDep, path: str = Query(...)) -> NoteListResponse:
    return NoteListResponse(items=service.get_backlinks(path), next_cursor=None)


@router.get("/related", response_model=NoteListResponse)
async def related(service: ServiceDep, path: str = Query(...)) -> NoteListResponse:
    return NoteListResponse(items=service.get_related(path), next_cursor=None)


@router.get("/links", response_model=list[OutgoingLink])
async def links(service: ServiceDep, path: str = Query(...)) -> list[OutgoingLink]:
    return service.get_outgoing_links(path)


@router.get("/graph", response_model=GraphView)
async def graph(
    service: ServiceDep, path: str = Query(...), depth: int = Query(1, ge=1, le=4)
) -> GraphView:
    return service.get_graph(path, depth=depth)


@router.get("/folders", response_model=list[str])
async def folders(service: ServiceDep) -> list[str]:
    return service.list_folders()


@router.get("/tags", response_model=list[TagCount])
async def tags(service: ServiceDep) -> list[TagCount]:
    return service.list_tags()
