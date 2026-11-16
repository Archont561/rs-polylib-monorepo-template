"""Starter greeting task verifying Tasknest discovery."""

from __future__ import annotations

from tasknest import ToolContext, tool


@tool(marks=("fast",), description="Print a greeting from the polyglot Tasknest workspace.")
def hello(ctx: ToolContext, name: str = "world") -> None:
    """Print a greeting showing the active repository root."""
    print(f"Hello, {name}! ({ctx.repo_root.name})")
