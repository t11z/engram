from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from engram_core.errors import NoteNotFound, NoteNotInTrash
from engram_core.models import Note
from engram_core.store import VaultStore

NOW = datetime(2026, 5, 10, 12, 0, tzinfo=UTC)


def _note(title: str, *, note_id: str | None = None, path: str = "") -> Note:
    dt = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    return Note(
        id=note_id,
        title=title,
        created_at=dt,
        updated_at=dt,
        body=f"body of {title}",
        path=path,
    )


@pytest.fixture
def store(tmp_path: Path) -> VaultStore:
    s = VaultStore(tmp_path / "vault")
    s.ensure_layout()
    return s


def test_write_assigns_slug_filename(store: VaultStore) -> None:
    stored = store.write(_note("Hello World"))
    assert stored.path == "hello-world.md"
    assert stored.id is None
    assert (store.vault_path / stored.path).exists()


def test_write_then_read_by_path(store: VaultStore) -> None:
    stored = store.write(_note("Hello"))
    assert store.read(stored.path).title == "Hello"


def test_read_missing_raises(store: VaultStore) -> None:
    with pytest.raises(NoteNotFound):
        store.read("nope.md")


def test_filename_collision_gets_numeric_suffix(store: VaultStore) -> None:
    a = store.write(_note("Same Title"))
    b = store.write(_note("Same Title"))
    assert a.path == "same-title.md"
    assert b.path == "same-title-2.md"


def test_write_at_explicit_path_and_nested(store: VaultStore) -> None:
    stored = store.write(_note("Nested", path="sub/dir/note.md"))
    assert stored.path == "sub/dir/note.md"
    assert store.read("sub/dir/note.md").title == "Nested"


def test_path_for_id_alias(store: VaultStore) -> None:
    store.write(_note("Aliased", note_id="01KSB998H8WTTDZCMR8C67KBR7"))
    assert store.path_for_id("01KSB998H8WTTDZCMR8C67KBR7") == "aliased.md"
    assert store.path_for_id("missing") is None


def test_iter_notes_recurses_and_skips_dotfolders(store: VaultStore) -> None:
    store.write(_note("One"))
    store.write(_note("Two", path="sub/two.md"))
    store.move_to_trash("one.md", NOW)  # goes under .trash/, must be skipped by iter_notes
    store.write(_note("Three"))
    assert {n.title for n in store.iter_notes()} == {"Two", "Three"}


def test_write_leaves_no_tmp_file(store: VaultStore) -> None:
    store.write(_note("Hello"))
    assert list(store.vault_path.rglob("*.tmp")) == []


def test_move_to_trash_then_gone(store: VaultStore) -> None:
    stored = store.write(_note("Doomed"))
    trash_rel = store.move_to_trash(stored.path, NOW)
    assert trash_rel == ".trash/doomed.md"
    with pytest.raises(NoteNotFound):
        store.read(stored.path)
    assert [n.path for n in store.iter_trash()] == [".trash/doomed.md"]


def test_move_to_trash_sets_deletion_mtime(store: VaultStore) -> None:
    stored = store.write(_note("Doomed"))
    trash_rel = store.move_to_trash(stored.path, NOW)
    assert (store.vault_path / trash_rel).stat().st_mtime == pytest.approx(NOW.timestamp())


def test_move_to_trash_missing_raises(store: VaultStore) -> None:
    with pytest.raises(NoteNotFound):
        store.move_to_trash("nope.md", NOW)


def test_restore_round_trip(store: VaultStore) -> None:
    stored = store.write(_note("Comeback"))
    trash_rel = store.move_to_trash(stored.path, NOW)
    restored = store.restore(trash_rel)
    assert restored.path == "comeback.md"
    assert (store.vault_path / "comeback.md").exists()
    assert list(store.iter_trash()) == []


def test_restore_preserves_subfolder(store: VaultStore) -> None:
    store.write(_note("Nested", path="sub/nested.md"))
    trash_rel = store.move_to_trash("sub/nested.md", NOW)
    assert trash_rel == ".trash/sub/nested.md"
    restored = store.restore(trash_rel)
    assert restored.path == "sub/nested.md"


def test_restore_non_trashed_raises(store: VaultStore) -> None:
    with pytest.raises(NoteNotInTrash):
        store.restore(".trash/missing.md")


def test_purge_expired_removes_only_old(store: VaultStore) -> None:
    store.write(_note("Old"))
    store.write(_note("Fresh"))
    store.move_to_trash("old.md", NOW - timedelta(days=40))
    store.move_to_trash("fresh.md", NOW - timedelta(days=2))
    purged = store.purge_expired(retention_days=30, now=NOW)
    assert purged == [".trash/old.md"]
    assert {n.path for n in store.iter_trash()} == {".trash/fresh.md"}


def test_trash_filename_collision_gets_suffix(store: VaultStore) -> None:
    store.write(_note("Dup"))
    store.move_to_trash("dup.md", NOW)
    store.write(_note("Dup"))  # root "dup.md" is free again
    store.move_to_trash("dup.md", NOW)
    assert len(list(store.trash_dir.rglob("*.md"))) == 2
