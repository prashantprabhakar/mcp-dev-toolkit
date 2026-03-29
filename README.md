# MCP Dev Toolkit

A personal MCP server that gives Claude a set of developer tools. Built in Python, connected via stdio transport.

## Setup

**Install dependencies (one time):**

```bash
uv sync
```

## Register with Claude Code

Run this once from the project directory:

```bash
claude mcp add --scope user --transport stdio dev-toolkit -- uv run python E:/prashant/projects/ai/mcp/mcp-dev-toolkit/server.py
```

Verify it's registered:

```bash
claude mcp list
```

You do not run the server manually. Claude Code launches it automatically when a tool is needed.

## Test it

Start a Claude Code session and ask:

> "Call get_system_info and tell me what OS I'm on"

## Troubleshooting

```bash
claude mcp get dev-toolkit     # inspect config
claude mcp remove dev-toolkit  # remove and re-add
```

Config is stored in `~/.claude.json` and can be edited directly.

## Phases

See `requirements.md` for the full build plan.
