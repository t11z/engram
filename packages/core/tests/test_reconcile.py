import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

from engram_core.config import Settings
from engram_core.reindex import main as reindex_main
from engram_core.service import NoteService

LIVE_COUNT = 5
TRASH_COUNT = 1


@pytest.fixture
def service(temp_vault: Path, tmp_path: Path) -> Iterator[NoteService]:
    svc = NoteService(Settings(vault_path=temp_vault, index_path=tmp_path / "index.db"))
    svc.startup()
    yield svc
    svc.close()


def test_startup_indexes_sample_vault(service: NoteService) -> None:
    live, _ = service.list_notes(limit=50)
    trash, _ = service.list_trash(limit=50)
    assert len(live) == LIVE_COUNT
    assert len(trash) == TRASH_COUNT
    assert [h.id for h in service.search("postgres")]


def test_reconcile_picks_up_out_of_band_edit(service: NoteService, temp_vault: Path) -> None:
    assert service.search("zzqqx") == []
    path = temp_vault / "2026-02-15-reading-list.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nzzqqx marker\n", encoding="utf-8")
    service.reconcile()
    assert [h.id for h in service.search("zzqqx")]


def test_reconcile_removes_deleted_file(service: NoteService, temp_vault: Path) -> None:
    (temp_vault / "2026-03-01-meeting-notes.md").unlink()
    report = service.reconcile()
    assert report.removed == 1
    live, _ = service.list_notes(limit=50)
    assert len(live) == LIVE_COUNT - 1


def test_reconcile_detects_out_of_band_trash(service: NoteService, temp_vault: Path) -> None:
    src = temp_vault / "2026-04-20-cafe-resume.md"
    shutil.move(str(src), str(temp_vault / ".trash" / src.name))
    service.reconcile()
    live, _ = service.list_notes(limit=50)
    trash, _ = service.list_trash(limit=50)
    assert len(live) == LIVE_COUNT - 1
    assert len(trash) == TRASH_COUNT + 1


def test_reindex_is_reproducible(service: NoteService) -> None:
    before_live = [s.id for s in service.list_notes(limit=50)[0]]
    before_search = [(h.id, round(h.score, 6), h.snippet) for h in service.search("postgres")]
    report = service.reindex()
    after_live = [s.id for s in service.list_notes(limit=50)[0]]
    after_search = [(h.id, round(h.score, 6), h.snippet) for h in service.search("postgres")]
    assert report.live == LIVE_COUNT
    assert report.trash == TRASH_COUNT
    assert before_live == after_live
    assert before_search == after_search


def test_reindex_cli(temp_vault: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = reindex_main(["--vault", str(temp_vault), "--index", str(tmp_path / "cli-index.db")])
    assert code == 0
    out = capsys.readouterr().out
    assert "Reindexed 5 live note(s) and 1 trashed note(s)." in out
