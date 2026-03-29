"""System tools — basic machine information."""

import os
import platform
import sys


def get_system_info() -> dict:
    """Returns basic system information: OS, Python version, and current directory."""
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "python_version": sys.version,
        "cwd": os.getcwd(),
        "hostname": platform.node(),
    }
