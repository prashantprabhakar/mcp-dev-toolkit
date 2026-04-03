"""
MCP Dev Toolkit — Main Server

Entry point for the MCP server. Tools, resources, and prompts are
registered here and implemented in the tools/ directory.
"""

from contextlib import asynccontextmanager
import asyncio

from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp.utilities.logging import get_logger
logger = get_logger(__name__)

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from tools.system import get_system_info
from tools.filesystem import read_file, list_directory, run_command
from tools.resources import get_pyproject_toml, get_git_log, get_directory_tree
from tools.external import fetch_github_readme, search_web
from tools.database import run_sqlite_query
from tools.prompts import review_file, summarize_repo
from tools.advanced import scan_directory_deep, inspect_file
from tools.sampling import explain_error, suggest_fix
from tools.subscriptions import (
    get_config_resource,
    watch_whitelist,
    CONFIG_RESOURCE_URI,
)

# ---------------------------------------------------------------------------
# Phase 9: Resource subscription state
# Tracks which sessions have subscribed to project://config.
# Populated by on_subscribe / drained by on_unsubscribe and the watcher.
# ---------------------------------------------------------------------------
_subscribed_sessions: set = set()


# ---------------------------------------------------------------------------
# Lifespan — starts the file-watcher background task for Phase 9
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastMCP):
    # Patch the low-level server to advertise subscribe=True.
    # get_capabilities() hardcodes subscribe=False, so we override it.
    _patch_subscribe_capability(app)

    # Register subscribe / unsubscribe handlers on the low-level server.
    @app._mcp_server.subscribe_resource()
    async def on_subscribe(uri) -> None:
        session = app._mcp_server.request_context.session
        _subscribed_sessions.add(session)

    @app._mcp_server.unsubscribe_resource()
    async def on_unsubscribe(uri) -> None:
        session = app._mcp_server.request_context.session
        _subscribed_sessions.discard(session)

    # Start the background watcher.
    watcher = asyncio.create_task(watch_whitelist(_subscribed_sessions))
    try:
        yield
    finally:
        watcher.cancel()
        try:
            await watcher
        except asyncio.CancelledError:
            pass


def _patch_subscribe_capability(app: FastMCP) -> None:
    """
    Force subscribe=True in the server's advertised capabilities.

    The low-level server's get_capabilities() hardcodes subscribe=False regardless
    of whether a SubscribeRequest handler is registered. We wrap it to fix that.
    """
    original = app._mcp_server.get_capabilities

    def patched(notification_options, experimental_capabilities):
        caps = original(notification_options, experimental_capabilities)
        if caps.resources is not None:
            caps.resources.subscribe = True
        return caps

    app._mcp_server.get_capabilities = patched


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP("Dev Toolkit", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Phase 1–2: Core + Filesystem tools
# ---------------------------------------------------------------------------

mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))(get_system_info)
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))(read_file)
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))(list_directory)
mcp.tool(annotations=ToolAnnotations(destructiveHint=True))(run_command)

# Phase 4: External APIs
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))(fetch_github_readme)
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))(search_web)

# Phase 5: Database
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))(run_sqlite_query)

# Phase 6: Advanced tools
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))(scan_directory_deep)
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))(inspect_file)

# Phase 8: Sampling
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))(explain_error)
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))(suggest_fix)

# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

# Phase 3: static project metadata
mcp.resource("project://pyproject.toml")(get_pyproject_toml)
mcp.resource("project://git-log")(get_git_log)
mcp.resource("project://directory-tree")(get_directory_tree)

# Phase 9: watchable config resource
mcp.resource(
    CONFIG_RESOURCE_URI,
    description="The server's path and command allowlist (whitelist.json). "
                "Subscribing to this resource delivers a notification whenever the file changes.",
)(get_config_resource)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

mcp.prompt()(review_file)
mcp.prompt()(summarize_repo)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="MCP Dev Toolkit server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help=(
            "Transport to use. "
            "'stdio' for Claude Desktop (default). "
            "'sse' for HTTP+SSE at http://HOST:PORT/sse. "
            "'streamable-http' for modern HTTP at http://HOST:PORT/mcp."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP transports (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP transports (default: 8000)")
    args = parser.parse_args()

    if args.transport in ("sse", "streamable-http"):
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        path = "/sse" if args.transport == "sse" else "/mcp"
        logger.info("Starting MCP Dev Toolkit over %s on http://%s:%d%s", args.transport.upper(), args.host, args.port, path)

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
