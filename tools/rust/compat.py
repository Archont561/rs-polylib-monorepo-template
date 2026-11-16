"""Run full Cargo compatibility gate (features, packages, isolated `.crate` consumer)."""

from __future__ import annotations

from tasknest import ToolContext, ToolError, tool

from tools._lib.compat_rs import check_features, check_packages, verify_crate_consumer


@tool(
    marks=("ci", "rust", "compat"),
    description="Verify Rust feature boundaries, tarballs, and isolated .crate consumer builds.",
)
def rs_compat(ctx: ToolContext) -> None:
    """Run manifest feature checks, `cargo package --list`, and unpacked `.crate` smoke builds."""
    try:
        check_features(ctx.repo_root)
        check_packages(ctx.repo_root)
        verify_crate_consumer(ctx.repo_root)
    except RuntimeError as exc:
        raise ToolError(str(exc)) from exc
