"""Phase B core service: graph/structure reads and in-place editing."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from engram_core.config import Settings
from engram_core.errors import NoteConflict, NoteNotFound
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
    svc: NoteService, title: str, body: str = "body", tags: list[str] | None = None
) -> Note:
    note, _ = svc.create(NoteCreate(title=title, body=body, tags=tags or []), now=NOW)
    return note


def _stem(note: Note) -> str:
    return Path(note.path).stem


# --- structure reads --------------------------------------------------------


def test_related_collects_backlinks_and_outgoing(service: NoteService) -> None:
    a = _create(service, "A")
    b = _create(service, "B", f"links to [[{_stem(a)}]]")
    c = _create(service, "C", f"links to [[{_stem(b)}]]")
    related = {s.path for s in service.get_related(b.path)}
    assert related == {a.path, c.path}  # outgoing target a, backlink source c


def test_graph_scoped_to_depth(service: NoteService) -> None:
    a = _create(service, "A")
    b = _create(service, "B", f"[[{_stem(a)}]]")
    c = _create(service, "C", f"[[{_stem(b)}]]")
    graph = service.get_graph(b.path, depth=1)
    assert {n.path for n in graph.nodes} == {a.path, b.path, c.path}
    assert any(e.source == b.path and e.target == a.path for e in graph.edges)
    assert any(e.source == c.path and e.target == b.path for e in graph.edges)


def test_list_folders(service: NoteService) -> None:
    nested = service.settings.vault_path / "sub" / "deep" / "n.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("# Nested\n", encoding="utf-8")
    service.reconcile()
    assert service.list_folders() == ["sub", "sub/deep"]


def test_list_tags_includes_inline(service: NoteService) -> None:
    _create(service, "A", "body with #inline here", tags=["work"])
    counts = {t.tag: t.count for t in service.list_tags()}
    assert counts.get("work") == 1
    assert counts.get("inline") == 1


def test_get_by_title(service: NoteService) -> None:
    note = _create(service, "Unique Title")
    assert service.get_by_title("Unique Title").path == note.path
    with pytest.raises(NoteNotFound):
        service.get_by_title("No Such Title")


# --- in-place editing -------------------------------------------------------


def test_update_note_changes_fields_and_etag(service: NoteService) -> None:
    note = _create(service, "X", "first body")
    before = service.get_etag(note.path)
    updated = service.update_note(note.path, title="Y", body="second body", now=NOW)
    assert updated.title == "Y"
    assert service.get(note.path).body == "second body"
    assert service.get_etag(note.path) != before


def test_update_with_matching_etag_succeeds(service: NoteService) -> None:
    note = _create(service, "X", "body")
    etag = service.get_etag(note.path)
    assert etag is not None
    service.update_note(note.path, body="changed", expected_etag=etag, now=NOW)
    assert service.get(note.path).body == "changed"


def test_update_with_stale_etag_conflicts(service: NoteService) -> None:
    note = _create(service, "X", "body")
    stale = service.get_etag(note.path)
    assert stale is not None
    service.update_note(note.path, body="other edit", now=NOW)  # etag moves on
    with pytest.raises(NoteConflict):
        service.update_note(note.path, body="racing edit", expected_etag=stale, now=NOW)


def test_append_to_note(service: NoteService) -> None:
    note = _create(service, "X", "alpha")
    service.append_to_note(note.path, "beta", now=NOW)
    body = service.get(note.path).body
    assert "alpha" in body
    assert body.rstrip().endswith("beta")


def test_patch_section_creates_then_replaces(service: NoteService) -> None:
    note = _create(service, "X", "# X\n\nintro\n")
    service.patch_section(note.path, "Log", "first entry", now=NOW)
    assert "## Log" in service.get(note.path).body
    service.patch_section(note.path, "Log", "second entry", now=NOW)
    body = service.get(note.path).body
    assert "second entry" in body
    assert "first entry" not in body


def test_edit_updates_link_graph(service: NoteService) -> None:
    target = _create(service, "Target")
    source = _create(service, "Source", "no link yet")
    assert service.get_backlinks(target.path) == []
    service.update_note(source.path, body=f"now links [[{_stem(target)}]]", now=NOW)
    assert [s.path for s in service.get_backlinks(target.path)] == [source.path]
