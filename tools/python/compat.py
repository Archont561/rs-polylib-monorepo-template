"""Run Python wheel and sdist compatibility verification."""

from __future__ import annotations

from tasknest import ToolContext, ToolError, tool

from tools._lib.compat_py import verify_py_compat
from tools._lib.status import publish_ready, render


@tool(
    marks=("ci", "python", "rust", "compat"),
    description="Build polylib wheel/sdist with maturin and verify metadata + venv smoke.",
)
def py_compat(ctx: ToolContext) -> None:
    """Verify `packages/polylib-py` wheel/sdist build, metadata, and clean virtualenv import."""
    results = verify_py_compat(ctx.repo_root)
    print(render(results))
    if not publish_ready(results):
        raise ToolError("Python compatibility did not fully pass; see the lanes above.")
