"""Run Kotlin, Swift, and Ruby UniFFI unit and shared conformance test suites."""

from __future__ import annotations

from tasknest import ToolContext, ToolError, tool

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
from tools._lib.status import CheckResult, passed, publish_ready, render


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
    """Execute unit tests and shared Gherkin conformance suites for UniFFI bindings.

    Only lanes the target selects are reported. Excluding a lane is not a skip:
    `--target kotlin` is a complete run of what was asked for, and marking the
    unselected lane `skipped` would make every scoped run refuse to pass.

    A selected lane whose toolchain is absent reports `skipped` with a reason. Pass
    `require_swift` on a macOS runner, where Swift is expected, to turn that
    skip into a failure instead of letting the job pass without running it.
    """
    targets = resolve_ffi_targets(target)
    results: list[CheckResult] = []
    if TARGET_KOTLIN in targets:
        if coverage:
            test_kotlin_with_coverage(ctx, min_coverage=min_coverage)
        else:
            test_kotlin(ctx)
        results.append(passed("kotlin-test", evidence="kotlin suite ran"))
    if TARGET_SWIFT in targets:
        if coverage:
            results.append(
                test_swift_with_coverage(
                    ctx, require_toolchain=require_swift, min_coverage=min_coverage
                )
            )
        else:
            results.append(test_swift(ctx, require_toolchain=require_swift))
    if TARGET_RUBY in targets:
        if coverage:
            test_ruby_with_coverage(ctx, min_coverage=min_coverage)
        else:
            test_ruby(ctx)
        results.append(passed("ruby-test", evidence="ruby suite ran"))
    print(render(results))
    if not publish_ready(results):
        raise ToolError("FFI tests did not fully pass; see the per-lane results above.")
