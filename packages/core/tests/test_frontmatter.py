from datetime import UTC, datetime
from pathlib import Path

import pytest

from engram_core.errors import InvalidNote
from engram_core.frontmatter import (
    dump_note,
    parse_note,
    read_note_file,
    write_note_file,
)
from engram_core.models import Note, to_rfc3339


def test_parse_full_note(sample_vault_path: Path) -> None:
    name = "2026-01-10-postgres-backup.md"
    note = read_note_file(sample_vault_path / name, name)
    assert note.id == "01KSB998H8WTTDZCMR8C67KBR7"
    assert note.title == "Postgres backup command"
    assert note.tags == ["ops", "postgres"]
    assert note.source_url == "https://example.com/postgres-backup"
    assert note.idempotency_key == "seed-postgres-backup"
    assert "pg_dump" in note.body
    assert to_rfc3339(note.created_at) == "2026-01-10T08:30:00Z"
    assert note.path == name


def test_parse_minimal_note(sample_vault_path: Path) -> None:
    name = "2026-03-01-meeting-notes.md"
    note = read_note_file(sample_vault_path / name, name)
    assert note.tags == []
    assert note.source_url is None
    assert note.idempotency_key is None


def test_dump_is_idempotent_for_every_fixture(sample_vault_path: Path) -> None:
    for path in sorted(sample_vault_path.glob("*.md")):
        note = read_note_file(path, path.name)
        once = dump_note(note)
        twice = dump_note(parse_note(once, path.name))
        assert once == twice, f"dump not idempotent for {path.name}"


def test_dump_preserves_field_order() -> None:
    note = Note(
        id="01KSB998H8WTTDZCMR8C67KBR7",
        title="Hi",
        created_at=datetime(2026, 1, 10, 8, 30, tzinfo=UTC),
        updated_at=datetime(2026, 1, 10, 9, 0, tzinfo=UTC),
        tags=["a", "b"],
        source_url="https://e.x",
        idempotency_key="k",
        body="hello",
        path="x.md",
    )
    header = dump_note(note).split("---\n")[1]
    top_keys = [
        line.split(":", 1)[0]
        for line in header.splitlines()
        if line and not line.startswith((" ", "-"))
    ]
    assert top_keys == [
        "id",
        "title",
        "created_at",
        "updated_at",
        "tags",
        "source_url",
        "idempotency_key",
    ]


def test_dump_omits_none_optionals() -> None:
    note = Note(
        id="01KSB998H8WTTDZCMR8C67KBR9",
        title="Hi",
        created_at=datetime(2026, 3, 1, 14, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 1, 14, 0, tzinfo=UTC),
        body="hi",
        path="x.md",
    )
    text = dump_note(note)
    assert "source_url" not in text
    assert "idempotency_key" not in text
    assert "tags: []" in text


def test_unicode_preserved(sample_vault_path: Path) -> None:
    name = "2026-04-20-cafe-resume.md"
    note = read_note_file(sample_vault_path / name, name)
    assert "résumé" in note.title
    assert "日本語" in note.body


def test_malformed_yaml_raises() -> None:
    with pytest.raises(InvalidNote):
        parse_note("---\nid: [unclosed\n---\nbody\n", "bad.md")


def test_unknown_fields_preserved_and_round_trip() -> None:
    text = (
        "---\n"
        "id: 01KSB998H8WTTDZCMR8C67KBR7\n"
        "title: x\n"
        "created_at: '2026-01-10T08:30:00Z'\n"
        "updated_at: '2026-01-10T08:30:00Z'\n"
        "author: nope\n"
        "aliases:\n"
        "  - alt\n"
        "---\n\nbody\n"
    )
    note = parse_note(text, "extra.md")
    assert note.model_extra == {"author": "nope", "aliases": ["alt"]}
    once = dump_note(note)
    # Unknown keys survive, sit after the known fields, and round-trip idempotently.
    assert "author: nope" in once
    assert once.index("author") > once.index("tags:")
    assert dump_note(parse_note(once, "extra.md")) == once


def test_missing_required_field_raises() -> None:
    with pytest.raises(InvalidNote):
        parse_note("---\ntitle: x\n---\n\nbody\n", "bad.md")


def test_write_read_round_trip(tmp_path: Path) -> None:
    note = Note(
        id="01KSB998H8WTTDZCMR8C67KBR7",
        title="Title: with colon",
        created_at=datetime(2026, 1, 10, 8, 30, tzinfo=UTC),
        updated_at=datetime(2026, 1, 10, 8, 30, tzinfo=UTC),
        tags=["x"],
        body="line one\nline two",
        path="x.md",
    )
    path = tmp_path / "x.md"
    write_note_file(path, note)
    assert not (tmp_path / "x.md.tmp").exists()
    back = read_note_file(path, "x.md")
    assert back.title == note.title
    assert back.body == note.body
    assert dump_note(back) == dump_note(note)
