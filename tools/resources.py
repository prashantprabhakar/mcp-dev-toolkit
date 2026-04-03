"""MCP Resources — project metadata exposed as readable resources."""

import os
import subprocess

from mcp.server.fastmcp.exceptions import ToolError


def get_pyproject_toml() -> str:
    """Contents of pyproject.toml from the current working directory."""
    path = os.path.join(os.getcwd(), "pyproject.toml")
    if not os.path.isfile(path):
        return "pyproject.toml not found in current directory."
    with open(path) as f:
        return f.read()


def get_git_log() -> str:
    """Last 20 commits from git log in the current directory."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-20"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout or result.stderr or "No commits found."
    except Exception as e:
        return str(e)


def get_project_file(filename: str) -> str:
    """
    Read a file from the project root directory by name.
    URI template: project://files/{filename}

    filename must be a single name or relative path with no leading slash
    (e.g. 'server.py', 'whitelist.json'). Subdirectory access like
    'tools/filesystem.py' is not supported — the template variable cannot
    contain path separators due to URI template matching rules.
    """
    path = os.path.normpath(os.path.join(os.getcwd(), filename))
    # Block traversal: resolved path must stay inside cwd
    if not path.startswith(os.path.normpath(os.getcwd())):
        raise ToolError(f"Access denied: '{filename}' resolves outside the project root.")
    if not os.path.isfile(path):
        raise ValueError(f"File not found in project root: '{filename}'")
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def get_directory_tree() -> str:
    """Recursive file tree of the current working directory, skipping hidden folders and .venv."""
    lines = []
    cwd = os.getcwd()
    for root, dirs, files in os.walk(cwd):
        dirs[:] = sorted(
            d for d in dirs
            if not d.startswith(".") and d not in ("__pycache__", ".venv", "node_modules")
        )
        level = root.replace(cwd, "").count(os.sep)
        indent = "  " * level
        lines.append(f"{indent}{os.path.basename(root)}/")
        for file in sorted(files):
            lines.append(f"{indent}  {file}")
    return "\n".join(lines)
