"""
MCP Dev Toolkit — Main Server

Entry point for the MCP server. Tools, resources, and prompts are
registered here and implemented in the tools/ directory.
"""

from dotenv import load_dotenv
load_dotenv()

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

mcp = FastMCP("Dev Toolkit")

# ---------------------------------------------------------------------------
# Phase 1–2: Core + Filesystem tools
# Annotations tell clients how safe each tool is to call automatically.
# ---------------------------------------------------------------------------

mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))(get_system_info)

mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))(read_file)
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))(list_directory)
mcp.tool(annotations=ToolAnnotations(destructiveHint=True))(run_command)

# Phase 4: External APIs — open-world (network), not idempotent (rate limits / caching)
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))(fetch_github_readme)
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))(search_web)

# Phase 5: Database — read-only SELECT only
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))(run_sqlite_query)

# ---------------------------------------------------------------------------
# Phase 6: Advanced tools
# ---------------------------------------------------------------------------

# Progress notifications — async, streams ctx.report_progress() while scanning
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))(scan_directory_deep)

# Multi-content return — returns [TextContent, EmbeddedResource] in one call
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))(inspect_file)

# ---------------------------------------------------------------------------
# Phase 8: Sampling tools
# These call back into the LLM mid-execution via session.create_message().
# ---------------------------------------------------------------------------

mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))(explain_error)
mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))(suggest_fix)

# ---------------------------------------------------------------------------
# Resources (Phase 3)
# ---------------------------------------------------------------------------

mcp.resource("project://pyproject.toml")(get_pyproject_toml)
mcp.resource("project://git-log")(get_git_log)
mcp.resource("project://directory-tree")(get_directory_tree)

# ---------------------------------------------------------------------------
# Prompts (Phase 5)
# ---------------------------------------------------------------------------

mcp.prompt()(review_file)
mcp.prompt()(summarize_repo)


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

    # Inject host/port into FastMCP settings when using an HTTP transport.
    if args.transport in ("sse", "streamable-http"):
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        path = "/sse" if args.transport == "sse" else "/mcp"
        print(f"Starting MCP Dev Toolkit over {args.transport.upper()} on http://{args.host}:{args.port}{path}")

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
