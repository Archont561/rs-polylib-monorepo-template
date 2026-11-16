"""Verify packaged Kotlin JAR, SwiftPM, and Ruby gem UniFFI compatibility."""

from __future__ import annotations

from tasknest import ToolContext, ToolError, tool

from tools._lib.compat_ffi import TARGET_ALL, verify_ffi_compat


@tool(
    marks=("rust", "ffi", "compat"),
    description="Verify Kotlin JAR, SwiftPM C-ABI/Swift, and isolated Ruby gem compatibility.",
)
def compat_ffi(ctx: ToolContext, target: str = TARGET_ALL) -> None:
    """Verify packaged artifacts for Kotlin, Swift, and Ruby (`all`, `kotlin`, `swift`, `ruby`)."""
    try:
        verify_ffi_compat(ctx.repo_root, target=target)
    except (RuntimeError, ValueError) as exc:
        raise ToolError(str(exc)) from exc
