"""Wikilink / Markdown-link / inline-tag parsing and link resolution.

Pure functions over note body text — no I/O. This is distinct from
``link_extractor.py``, which fetches *remote URLs*; here we parse the *internal*
graph a note describes: ``[[wikilinks]]``, ``![[embeds]]``, standard Markdown
links, and inline ``#tags``.

Link targets are resolved against the set of note paths in the vault using the
portable convention "exact relative path, else basename with a shortest-path
tiebreak". Markdown links are resolved relative to the linking note's folder.
Resolution is deliberately separated from extraction so the index can extract
once (on write) and re-resolve cheaply against the current note set.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Iterable
from dataclasses import dataclass

WIKILINK = "wikilink"
EMBED = "embed"
MARKDOWN = "markdown"

# Strip fenced code blocks and inline code before scanning so code samples do not
# produce phantom links or tags.
_FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]*`")

_EMBED = re.compile(r"!\[\[([^\]\n]+)\]\]")
_WIKILINK = re.compile(r"(?<!!)\[\[([^\]\n]+)\]\]")
# Markdown link [text](target); the negative lookbehind drops image embeds ![](…).
_MD_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_INLINE_TAG = re.compile(r"(?:^|(?<=\s))#([A-Za-z_][\w\-/]*)")


@dataclass(frozen=True)
class ParsedLink:
    """A single outgoing reference found in a note body.

    ``target`` is the cleaned reference (wiki alias and ``#heading`` stripped; for
    Markdown links, the raw href). ``type`` is one of ``wikilink``/``embed``/
    ``markdown``.
    """

    target: str
    type: str


def _strip_code(text: str) -> str:
    text = _FENCED_CODE.sub(" ", text)
    return _INLINE_CODE.sub(" ", text)


def _clean_wiki_target(raw: str) -> str:
    """Drop a ``|alias`` and a ``#heading``/``#^block`` from a wikilink target."""
    target = raw.split("|", 1)[0]
    target = target.split("#", 1)[0]
    return target.strip()


def extract_links(body: str) -> list[ParsedLink]:
    """Return the outgoing links in ``body``, de-duplicated by (target, type),
    in first-seen order. Embeds and wikilinks with an empty target (e.g. a bare
    ``[[#heading]]`` self-reference) are skipped.
    """
    text = _strip_code(body)
    seen: set[tuple[str, str]] = set()
    links: list[ParsedLink] = []

    def add(target: str, link_type: str) -> None:
        target = target.strip()
        if not target:
            return
        key = (target, link_type)
        if key in seen:
            return
        seen.add(key)
        links.append(ParsedLink(target=target, type=link_type))

    for match in _EMBED.finditer(text):
        add(_clean_wiki_target(match.group(1)), EMBED)
    for match in _WIKILINK.finditer(text):
        add(_clean_wiki_target(match.group(1)), WIKILINK)
    for match in _MD_LINK.finditer(text):
        add(match.group(1), MARKDOWN)
    return links


def extract_inline_tags(body: str) -> list[str]:
    """Return inline ``#tags`` (without the ``#``), de-duplicated in first-seen
    order. Heading markers and purely numeric ``#123`` are not matched.
    """
    text = _strip_code(body)
    seen: set[str] = set()
    tags: list[str] = []
    for match in _INLINE_TAG.finditer(text):
        tag = match.group(1)
        if tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tags


def _norm(path: str) -> str:
    """Lowercase, drop a leading ``./`` and a trailing ``.md``, unify slashes."""
    path = path.strip().replace("\\", "/")
    if path.startswith("./"):
        path = path[2:]
    if path.lower().endswith(".md"):
        path = path[:-3]
    return path.lower()


def _shortest(paths: list[str]) -> str:
    """Deterministic tiebreak for an ambiguous basename: fewest path segments,
    then shortest string, then lexicographic.
    """
    return min(paths, key=lambda p: (p.count("/"), len(p), p))


class LinkResolver:
    """Resolves raw link targets to vault-relative note paths.

    Built once from the current set of note paths; ``resolve`` is then O(1) per
    link. Only Markdown notes are resolution candidates (attachments are out of
    scope here).
    """

    def __init__(self, paths: Iterable[str]) -> None:
        self._by_relpath: dict[str, str] = {}
        self._by_basename: dict[str, list[str]] = {}
        for path in paths:
            self._by_relpath.setdefault(_norm(path), path)
            base = _norm(posixpath.basename(path))
            self._by_basename.setdefault(base, []).append(path)

    def resolve(self, link_type: str, target: str, src_path: str) -> str | None:
        if link_type == MARKDOWN:
            return self._resolve_markdown(target, src_path)
        return self._resolve_wiki(target)

    def _resolve_wiki(self, target: str) -> str | None:
        key = _norm(target)
        if not key:
            return None
        if "/" in key:
            return self._by_relpath.get(key)
        candidates = self._by_basename.get(key)
        if candidates:
            return _shortest(candidates)
        return self._by_relpath.get(key)

    def _resolve_markdown(self, href: str, src_path: str) -> str | None:
        if "://" in href or href.startswith(("#", "mailto:", "tel:", "data:", "/")):
            return None
        clean = href.split("#", 1)[0].split("?", 1)[0]
        if not clean:
            return None
        joined = posixpath.normpath(posixpath.join(posixpath.dirname(src_path), clean))
        return self._by_relpath.get(_norm(joined))
