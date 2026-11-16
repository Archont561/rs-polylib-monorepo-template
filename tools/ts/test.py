"""Run TypeScript unit, property, and conformance tests with Bun."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from tasknest import ToolContext, tool

from tools._lib.coverage import (
    LCOV_FILENAME,
    MIN_COVERAGE_PERCENT,
    coverage_dir,
    enforce_threshold,
    merge_lcov_files,
)

if TYPE_CHECKING:
    from pathlib import Path

_LANG_TS = "ts"
_TS_PACKAGES: tuple[str, ...] = ("polylib-wasm", "polylib-js", "polylib-ts")
_TS_PREFIXES: tuple[str, ...] = (
    "packages/polylib-wasm/src/",
    "packages/polylib-js/src/",
    "packages/polylib-ts/src/",
)
_TS_EXCLUDES: tuple[str, ...] = ("/src/wasm/", "/src/native/")


@tool(
    marks=("ci", _LANG_TS),
    description="Run bun test across TS packages (optional merged coverage/ts >= 90%).",
)
def test_ts(
    ctx: ToolContext,
    coverage: bool = False,
    min_coverage: float = MIN_COVERAGE_PERCENT,
) -> None:
    """Execute WASM, NAPI-RS, and unified TypeScript facade test suites."""
    if not coverage:
        for pkg in _TS_PACKAGES:
            ctx.run(["bun", "test"], cwd=ctx.repo_root / "packages" / pkg)
        return
    out_dir = coverage_dir(ctx.repo_root, _LANG_TS)
    sources: list[tuple[Path, Path]] = []
    for pkg in _TS_PACKAGES:
        pkg_dir = ctx.repo_root / "packages" / pkg
        pkg_cov = out_dir / pkg
        if pkg_cov.exists():
            shutil.rmtree(pkg_cov)
        ctx.run(["bun", "test", "--coverage"], cwd=pkg_dir)
        sources.append((pkg_cov / LCOV_FILENAME, pkg_dir))
    report_path = out_dir / LCOV_FILENAME
    stats = merge_lcov_files(
        sources,
        report_path,
        ctx.repo_root,
        include_prefixes=_TS_PREFIXES,
        exclude_fragments=_TS_EXCLUDES,
    )
    for pkg in _TS_PACKAGES:
        shutil.rmtree(out_dir / pkg, ignore_errors=True)
    enforce_threshold(_LANG_TS, report_path, stats, min_percent=min_coverage)
