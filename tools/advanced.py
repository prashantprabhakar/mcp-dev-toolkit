"""
Advanced tools — Phase 6

Covers two new MCP concepts demonstrated here:
  1. Progress notifications  — scan_directory_deep streams ctx.report_progress()
  2. Multi-content return    — inspect_file returns [TextContent, EmbeddedResource]

Structured input schema (Pydantic model) is demonstrated in tools/database.py
via SqliteQueryInput — the right home for a model is next to the tool it belongs to.
"""

import os

from mcp.server.fastmcp import Context
from mcp.types import EmbeddedResource, TextContent, TextResourceContents

from tools.filesystem import _is_allowed_path


# ---------------------------------------------------------------------------
# 1. Progress notifications
# ---------------------------------------------------------------------------

async def scan_directory_deep(path: str, ctx: Context) -> dict:
    """
    Recursively scan a directory and count all files grouped by extension.
    Streams progress back to the client as each sub-directory is visited.
    The path must be inside a whitelisted directory.
    """
    if not _is_allowed_path(path):
        return {"error": f"Access denied: {path} is not in the whitelist."}
    if not os.path.isdir(path):
        return {"error": f"Not a directory: {path}"}

    # Collect all (root, dirs, files) entries first so we know the total.
    # Skip hidden folders, __pycache__, .venv, node_modules.
    walk_entries: list[tuple[str, list[str], list[str]]] = []
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(
            d for d in dirs
            if not d.startswith(".") and d not in ("__pycache__", ".venv", "node_modules")
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

    # Sort by count descending so the most common types appear first.
    by_extension = dict(sorted(ext_counts.items(), key=lambda x: x[1], reverse=True))

    return {
        "path": path,
        "total_dirs": total,
        "total_files": total_files,
        "by_extension": by_extension,
    }


# ---------------------------------------------------------------------------
# 3. Multi-content return (TextContent + EmbeddedResource)
# ---------------------------------------------------------------------------

def inspect_file(path: str) -> list[TextContent | EmbeddedResource]:
    """
    Inspect a file and return two content blocks:
      - TextContent  : human-readable metadata (name, size, line count, extension)
      - EmbeddedResource : the actual file contents embedded inline

    This demonstrates returning multiple content types from a single tool call.
    The path must be inside a whitelisted directory.
    """
    if not _is_allowed_path(path):
        return [TextContent(type="text", text=f"Access denied: {path} is not in the whitelist.")]
    if not os.path.isfile(path):
        return [TextContent(type="text", text=f"File not found: {path}")]

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
    except Exception as e:
        return [TextContent(type="text", text=f"Error reading file: {e}")]
