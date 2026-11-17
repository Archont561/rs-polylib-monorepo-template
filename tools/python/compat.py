"""Run Python wheel and sdist compatibility verification."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tasknest import ToolContext, tool

from tools._lib.compat_py import verify_py_compat
from tools._lib.verification import reports_verification

if TYPE_CHECKING:
    from tools._lib.status import CheckResult


@tool(
    marks=("ci", "python", "rust", "compat"),
    description="Build polylib wheel/sdist with maturin and verify metadata + venv smoke.",
)
@reports_verification("Python compatibility")
def py_compat(ctx: ToolContext) -> list[CheckResult]:
    """Verify `packages/polylib-py` wheel/sdist build, metadata, and clean virtualenv import."""
    return verify_py_compat(ctx.repo_root)
