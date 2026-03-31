# MCP Dev Toolkit

A personal MCP server that gives Claude a set of developer tools — filesystem access, shell commands, web search, SQLite queries, GitHub READMEs, and more. Built in Python as a hands-on way to learn the Model Context Protocol end-to-end.

## What's inside

### Tools

| Tool | What it does |
|---|---|
| `get_system_info` | OS, Python version, hostname, current directory |
| `read_file` | Read a file's contents (whitelist-restricted) |
| `list_directory` | List files and folders in a directory |
| `run_command` | Run a shell command from an allowlist |
| `fetch_github_readme` | Fetch the README of any public GitHub repo |
| `search_web` | Web search via Brave Search API |
| `run_sqlite_query` | Run a read-only SELECT against a local SQLite DB |
| `scan_directory_deep` | Recursively count files by extension, with live progress |
| `inspect_file` | File metadata + contents as separate content blocks |
| `explain_error` | Explain a Python error in plain English (uses MCP Sampling) |
| `suggest_fix` | Given code + error, return corrected code (uses MCP Sampling) |

### Resources

Resources are read-only data Claude can access. They appear in the Claude Desktop context panel.

| URI | What it contains |
|---|---|
| `project://pyproject.toml` | The current project's `pyproject.toml` |
| `project://git-log` | Last 20 commits (`git log --oneline`) |
| `project://directory-tree` | Recursive file tree, skipping hidden folders |

### Prompts

Reusable prompt templates surfaced as slash commands in Claude Desktop.

| Prompt | What it does |
|---|---|
| `review_file` | Prompts Claude to review a file for bugs, security issues, and quality |
| `summarize_repo` | Prompts Claude to explore and summarize the current repository |

---

## Setup

**Install dependencies:**

```bash
uv sync
```

**Create your whitelist config:**

```bash
cp whitelist.example.json whitelist.json
```

Edit `whitelist.json` — set which directories Claude can read and which shell commands it can run:

```json
{
  "allowed_paths": ["E:/your/projects"],
  "allowed_commands": ["git status", "git log", "python --version"]
}
```

**Create your env config:**

```bash
cp .env.example .env
```

Fill in API keys:

```
GITHUB_TOKEN=...      # optional, avoids GitHub rate limits
BRAVE_API_KEY=...     # required for search_web
```

---

## Running the server

### stdio — for Claude Desktop / Claude Code (default)

The server is spawned automatically by the client. You do not run it manually.

**Register with Claude Code (once):**

```bash
claude mcp add --scope user --transport stdio dev-toolkit -- uv run python <absolute_path_to_server.py>
```

Verify:
```bash
claude mcp list
claude mcp get dev-toolkit
```

**Register with Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dev-toolkit": {
      "command": "uv",
      "args": ["run", "python", "C:/path/to/server.py"]
    }
  }
}
```

### SSE — HTTP transport (legacy, widely supported)

```bash
python server.py --transport sse --port 8000
```

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dev-toolkit": {
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```

### Streamable HTTP — HTTP transport (modern, preferred)

```bash
python server.py --transport streamable-http --port 8000
```

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dev-toolkit": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

### CLI flags

```
--transport   stdio | sse | streamable-http  (default: stdio)
--host        bind address for HTTP transports (default: 127.0.0.1)
--port        port for HTTP transports        (default: 8000)
```

---

## Test it

Start a Claude session and try:

```
"Call get_system_info and tell me what OS I'm on"
"Use scan_directory_deep on E:/prashant/projects and show me the breakdown by extension"
"Use inspect_file on server.py"
"Fetch the GitHub README for modelcontextprotocol/python-sdk"
```

---

## Project layout

```
server.py              # entry point — registers all tools, resources, prompts
whitelist.json         # your personal allowlist (gitignored)
.env                   # your API keys (gitignored)
tools/
  system.py            # get_system_info
  filesystem.py        # read_file, list_directory, run_command
  resources.py         # MCP resource handlers
  external.py          # fetch_github_readme, search_web
  database.py          # run_sqlite_query + SqliteQueryInput schema
  prompts.py           # review_file, summarize_repo
  advanced.py          # scan_directory_deep, inspect_file
  sampling.py          # explain_error, suggest_fix (MCP Sampling)
dev-corner/
  requirements.md      # phased build plan
  knowledgebase.md     # concept explanations: tools vs resources, content types, etc.
```

---

## Troubleshooting

```bash
claude mcp get dev-toolkit     # inspect registered config
claude mcp remove dev-toolkit  # remove and re-add if config is wrong
```

Config lives in `~/.claude.json` and can be edited directly.

---

## Build plan

This server is built in phases to cover every MCP primitive. See [`dev-corner/requirements.md`](dev-corner/requirements.md) for the full plan and current status. Concept explanations live in [`dev-corner/knowledgebase.md`](dev-corner/knowledgebase.md).

| Phase | Topic | Status |
|---|---|---|
| 1 | Server setup, first tool, stdio | Done |
| 2 | Filesystem tools | Done |
| 3 | MCP Resources | Done |
| 4 | External APIs | Done |
| 5 | Prompts + SQLite | Done |
| 6 | Tool annotations, structured schemas, progress, multi-content | Done |
| 7 | SSE + Streamable HTTP transport | Done |
| 8 | Sampling (server → LLM loop-back) | Done |
| 9 | Resource subscriptions + file watching | Upcoming |
| 10 | Packaging + distribution | Upcoming |
