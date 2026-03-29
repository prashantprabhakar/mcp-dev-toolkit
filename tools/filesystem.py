"""
Filesystem tools

All tools here check the requested path against whitelist.json
before touching anything on disk.
"""

import json
import os
import subprocess

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


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def read_file(path: str) -> dict:
    """
    Read and return the contents of a file at the given path.
    The path must be inside one of the whitelisted directories in whitelist.json.
    Returns the file contents as a string, or an error if access is denied or the file doesn't exist.
    """
    if not _is_allowed_path(path):
        return {"error": f"Access denied: {path} is not in the whitelist."}
    if not os.path.isfile(path):
        return {"error": f"File not found: {path}"}
    try:
        with open(path, encoding="utf-8") as f:
            return {"path": path, "contents": f.read()}
    except Exception as e:
        return {"error": str(e)}


def list_directory(path: str) -> dict:
    """
    List files and folders in the given directory path.
    The path must be inside one of the whitelisted directories in whitelist.json.
    Returns a list of entries with their name and type (file or directory).
    """
    if not _is_allowed_path(path):
        return {"error": f"Access denied: {path} is not in the whitelist."}
    if not os.path.isdir(path):
        return {"error": f"Directory not found: {path}"}
    try:
        entries = []
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            entries.append({
                "name": name,
                "type": "directory" if os.path.isdir(full) else "file",
            })
        return {"path": path, "entries": entries}
    except Exception as e:
        return {"error": str(e)}


def run_command(command: str) -> dict:
    """
    Run a shell command from the allowlist and return its output.
    Only commands explicitly listed in the allowlist are permitted.
    Returns stdout, stderr, and the exit code.
    """
    if not _is_allowed_command(command):
        allowed = _load_config()["allowed_commands"]
        return {"error": f"Command not allowed: '{command}'. Allowed commands: {allowed}"}
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out: {command}"}
    except Exception as e:
        return {"error": str(e)}
