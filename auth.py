"""
Bearer auth for HTTP transport — token verification and scope decorators.

Three token tiers (set in .env):
  MCP_READ_TOKEN  → mcp:read              (read-only tools)
  MCP_WRITE_TOKEN → mcp:read mcp:write    (+ write_file)
  MCP_ADMIN_TOKEN → mcp:read mcp:write mcp:admin  (+ run_command)

stdio transport does not use any of this — auth only applies to HTTP.

In production you would validate JWTs against a real OAuth authorization server.
For local use, static tokens are sufficient and much simpler.

Generate tokens:
    python -c "import secrets; print(secrets.token_hex(32))"
"""

import functools
import inspect
import os

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.fastmcp.exceptions import ToolError


# ---------------------------------------------------------------------------
# Token verifier
# ---------------------------------------------------------------------------

class StaticTokenVerifier:
    """
    Verifies Bearer tokens against static values from environment variables.
    Returns None for any unrecognised token — the SDK returns 401 automatically.
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        admin_token = os.environ.get("MCP_ADMIN_TOKEN", "")
        write_token = os.environ.get("MCP_WRITE_TOKEN", "")
        read_token  = os.environ.get("MCP_READ_TOKEN", "")

        if admin_token and token == admin_token:
            return AccessToken(
                token=token,
                client_id="admin",
                scopes=["mcp:read", "mcp:write", "mcp:admin"],
            )
        if write_token and token == write_token:
            return AccessToken(
                token=token,
                client_id="writer",
                scopes=["mcp:read", "mcp:write"],
            )
        if read_token and token == read_token:
            return AccessToken(
                token=token,
                client_id="reader",
                scopes=["mcp:read"],
            )
        return None


# ---------------------------------------------------------------------------
# Scope decorator
# ---------------------------------------------------------------------------

def require_scope(scope: str):
    """
    Decorator that enforces a required scope on a tool function.

    - On HTTP transport: checks the Bearer token's scopes. Raises ToolError
      with a 403-equivalent message if the required scope is missing.
    - On stdio transport: get_access_token() returns None → check is skipped.
      stdio is a local process; it does not go through auth middleware.

    Works on both sync and async tool functions.

    Usage:
        @require_scope("mcp:write")
        async def write_file(...): ...

        @require_scope("mcp:admin")
        def run_command(...): ...
    """
    # Level 2: decorator(fn) — called once at import time when Python processes
    # the @require_scope(...) line. fn is the original tool function.
    def decorator(fn):

        # Python requires the wrapper to match the original's calling convention.
        # Unlike JavaScript, you cannot `await` a non-async function — it raises
        # TypeError at runtime. So we branch once here (at decoration time, not
        # at every call) and return the right kind of wrapper permanently.
        if inspect.iscoroutinefunction(fn):

            # --- Async branch: wraps async def tools (e.g. write_file) ---

            # @functools.wraps copies __name__, __doc__, __annotations__ from fn
            # onto async_wrapper. Without this, the tool would appear as
            # "async_wrapper" in the MCP Inspector and Claude's tool list.
            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                # get_access_token() reads from a contextvar set by AuthContextMiddleware.
                # Returns None on stdio (no middleware) → skip the check entirely.
                # Returns an AccessToken on HTTP → check its scopes.
                token = get_access_token()

                # `token is not None` means we're on HTTP transport.
                # Only then do we enforce the scope — stdio is always trusted.
                if token is not None and scope not in token.scopes:
                    raise ToolError(
                        f"Insufficient scope: '{scope}' required. "
                        f"Your token has: {token.scopes}"
                    )

                # Scope ok (or stdio) — call the original function.
                # `await` is required because fn is async def.
                return await fn(*args, **kwargs)

            return async_wrapper  # write_file is now async_wrapper

        else:

            # --- Sync branch: wraps regular def tools (e.g. run_command) ---

            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs):
                token = get_access_token()
                if token is not None and scope not in token.scopes:
                    raise ToolError(
                        f"Insufficient scope: '{scope}' required. "
                        f"Your token has: {token.scopes}"
                    )

                # Plain call — no await, fn is not a coroutine.
                return fn(*args, **kwargs)

            return sync_wrapper  # run_command is now sync_wrapper

    # Level 1: require_scope("mcp:write") returns decorator.
    # Python then immediately calls decorator(write_file).
    return decorator
