"""Response wrappers used by the REST layer (and documented in OpenAPI)."""

from __future__ import annotations

from pydantic import BaseModel

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
