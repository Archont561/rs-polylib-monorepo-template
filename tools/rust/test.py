"""Run Rust unit, integration, BDD, conformance, and documentation tests."""

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

_LANG_RUST = "rust"
_CARGO = "cargo"
_WORKSPACE_FLAGS: tuple[str, ...] = ("--workspace", "--all-features", "--locked")
_COV_CRATE_FLAGS: tuple[str, ...] = (
    "-p",
    "polylib-core",
    "-p",
    "polylib",
    "--all-features",
    "--locked",
)
_RUST_PREFIXES: tuple[str, ...] = ("crates/polylib-core/src/", "crates/polylib/src/")


def _run_rust_coverage(ctx: ToolContext, min_coverage: float) -> None:
    out_dir = coverage_dir(ctx.repo_root, _LANG_RUST)
    report_path = out_dir / LCOV_FILENAME
    with tempfile.TemporaryDirectory(prefix="polylib-rs-cov-") as tmp_str:
        raw_lcov = Path(tmp_str) / LCOV_FILENAME
        cmd = [
            _CARGO,
            "llvm-cov",
            "nextest",
            *_COV_CRATE_FLAGS,
            "--lcov",
            "--output-path",
            str(raw_lcov),
            "--fail-under-lines",
            f"{min_coverage:g}",
        ]
        ctx.run(cmd, cwd=ctx.repo_root)
        stats = merge_lcov_files(
            [(raw_lcov, ctx.repo_root)],
            report_path,
            ctx.repo_root,
            include_prefixes=_RUST_PREFIXES,
        )
    enforce_threshold(_LANG_RUST, report_path, stats, min_percent=min_coverage)


@tool(
    marks=("ci", _LANG_RUST),
    description="Run cargo nextest and cargo doc tests (optional coverage/rust >= 90%).",
)
def test_rs(
    ctx: ToolContext,
    coverage: bool = False,
    min_coverage: float = MIN_COVERAGE_PERCENT,
) -> None:
    """Execute Rust tests via `cargo nextest` (or `cargo llvm-cov`) plus doc tests."""
    if coverage:
        _run_rust_coverage(ctx, min_coverage)
    else:
        ctx.run([_CARGO, "nextest", "run", *_WORKSPACE_FLAGS], cwd=ctx.repo_root)
    ctx.run([_CARGO, "test", *_WORKSPACE_FLAGS, "--doc"], cwd=ctx.repo_root)
