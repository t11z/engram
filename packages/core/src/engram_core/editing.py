"""Pure Markdown body edits used by in-place editing (no I/O).

Kept separate from the service so the text transforms are unit-testable on their
own. The service reads a note, applies one of these to the body, and writes it
back.
"""

from __future__ import annotations

import re

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def append_body(body: str, text: str) -> str:
    """Append ``text`` as a new block, separated by a blank line."""
    base = body.rstrip("\n")
    snippet = text.strip("\n")
    if not snippet:
        return body if body.endswith("\n") or not body else body + "\n"
    if not base:
        return snippet + "\n"
    return f"{base}\n\n{snippet}\n"


def replace_section(body: str, heading: str, content: str) -> str:
    """Replace the body of the first section whose heading text matches ``heading``
    (any level; the heading line is kept). If no such heading exists, append a new
    level-2 section with that heading.
    """
    target = heading.strip().lstrip("#").strip()
    snippet = content.strip("\n")
    lines = body.splitlines()

    start = level = None
    for i, line in enumerate(lines):
        match = _HEADING.match(line)
        if match and match.group(2).strip() == target:
            start, level = i, len(match.group(1))
            break

    if start is None or level is None:
        base = body.rstrip("\n")
        section = f"## {target}\n\n{snippet}\n" if snippet else f"## {target}\n"
        return f"{base}\n\n{section}" if base else section

    end = len(lines)
    for j in range(start + 1, len(lines)):
        match = _HEADING.match(lines[j])
        if match and len(match.group(1)) <= level:
            end = j
            break

    block = [lines[start]]
    if snippet:
        block += ["", *snippet.splitlines()]
    tail = lines[end:]
    rebuilt = lines[:start] + block + (["", *tail] if tail else [])
    return "\n".join(rebuilt).rstrip("\n") + "\n"
