from datetime import UTC, datetime

from engram_core.ids import is_valid_ulid, new_ulid, ulid_timestamp
from engram_core.slug import build_filename, short_suffix, slugify


def test_new_ulid_is_valid_and_26_chars() -> None:
    value = new_ulid()
    assert len(value) == 26
    assert is_valid_ulid(value)


def test_is_valid_ulid_rejects_garbage() -> None:
    assert not is_valid_ulid("not-a-ulid")
    assert not is_valid_ulid("")


def test_ulid_timestamp_is_recent_and_utc() -> None:
    before = datetime.now(UTC)
    ts = ulid_timestamp(new_ulid())
    assert ts.tzinfo is not None
    assert abs((ts - before).total_seconds()) < 5


def test_slugify_basic() -> None:
    assert slugify("Postgres Backup Cmd") == "postgres-backup-cmd"


def test_slugify_unicode_transliterates() -> None:
    assert slugify("Café ☕ 2026!") == "cafe-2026"


def test_slugify_empty_falls_back() -> None:
    assert slugify("   ") == "untitled"
    assert slugify("!!!") == "untitled"


def test_slugify_respects_max_len() -> None:
    assert slugify("a" * 100, max_len=10) == "a" * 10


def test_short_suffix_deterministic() -> None:
    ulid = "01J0000000000000000000ABCD"
    assert short_suffix(ulid) == "abcd"


def test_build_filename() -> None:
    dt = datetime(2026, 1, 10, 8, 30, tzinfo=UTC)
    assert build_filename(dt, "hi") == "2026-01-10-hi.md"
    assert build_filename(dt, "hi", "abcd") == "2026-01-10-hi-abcd.md"
