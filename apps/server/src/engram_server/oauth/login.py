"""Password-gated consent page for the OAuth authorization flow.

``GET /oauth/login`` renders a minimal form carrying the opaque ``ticket`` that
``EngramOAuthProvider.authorize`` parked. ``POST /oauth/login`` checks the
submitted password (constant-time) against ``ENGRAM_OAUTH_PASSWORD`` and, on
success, asks the provider to mint an authorization code and redirects back to the
client. This is what stops anyone who can reach the public URL from minting a token.
"""

from __future__ import annotations

import html
import secrets

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route

from .provider import LOGIN_PATH, EngramOAuthProvider

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Engram — authorize connection</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #f5f5f4; margin: 0;
         display: flex; min-height: 100vh; align-items: center; justify-content: center; }}
  .card {{ background: #fff; padding: 2rem; border-radius: 12px; max-width: 22rem; width: 100%;
          box-shadow: 0 1px 3px rgba(0,0,0,.12); }}
  h1 {{ font-size: 1.15rem; margin: 0 0 .25rem; }}
  p {{ color: #57534e; font-size: .9rem; margin: 0 0 1.25rem; }}
  label {{ display: block; font-size: .85rem; margin-bottom: .35rem; color: #44403c; }}
  input[type=password] {{ width: 100%; padding: .6rem; border: 1px solid #d6d3d1;
          border-radius: 8px; box-sizing: border-box; font-size: 1rem; }}
  button {{ margin-top: 1rem; width: 100%; padding: .65rem; border: 0; border-radius: 8px;
          background: #1c1917; color: #fff; font-size: 1rem; cursor: pointer; }}
  .error {{ color: #b91c1c; font-size: .85rem; margin: .75rem 0 0; }}
</style>
</head>
<body>
  <div class="card">
    <h1>Authorize connection</h1>
    <p>A client wants to connect to your Engram vault. Enter the access password to allow it.</p>
    <form method="post" action="{action}">
      <input type="hidden" name="ticket" value="{ticket}">
      <label for="password">Access password</label>
      <input id="password" name="password" type="password"
             autocomplete="current-password" autofocus required>
      <button type="submit">Authorize</button>
      {error}
    </form>
  </div>
</body>
</html>
"""


def _render(ticket: str, *, error: str | None = None) -> str:
    error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
    return _PAGE.format(
        action=html.escape(LOGIN_PATH, quote=True),
        ticket=html.escape(ticket, quote=True),
        error=error_html,
    )


def create_login_routes(provider: EngramOAuthProvider, password: str) -> list[Route]:
    async def get_login(request: Request) -> Response:
        ticket = request.query_params.get("ticket")
        if not ticket:
            return HTMLResponse("Missing authorization ticket.", status_code=400)
        return HTMLResponse(_render(ticket))

    async def post_login(request: Request) -> Response:
        form = await request.form()
        ticket = form.get("ticket")
        submitted = form.get("password")
        ticket = ticket if isinstance(ticket, str) else ""
        submitted = submitted if isinstance(submitted, str) else ""
        if not ticket:
            return HTMLResponse("Missing authorization ticket.", status_code=400)
        if not (password and secrets.compare_digest(submitted, password)):
            return HTMLResponse(_render(ticket, error="Incorrect password."), status_code=401)
        redirect_url = provider.complete_login(ticket)
        if redirect_url is None:
            return HTMLResponse(
                "Authorization request expired. Please start again.", status_code=400
            )
        return RedirectResponse(
            redirect_url, status_code=302, headers={"Cache-Control": "no-store"}
        )

    return [
        Route(LOGIN_PATH, endpoint=get_login, methods=["GET"]),
        Route(LOGIN_PATH, endpoint=post_login, methods=["POST"]),
    ]
