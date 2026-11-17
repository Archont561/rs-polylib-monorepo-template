"""Verify packaged Kotlin JAR, SwiftPM, and Ruby gem UniFFI compatibility."""

from __future__ import annotations

from tasknest import ToolContext, ToolError, tool

from tools._lib.compat_ffi import TARGET_ALL, verify_ffi_compat
from tools._lib.status import publish_ready, render


@tool(
    marks=("rust", "ffi", "compat"),
    description="Verify Kotlin JAR, SwiftPM C-ABI/Swift, and isolated Ruby gem compatibility.",
)
def compat_ffi(ctx: ToolContext, target: str = TARGET_ALL, require_toolchain: bool = False) -> None:
    """Verify packaged artifacts for Kotlin, Swift, and Ruby (`all`, `kotlin`, `swift`, `ruby`).

    A lane whose toolchain is absent reports `skipped` with a reason rather than
    a pass. Pass `require_toolchain` on a runner where the toolchain is expected,
    which turns those skips into failures instead of letting the run look clean.
    """
    try:
        results = verify_ffi_compat(
            ctx.repo_root, target=target, require_toolchain=require_toolchain
        )
    except (RuntimeError, ValueError) as exc:
        raise ToolError(str(exc)) from exc
    print(render(results))
    if not publish_ready(results):
        raise ToolError("FFI compatibility did not fully pass; see the per-lane results above.")
