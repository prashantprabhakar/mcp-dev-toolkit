"""
Advanced tools — Phase 6

Demonstrates:
  1. Progress notifications  — scan_directory_deep streams ctx.report_progress()
  2. Multi-content return    — inspect_file returns [TextContent, EmbeddedResource]

Structured input schema (Pydantic model) is in tools/database.py via SqliteQueryInput —
the right home for a model is next to the tool it belongs to.
"""

import os

from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.utilities.logging import get_logger
from mcp.types import EmbeddedResource, TextContent, TextResourceContents

from tools.filesystem import _is_allowed_path

logger = get_logger(__name__)


async def scan_directory_deep(path: str, ctx: Context, exclude: list[str] | None = None) -> dict:
    """
    Recursively scan a directory and count all files grouped by extension.
    Streams progress back to the client as each sub-directory is visited.
    The path must be inside a whitelisted directory.

    exclude: optional list of directory names to skip (e.g. ["__pycache__", "dev-corner"]).
             Always skips hidden dirs, .venv, and node_modules regardless.
    """
    logger.debug("scan_directory_deep: %s (exclude=%s)", path, exclude)
    if not _is_allowed_path(path):
        logger.warning("scan_directory_deep: access denied for %s", path)
        raise ToolError(f"Access denied: '{path}' is not in the whitelist.")
    if not os.path.isdir(path):
        raise ToolError(f"Not a directory: '{path}'")

    always_excluded = {"__pycache__", ".venv", "node_modules"}
    user_excluded = set(exclude) if exclude else set()
    skip = always_excluded | user_excluded

    walk_entries: list[tuple[str, list[str], list[str]]] = []
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(
            d for d in dirs
            if not d.startswith(".") and d not in skip
        )
        walk_entries.append((root, list(dirs), list(files)))

    total = len(walk_entries)
    ext_counts: dict[str, int] = {}
    total_files = 0

    for i, (root, _dirs, files) in enumerate(walk_entries):
        folder_name = os.path.basename(root) or root
        await ctx.report_progress(i + 1, total, message=f"Scanning {folder_name}/")
        for filename in files:
            total_files += 1
            ext = os.path.splitext(filename)[1].lower() or "(no extension)"
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

    by_extension = dict(sorted(ext_counts.items(), key=lambda x: x[1], reverse=True))
    logger.debug("scan_directory_deep: %d files across %d dirs in %s", total_files, total, path)
    return {
        "path": path,
        "total_dirs": total,
        "total_files": total_files,
        "by_extension": by_extension,
    }


def inspect_file(path: str) -> list[TextContent | EmbeddedResource]:
    """
    Inspect a file and return two content blocks:
      - TextContent  : human-readable metadata (name, size, line count, extension)
      - EmbeddedResource : the actual file contents embedded inline

    The path must be inside a whitelisted directory.
    """
    logger.debug("inspect_file: %s", path)
    if not _is_allowed_path(path):
        logger.warning("inspect_file: access denied for %s", path)
        raise ToolError(f"Access denied: '{path}' is not in the whitelist.")
    if not os.path.isfile(path):
        raise ToolError(f"File not found: '{path}'")

    try:
        stat = os.stat(path)
        with open(path, encoding="utf-8", errors="replace") as f:
            contents = f.read()

        line_count = contents.count("\n") + (1 if contents and not contents.endswith("\n") else 0)
        ext = os.path.splitext(path)[1].lower() or "(none)"
        size_kb = stat.st_size / 1024
        abs_path = os.path.abspath(path)

        metadata = (
            f"File:      {os.path.basename(path)}\n"
            f"Extension: {ext}\n"
            f"Size:      {size_kb:.1f} KB ({stat.st_size:,} bytes)\n"
            f"Lines:     {line_count:,}"
        )

        return [
            TextContent(type="text", text=metadata),
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri=f"file:///{abs_path.replace(os.sep, '/')}",
                    mimeType="text/plain",
                    text=contents,
                ),
            ),
        ]
    except ToolError:
        raise
    except Exception as e:
        logger.error("inspect_file: unexpected error reading %s: %s", path, e)
        raise ToolError(f"Could not inspect file: {e}") from e
