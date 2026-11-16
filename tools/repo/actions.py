"""Lint GitHub Actions workflows with actionlint and pinned shellcheck."""

from __future__ import annotations

from tasknest import ToolContext, tool


@tool(
    marks=("fast", "ci"),
    description="Validate GitHub Actions workflows with actionlint and shellcheck.",
)
def lint_actions(ctx: ToolContext) -> None:
    """Run `actionlint` against all workflow YAML files."""
    workflows = sorted(
        str(path.relative_to(ctx.repo_root))
        for path in (ctx.repo_root / ".github" / "workflows").glob("*.yml")
    )
    if workflows:
        ctx.run(["actionlint", *workflows], cwd=ctx.repo_root)
