"""
MCP Dev Toolkit — Main Server

Entry point for the MCP server. Tools are registered here and
implemented in the tools/ directory.
"""

from mcp.server.fastmcp import FastMCP
from tools.system import get_system_info
from tools.filesystem import read_file, list_directory, run_command

mcp = FastMCP("Dev Toolkit")

mcp.tool()(get_system_info)
mcp.tool()(read_file)
mcp.tool()(list_directory)
mcp.tool()(run_command)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
