"""Run repository layout, schema, and import-boundary checks with alint."""

from __future__ import annotations

from tasknest import ToolContext, tool


@tool(marks=("fast", "ci"), description="Run alint repository policy, schema, and boundary checks.")
def alint(ctx: ToolContext) -> None:
    """Execute `alint check` against `.alint.yml`."""
    ctx.run(["alint", "check"], cwd=ctx.repo_root)
