"""
Filesystem tools

All tools check the requested path against whitelist.json before touching anything on disk.
"""

import json
import os
import subprocess
from pydantic import BaseModel, Field

from mcp.server.fastmcp import Context
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


async def write_file(content: str, ctx: Context, path: str | None = None) -> dict:
    """
    Write content to a file.
    If path is not provided, guides the user step-by-step:
      1. Choose a target directory from the whitelist (dropdown)
      2. Enter a filename (free text)
      3. Confirm the write (boolean)
    If path is provided, goes straight to the confirmation step.
    The final path must be inside a whitelisted directory.
    """

    # ------------------------------------------------------------------
    # Step 1 & 2 — elicit path if not provided
    # ------------------------------------------------------------------
    if path is None:
        allowed = _load_config()["allowed_paths"]
        if not allowed:
            raise ToolError("No directories are whitelisted. Add paths to whitelist.json first.")

        # Elicitation only allows primitive types — no Literal enums or nested models.
        # Represent options as a numbered list in the description; user picks an int.
        options_text = "\n".join(f"{i + 1}. {d}" for i, d in enumerate(allowed))

        class DirectoryChoice(BaseModel):
            choice: int = Field(
                description=f"Enter the number of the target directory:\n{options_text}"
            )

        dir_result = await ctx.elicit("Choose a target directory:", DirectoryChoice)
        if dir_result.action != "accept":
            return {"status": "cancelled"}

        idx = dir_result.data.choice - 1
        if not (0 <= idx < len(allowed)):
            raise ToolError(f"Invalid choice: {dir_result.data.choice}. Enter a number between 1 and {len(allowed)}.")
        chosen_dir = allowed[idx]

        # Free text: ask for filename
        class FilenameInput(BaseModel):
            filename: str = Field(
                description="File name to create (e.g. notes.md). No path separators — just the name."
            )

        name_result = await ctx.elicit(
            f"Enter a filename to create inside '{chosen_dir}':", FilenameInput
        )
        if name_result.action != "accept":
            return {"status": "cancelled"}

        filename = name_result.data.filename.strip()
        if not filename or any(sep in filename for sep in (os.sep, "/")):
            raise ToolError("Filename must be a single name with no path separators (e.g. notes.md).")

        path = os.path.join(chosen_dir, filename)

    # ------------------------------------------------------------------
    # Whitelist check (applies whether path came from user or elicitation)
    # ------------------------------------------------------------------
    logger.debug("write_file: %s (%d bytes)", path, len(content))
    if not _is_allowed_path(path):
        logger.warning("write_file: access denied for %s", path)
        raise ToolError(f"Access denied: '{path}' is not in the whitelist.")

    # ------------------------------------------------------------------
    # Step 3 — confirm (boolean)
    # ------------------------------------------------------------------
    class WriteConfirmation(BaseModel):
        confirm: bool = Field(description="true to write the file, false to cancel.")

    action_label = "overwrite" if os.path.isfile(path) else "create"
    confirm_result = await ctx.elicit(
        f"Write {len(content):,} bytes to '{path}' ({action_label})?",
        WriteConfirmation,
    )

    if confirm_result.action != "accept" or not confirm_result.data.confirm:
        logger.debug("write_file: cancelled by user for %s", path)
        return {"status": "cancelled", "path": path}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.debug("write_file: wrote %d bytes to %s", len(content), path)
        return {"status": "written", "path": path, "bytes": len(content)}
    except Exception as e:
        logger.error("write_file: failed to write %s: %s", path, e)
        raise ToolError(f"Could not write file: {e}") from e


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
