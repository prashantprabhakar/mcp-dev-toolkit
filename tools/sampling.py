"""
Sampling tools

Sampling is the MCP primitive where the *server* calls back into the LLM mid-execution.
The round-trip is:
  Claude calls tool → server sends sampling/createMessage to client
  → client forwards to LLM → LLM responds → client returns result to server
  → server returns final answer to Claude

FastMCP's Context has no .sample() shorthand — sampling goes through
ctx.request_context.session.create_message() with explicit SamplingMessage objects.

The client (Claude Desktop) controls whether sampling is permitted and will prompt
the user to approve the request.
"""

from mcp.server.fastmcp import Context
from mcp.types import SamplingMessage, TextContent


async def explain_error(error_message: str, ctx: Context) -> str:
    """
    Explain a Python error or stack trace in plain English using sampling.
    Paste a raw error message and get a clear, jargon-free explanation of what
    went wrong and how to fix it.

    This tool uses MCP Sampling — the server calls back into the LLM to generate
    the explanation, then returns the result.
    """
    prompt = (
        "You are a helpful Python tutor. "
        "Explain the following error in plain English — what caused it and how to fix it. "
        "Be concise and direct. Do not repeat the error back verbatim.\n\n"
        f"Error:\n{error_message}"
    )

    result = await ctx.request_context.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=prompt),
            )
        ],
        max_tokens=500,
    )

    # result.content is TextContent | ImageContent | AudioContent
    # For a text prompt, the LLM will always return TextContent.
    if hasattr(result.content, "text"):
        return result.content.text

    return f"[Unexpected response type: {type(result.content).__name__}]"


async def suggest_fix(code: str, error_message: str, ctx: Context) -> str:
    """
    Given a code snippet and an error it produced, suggest a corrected version.
    Uses MCP Sampling to ask the LLM to rewrite just the broken part.

    This demonstrates chaining context into a sampling call — the server
    sends both the code and the error together as a single structured prompt.
    """
    prompt = (
        "You are a Python code reviewer. "
        "The following code produced an error. "
        "Show the corrected code only — no explanation, no markdown fences.\n\n"
        f"Code:\n{code}\n\n"
        f"Error:\n{error_message}"
    )

    result = await ctx.request_context.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=prompt),
            )
        ],
        max_tokens=1000,
        system_prompt="Return only the corrected Python code. No prose, no code fences.",
    )

    if hasattr(result.content, "text"):
        return result.content.text

    return f"[Unexpected response type: {type(result.content).__name__}]"
