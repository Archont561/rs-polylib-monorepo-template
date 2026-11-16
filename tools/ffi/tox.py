"""Run UniFFI (Kotlin, Ruby, Swift) compatibility matrix via `tox` (`tox.ini`)."""

from __future__ import annotations

from tasknest import ToolContext, tool

from tools._lib.tox_runner import run_tox


@tool(
    marks=("rust", "ffi", "compat"),
    description="Run UniFFI `tox` envs (`kotlin-compat`, `ruby-compat`, `swift-compat`).",
)
def ffi_tox(
    ctx: ToolContext,
    env: str = "",
    all_envs: bool = False,
    list_only: bool = False,
) -> None:
    """Execute `tox` UniFFI compatibility environments (defaults to `-m ffi`)."""
    if list_only:
        run_tox(ctx, list_only=True)
        return
    if all_envs or not env:
        run_tox(ctx, label="ffi")
        return
    run_tox(ctx, env=env)
