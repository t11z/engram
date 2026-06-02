from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from engram_core.config import Settings
from engram_core.errors import NoteNotFound, NoteNotInTrash
from engram_core.models import Note, NoteCreate
from engram_core.service import NoteService

NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def service(tmp_path: Path) -> Iterator[NoteService]:
    svc = NoteService(Settings(vault_path=tmp_path / "vault", index_path=tmp_path / "index.db"))
    svc.startup()
    yield svc
    svc.close()


def _create(
    service: NoteService,
    title: str,
    body: str = "body",
    *,
    tags: list[str] | None = None,
    idempotency_key: str | None = None,
) -> Note:
    note, created = service.create(
        NoteCreate(title=title, body=body, tags=tags or [], idempotency_key=idempotency_key),
        now=NOW,
    )
    assert created is True
    return note


def test_create_then_get_and_list(service: NoteService) -> None:
    note = _create(service, "Hello", "the body")
    assert note.id is None  # id injection is off by default; path is the handle
    assert note.path == "hello.md"
    fetched = service.get(note.path)
    assert fetched.title == "Hello"
    assert fetched.body == "the body"
    summaries, cursor = service.list_notes()
    assert [s.path for s in summaries] == [note.path]
    assert cursor is None


def test_idempotent_create_returns_existing(service: NoteService) -> None:
    first, c1 = service.create(NoteCreate(title="A", body="x", idempotency_key="k"), now=NOW)
    second, c2 = service.create(NoteCreate(title="A", body="x", idempotency_key="k"), now=NOW)
    assert c1 is True
    assert c2 is False
    assert first.path == second.path
    summaries, _ = service.list_notes()
    assert len(summaries) == 1


def test_idempotency_ignores_trashed_match(service: NoteService) -> None:
    first, _ = service.create(NoteCreate(title="A", body="x", idempotency_key="k"), now=NOW)
    service.delete(first.path, now=NOW)
    second, created = service.create(NoteCreate(title="A", body="x", idempotency_key="k"), now=NOW)
    assert created is True
    live, _ = service.list_notes()
    assert [s.path for s in live] == [second.path]


def test_get_missing_raises(service: NoteService) -> None:
    with pytest.raises(NoteNotFound):
        service.get("nope.md")


def test_get_by_id_alias(tmp_path: Path) -> None:
    svc = NoteService(
        Settings(vault_path=tmp_path / "v", index_path=tmp_path / "i.db", inject_id=True)
    )
    svc.startup()
    try:
        note = _create(svc, "Aliased")
        assert note.id is not None
        assert svc.get(note.id).path == note.path  # addressable by id alias too
    finally:
        svc.close()


def test_delete_moves_to_trash(service: NoteService) -> None:
    note = _create(service, "Doomed")
    service.delete(note.path, now=NOW)
    with pytest.raises(NoteNotFound):
        service.get(note.path)
    live, _ = service.list_notes()
    assert live == []
    trash, _ = service.list_trash()
    assert [s.path for s in trash] == [".trash/doomed.md"]


def test_restore(service: NoteService) -> None:
    note = _create(service, "Comeback")
    service.delete(note.path, now=NOW)
    trash_path = service.list_trash()[0][0].path
    restored = service.restore(trash_path)
    assert restored.path == note.path
    live, _ = service.list_notes()
    assert [s.path for s in live] == [note.path]
    assert service.list_trash()[0] == []


def test_restore_non_trashed_raises(service: NoteService) -> None:
    with pytest.raises(NoteNotInTrash):
        service.restore(".trash/missing.md")


def test_purge_expired_trash(service: NoteService) -> None:
    note = _create(service, "Old")
    service.delete(note.path, now=NOW - timedelta(days=40))
    purged = service.purge_expired_trash(now=NOW)
    assert purged == [".trash/old.md"]
    assert service.list_trash()[0] == []


def test_purge_keeps_recent(service: NoteService) -> None:
    note = _create(service, "Recent")
    service.delete(note.path, now=NOW - timedelta(days=5))
    assert service.purge_expired_trash(now=NOW) == []
    assert len(service.list_trash()[0]) == 1


def test_search_via_service(service: NoteService) -> None:
    _create(service, "Postgres", "how to back up postgres", tags=["ops"])
    _create(service, "Cooking", "how to bake bread")
    hits = service.search("postgres")
    assert [h.title for h in hits] == ["Postgres"]
    assert service.search("postgres", tag="nope") == []
