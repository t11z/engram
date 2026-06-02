"""Best-effort detection of vault settings from a well-known editor config.

Some editors keep a small JSON config inside the vault (e.g. an ``.obsidian/``
folder) describing where new notes, attachments, and daily notes live. When the
operator hasn't set the corresponding ``ENGRAM_*`` variable, we adopt these as
sensible defaults so engram drops into an existing vault without configuration.
This is detection, not a compatibility target — anything unrecognised is ignored.
"""

from __future__ import annotations

import json
from pathlib import Path


def _read_json(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def detect_vault_config(vault_path: Path) -> dict[str, str]:
    """Return any of ``new_note_dir``/``attachment_dir``/``daily_note_dir`` that a
    well-known editor config in the vault declares. Missing or unreadable config
    yields an empty dict.
    """
    config_dir = vault_path / ".obsidian"
    if not config_dir.is_dir():
        return {}

    detected: dict[str, str] = {}
    app = _read_json(config_dir / "app.json")

    attachment = app.get("attachmentFolderPath")
    if isinstance(attachment, str) and attachment and not attachment.startswith("./"):
        detected["attachment_dir"] = attachment.strip("/")

    if app.get("newFileLocation") == "folder":
        new_dir = app.get("newFileFolderPath")
        if isinstance(new_dir, str) and new_dir:
            detected["new_note_dir"] = new_dir.strip("/")

    daily = _read_json(config_dir / "daily-notes.json")
    daily_folder = daily.get("folder")
    if isinstance(daily_folder, str) and daily_folder:
        detected["daily_note_dir"] = daily_folder.strip("/")

    return detected
