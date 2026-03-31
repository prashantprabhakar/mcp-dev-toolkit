"""
Resource subscriptions

Covers two new MCP concepts:
  1. resources/subscribe  — client asks server to be notified when a resource changes
  2. notifications/resources/updated — server pushes the notification when it detects a change

The resource we watch: project://config → whitelist.json
When the file changes on disk, every subscribed session gets a ResourceUpdatedNotification.

Implementation notes:
  - FastMCP has no built-in subscription support — we drop down to the low-level server.
  - get_capabilities() hardcodes subscribe=False, so we monkey-patch it after setup.
  - File watching uses asyncio polling (mtime comparison) — no extra dependencies.
  - Subscribed sessions are tracked in a module-level set; the background task iterates it.
"""

import asyncio
import os

CONFIG_RESOURCE_URI = "project://config"
_WHITELIST_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "whitelist.json")
)


def get_config_resource() -> str:
    """Contents of whitelist.json — the server's path and command allowlist."""
    if not os.path.isfile(_WHITELIST_PATH):
        return '{"error": "whitelist.json not found"}'
    with open(_WHITELIST_PATH) as f:
        return f.read()


async def watch_whitelist(
    subscribed_sessions: set,
    poll_interval: float = 1.0,
) -> None:
    """
    Background task: poll whitelist.json every `poll_interval` seconds.
    When the file's mtime changes, send ResourceUpdatedNotification to every
    session that has subscribed to project://config.

    This runs for the lifetime of the server (cancelled on shutdown via lifespan).
    """
    from pydantic import AnyUrl

    uri = AnyUrl(CONFIG_RESOURCE_URI)
    last_mtime: float = _get_mtime()

    while True:
        await asyncio.sleep(poll_interval)
        current_mtime = _get_mtime()
        if current_mtime != last_mtime:
            last_mtime = current_mtime
            # Notify all subscribed sessions; silently drop dead ones.
            dead = set()
            for session in list(subscribed_sessions):
                try:
                    await session.send_resource_updated(uri)
                except Exception:
                    dead.add(session)
            subscribed_sessions -= dead


def _get_mtime() -> float:
    try:
        return os.path.getmtime(_WHITELIST_PATH)
    except OSError:
        return 0.0
