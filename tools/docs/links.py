"""Verify documentation links with lychee."""

from __future__ import annotations

from tasknest import ToolContext, tool


@tool(marks=("fast", "ci", "docs"), description="Verify documentation links using lychee.")
def lint_links(ctx: ToolContext, online: bool = False) -> None:
    """Check Markdown and MDX links (offline by default; pass `--online` for live URLs)."""
    argv = ["lychee", "--config", "lychee.toml"]
    if not online:
        argv.append("--offline")
    argv.extend(["README.md", "AGENTS.md", "crates", "packages", "docs"])
    ctx.run(argv, cwd=ctx.repo_root)
