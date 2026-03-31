"""External API tools — GitHub and web search."""

import os
import httpx


def fetch_github_readme(owner: str, repo: str) -> dict:
    """
    Fetch the README of a public GitHub repository.
    Provide the owner (username or org) and repo name.
    Optionally set the GITHUB_TOKEN environment variable to avoid rate limits.
    """
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
            return {"owner": owner, "repo": repo, "readme": resp.text}
        return {"error": f"GitHub API returned {resp.status_code} for {owner}/{repo}"}
    except Exception as e:
        return {"error": str(e)}


def search_web(query: str) -> dict:
    """
    Search the web using the Brave Search API.
    Requires the BRAVE_API_KEY environment variable to be set.
    Returns the top 5 results with title, URL, and description.
    """
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        return {"error": "BRAVE_API_KEY environment variable is not set."}

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
            return {"error": f"Brave API returned {resp.status_code}"}

        results = [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "description": item.get("description"),
            }
            for item in resp.json().get("web", {}).get("results", [])
        ]
        return {"query": query, "results": results}
    except Exception as e:
        return {"error": str(e)}
