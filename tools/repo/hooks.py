"""Install lefthook git hooks into `.git/hooks`."""

from __future__ import annotations

from tasknest import ToolContext, tool


@tool(marks=("writes",), description="Install lefthook git hooks into .git/hooks.")
def hooks_install(ctx: ToolContext) -> None:
    """Install configured `lefthook.yml` git hooks."""
    ctx.run(["lefthook", "install"], cwd=ctx.repo_root)
