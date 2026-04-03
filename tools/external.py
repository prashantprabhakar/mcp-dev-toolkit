"""External API tools — GitHub and web search."""

import os

import httpx

from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.utilities.logging import get_logger

logger = get_logger(__name__)


def fetch_github_readme(owner: str, repo: str) -> dict:
    """
    Fetch the README of a public GitHub repository.
    Provide the owner (username or org) and repo name.
    Optionally set the GITHUB_TOKEN environment variable to avoid rate limits.
    """
    logger.debug("fetch_github_readme: %s/%s", owner, repo)
    headers = {"Accept": "application/vnd.github.v3.raw"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with httpx.Client() as client:
            resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/readme",
                headers=headers,
                timeout=10,
            )
        if resp.status_code == 200:
            logger.debug("fetch_github_readme: got %d bytes for %s/%s", len(resp.text), owner, repo)
            return {"owner": owner, "repo": repo, "readme": resp.text}
        logger.warning("fetch_github_readme: GitHub returned %d for %s/%s", resp.status_code, owner, repo)
        raise ToolError(f"GitHub API returned {resp.status_code} for '{owner}/{repo}'.")
    except ToolError:
        raise
    except Exception as e:
        logger.error("fetch_github_readme: unexpected error for %s/%s: %s", owner, repo, e)
        raise ToolError(f"Request failed: {e}") from e


def search_web(query: str) -> dict:
    """
    Search the web using the Brave Search API.
    Requires the BRAVE_API_KEY environment variable to be set.
    Returns the top 5 results with title, URL, and description.
    """
    logger.debug("search_web: %s", query)
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        raise ToolError("BRAVE_API_KEY environment variable is not set.")
    try:
        with httpx.Client() as client:
            resp = client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": api_key,
                },
                params={"q": query, "count": 5},
                timeout=10,
            )
        if resp.status_code != 200:
            logger.warning("search_web: Brave API returned %d", resp.status_code)
            raise ToolError(f"Brave Search API returned {resp.status_code}.")
        results = [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "description": item.get("description"),
            }
            for item in resp.json().get("web", {}).get("results", [])
        ]
        logger.debug("search_web: %d results for '%s'", len(results), query)
        return {"query": query, "results": results}
    except ToolError:
        raise
    except Exception as e:
        logger.error("search_web: unexpected error for '%s': %s", query, e)
        raise ToolError(f"Request failed: {e}") from e
