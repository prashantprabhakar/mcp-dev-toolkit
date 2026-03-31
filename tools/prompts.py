"""MCP Prompts — reusable prompt templates."""


def review_file(file_path: str) -> str:
    """Generate a prompt to review a file for bugs, security issues, and code quality."""
    return f"""Please review the file at: {file_path}

Use the read_file tool to read it, then look for:
- Bugs or logical errors
- Security vulnerabilities
- Code quality and readability issues
- Specific suggestions for improvement

Be direct and prioritise the most important findings."""


def summarize_repo() -> str:
    """Generate a prompt to explore and summarize the current repository."""
    return """Please summarize this repository.

Steps:
1. Use get_directory_tree to see the project structure
2. Use read_file to read key files (README, pyproject.toml, main source files)
3. Provide a summary covering:
   - What the project does
   - How it's structured
   - Tech stack
   - Anything notable or worth knowing"""
