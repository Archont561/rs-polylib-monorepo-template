"""Lint all Gherkin `.feature` specifications with gherlint."""

from __future__ import annotations

from tasknest import ToolContext, tool

_FEATURE_GLOBS: tuple[str, ...] = (
    "conformance/*.feature",
    "crates/*/features/*.feature",
    "packages/*/features/*.feature",
)


@tool(
    marks=("fast", "ci"),
    description="Lint Gherkin .feature files in conformance/, crates/, and packages/.",
)
def lint_gherkin(ctx: ToolContext) -> None:
    """Run `gherlint` across shared conformance specs and unit feature specifications."""
    for pattern in _FEATURE_GLOBS:
        for path in sorted(ctx.repo_root.glob(pattern)):
            ctx.run(["gherlint", "lint", str(path.relative_to(ctx.repo_root))], cwd=ctx.repo_root)
