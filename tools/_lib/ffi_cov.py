"""Coverage collection and 90% threshold enforcement for Kotlin, Ruby, and Swift UniFFI tests."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from tasknest import ToolError

from tools._lib.coverage import (
    JACOCO_FILENAME,
    LCOV_FILENAME,
    MIN_COVERAGE_PERCENT,
    coverage_dir,
    enforce_threshold,
    merge_lcov_files,
    merge_ruby_raw_coverage,
    parse_jacoco_xml,
    parse_lcov,
)
from tools._lib.ffi_platform import require_tool as _require_tool
from tools._lib.status import CheckResult, failed, passed, skipped

if TYPE_CHECKING:
    from tasknest import ToolContext

_GRADLE_BIN = "gradle"
_BUNDLE_BIN = "bundle"
_SWIFT_BIN = "swift"
_LLVM_COV_BIN = "llvm-cov"
_XCRUN_BIN = "xcrun"
_PACKAGES_DIR = "packages"
_TEST_CMD = "test"
_UTF8 = "utf-8"
_SWIFT_PREFIXES: tuple[str, ...] = ("packages/polylib-swift/Sources/Polylib/",)


def test_kotlin_with_coverage(
    ctx: ToolContext,
    *,
    min_coverage: float = MIN_COVERAGE_PERCENT,
) -> None:
    """Run Kotlin tests, generate `coverage/kotlin/jacoco.xml`, and enforce >= 90% coverage."""
    _require_tool(_GRADLE_BIN, "kt")
    out_dir = coverage_dir(ctx.repo_root, "kotlin")
    kt_root = ctx.repo_root / _PACKAGES_DIR / "polylib-kt"
    cmd = [
        _GRADLE_BIN,
        _TEST_CMD,
        "jacocoTestReport",
        "jacocoTestCoverageVerification",
        "--no-daemon",
        "--rerun-tasks",
    ]
    ctx.run(cmd, cwd=kt_root)
    report_path = out_dir / JACOCO_FILENAME
    stats = parse_jacoco_xml(report_path)
    enforce_threshold("kotlin", report_path, stats, min_percent=min_coverage)


def test_ruby_with_coverage(
    ctx: ToolContext,
    *,
    min_coverage: float = MIN_COVERAGE_PERCENT,
) -> None:
    """Run Ruby Minitest + Cucumber with stdlib Coverage and write `coverage/ruby/lcov.info`."""
    _require_tool(_BUNDLE_BIN, "rb")
    rb_root = ctx.repo_root / _PACKAGES_DIR / "polylib-rb"
    out_dir = coverage_dir(ctx.repo_root, "ruby")
    raw_dir = out_dir / ".raw"
    if raw_dir.exists():
        shutil.rmtree(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["BUNDLE_PATH"] = str(rb_root / "vendor" / _BUNDLE_BIN)
    env["POLYLIB_COVERAGE"] = "1"
    env["POLYLIB_COVERAGE_RAW_DIR"] = str(raw_dir)
    ctx.run([_BUNDLE_BIN, "install", "--quiet"], cwd=rb_root, env=env)
    ctx.run([_BUNDLE_BIN, "exec", "rake", _TEST_CMD], cwd=rb_root, env=env)
    report_path = out_dir / LCOV_FILENAME
    stats = merge_ruby_raw_coverage(raw_dir, report_path, ctx.repo_root)
    shutil.rmtree(raw_dir, ignore_errors=True)
    enforce_threshold("ruby", report_path, stats, min_percent=min_coverage)


def _swift_llvm_cov_prefix() -> list[str]:
    if platform.system().lower() == "darwin" and shutil.which(_XCRUN_BIN) is not None:
        return [_XCRUN_BIN, _LLVM_COV_BIN]
    if shutil.which(_LLVM_COV_BIN) is not None:
        return [_LLVM_COV_BIN]
    raise ToolError("`llvm-cov` (or `xcrun llvm-cov` on macOS) is required for Swift coverage.")


def _locate_swift_test_binary(bin_path: Path) -> Path:
    candidates = sorted(bin_path.glob("*PackageTests.xctest"))
    if not candidates:
        raise ToolError(f"Could not find `*PackageTests.xctest` under {bin_path}.")
    bundle = candidates[0]
    if bundle.is_dir():
        macos_bin = bundle / "Contents" / "MacOS" / bundle.stem
        if macos_bin.is_file():
            return macos_bin
    if bundle.is_file():
        return bundle
    raise ToolError(f"Unsupported Swift test bundle layout: {bundle}")


def _swift_bin_path(swift_root: Path) -> Path:
    bin_res = subprocess.run(
        [_SWIFT_BIN, "build", "--show-bin-path"],
        cwd=swift_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(bin_res.stdout.strip())


def _export_swift_lcov(swift_root: Path, repo_root: Path, output: Path) -> None:
    bin_path = _swift_bin_path(swift_root)
    profdata = bin_path / "codecov" / "default.profdata"
    if not profdata.is_file():
        raise ToolError(f"Missing Swift coverage profdata at {profdata}.")
    export_cmd = [
        *_swift_llvm_cov_prefix(),
        "export",
        "-format=lcov",
        f"-instr-profile={profdata}",
        str(_locate_swift_test_binary(bin_path)),
        str(swift_root / "Sources" / "Polylib"),
    ]
    exported = subprocess.run(
        export_cmd, cwd=swift_root, capture_output=True, text=True, check=True
    )
    with tempfile.TemporaryDirectory(prefix="polylib-swift-cov-") as tmp_str:
        raw_lcov = Path(tmp_str) / LCOV_FILENAME
        raw_lcov.write_text(exported.stdout, encoding=_UTF8)
        merge_lcov_files(
            [(raw_lcov, swift_root)], output, repo_root, include_prefixes=_SWIFT_PREFIXES
        )


def test_swift_with_coverage(
    ctx: ToolContext,
    *,
    require_toolchain: bool = False,
    min_coverage: float = MIN_COVERAGE_PERCENT,
) -> CheckResult:
    """Run SwiftPM tests with `--enable-code-coverage` and write `coverage/swift/lcov.info`."""
    swift_root = ctx.repo_root / _PACKAGES_DIR / "polylib-swift"
    if shutil.which(_SWIFT_BIN) is None:
        reason = (
            "`swift` not found on PATH, so the Swift coverage report was not produced; "
            "install the Swift toolchain or run on macOS CI."
        )
        if require_toolchain:
            return failed("swift-coverage", reason)
        return skipped("swift-coverage", reason)
    ctx.run([_SWIFT_BIN, _TEST_CMD, "--enable-code-coverage"], cwd=swift_root)
    out_dir = coverage_dir(ctx.repo_root, _SWIFT_BIN)
    report_path = out_dir / LCOV_FILENAME
    _export_swift_lcov(swift_root, ctx.repo_root, report_path)
    stats = parse_lcov(report_path)
    enforce_threshold(_SWIFT_BIN, report_path, stats, min_percent=min_coverage)
    return passed("swift-coverage", evidence=f"{stats.percent:.1f}% >= {min_coverage:g}%")
