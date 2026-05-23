"""Bartleby server: a thin FastAPI app exposing REST, MCP, and the static UI.

All note logic lives in ``bartleby_core``; this package validates input, calls
``NoteService``, and shapes responses.
"""

__version__ = "0.1.0"
