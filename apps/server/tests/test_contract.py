import json
from pathlib import Path

from bartleby_server.app import create_app

ROOT = Path(__file__).resolve().parents[3]


def test_committed_openapi_is_current() -> None:
    schema = create_app().openapi()
    generated = json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    committed = (ROOT / "packages" / "contract" / "openapi.json").read_text(encoding="utf-8")
    assert generated == committed, "openapi.json is stale; run `bartleby-export-openapi`."
