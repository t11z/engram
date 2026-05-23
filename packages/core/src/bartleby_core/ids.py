"""ULID helpers. The ULID is a note's canonical, immutable identity."""

from __future__ import annotations

from datetime import datetime

from ulid import ULID


def new_ulid() -> str:
    """Generate a new canonical 26-character ULID string."""
    return str(ULID())


def is_valid_ulid(value: str) -> bool:
    try:
        ULID.from_str(value)
    except (ValueError, TypeError):
        return False
    return True


def ulid_timestamp(value: str) -> datetime:
    """Return the timezone-aware UTC creation time encoded in a ULID."""
    return ULID.from_str(value).datetime
