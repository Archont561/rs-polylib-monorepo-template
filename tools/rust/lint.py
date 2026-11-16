"""Lint and format-check the Rust workspace."""

from __future__ import annotations

from tasknest import ToolContext, tool


@tool(
    marks=("ci", "rust"),
    description="Run cargo fmt --check and cargo clippy (-D warnings) across the Rust workspace.",
)
def lint_rs(ctx: ToolContext) -> None:
    """Verify Rust formatting and Clippy lints across all targets and features."""
    ctx.run(["cargo", "fmt", "--all", "--", "--check"], cwd=ctx.repo_root)
    ctx.run(
        [
            "cargo",
            "clippy",
            "--workspace",
            "--all-targets",
            "--all-features",
            "--locked",
            "--",
            "-D",
            "warnings",
        ],
        cwd=ctx.repo_root,
    )
