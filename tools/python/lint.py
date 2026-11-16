"""Lint and type-check Python library code and automation tools."""

from __future__ import annotations

from tasknest import ToolContext, tool

_TOOLS_DIR = "tools"
_PY_PKG = "packages/polylib-py"
_PY_SRC = f"{_PY_PKG}/src"


@tool(
    marks=("fast", "ci", "python"),
    description="Run Ruff lint/format, strict Mypy, and rude-clean-code over Python sources.",
)
def lint_py(ctx: ToolContext, fix: bool = False) -> None:
    """Run Ruff, Mypy, and Rude (`rude-clean-code`) across `packages/polylib-py` and `tools`."""
    ruff_argv = ["ruff", "check", _PY_PKG, _TOOLS_DIR]
    if fix:
        ruff_argv.append("--fix")
    ctx.run(ruff_argv, cwd=ctx.repo_root)
    fmt_argv = ["ruff", "format", _PY_PKG, _TOOLS_DIR]
    if not fix:
        fmt_argv.insert(2, "--check")
    ctx.run(fmt_argv, cwd=ctx.repo_root)
    ctx.run(["mypy", _PY_SRC, f"{_PY_PKG}/tests", _TOOLS_DIR], cwd=ctx.repo_root)
    ctx.run(["rude", "check", _PY_SRC, _TOOLS_DIR], cwd=ctx.repo_root)
