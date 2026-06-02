"""Service-level link graph: backlinks, outgoing links, and re-resolution."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from engram_core.config import Settings
from engram_core.errors import NoteNotFound
from engram_core.models import Note, NoteCreate
from engram_core.service import NoteService

NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def service(tmp_path: Path) -> Iterator[NoteService]:
    svc = NoteService(Settings(vault_path=tmp_path / "vault", index_path=tmp_path / "index.db"))
    svc.startup()
    yield svc
    svc.close()


def _create(service: NoteService, title: str, body: str = "body") -> Note:
    note, _ = service.create(NoteCreate(title=title, body=body), now=NOW)
    return note


def _stem(note: Note) -> str:
    return Path(note.path).stem


def test_backlinks_and_outgoing(service: NoteService) -> None:
    target = _create(service, "Target")
    source = _create(service, "Source", body=f"links to [[{_stem(target)}]]")

    backlinks = service.get_backlinks(target.id)
    assert [b.id for b in backlinks] == [source.id]

    outgoing = service.get_outgoing_links(source.id)
    assert len(outgoing) == 1
    assert outgoing[0].type == "wikilink"
    assert outgoing[0].resolved_id == target.id
    assert outgoing[0].resolved_path == target.path


def test_dangling_link_has_no_resolution(service: NoteService) -> None:
    source = _create(service, "Source", body="points at [[Nowhere]]")
    outgoing = service.get_outgoing_links(source.id)
    assert outgoing[0].resolved_id is None
    assert outgoing[0].resolved_path is None
    assert service.get_backlinks(source.id) == []


def test_link_resolves_when_target_created_later(service: NoteService) -> None:
    source = _create(service, "Source", body="see [[late-note]]")
    assert service.get_outgoing_links(source.id)[0].resolved_id is None

    target, _ = service.create(NoteCreate(title="Late", body="x"), now=NOW)
    # Rename the target's file so its basename matches the wikilink, then reindex.
    late_path = service.settings.vault_path / "late-note.md"
    (service.settings.vault_path / target.path).rename(late_path)
    service.reindex()

    resolved = service.get_outgoing_links(source.id)[0]
    assert resolved.resolved_path == "late-note.md"


def test_deleting_target_dangles_backlink(service: NoteService) -> None:
    target = _create(service, "Target")
    source = _create(service, "Source", body=f"to [[{_stem(target)}]]")
    assert service.get_outgoing_links(source.id)[0].resolved_id == target.id

    service.delete(target.id, now=NOW)
    outgoing = service.get_outgoing_links(source.id)
    assert outgoing[0].resolved_id is None


def test_trashed_note_links_are_dropped(service: NoteService) -> None:
    target = _create(service, "Target")
    source = _create(service, "Source", body=f"to [[{_stem(target)}]]")
    service.delete(source.id, now=NOW)
    # The deleted source no longer contributes a backlink.
    assert service.get_backlinks(target.id) == []


def test_backlinks_for_missing_note_raises(service: NoteService) -> None:
    with pytest.raises(NoteNotFound):
        service.get_backlinks("01KSB998H8WTTDZCMR8C67KBR7")
