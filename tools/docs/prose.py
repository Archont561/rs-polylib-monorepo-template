"""Lint English technical documentation prose with Vale.

Runs every style enabled in `.vale.ini`: the Microsoft Writing Style Guide
preset, the alex inclusive-language package, and the house `Polyglot` rules.
"""

from __future__ import annotations

from pathlib import Path

from tasknest import ToolContext, tool

_CONTENT_DIR = Path("docs/content/docs")


def _vale_targets(ctx: ToolContext) -> list[str]:
    """Collect every prose file Vale must check, including all MDX pages."""
    content_dir = ctx.repo_root / _CONTENT_DIR
    targets = ["README.md", "AGENTS.md"]
    pages = sorted(content_dir.rglob("*.mdx"))
    targets.extend(str(path.relative_to(ctx.repo_root)) for path in pages)
    return targets


@tool(
    marks=("fast", "ci", "docs"),
    description="Lint English technical prose with Vale (Microsoft, alex, and house styles).",
)
def lint_prose(ctx: ToolContext, sync: bool = False) -> None:
    """Run Vale over the top-level documentation and every MDX page."""
    if sync:
        ctx.run(["vale", "sync"], cwd=ctx.repo_root)
    ctx.run(["vale", *_vale_targets(ctx)], cwd=ctx.repo_root)
