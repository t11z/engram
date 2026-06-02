"""Phase E core: attachments, daily notes, and editor-config detection."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from engram_core.config import Settings
from engram_core.errors import NoteNotFound
from engram_core.service import NoteService

NOW = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def service(tmp_path: Path) -> Iterator[NoteService]:
    svc = NoteService(Settings(vault_path=tmp_path / "vault", index_path=tmp_path / "index.db"))
    svc.startup()
    yield svc
    svc.close()


# --- attachments ------------------------------------------------------------


def test_list_and_read_attachments(service: NoteService) -> None:
    vault = service.settings.vault_path
    (vault / "diagram.png").write_bytes(b"\x89PNG\r\nfake")
    (vault / "sub").mkdir()
    (vault / "sub" / "doc.pdf").write_bytes(b"%PDF-1.4 fake")
    (vault / "note.md").write_text("# not an attachment\n", encoding="utf-8")

    listed = {a.path: a for a in service.list_attachments()}
    assert set(listed) == {"diagram.png", "sub/doc.pdf"}  # the .md is excluded
    assert listed["diagram.png"].content_type == "image/png"
    assert listed["diagram.png"].size > 0

    data, content_type = service.read_attachment("diagram.png")
    assert data == b"\x89PNG\r\nfake"
    assert content_type == "image/png"


def test_read_attachment_refuses_traversal_notes_and_dotfolders(service: NoteService) -> None:
    with pytest.raises(NoteNotFound):
        service.read_attachment("../escape.txt")
    with pytest.raises(NoteNotFound):
        service.read_attachment("missing.png")
    # a Markdown file is a note, not an attachment
    (service.settings.vault_path / "x.md").write_text("# x\n", encoding="utf-8")
    with pytest.raises(NoteNotFound):
        service.read_attachment("x.md")


def test_attachment_dir_scopes_the_listing(tmp_path: Path) -> None:
    svc = NoteService(
        Settings(
            vault_path=tmp_path / "v",
            index_path=tmp_path / "i.db",
            attachment_dir="files",
        )
    )
    svc.startup()
    try:
        (svc.settings.vault_path / "files").mkdir(parents=True)
        (svc.settings.vault_path / "files" / "a.png").write_bytes(b"x")
        (svc.settings.vault_path / "loose.png").write_bytes(b"y")
        assert [a.path for a in svc.list_attachments()] == ["files/a.png"]
    finally:
        svc.close()


# --- daily notes ------------------------------------------------------------


def test_append_to_daily_note_creates_then_appends(service: NoteService) -> None:
    first = service.append_to_daily_note("first entry", now=NOW)
    assert first.path == "2026-05-01.md"
    assert "first entry" in first.body

    second = service.append_to_daily_note("second entry", now=NOW)
    assert second.path == "2026-05-01.md"
    assert "first entry" in second.body
    assert "second entry" in second.body


def test_daily_note_dir_is_honoured(tmp_path: Path) -> None:
    svc = NoteService(
        Settings(vault_path=tmp_path / "v", index_path=tmp_path / "i.db", daily_note_dir="journal")
    )
    svc.startup()
    try:
        note = svc.append_to_daily_note("hi", now=NOW)
        assert note.path == "journal/2026-05-01.md"
    finally:
        svc.close()


# --- editor-config detection ------------------------------------------------


def test_detects_dirs_from_editor_config(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    (vault / ".obsidian").mkdir(parents=True)
    (vault / ".obsidian" / "app.json").write_text(
        json.dumps(
            {
                "attachmentFolderPath": "files",
                "newFileLocation": "folder",
                "newFileFolderPath": "inbox",
            }
        ),
        encoding="utf-8",
    )
    (vault / ".obsidian" / "daily-notes.json").write_text(
        json.dumps({"folder": "journal"}), encoding="utf-8"
    )
    # Detection happens in the constructor; no index/startup needed.
    svc = NoteService(Settings(vault_path=vault, index_path=tmp_path / "i.db"))
    assert svc.attachment_dir == "files"
    assert svc.new_note_dir == "inbox"
    assert svc.daily_note_dir == "journal"


def test_explicit_settings_win_over_detection(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    (vault / ".obsidian").mkdir(parents=True)
    (vault / ".obsidian" / "app.json").write_text(
        json.dumps({"attachmentFolderPath": "files"}), encoding="utf-8"
    )
    svc = NoteService(
        Settings(vault_path=vault, index_path=tmp_path / "i.db", attachment_dir="my-files")
    )
    assert svc.attachment_dir == "my-files"
