"""Database tools — read-only SQLite queries."""

import os
import sqlite3

from tools.filesystem import _is_allowed_path


def run_sqlite_query(db_path: str, query: str) -> dict:
    """
    Run a read-only SELECT query against a local SQLite database.
    The database path must be inside a whitelisted directory.
    Only SELECT statements are permitted — no writes, deletes, or schema changes.
    Returns column names, rows as objects, and a total count.
    """
    if not query.strip().upper().startswith("SELECT"):
        return {"error": "Only SELECT queries are allowed."}

    if not _is_allowed_path(db_path):
        return {"error": f"Access denied: {db_path} is not in the whitelist."}

    if not os.path.isfile(db_path):
        return {"error": f"Database not found: {db_path}"}

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return {"columns": columns, "rows": rows, "count": len(rows)}
    except Exception as e:
        return {"error": str(e)}
