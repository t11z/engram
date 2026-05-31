from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from engram_core.errors import NoteNotFound, NoteNotInTrash
from engram_core.models import Note
from engram_core.store import VaultStore


def _note(note_id: str, title: str, created: str = "2026-05-01T10:00:00Z") -> Note:
    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
    return Note(
        id=note_id,
        title=title,
        created_at=dt,
        updated_at=dt,
        body=f"body of {title}",
        path="",
    )


@pytest.fixture
def store(tmp_path: Path) -> VaultStore:
    s = VaultStore(tmp_path / "vault")
    s.ensure_layout()
    return s


def test_write_assigns_dated_slug_filename(store: VaultStore) -> None:
    stored = store.write(_note("01KSB998H8WTTDZCMR8C67KBR7", "Hello World"))
    assert stored.path == "2026-05-01-hello-world.md"
    assert (store.vault_path / stored.path).exists()


def test_write_then_read_by_id(store: VaultStore) -> None:
    store.write(_note("01KSB998H8WTTDZCMR8C67KBR7", "Hello"))
    got = store.read("01KSB998H8WTTDZCMR8C67KBR7")
    assert got.title == "Hello"


def test_read_missing_raises(store: VaultStore) -> None:
    with pytest.raises(NoteNotFound):
        store.read("01KSB998H8WTTDZCMR8C67KBR7")


def test_title_edit_renames_keeps_id_and_date(store: VaultStore) -> None:
    note = store.write(_note("01KSB998H8WTTDZCMR8C67KBR7", "First Title"))
    updated = note.model_copy(update={"title": "Second Title"})
    stored = store.write(updated)
    assert stored.path == "2026-05-01-second-title.md"
    assert not (store.vault_path / "2026-05-01-first-title.md").exists()
    assert store.read("01KSB998H8WTTDZCMR8C67KBR7").title == "Second Title"
    # exactly one live file remains
    assert len(list(store.vault_path.glob("*.md"))) == 1


def test_filename_collision_gets_suffix(store: VaultStore) -> None:
    a = store.write(_note("01KSB998H8WTTDZCMR8C67KBR7", "Same Title"))
    b = store.write(_note("01KSB998H9N7Z7W8S5WVDKDCW5", "Same Title"))
    assert a.path == "2026-05-01-same-title.md"
    assert a.path != b.path
    assert b.path.startswith("2026-05-01-same-title-")


def test_rewriting_same_note_keeps_filename(store: VaultStore) -> None:
    a = store.write(_note("01KSB998H8WTTDZCMR8C67KBR7", "Stable"))
    again = store.write(a.model_copy(update={"body": "changed"}))
    assert again.path == a.path
    assert len(list(store.vault_path.glob("*.md"))) == 1


def test_iter_notes_lists_all_live(store: VaultStore) -> None:
    store.write(_note("01KSB998H8WTTDZCMR8C67KBR7", "One"))
    store.write(_note("01KSB998H9N7Z7W8S5WVDKDCW5", "Two"))
    ids = {n.id for n in store.iter_notes()}
    assert ids == {"01KSB998H8WTTDZCMR8C67KBR7", "01KSB998H9N7Z7W8S5WVDKDCW5"}


def test_write_leaves_no_tmp_file(store: VaultStore) -> None:
    store.write(_note("01KSB998H8WTTDZCMR8C67KBR7", "Hello"))
    assert list(store.vault_path.glob("*.tmp")) == []


NOW = datetime(2026, 5, 10, 12, 0, tzinfo=UTC)


def test_move_to_trash_then_not_live(store: VaultStore) -> None:
    store.write(_note("01KSB998H8WTTDZCMR8C67KBR7", "Doomed"))
    store.move_to_trash("01KSB998H8WTTDZCMR8C67KBR7", NOW)
    assert not store.exists("01KSB998H8WTTDZCMR8C67KBR7")
    trashed = list(store.iter_trash())
    assert [n.id for n in trashed] == ["01KSB998H8WTTDZCMR8C67KBR7"]
    assert trashed[0].path.startswith(".trash/")


def test_move_to_trash_sets_deletion_mtime(store: VaultStore) -> None:
    store.write(_note("01KSB998H8WTTDZCMR8C67KBR7", "Doomed"))
    dest = store.move_to_trash("01KSB998H8WTTDZCMR8C67KBR7", NOW)
    assert dest.stat().st_mtime == pytest.approx(NOW.timestamp())


def test_move_to_trash_missing_raises(store: VaultStore) -> None:
    with pytest.raises(NoteNotFound):
        store.move_to_trash("01KSB998H8WTTDZCMR8C67KBR7", NOW)


def test_restore_round_trip(store: VaultStore) -> None:
    note = store.write(_note("01KSB998H8WTTDZCMR8C67KBR7", "Comeback"))
    store.move_to_trash(note.id, NOW)
    restored = store.restore(note.id)
    assert restored.path == "2026-05-01-comeback.md"
    assert store.exists(note.id)
    assert list(store.iter_trash()) == []


def test_restore_non_trashed_raises(store: VaultStore) -> None:
    with pytest.raises(NoteNotInTrash):
        store.restore("01KSB998H8WTTDZCMR8C67KBR7")


def test_purge_expired_removes_only_old(store: VaultStore) -> None:
    store.write(_note("01KSB998H8WTTDZCMR8C67KBR7", "Old"))
    store.write(_note("01KSB998H9N7Z7W8S5WVDKDCW5", "Fresh"))
    store.move_to_trash("01KSB998H8WTTDZCMR8C67KBR7", NOW - timedelta(days=40))
    store.move_to_trash("01KSB998H9N7Z7W8S5WVDKDCW5", NOW - timedelta(days=2))
    purged = store.purge_expired(retention_days=30, now=NOW)
    assert purged == ["01KSB998H8WTTDZCMR8C67KBR7"]
    remaining = {n.id for n in store.iter_trash()}
    assert remaining == {"01KSB998H9N7Z7W8S5WVDKDCW5"}


def test_trash_filename_collision_gets_suffix(store: VaultStore) -> None:
    store.write(_note("01KSB998H8WTTDZCMR8C67KBR7", "Dup"))
    store.move_to_trash("01KSB998H8WTTDZCMR8C67KBR7", NOW)
    # a second note that resolves to the same filename, then trashed
    store.write(_note("01KSB998H9N7Z7W8S5WVDKDCW5", "Dup"))
    store.move_to_trash("01KSB998H9N7Z7W8S5WVDKDCW5", NOW)
    assert len(list(store.trash_dir.glob("*.md"))) == 2
