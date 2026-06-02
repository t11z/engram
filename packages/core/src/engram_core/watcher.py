"""Filesystem watcher for live reconciliation (ADR-0011).

The vault may change underneath a running server — another editor saves a note,
or a sync tool (Syncthing, iCloud, git) lands a batch of files. ``VaultWatcher``
observes the vault tree and fires a debounced callback (typically
``NoteService.reconcile``) so the index and link graph catch up promptly instead
of only at startup. A burst of events (a sync writing many files) is coalesced
into a single refresh by the debounce window.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

logger = logging.getLogger("engram.watcher")


class VaultWatcher:
    def __init__(
        self, vault_path: Path, on_change: Callable[[], None], *, debounce: float = 0.5
    ) -> None:
        self.vault_path = vault_path
        self.on_change = on_change
        self.debounce = debounce
        self._observer: BaseObserver | None = None
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        observer = Observer()
        observer.schedule(_Handler(self._schedule), str(self.vault_path), recursive=True)
        observer.daemon = True
        observer.start()
        self._observer = observer

    def stop(self) -> None:
        observer, self._observer = self._observer, None
        if observer is not None:
            observer.stop()
            observer.join(timeout=2)
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def _schedule(self) -> None:
        """Restart the debounce timer; the callback fires once events go quiet."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        try:
            self.on_change()
        except Exception:  # pragma: no cover - a refresh must never crash the server
            logger.exception("vault reconcile after a filesystem change failed")


class _Handler(FileSystemEventHandler):
    """Schedules a refresh for any Markdown create/modify/delete/move."""

    def __init__(self, schedule: Callable[[], None]) -> None:
        self._schedule = schedule

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        paths = (str(getattr(event, "src_path", "")), str(getattr(event, "dest_path", "")))
        if any(path.endswith(".md") for path in paths):
            self._schedule()
