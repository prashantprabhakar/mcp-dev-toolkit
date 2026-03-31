"""MCP Resources — project metadata exposed as readable resources."""

import os
import subprocess


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
