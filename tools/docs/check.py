"""Verify Jinja2-generated docs and GitHub templates have zero drift."""

from __future__ import annotations

from tasknest import ToolContext, tool

from tools._lib.docs import sync_docs


@tool(
    marks=("fast", "ci", "docs"),
    description="Check README.md, AGENTS.md, and .github templates against templates/.",
)
def docs_check(ctx: ToolContext) -> None:
    """Fail if any managed generated document differs from its Jinja2 template."""
    sync_docs(ctx.repo_root, check_only=True)
