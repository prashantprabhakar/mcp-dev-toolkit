"""Database tools — read-only SQLite queries."""

import os
import sqlite3

from pydantic import BaseModel, Field

from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.utilities.logging import get_logger

from tools.filesystem import _is_allowed_path

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
#  Structured input schema
# ---------------------------------------------------------------------------
class SqliteQueryInput(BaseModel):
    """Input model for run_sqlite_query — FastMCP turns this into a JSON Schema."""

    db_path: str = Field(description="Absolute path to the SQLite database file")
    query: str = Field(description="A read-only SELECT statement to execute")


def run_sqlite_query(input: SqliteQueryInput) -> dict:
    """
    Run a read-only SELECT query against a local SQLite database.
    The database path must be inside a whitelisted directory.
    Only SELECT statements are permitted — no writes, deletes, or schema changes.
    Returns column names, rows as objects, and a total count.
    """
    db_path = input.db_path
    query = input.query

    logger.debug("run_sqlite_query: %s | %s", db_path, query[:80])

    if not query.strip().upper().startswith("SELECT"):
        raise ToolError("Only SELECT queries are allowed.")

    if not _is_allowed_path(db_path):
        logger.warning("run_sqlite_query: access denied for %s", db_path)
        raise ToolError(f"Access denied: '{db_path}' is not in the whitelist.")

    if not os.path.isfile(db_path):
        raise ToolError(f"Database not found: '{db_path}'")

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        logger.debug("run_sqlite_query: returned %d rows", len(rows))
        return {"columns": columns, "rows": rows, "count": len(rows)}
    except Exception as e:
        logger.error("run_sqlite_query: query failed: %s", e)
        raise ToolError(f"Query failed: {e}") from e
