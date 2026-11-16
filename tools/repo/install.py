"""Install frozen Bun workspace dependencies."""

from __future__ import annotations

from tasknest import ToolContext, tool


@tool(marks=("writes", "ts"), description="Install frozen Bun workspace dependencies.")
def install(ctx: ToolContext, frozen: bool = True) -> None:
    """Install Bun workspace packages from `bun.lock`."""
    argv = ["bun", "install"]
    if frozen:
        argv.append("--frozen-lockfile")
    ctx.run(argv, cwd=ctx.repo_root)
