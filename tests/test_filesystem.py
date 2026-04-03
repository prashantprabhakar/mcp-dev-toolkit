"""
Tests for tools/filesystem.py

Strategy:
- Mock _load_config so tests never touch whitelist.json
- Use tmp_path (pytest fixture) for real temp files/dirs
- Call functions directly — no MCP server needed
"""

import pytest
from unittest.mock import patch
from mcp.server.fastmcp.exceptions import ToolError
from tools.filesystem import _is_allowed_path, read_file, list_directory, run_command


def mock_config(allowed_paths=None, allowed_commands=None):
    return {
        "allowed_paths": allowed_paths or [],
        "allowed_commands": allowed_commands or [],
    }


# ---------------------------------------------------------------------------
# _is_allowed_path
# ---------------------------------------------------------------------------

class TestIsAllowedPath:
    def test_path_inside_whitelist_is_allowed(self, tmp_path):
        config = mock_config(allowed_paths=[str(tmp_path)])
        with patch("tools.filesystem._load_config", return_value=config):
            assert _is_allowed_path(str(tmp_path / "file.txt")) is True

    def test_path_outside_whitelist_is_blocked(self, tmp_path):
        safe = tmp_path / "safe"
        safe.mkdir()
        config = mock_config(allowed_paths=[str(safe)])
        with patch("tools.filesystem._load_config", return_value=config):
            assert _is_allowed_path(str(tmp_path / "outside.txt")) is False

    def test_path_traversal_is_blocked(self, tmp_path):
        safe = tmp_path / "safe"
        safe.mkdir()
        config = mock_config(allowed_paths=[str(safe)])
        # ../../ tries to escape the safe dir
        traversal = str(safe / ".." / ".." / "etc" / "passwd")
        with patch("tools.filesystem._load_config", return_value=config):
            assert _is_allowed_path(traversal) is False

    def test_empty_whitelist_blocks_everything(self, tmp_path):
        config = mock_config(allowed_paths=[])
        with patch("tools.filesystem._load_config", return_value=config):
            assert _is_allowed_path(str(tmp_path / "file.txt")) is False


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

class TestReadFile:
    def test_reads_file_contents(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("hello world")
        config = mock_config(allowed_paths=[str(tmp_path)])
        with patch("tools.filesystem._load_config", return_value=config):
            result = read_file(str(f))
        assert result["contents"] == "hello world"
        assert result["path"] == str(f)

    def test_access_denied_for_blocked_path(self, tmp_path):
        f = tmp_path / "secret.txt"
        f.write_text("secret")
        config = mock_config(allowed_paths=[])
        with patch("tools.filesystem._load_config", return_value=config):
            with pytest.raises(ToolError, match="Access denied"):
                read_file(str(f))

    def test_file_not_found_raises_tool_error(self, tmp_path):
        config = mock_config(allowed_paths=[str(tmp_path)])
        with patch("tools.filesystem._load_config", return_value=config):
            with pytest.raises(ToolError, match="not found"):
                read_file(str(tmp_path / "nonexistent.txt"))

    def test_path_traversal_is_blocked(self, tmp_path):
        safe = tmp_path / "safe"
        safe.mkdir()
        (tmp_path / "outside.txt").write_text("secret")
        config = mock_config(allowed_paths=[str(safe)])
        traversal = str(safe / ".." / "outside.txt")
        with patch("tools.filesystem._load_config", return_value=config):
            with pytest.raises(ToolError, match="Access denied"):
                read_file(traversal)


# ---------------------------------------------------------------------------
# list_directory
# ---------------------------------------------------------------------------

class TestListDirectory:
    def test_lists_files_and_dirs(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        (tmp_path / "subdir").mkdir()
        config = mock_config(allowed_paths=[str(tmp_path)])
        with patch("tools.filesystem._load_config", return_value=config):
            result = list_directory(str(tmp_path))
        names = [e["name"] for e in result["entries"]]
        assert "a.txt" in names
        assert "b.txt" in names
        assert "subdir" in names

    def test_entry_types_are_correct(self, tmp_path):
        (tmp_path / "file.txt").write_text("x")
        (tmp_path / "folder").mkdir()
        config = mock_config(allowed_paths=[str(tmp_path)])
        with patch("tools.filesystem._load_config", return_value=config):
            result = list_directory(str(tmp_path))
        by_name = {e["name"]: e["type"] for e in result["entries"]}
        assert by_name["file.txt"] == "file"
        assert by_name["folder"] == "directory"

    def test_access_denied_for_blocked_path(self, tmp_path):
        config = mock_config(allowed_paths=[])
        with patch("tools.filesystem._load_config", return_value=config):
            with pytest.raises(ToolError, match="Access denied"):
                list_directory(str(tmp_path))

    def test_directory_not_found_raises_tool_error(self, tmp_path):
        config = mock_config(allowed_paths=[str(tmp_path)])
        with patch("tools.filesystem._load_config", return_value=config):
            with pytest.raises(ToolError, match="not found"):
                list_directory(str(tmp_path / "nonexistent"))


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------

class TestRunCommand:
    def test_allowed_command_runs_successfully(self):
        config = mock_config(allowed_commands=["python --version"])
        with patch("tools.filesystem._load_config", return_value=config):
            result = run_command("python --version")
        assert result["exit_code"] == 0
        assert result["command"] == "python --version"

    def test_blocked_command_raises_tool_error(self):
        config = mock_config(allowed_commands=["git status"])
        with patch("tools.filesystem._load_config", return_value=config):
            with pytest.raises(ToolError, match="not allowed"):
                run_command("rm -rf /")

    def test_command_injection_is_blocked(self):
        # "git status; rm -rf /" is not in the allowlist — exact match required
        config = mock_config(allowed_commands=["git status"])
        with patch("tools.filesystem._load_config", return_value=config):
            with pytest.raises(ToolError, match="not allowed"):
                run_command("git status; rm -rf /")

    def test_empty_allowlist_blocks_everything(self):
        config = mock_config(allowed_commands=[])
        with patch("tools.filesystem._load_config", return_value=config):
            with pytest.raises(ToolError, match="not allowed"):
                run_command("git status")
