"""
MCP Dev Toolkit — Main Server

Entry point for the MCP server. Tools, resources, and prompts are
registered here and implemented in the tools/ directory.
"""

from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP

from tools.system import get_system_info
from tools.filesystem import read_file, list_directory, run_command
from tools.resources import get_pyproject_toml, get_git_log, get_directory_tree
from tools.external import fetch_github_readme, search_web
from tools.database import run_sqlite_query
from tools.prompts import review_file, summarize_repo

mcp = FastMCP("Dev Toolkit")

# Tools
mcp.tool()(get_system_info)
mcp.tool()(read_file)
mcp.tool()(list_directory)
mcp.tool()(run_command)
mcp.tool()(fetch_github_readme)
mcp.tool()(search_web)
mcp.tool()(run_sqlite_query)

# Resources
mcp.resource("project://pyproject.toml")(get_pyproject_toml)
mcp.resource("project://git-log")(get_git_log)
mcp.resource("project://directory-tree")(get_directory_tree)

# Prompts
mcp.prompt()(review_file)
mcp.prompt()(summarize_repo)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
