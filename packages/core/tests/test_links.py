"""Unit tests for the wikilink / Markdown-link / inline-tag parser and resolver."""

from __future__ import annotations

from engram_core.links import (
    EMBED,
    MARKDOWN,
    WIKILINK,
    LinkResolver,
    extract_inline_tags,
    extract_links,
)


def _targets(body: str) -> list[tuple[str, str]]:
    return [(link.target, link.type) for link in extract_links(body)]


def test_extract_wikilink_variants() -> None:
    body = "See [[Alpha]], [[Beta|the beta]], and [[Gamma#section]]."
    assert _targets(body) == [("Alpha", WIKILINK), ("Beta", WIKILINK), ("Gamma", WIKILINK)]


def test_extract_embed_distinct_from_wikilink() -> None:
    assert _targets("![[diagram.png]] and [[Note]]") == [
        ("diagram.png", EMBED),
        ("Note", WIKILINK),
    ]


def test_extract_markdown_links_and_images() -> None:
    body = "[a](notes/a.md) [ext](https://example.com) ![img](pic.png)"
    # The image (![img](pic.png)) is excluded; the external URL is kept as a raw target.
    assert _targets(body) == [
        ("notes/a.md", MARKDOWN),
        ("https://example.com", MARKDOWN),
    ]


def test_extract_dedupes_and_skips_empty_heading_link() -> None:
    assert _targets("[[Alpha]] [[Alpha]] [[#only-heading]]") == [("Alpha", WIKILINK)]


def test_code_is_ignored() -> None:
    body = "real [[Alpha]]\n\n```\n[[InFence]] #notatag\n```\n\ninline `[[InCode]]`"
    assert _targets(body) == [("Alpha", WIKILINK)]
    assert extract_inline_tags(body) == []


def test_inline_tags() -> None:
    body = "## Heading is not a tag\n#ops and #db/postgres and #ops again, not #123 or C#"
    assert extract_inline_tags(body) == ["ops", "db/postgres"]


def test_resolver_basename_and_relpath() -> None:
    resolver = LinkResolver(["Alpha.md", "sub/Beta.md"])
    assert resolver.resolve(WIKILINK, "Alpha", "x.md") == "Alpha.md"
    assert resolver.resolve(WIKILINK, "Beta", "x.md") == "sub/Beta.md"
    assert resolver.resolve(WIKILINK, "sub/Beta", "x.md") == "sub/Beta.md"
    assert resolver.resolve(WIKILINK, "Missing", "x.md") is None


def test_resolver_ambiguous_basename_prefers_shortest_path() -> None:
    resolver = LinkResolver(["Note.md", "deep/nested/Note.md"])
    assert resolver.resolve(WIKILINK, "Note", "x.md") == "Note.md"


def test_resolver_markdown_is_relative_to_source_dir() -> None:
    resolver = LinkResolver(["folder/a.md", "b.md"])
    assert resolver.resolve(MARKDOWN, "../b.md", "folder/a.md") == "b.md"
    assert resolver.resolve(MARKDOWN, "a.md", "folder/x.md") == "folder/a.md"


def test_resolver_markdown_ignores_external_and_anchors() -> None:
    resolver = LinkResolver(["a.md"])
    assert resolver.resolve(MARKDOWN, "https://example.com", "a.md") is None
    assert resolver.resolve(MARKDOWN, "mailto:x@y.z", "a.md") is None
    assert resolver.resolve(MARKDOWN, "#section", "a.md") is None
