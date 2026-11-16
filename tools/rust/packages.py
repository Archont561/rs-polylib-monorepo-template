"""Rehearse crates.io tarball contents and metadata offline."""

from __future__ import annotations

from tasknest import ToolContext, ToolError, tool

from tools._lib.compat_rs import check_packages as run_package_checks


@tool(
    marks=("ci", "rust", "compat"),
    description="Verify `cargo package --list` contents and metadata for publishable crates.",
)
def check_packages(ctx: ToolContext) -> None:
    """Check `polylib-core` and `polylib` package file lists and workspace metadata."""
    try:
        run_package_checks(ctx.repo_root)
    except RuntimeError as exc:
        raise ToolError(str(exc)) from exc
