"""
Tests for tools/database.py

Strategy:
- Use tmp_path to create a real SQLite DB (sqlite3 is stdlib, no extra deps)
- Mock _is_allowed_path so tests don't depend on whitelist.json
- Test the SELECT guard, whitelist check, and happy path separately
"""

import sqlite3
import pytest
from unittest.mock import patch
from mcp.server.fastmcp.exceptions import ToolError
from tools.database import SqliteQueryInput, run_sqlite_query


@pytest.fixture
def sample_db(tmp_path):
    """A minimal SQLite database with a users table."""
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice', 30)")
    conn.execute("INSERT INTO users VALUES (2, 'Bob', 25)")
    conn.commit()
    conn.close()
    return str(db)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestRunSqliteQueryHappyPath:
    def test_select_returns_correct_rows(self, sample_db):
        with patch("tools.database._is_allowed_path", return_value=True):
            result = run_sqlite_query(SqliteQueryInput(db_path=sample_db, query="SELECT * FROM users"))
        assert result["count"] == 2
        assert result["columns"] == ["id", "name", "age"]

    def test_select_returns_row_dicts(self, sample_db):
        with patch("tools.database._is_allowed_path", return_value=True):
            result = run_sqlite_query(SqliteQueryInput(db_path=sample_db, query="SELECT * FROM users"))
        assert {"id": 1, "name": "Alice", "age": 30} in result["rows"]

    def test_select_with_where_filters_rows(self, sample_db):
        with patch("tools.database._is_allowed_path", return_value=True):
            result = run_sqlite_query(SqliteQueryInput(
                db_path=sample_db,
                query="SELECT * FROM users WHERE name = 'Alice'"
            ))
        assert result["count"] == 1
        assert result["rows"][0]["name"] == "Alice"

    def test_select_count_query(self, sample_db):
        with patch("tools.database._is_allowed_path", return_value=True):
            result = run_sqlite_query(SqliteQueryInput(
                db_path=sample_db,
                query="SELECT COUNT(*) AS total FROM users"
            ))
        assert result["rows"][0]["total"] == 2


# ---------------------------------------------------------------------------
# SELECT guard — only SELECT is allowed
# ---------------------------------------------------------------------------

class TestSelectGuard:
    @pytest.mark.parametrize("query", [
        "INSERT INTO users VALUES (3, 'Charlie', 20)",
        "UPDATE users SET name = 'X' WHERE id = 1",
        "DELETE FROM users WHERE id = 1",
        "DROP TABLE users",
        "CREATE TABLE foo (id INTEGER)",
    ])
    def test_non_select_raises_tool_error(self, sample_db, query):
        with patch("tools.database._is_allowed_path", return_value=True):
            with pytest.raises(ToolError, match="Only SELECT"):
                run_sqlite_query(SqliteQueryInput(db_path=sample_db, query=query))

    def test_select_is_case_insensitive(self, sample_db):
        # "select" lowercase should still be allowed
        with patch("tools.database._is_allowed_path", return_value=True):
            result = run_sqlite_query(SqliteQueryInput(
                db_path=sample_db,
                query="select * from users"
            ))
        assert result["count"] == 2


# ---------------------------------------------------------------------------
# Whitelist check
# ---------------------------------------------------------------------------

class TestWhitelistCheck:
    def test_blocked_path_raises_tool_error(self, sample_db):
        with patch("tools.database._is_allowed_path", return_value=False):
            with pytest.raises(ToolError, match="Access denied"):
                run_sqlite_query(SqliteQueryInput(db_path=sample_db, query="SELECT 1"))

    def test_nonexistent_db_raises_tool_error(self):
        with patch("tools.database._is_allowed_path", return_value=True):
            with pytest.raises(ToolError, match="not found"):
                run_sqlite_query(SqliteQueryInput(
                    db_path="/nonexistent/path/db.sqlite",
                    query="SELECT 1"
                ))
