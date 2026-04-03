# MCP Dev Toolkit — convenience scripts
# Usage: make <target>

HOST := 127.0.0.1
PORT := 8000

.PHONY: stdio http sse install test

## Run server over stdio (Claude Desktop / Claude Code)
stdio:
	uv run python server.py --transport stdio

## Run server over Streamable HTTP
http:
	uv run python server.py --transport streamable-http --host $(HOST) --port $(PORT)

## Run server over SSE (legacy HTTP transport)
sse:
	uv run python server.py --transport sse --host $(HOST) --port $(PORT)

## Install dependencies
install:
	uv sync

## Run tests
test:
	uv run pytest
