"""Audit `Cargo.lock` against RustSec security advisories."""

from __future__ import annotations

from tasknest import ToolContext, tool


@tool(marks=("security", "rust"), description="Audit Cargo.lock against RustSec advisories.")
def audit_rs(ctx: ToolContext) -> None:
    """Run `cargo audit --deny warnings` against `Cargo.lock`."""
    ctx.run(["cargo", "audit", "--deny", "warnings"], cwd=ctx.repo_root)
