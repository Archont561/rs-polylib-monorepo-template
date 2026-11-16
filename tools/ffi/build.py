"""Build UniFFI native cdylib and Kotlin, Swift, and Ruby bindings."""

from __future__ import annotations

from tasknest import ToolContext, tool

from tools._lib.ffi import TARGET_ALL, build_ffi_targets


@tool(
    marks=("rust", "ffi", "writes"),
    description="Build `polylib-ffi` and UniFFI bindings (`all`, `kotlin`, `swift`, `ruby`).",
)
def build_ffi(ctx: ToolContext, target: str = TARGET_ALL) -> None:
    """Compile `polylib-ffi` cdylib and stage Kotlin, Swift, and/or Ruby UniFFI bindings."""
    build_ffi_targets(ctx, target=target)
