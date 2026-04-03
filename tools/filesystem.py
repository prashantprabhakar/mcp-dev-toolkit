"""
Filesystem tools

All tools check the requested path against whitelist.json before touching anything on disk.
"""

import json
import os
import subprocess

from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.utilities.logging import get_logger

logger = get_logger(__name__)

_WHITELIST_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "whitelist.json"))


def _load_config() -> dict:
    with open(_WHITELIST_PATH) as f:
        return json.load(f)


def _is_allowed_path(path: str) -> bool:
    resolved = os.path.normpath(os.path.realpath(os.path.abspath(path)))
    allowed = [os.path.normpath(p) for p in _load_config()["allowed_paths"]]
    return any(resolved.startswith(a) for a in allowed)


def _is_allowed_command(command: str) -> bool:
    return command.strip() in _load_config()["allowed_commands"]


def read_file(path: str) -> dict:
    """
    Read and return the contents of a file at the given path.
    The path must be inside one of the whitelisted directories in whitelist.json.
    """
    logger.debug("read_file: %s", path)
    if not _is_allowed_path(path):
        logger.warning("read_file: access denied for %s", path)
        raise ToolError(f"Access denied: '{path}' is not in the whitelist.")
    if not os.path.isfile(path):
        raise ToolError(f"File not found: '{path}'")
    try:
        with open(path, encoding="utf-8") as f:
            contents = f.read()
        logger.debug("read_file: read %d bytes from %s", len(contents), path)
        return {"path": path, "contents": contents}
    except Exception as e:
        logger.error("read_file: unexpected error reading %s: %s", path, e)
        raise ToolError(f"Could not read file: {e}") from e


def list_directory(path: str) -> dict:
    """
    List files and folders in the given directory path.
    The path must be inside one of the whitelisted directories in whitelist.json.
    """
    logger.debug("list_directory: %s", path)
    if not _is_allowed_path(path):
        logger.warning("list_directory: access denied for %s", path)
        raise ToolError(f"Access denied: '{path}' is not in the whitelist.")
    if not os.path.isdir(path):
        raise ToolError(f"Directory not found: '{path}'")
    try:
        entries = []
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            entries.append({"name": name, "type": "directory" if os.path.isdir(full) else "file"})
        logger.debug("list_directory: %d entries in %s", len(entries), path)
        return {"path": path, "entries": entries}
    except Exception as e:
        logger.error("list_directory: unexpected error listing %s: %s", path, e)
        raise ToolError(f"Could not list directory: {e}") from e


def run_command(command: str) -> dict:
    """
    Run a shell command from the allowlist and return its output.
    Only commands explicitly listed in whitelist.json are permitted.
    """
    logger.debug("run_command: %s", command)
    if not _is_allowed_command(command):
        allowed = _load_config()["allowed_commands"]
        logger.warning("run_command: rejected command: %s", command)
        raise ToolError(f"Command not allowed: '{command}'. Allowed: {allowed}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        logger.debug("run_command: exit_code=%d for '%s'", result.returncode, command)
        return {
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        logger.warning("run_command: timed out: %s", command)
        raise ToolError(f"Command timed out after 10 seconds: '{command}'")
    except Exception as e:
        logger.error("run_command: unexpected error for '%s': %s", command, e)
        raise ToolError(f"Command failed: {e}") from e
