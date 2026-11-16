"""Run Kotlin, Swift, and Ruby UniFFI unit and shared conformance test suites."""

from __future__ import annotations

from tasknest import ToolContext, tool

from tools._lib.coverage import MIN_COVERAGE_PERCENT
from tools._lib.ffi import (
    TARGET_ALL,
    TARGET_KOTLIN,
    TARGET_RUBY,
    TARGET_SWIFT,
    resolve_ffi_targets,
    test_kotlin,
    test_ruby,
    test_swift,
)
from tools._lib.ffi_cov import (
    test_kotlin_with_coverage,
    test_ruby_with_coverage,
    test_swift_with_coverage,
)


@tool(
    marks=("rust", "ffi"),
    description="Run UniFFI tests (`all`, `kotlin`, `swift`, `ruby`) with optional >=90% coverage.",
)
def test_ffi(
    ctx: ToolContext,
    target: str = TARGET_ALL,
    require_swift: bool = False,
    coverage: bool = False,
    min_coverage: float = MIN_COVERAGE_PERCENT,
) -> None:
    """Execute unit tests and shared Gherkin conformance suites for UniFFI bindings."""
    targets = resolve_ffi_targets(target)
    if TARGET_KOTLIN in targets:
        if coverage:
            test_kotlin_with_coverage(ctx, min_coverage=min_coverage)
        else:
            test_kotlin(ctx)
    if TARGET_SWIFT in targets:
        if coverage:
            test_swift_with_coverage(
                ctx, require_toolchain=require_swift, min_coverage=min_coverage
            )
        else:
            test_swift(ctx, require_toolchain=require_swift)
    if TARGET_RUBY in targets:
        if coverage:
            test_ruby_with_coverage(ctx, min_coverage=min_coverage)
        else:
            test_ruby(ctx)
