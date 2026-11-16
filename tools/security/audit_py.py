"""Audit Python environment dependencies via `pip-audit`."""

from __future__ import annotations

from tasknest import ToolContext, tool


@tool(
    marks=("security", "python"),
    description="Audit Python environment dependencies via pip-audit.",
)
def audit_py(ctx: ToolContext) -> None:
    """Run `pip-audit` against the active Python environment."""
    ctx.run(["pip-audit"], cwd=ctx.repo_root)
