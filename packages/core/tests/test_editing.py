"""Pure Markdown body edit helpers."""

from __future__ import annotations

from engram_core.editing import append_body, replace_section


def test_append_to_empty_body() -> None:
    assert append_body("", "hello") == "hello\n"


def test_append_adds_blank_line() -> None:
    assert append_body("alpha\n", "beta") == "alpha\n\nbeta\n"


def test_replace_existing_section_keeps_others() -> None:
    body = "# Title\n\nintro\n\n## Notes\nold note\n\n## Other\nkeep me\n"
    out = replace_section(body, "Notes", "fresh note")
    assert "## Notes\n\nfresh note" in out
    assert "old note" not in out
    assert "## Other" in out and "keep me" in out


def test_replace_appends_when_heading_absent() -> None:
    out = replace_section("# Title\n\nbody\n", "References", "see [[x]]")
    assert out.endswith("## References\n\nsee [[x]]\n")


def test_replace_section_stops_at_same_or_higher_level() -> None:
    body = "## A\nold\n### sub of A\nkeep\n## B\nb\n"
    out = replace_section(body, "A", "new")
    assert "new" in out and "old" not in out
    # The same-level "## B" section is untouched; the deeper "### sub" under A is replaced.
    assert "## B" in out and "\nb\n" in out
    assert "keep" not in out
