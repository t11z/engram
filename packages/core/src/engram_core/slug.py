"""Filename slug generation.

In the convention-based model the vault-relative path is the canonical handle, so
a note's filename is derived from its title (``<slug>.md``), not a fixed date
prefix. Slug collisions get a numeric suffix; identity does not depend on the
filename.
"""

from __future__ import annotations

import re
import unicodedata

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(title: str, max_len: int = 60) -> str:
    """Lowercase ASCII slug: transliterate, collapse to single hyphens, trim."""
    normalized = unicodedata.normalize("NFKD", title)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = _NON_SLUG.sub("-", ascii_text).strip("-")
    slug = slug[:max_len].strip("-")
    return slug or "untitled"


def build_filename(slug: str, suffix: int | None = None) -> str:
    if suffix is not None:
        return f"{slug}-{suffix}.md"
    return f"{slug}.md"
