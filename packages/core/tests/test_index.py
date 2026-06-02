import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from engram_core.index import SearchIndex
from engram_core.models import Note

BASE = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


def _note(
    note_id: str,
    title: str,
    body: str,
    *,
    tags: list[str] | None = None,
    minutes: int = 0,
    idem: str | None = None,
) -> Note:
    ts = BASE + timedelta(minutes=minutes)
    return Note(
        id=note_id,
        title=title,
        created_at=ts,
        updated_at=ts,
        tags=tags or [],
        idempotency_key=idem,
        body=body,
        path=f"{note_id}.md",
    )


@pytest.fixture
def index(tmp_path: Path) -> Iterator[SearchIndex]:
    idx = SearchIndex(tmp_path / "index.db")
    idx.open()
    yield idx
    idx.close()


def _put(index: SearchIndex, note: Note, deleted_at: datetime | None = None) -> int:
    return index.upsert(note, size=len(note.body), mtime=1.0, deleted_at=deleted_at)


def _trash(index: SearchIndex, note: Note, deleted_at: datetime = BASE) -> None:
    """Trash a note: re-upsert it (matched by id) at its trash path, deleted."""
    trashed = note.model_copy(update={"path": f".trash/{note.path}"})
    index.upsert(trashed, size=len(note.body), mtime=2.0, deleted_at=deleted_at)


def test_search_finds_and_ranks(index: SearchIndex) -> None:
    _put(index, _note("01A", "Strong", "postgres postgres postgres backups"))
    _put(index, _note("01B", "Weak", "a long note that mentions postgres once only here"))
    results = index.search("postgres")
    assert [r.id for r in results] == ["01A", "01B"]
    assert results[0].score >= results[1].score


def test_search_snippet_contains_term(index: SearchIndex) -> None:
    _put(index, _note("01A", "Doc", "intro then postgres backup details follow"))
    [hit] = index.search("postgres")
    assert "postgres" in hit.snippet.lower()


def test_search_tag_filter_is_exact_token(index: SearchIndex) -> None:
    _put(index, _note("01A", "Ops note", "deploy postgres", tags=["ops"]))
    _put(index, _note("01B", "Opsec note", "secure postgres", tags=["opsec"]))
    assert [r.id for r in index.search("postgres", tag="ops")] == ["01A"]


def test_search_empty_and_no_match(index: SearchIndex) -> None:
    _put(index, _note("01A", "Doc", "hello world"))
    assert index.search("   ") == []
    assert index.search("nonexistentterm") == []


def test_idempotency_lookup_returns_path_live_only(index: SearchIndex) -> None:
    note = _note("01A", "Doc", "body", idem="key-1")
    _put(index, note)
    assert index.find_by_idempotency_key("key-1") == "01A.md"
    _trash(index, note)
    assert index.find_by_idempotency_key("key-1") is None


def test_duplicate_live_idempotency_key_rejected(index: SearchIndex) -> None:
    _put(index, _note("01A", "A", "body", idem="dup"))
    with pytest.raises(sqlite3.IntegrityError):
        _put(index, _note("01B", "B", "body", idem="dup"))


def test_resolve_handle_by_id_and_path(index: SearchIndex) -> None:
    note = _note("01A", "Doc", "body")
    _put(index, note)
    assert index.resolve_handle("01A") == "01A.md"  # by id alias
    assert index.resolve_handle("01A.md") == "01A.md"  # by path
    _trash(index, note)
    assert index.resolve_handle("01A") is None
    assert index.resolve_handle("missing") is None


def test_trashed_excluded_from_search_and_list(index: SearchIndex) -> None:
    note = _note("01A", "Doc", "postgres")
    _put(index, note)
    _trash(index, note)
    assert index.search("postgres") == []
    assert index.list_live()[0] == []
    trash, _ = index.list_trash()
    assert [s.id for s in trash] == ["01A"]
    assert [s.path for s in trash] == [".trash/01A.md"]


def test_reupsert_live_restores_from_trash(index: SearchIndex) -> None:
    note = _note("01A", "Doc", "postgres")
    _put(index, note)
    _trash(index, note)
    _put(index, note)  # back to live at original path
    assert [r.id for r in index.search("postgres")] == ["01A"]
    assert index.resolve_handle("01A") == "01A.md"


def test_list_live_newest_first_and_pagination(index: SearchIndex) -> None:
    for i in range(5):
        _put(index, _note(f"0{i}", f"Note {i}", "body", minutes=i))
    page1, cur1 = index.list_live(limit=2)
    assert [s.id for s in page1] == ["04", "03"]
    assert cur1 is not None
    page2, cur2 = index.list_live(limit=2, cursor=cur1)
    assert [s.id for s in page2] == ["02", "01"]
    page3, cur3 = index.list_live(limit=2, cursor=cur2)
    assert [s.id for s in page3] == ["00"]
    assert cur3 is None


def test_list_live_tag_filter(index: SearchIndex) -> None:
    _put(index, _note("01A", "A", "body", tags=["work"], minutes=1))
    _put(index, _note("01B", "B", "body", tags=["home"], minutes=2))
    assert [s.id for s in index.list_live(tag="work")[0]] == ["01A"]


def test_remove_and_clear(index: SearchIndex) -> None:
    nid = _put(index, _note("01A", "Doc", "postgres"))
    _put(index, _note("01B", "Doc2", "postgres"))
    index.remove_noteid(nid)
    assert [r.id for r in index.search("postgres")] == ["01B"]
    index.clear()
    assert index.search("postgres") == []
    assert list(index.all_rows()) == []


def test_all_rows_reports_state(index: SearchIndex) -> None:
    note = _note("01A", "Doc", "body")
    _put(index, note)
    _trash(index, note)
    rows = list(index.all_rows())
    assert len(rows) == 1
    _noteid, note_id, path, _size, _mtime, deleted_at = rows[0]
    assert note_id == "01A"
    assert path == ".trash/01A.md"
    assert deleted_at is not None


def test_id_less_note_addressed_by_path(index: SearchIndex) -> None:
    note = Note(
        id=None,
        title="No Id",
        created_at=BASE,
        updated_at=BASE,
        body="postgres here",
        path="folder/no-id.md",
    )
    _put(index, note)
    assert index.resolve_handle("folder/no-id.md") == "folder/no-id.md"
    assert [s.path for s in index.list_live()[0]] == ["folder/no-id.md"]
    assert [r.id for r in index.search("postgres")] == [None]


def test_invalid_cursor_raises(index: SearchIndex) -> None:
    with pytest.raises(ValueError):
        index.list_live(cursor="not-valid-base64!!")
