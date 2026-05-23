"""``bartleby-export-openapi <path>``: write the FastAPI OpenAPI schema as
canonical JSON (sorted keys, fixed indent, trailing newline) so the committed
contract is byte-stable and the CI drift gate is deterministic.
"""

from __future__ import annotations

import json
import sys

from .app import create_app


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        sys.stderr.write("usage: bartleby-export-openapi <path>\n")
        return 2
    schema = create_app().openapi()
    with open(args[0], "w", encoding="utf-8") as fh:
        json.dump(schema, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    return 0
