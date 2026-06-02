"""Pydantic models and RFC 3339 helpers. Pure data shapes — no I/O, no logic.

Timestamps are modeled as timezone-aware ``datetime`` in Python but serialize to
RFC 3339 UTC strings with second precision and a ``Z`` suffix (ULIDs already carry
millisecond ordering, so seconds in the human-readable header suffice).
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


def to_rfc3339(value: datetime) -> str:
    """Format a datetime as ``YYYY-MM-DDTHH:MM:SSZ`` (UTC, seconds)."""
    return value.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def from_rfc3339(value: str) -> datetime:
    """Parse an RFC 3339 string to a timezone-aware UTC datetime."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp {value!r} is missing a timezone")
    return parsed.astimezone(UTC)


class NoteMeta(BaseModel):
    """The YAML frontmatter of a note.

    Unknown keys are tolerated and preserved (kept in ``model_extra``), not
    rejected: a shared vault may carry properties written by another editor, and
    engram must round-trip them rather than drop the note. Known fields are still
    validated.
    """

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    title: str
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)
    source_url: str | None = None
    idempotency_key: str | None = None

    @field_validator("created_at", "updated_at")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware (UTC)")
        return value.astimezone(UTC)

    @field_serializer("created_at", "updated_at")
    def _serialize_dt(self, value: datetime) -> str:
        return to_rfc3339(value)


class Note(NoteMeta):
    """A full note: frontmatter plus the Markdown body and its vault-relative path."""

    body: str
    path: str

    def to_meta(self) -> NoteMeta:
        return NoteMeta(
            id=self.id,
            title=self.title,
            created_at=self.created_at,
            updated_at=self.updated_at,
            tags=list(self.tags),
            source_url=self.source_url,
            idempotency_key=self.idempotency_key,
            **(self.model_extra or {}),
        )

    def to_summary(self) -> NoteSummary:
        return NoteSummary(
            id=self.id,
            title=self.title,
            tags=list(self.tags),
            updated_at=self.updated_at,
            path=self.path,
        )


class NoteCreate(BaseModel):
    """Input for creating a note."""

    title: str
    body: str
    tags: list[str] = Field(default_factory=list)
    source_url: str | None = None
    idempotency_key: str | None = None


class NoteSummary(BaseModel):
    """A lightweight projection for list and search results (no body)."""

    id: str | None = None
    title: str
    tags: list[str] = Field(default_factory=list)
    updated_at: datetime
    path: str

    @field_serializer("updated_at")
    def _serialize_dt(self, value: datetime) -> str:
        return to_rfc3339(value)


class SearchResult(NoteSummary):
    """A search hit: a summary plus relevance score and a text snippet."""

    score: float
    snippet: str


class OutgoingLink(BaseModel):
    """An outgoing reference from a note, with its resolution against the vault.

    ``resolved_path``/``resolved_id`` are ``None`` for a dangling link (a target
    that matches no note — e.g. a stub for a note not yet written).
    """

    target: str
    type: str
    resolved_path: str | None = None
    resolved_id: str | None = None
