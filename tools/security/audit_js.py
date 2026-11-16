"""Audit Bun workspace packages for known vulnerabilities."""

from __future__ import annotations

from tasknest import ToolContext, tool


@tool(marks=("security", "ts"), description="Audit Bun workspace packages for vulnerabilities.")
def audit_js(ctx: ToolContext, level: str = "high") -> None:
    """Run `bun audit --audit-level <level>`."""
    ctx.run(["bun", "audit", "--audit-level", level], cwd=ctx.repo_root)
