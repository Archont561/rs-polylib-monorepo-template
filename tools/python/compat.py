"""Run Python wheel and sdist compatibility verification."""

from __future__ import annotations

from tasknest import ToolContext, tool

from tools._lib.compat_py import verify_py_compat


@tool(
    marks=("ci", "python", "rust", "compat"),
    description="Build polylib wheel/sdist with maturin and verify metadata + venv smoke.",
)
def py_compat(ctx: ToolContext) -> None:
    """Verify `packages/polylib-py` wheel/sdist build, metadata, and clean virtualenv import."""
    verify_py_compat(ctx.repo_root)
