"""Response wrappers used by the REST layer (and documented in OpenAPI)."""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl

from bartleby_core.models import NoteSummary, SearchResult


class NoteListResponse(BaseModel):
    items: list[NoteSummary]
    next_cursor: str | None = None


class SearchResponse(BaseModel):
    items: list[SearchResult]


class HealthResponse(BaseModel):
    status: str
    version: str


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class LinkCreate(BaseModel):
    """Input for ``POST /api/v1/links``: a URL the server should fetch and import."""

    url: HttpUrl
    tags: list[str] = Field(default_factory=list)
    title: str | None = None
    idempotency_key: str | None = None
