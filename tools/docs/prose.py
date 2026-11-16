"""Lint English technical documentation prose with Vale (Microsoft preset)."""

from __future__ import annotations

from tasknest import ToolContext, tool


@tool(
    marks=("fast", "ci", "docs"),
    description="Lint English technical prose with Vale using the Microsoft style preset.",
)
def lint_prose(ctx: ToolContext, sync: bool = False) -> None:
    """Run Vale (Microsoft Writing Style Guide) over top-level documentation."""
    if sync:
        ctx.run(["vale", "sync"], cwd=ctx.repo_root)
    ctx.run(
        ["vale", "README.md", "AGENTS.md", "apps/docs/content/docs/index.mdx"],
        cwd=ctx.repo_root,
    )
