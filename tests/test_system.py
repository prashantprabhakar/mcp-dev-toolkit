"""Tests for tools/system.py — no mocking needed, pure stdlib."""

from tools.system import get_system_info


def test_returns_all_expected_keys():
    result = get_system_info()
    assert {"os", "os_version", "python_version", "cwd", "hostname"} <= result.keys()


def test_all_values_are_strings():
    result = get_system_info()
    for key, value in result.items():
        assert isinstance(value, str), f"Expected str for '{key}', got {type(value)}"


def test_python_version_looks_right():
    result = get_system_info()
    # e.g. "3.11.9 (main, ...)"
    assert result["python_version"].startswith("3.")


def test_cwd_is_absolute_path():
    import os
    result = get_system_info()
    assert os.path.isabs(result["cwd"])
