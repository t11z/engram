"""Serialize/deserialize a note ``.md`` file (YAML frontmatter + Markdown body).

Parsing uses ``python-frontmatter`` and is *tolerant*: a note need not carry
``id``, ``title``, or timestamps. ``id`` stays optional (path is the canonical
handle); ``title`` is derived from the first heading or the filename; timestamps
fall back to the file's mtime. Writing is hand-rolled with a fixed field order
and pre-formatted RFC 3339 timestamps so output is deterministic.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path

import frontmatter
import yaml
from pydantic import ValidationError

from .errors import InvalidNote
from .models import Note, to_rfc3339

FRONTMATTER_FIELD_ORDER = [
    "id",
    "title",
    "created_at",
    "updated_at",
    "tags",
    "source_url",
    "idempotency_key",
]

_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)


def _derive_title(body: str, path: str) -> str:
    """First Markdown heading, else the filename stem."""
    match = _HEADING.search(body)
    if match:
        return match.group(1).strip()
    return Path(path).stem or "Untitled"


def parse_note(text: str, path: str, *, mtime: datetime | None = None) -> Note:
    """Parse note file text into a ``Note``. Raises ``InvalidNote`` on failure.

    Missing ``title`` is derived (heading, then filename); missing timestamps
    fall back to ``mtime`` (the file's modification time). ``id`` may be absent.
    """
    try:
        post = frontmatter.loads(text)
    except yaml.YAMLError as exc:
        raise InvalidNote(path, f"invalid YAML frontmatter: {exc}") from exc
    meta = dict(post.metadata)

    if not meta.get("title"):
        meta["title"] = _derive_title(post.content, path)

    created = meta.get("created_at")
    updated = meta.get("updated_at")
    if created is None and updated is None:
        if mtime is None:
            raise InvalidNote(path, "note has no timestamps and no file mtime to fall back on")
        meta["created_at"] = meta["updated_at"] = mtime
    elif created is None:
        meta["created_at"] = updated
    elif updated is None:
        meta["updated_at"] = created

    try:
        return Note(**meta, body=post.content, path=path)
    except ValidationError as exc:
        raise InvalidNote(path, str(exc)) from exc


def dump_note(note: Note) -> str:
    """Serialize a ``Note`` to deterministic file text with an ordered header.

    ``id`` is emitted only when present (engram never injects an id into a note
    that does not have one). Unknown keys are preserved after the known fields.
    """
    header: dict[str, object] = {}
    if note.id is not None:
        header["id"] = note.id
    header["title"] = note.title
    header["created_at"] = to_rfc3339(note.created_at)
    header["updated_at"] = to_rfc3339(note.updated_at)
    header["tags"] = list(note.tags)
    if note.source_url is not None:
        header["source_url"] = note.source_url
    if note.idempotency_key is not None:
        header["idempotency_key"] = note.idempotency_key
    # Unknown keys (e.g. properties added by another editor) are preserved after
    # the known fields, in their original order, so a shared vault round-trips.
    for key, value in (note.model_extra or {}).items():
        header[key] = value

    yaml_header = yaml.safe_dump(
        header,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip("\n")
    body = note.body.rstrip("\n")
    return f"---\n{yaml_header}\n---\n\n{body}\n"


def read_note_file(abs_path: Path, rel_path: str) -> Note:
    mtime = datetime.fromtimestamp(abs_path.stat().st_mtime, tz=UTC)
    return parse_note(abs_path.read_text(encoding="utf-8"), rel_path, mtime=mtime)


def write_note_file(abs_path: Path, note: Note) -> None:
    """Atomically write a note to disk (temp file + ``os.replace``)."""
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = abs_path.with_name(abs_path.name + ".tmp")
    tmp_path.write_text(dump_note(note), encoding="utf-8")
    os.replace(tmp_path, abs_path)
