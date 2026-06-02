"""Error envelope and exception handlers.

Every failure response uses the shape ``{"error": {"code", "message"}}``. Core
domain exceptions map to HTTP status codes here; the auth middleware builds the
same envelope itself (it runs outside FastAPI's handler machinery).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from engram_core.errors import (
    BlockedHost,
    EngramError,
    IndexUnavailable,
    InvalidNote,
    LinkExtractionFailed,
    LinkTimeout,
    LinkTooLarge,
    LinkUnreachable,
    NoteAlreadyExists,
    NoteConflict,
    NoteNotFound,
    NoteNotInTrash,
    UnsupportedContentType,
    VaultError,
)


class PreconditionRequired(EngramError):
    """A write that needs an ``If-Match`` precondition was sent without one."""

    def __init__(self) -> None:
        super().__init__("An If-Match header is required for this write.")


_STATUS: dict[type[EngramError], tuple[int, str]] = {
    PreconditionRequired: (428, "precondition_required"),
    NoteNotFound: (404, "not_found"),
    NoteNotInTrash: (404, "not_in_trash"),
    NoteAlreadyExists: (409, "already_exists"),
    NoteConflict: (409, "conflict"),
    InvalidNote: (400, "invalid_note"),
    IndexUnavailable: (503, "index_unavailable"),
    VaultError: (500, "vault_error"),
    BlockedHost: (400, "blocked_host"),
    LinkUnreachable: (422, "link_unreachable"),
    LinkTimeout: (504, "link_timeout"),
    LinkTooLarge: (413, "link_too_large"),
    UnsupportedContentType: (415, "unsupported_content_type"),
    LinkExtractionFailed: (422, "extraction_failed"),
}


def envelope(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(EngramError)
    async def _engram(_: Request, exc: EngramError) -> JSONResponse:
        status, code = _STATUS.get(type(exc), (500, "internal_error"))
        return envelope(status, code, str(exc))

    @app.exception_handler(ValueError)
    async def _value_error(_: Request, exc: ValueError) -> JSONResponse:
        # Core raises a bare ValueError for a malformed pagination cursor.
        return envelope(400, "invalid_request", str(exc))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return envelope(422, "validation_error", "Request validation failed.")

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        return envelope(500, "internal_error", "Internal server error.")
