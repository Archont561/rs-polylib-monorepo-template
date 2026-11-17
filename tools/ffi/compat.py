"""Verify packaged Kotlin JAR, SwiftPM, and Ruby gem UniFFI compatibility."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tasknest import ToolContext, ToolError, tool

from tools._lib.compat_ffi import TARGET_ALL, FfiTarget, verify_ffi_compat
from tools._lib.verification import reports_verification

if TYPE_CHECKING:
    from tools._lib.status import CheckResult


@tool(
    marks=("rust", "ffi", "compat"),
    description="Verify Kotlin JAR, SwiftPM C-ABI/Swift, and isolated Ruby gem compatibility.",
)
@reports_verification("FFI compatibility")
def compat_ffi(
    ctx: ToolContext, target: FfiTarget = TARGET_ALL, require_toolchain: bool = False
) -> list[CheckResult]:
    """Verify packaged artifacts for Kotlin, Swift, and Ruby (`all`, `kotlin`, `swift`, `ruby`).

    A lane whose toolchain is absent reports `skipped` with a reason rather than
    a pass. Pass `require_toolchain` on a runner where the toolchain is expected,
    which turns those skips into failures instead of letting the run look clean.
    """
    try:
        return verify_ffi_compat(ctx.repo_root, target=target, require_toolchain=require_toolchain)
    except (RuntimeError, ValueError) as exc:
        raise ToolError(str(exc)) from exc
