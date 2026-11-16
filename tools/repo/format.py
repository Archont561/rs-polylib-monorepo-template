"""Check formatting across Python, TypeScript/JSON, TOML, and Markdown."""

from __future__ import annotations

from tasknest import ToolContext, tool

_CHECK_FLAG = "--check"


@tool(
    marks=("fast", "ci"),
    description="Verify formatting for Python, TypeScript/JSON, TOML, and Markdown.",
)
def format_check(ctx: ToolContext, include_rust: bool = False) -> None:
    """Verify formatting across repository files without modifying them."""
    ctx.run(["ruff", "format", _CHECK_FLAG, "packages/polylib-py", "tools"], cwd=ctx.repo_root)
    ctx.run(["taplo", "fmt", _CHECK_FLAG], cwd=ctx.repo_root)
    ctx.run(["bun", "x", "--bun", "--no-install", "biome", "check", "."], cwd=ctx.repo_root)
    ctx.run(["rumdl", "check", "--deny-config-warnings", "."], cwd=ctx.repo_root)
    if include_rust:
        ctx.run(["cargo", "fmt", "--all", "--", _CHECK_FLAG], cwd=ctx.repo_root)
