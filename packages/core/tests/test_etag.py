"""Content-hash etag (version token) caching — foundation for ADR-0009."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from engram_core.config import Settings
from engram_core.errors import NoteNotFound
from engram_core.models import NoteCreate
from engram_core.service import NoteService

NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def service(tmp_path: Path) -> Iterator[NoteService]:
    svc = NoteService(Settings(vault_path=tmp_path / "vault", index_path=tmp_path / "index.db"))
    svc.startup()
    yield svc
    svc.close()


def _file_hash(service: NoteService, rel_path: str) -> str:
    return hashlib.sha256((service.settings.vault_path / rel_path).read_bytes()).hexdigest()


def test_create_caches_file_content_hash(service: NoteService) -> None:
    note, _ = service.create(NoteCreate(title="Hello", body="the body"), now=NOW)
    assert service.get_etag(note.path) == _file_hash(service, note.path)


def test_etag_stable_across_noop_reconcile(service: NoteService) -> None:
    note, _ = service.create(NoteCreate(title="Stable", body="x"), now=NOW)
    before = service.get_etag(note.path)
    service.reconcile()
    assert service.get_etag(note.path) == before


def test_etag_changes_after_out_of_band_edit(service: NoteService) -> None:
    note, _ = service.create(NoteCreate(title="Edited", body="original"), now=NOW)
    before = service.get_etag(note.path)
    abs_path = service.settings.vault_path / note.path
    abs_path.write_text(abs_path.read_text(encoding="utf-8") + "\nmore\n", encoding="utf-8")
    service.reconcile()
    after = service.get_etag(note.path)
    assert after != before
    assert after == _file_hash(service, note.path)


def test_etag_for_missing_raises(service: NoteService) -> None:
    with pytest.raises(NoteNotFound):
        service.get_etag("nope.md")
