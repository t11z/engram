"""Filename slug generation. Identity is the ULID; the filename is a human-friendly
``YYYY-MM-DD-<slug>.md`` for browsing, with a short suffix on collision.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(title: str, max_len: int = 60) -> str:
    """Lowercase ASCII slug: transliterate, collapse to single hyphens, trim."""
    normalized = unicodedata.normalize("NFKD", title)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = _NON_SLUG.sub("-", ascii_text).strip("-")
    slug = slug[:max_len].strip("-")
    return slug or "untitled"


def short_suffix(note_id: str) -> str:
    """Deterministic cosmetic suffix derived from the ULID's tail."""
    return note_id[-4:].lower()


def build_filename(created_at: datetime, slug: str, suffix: str | None = None) -> str:
    date = created_at.astimezone(UTC).strftime("%Y-%m-%d")
    if suffix:
        return f"{date}-{slug}-{suffix}.md"
    return f"{date}-{slug}.md"
