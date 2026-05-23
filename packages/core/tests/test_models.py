from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from bartleby_core.models import (
    Note,
    NoteMeta,
    NoteSummary,
    from_rfc3339,
    to_rfc3339,
)


def _dt(s: str) -> datetime:
    return from_rfc3339(s)


def test_rfc3339_round_trip() -> None:
    s = "2026-01-10T08:30:00Z"
    assert to_rfc3339(from_rfc3339(s)) == s


def test_rfc3339_normalizes_offset_to_utc() -> None:
    assert to_rfc3339(from_rfc3339("2026-01-10T10:30:00+02:00")) == "2026-01-10T08:30:00Z"


def test_to_rfc3339_drops_microseconds() -> None:
    dt = datetime(2026, 1, 10, 8, 30, 0, 123456, tzinfo=UTC)
    assert to_rfc3339(dt) == "2026-01-10T08:30:00Z"


def test_from_rfc3339_rejects_naive() -> None:
    with pytest.raises(ValueError):
        from_rfc3339("2026-01-10T08:30:00")


def test_notemeta_defaults_tags_empty() -> None:
    meta = NoteMeta(
        id="01J0000000000000000000000A",
        title="Hi",
        created_at=_dt("2026-01-10T08:30:00Z"),
        updated_at=_dt("2026-01-10T08:30:00Z"),
    )
    assert meta.tags == []
    assert meta.source_url is None
    assert meta.idempotency_key is None


def test_notemeta_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        NoteMeta(
            id="01J0000000000000000000000A",
            title="Hi",
            created_at=_dt("2026-01-10T08:30:00Z"),
            updated_at=_dt("2026-01-10T08:30:00Z"),
            author="someone",  # type: ignore[call-arg]
        )


def test_notemeta_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError):
        NoteMeta(
            id="01J0000000000000000000000A",
            title="Hi",
            created_at=datetime(2026, 1, 10, 8, 30, 0),  # naive
            updated_at=_dt("2026-01-10T08:30:00Z"),
        )


def test_model_dump_serializes_timestamps_as_rfc3339() -> None:
    meta = NoteMeta(
        id="01J0000000000000000000000A",
        title="Hi",
        created_at=_dt("2026-01-10T08:30:00Z"),
        updated_at=_dt("2026-01-10T09:00:00Z"),
    )
    dumped = meta.model_dump()
    assert dumped["created_at"] == "2026-01-10T08:30:00Z"
    assert dumped["updated_at"] == "2026-01-10T09:00:00Z"


def test_note_projections() -> None:
    note = Note(
        id="01J0000000000000000000000A",
        title="Hi",
        created_at=_dt("2026-01-10T08:30:00Z"),
        updated_at=_dt("2026-01-10T09:00:00Z"),
        tags=["a", "b"],
        body="hello",
        path="2026-01-10-hi.md",
    )
    assert isinstance(note.to_meta(), NoteMeta)
    summary = note.to_summary()
    assert isinstance(summary, NoteSummary)
    assert summary.id == note.id
    assert summary.tags == ["a", "b"]
    assert not hasattr(summary, "body")
