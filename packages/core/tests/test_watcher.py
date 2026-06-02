"""VaultWatcher: event filtering, debounce coalescing, and live observation."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from watchdog.events import DirCreatedEvent, FileCreatedEvent, FileMovedEvent

from engram_core.watcher import VaultWatcher, _Handler


def test_handler_triggers_only_for_markdown() -> None:
    fired: list[int] = []
    handler = _Handler(lambda: fired.append(1))
    handler.on_any_event(FileCreatedEvent("/v/a.md"))
    handler.on_any_event(FileCreatedEvent("/v/a.txt"))
    handler.on_any_event(DirCreatedEvent("/v/dir"))
    handler.on_any_event(FileMovedEvent("/v/old.tmp", "/v/new.md"))  # rename into .md
    assert fired == [1, 1]


def test_debounce_coalesces_bursts(tmp_path: Path) -> None:
    calls: list[int] = []
    done = threading.Event()

    def cb() -> None:
        calls.append(1)
        done.set()

    watcher = VaultWatcher(tmp_path, cb, debounce=0.05)
    watcher._schedule()
    watcher._schedule()
    watcher._schedule()
    assert done.wait(2)
    time.sleep(0.1)
    assert calls == [1]  # a burst collapses to a single refresh


def test_observer_fires_on_new_markdown(tmp_path: Path) -> None:
    seen = threading.Event()
    watcher = VaultWatcher(tmp_path, seen.set, debounce=0.05)
    watcher.start()
    try:
        (tmp_path / "fresh.md").write_text("# hi\n", encoding="utf-8")
        assert seen.wait(5)
    finally:
        watcher.stop()
