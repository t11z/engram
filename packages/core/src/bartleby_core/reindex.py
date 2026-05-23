"""``python -m bartleby_core.reindex`` — rebuild the search index from the vault.

A minimal recovery entry point for use before the server exists. It claims no
user-facing command name; that is reserved for the server phase.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import Settings
from .service import NoteService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bartleby_core.reindex",
        description="Rebuild the Bartleby search index from the vault files.",
    )
    parser.add_argument("--vault", type=Path, default=None, help="Override BARTLEBY_VAULT_PATH.")
    parser.add_argument("--index", type=Path, default=None, help="Override BARTLEBY_INDEX_PATH.")
    args = parser.parse_args(argv)

    settings = Settings()
    updates: dict[str, object] = {}
    if args.vault is not None:
        updates["vault_path"] = args.vault
    if args.index is not None:
        updates["index_path"] = args.index
    if updates:
        settings = settings.model_copy(update=updates)

    service = NoteService(settings)
    service.store.ensure_layout()
    service.index.open()
    try:
        report = service.reindex()
    finally:
        service.close()
    print(f"Reindexed {report.live} live note(s) and {report.trash} trashed note(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
