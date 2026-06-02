"""Serialize/deserialize a note ``.md`` file (YAML frontmatter + Markdown body).

Parsing uses ``python-frontmatter``. Writing is hand-rolled with a fixed field
order and pre-formatted RFC 3339 timestamps so output is deterministic (stable git
diffs, reproducible reindex) — PyYAML's default dump would otherwise sort keys and
coerce timestamps.
"""

from __future__ import annotations

import os
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


def parse_note(text: str, path: str) -> Note:
    """Parse note file text into a ``Note``. Raises ``InvalidNote`` on failure."""
    try:
        post = frontmatter.loads(text)
    except yaml.YAMLError as exc:
        raise InvalidNote(path, f"invalid YAML frontmatter: {exc}") from exc
    metadata = dict(post.metadata)
    try:
        return Note(**metadata, body=post.content, path=path)
    except ValidationError as exc:
        raise InvalidNote(path, str(exc)) from exc


def dump_note(note: Note) -> str:
    """Serialize a ``Note`` to deterministic file text with an ordered header."""
    header: dict[str, object] = {
        "id": note.id,
        "title": note.title,
        "created_at": to_rfc3339(note.created_at),
        "updated_at": to_rfc3339(note.updated_at),
        "tags": list(note.tags),
    }
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
    return parse_note(abs_path.read_text(encoding="utf-8"), rel_path)


def write_note_file(abs_path: Path, note: Note) -> None:
    """Atomically write a note to disk (temp file + ``os.replace``)."""
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = abs_path.with_name(abs_path.name + ".tmp")
    tmp_path.write_text(dump_note(note), encoding="utf-8")
    os.replace(tmp_path, abs_path)
