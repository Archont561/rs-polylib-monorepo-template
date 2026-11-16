"""Check every feature boundary declared by the `polylib` Rust metacrate."""

from __future__ import annotations

from tasknest import ToolContext, ToolError, tool

from tools._lib.compat_rs import check_features as run_feature_checks


@tool(
    marks=("ci", "rust", "compat"),
    description="Compile every manifest-derived feature combination of crates/polylib.",
)
def check_features(ctx: ToolContext, toolchain: str = "") -> None:
    """Verify `--no-default-features`, each feature alone, and `--all-features`."""
    try:
        run_feature_checks(ctx.repo_root, toolchain=toolchain or None)
    except RuntimeError as exc:
        raise ToolError(str(exc)) from exc
