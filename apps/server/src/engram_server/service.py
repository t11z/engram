"""Holds the single process-wide ``NoteService``, shared by the REST handlers
(via a FastAPI dependency) and the module-level MCP tools. Set in the app
lifespan; read through ``get_service``.
"""

from __future__ import annotations

from engram_core import LinkService, NoteService

_service: NoteService | None = None


def set_service(service: NoteService | None) -> None:
    global _service
    _service = service


def get_service() -> NoteService:
    if _service is None:
        raise RuntimeError("NoteService is not initialized; the app lifespan has not run.")
    return _service


def get_link_service() -> LinkService:
    return LinkService(get_service())
