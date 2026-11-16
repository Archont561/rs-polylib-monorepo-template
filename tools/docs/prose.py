"""Lint English technical documentation prose with Vale (Microsoft preset)."""

from __future__ import annotations

from pathlib import Path

from tasknest import ToolContext, tool

_CONTENT_DIR = Path("apps/docs/content/docs")


def _vale_targets(ctx: ToolContext) -> list[str]:
    """Collect every prose file Vale must check, including all MDX pages."""
    content_dir = ctx.repo_root / _CONTENT_DIR
    targets = ["README.md", "AGENTS.md"]
    pages = sorted(content_dir.rglob("*.mdx"))
    targets.extend(str(path.relative_to(ctx.repo_root)) for path in pages)
    return targets


@tool(
    marks=("fast", "ci", "docs"),
    description="Lint English technical prose with Vale using the Microsoft style preset.",
)
def lint_prose(ctx: ToolContext, sync: bool = False) -> None:
    """Run Vale (Microsoft Writing Style Guide) over top-level documentation."""
    if sync:
        ctx.run(["vale", "sync"], cwd=ctx.repo_root)
    ctx.run(["vale", *_vale_targets(ctx)], cwd=ctx.repo_root)
