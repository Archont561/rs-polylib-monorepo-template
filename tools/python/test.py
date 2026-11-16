"""Run Python unit, BDD, Hypothesis property, and conformance tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

from tasknest import ToolContext, tool

from tools._lib.coverage import (
    LCOV_FILENAME,
    MIN_COVERAGE_PERCENT,
    coverage_dir,
    enforce_threshold,
    merge_lcov_files,
)

_LANG_PY = "python"
_PY_PREFIXES: tuple[str, ...] = ("packages/polylib-py/src/",)


@tool(
    marks=("ci", _LANG_PY),
    description="Run pytest over packages/polylib-py/tests (optional coverage/python >= 90%).",
)
def test_py(
    ctx: ToolContext,
    coverage: bool = False,
    min_coverage: float = MIN_COVERAGE_PERCENT,
) -> None:
    """Execute Python library tests with optional LCOV coverage export and threshold."""
    if not coverage:
        ctx.run(["pytest", "-v"], cwd=ctx.repo_root)
        return
    out_dir = coverage_dir(ctx.repo_root, _LANG_PY)
    report_path = out_dir / LCOV_FILENAME
    with tempfile.TemporaryDirectory(prefix="polylib-py-cov-") as tmp_str:
        raw_lcov = Path(tmp_str) / LCOV_FILENAME
        argv = [
            "pytest",
            "-v",
            "--cov=polylib",
            f"--cov-report=lcov:{raw_lcov}",
            "--cov-report=term-missing",
            f"--cov-fail-under={min_coverage:g}",
        ]
        ctx.run(argv, cwd=ctx.repo_root)
        stats = merge_lcov_files(
            [(raw_lcov, ctx.repo_root)],
            report_path,
            ctx.repo_root,
            include_prefixes=_PY_PREFIXES,
        )
    enforce_threshold(_LANG_PY, report_path, stats, min_percent=min_coverage)
