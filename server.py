"""
MCP Dev Toolkit — Main Server

Entry point for the MCP server. Tools are registered here and
implemented in the tools/ directory as we add them phase by phase.
"""

import platform
import sys
from mcp.server.fastmcp import FastMCP

# Create the MCP server instance
# The name shows up in Claude Desktop's tool list
mcp = FastMCP("Dev Toolkit")


# ---------------------------------------------------------------------------
# Phase 1 — First tool
# ---------------------------------------------------------------------------

@mcp.tool()
def get_system_info() -> dict:
    """Returns basic system information: OS, Python version, and current directory."""
    import os
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "python_version": sys.version,
        "cwd": os.getcwd(),
        "hostname": platform.node(),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
