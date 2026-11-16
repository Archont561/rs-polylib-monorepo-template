"""Run Rust compatibility matrix via `tox` (`tox.ini`)."""

from __future__ import annotations

from tasknest import ToolContext, tool

from tools._lib.tox_runner import run_tox


@tool(
    marks=("rust", "compat"),
    description="Run Rust `tox` compatibility envs (`rust-{compat,features,packages,consumer}`).",
)
def rs_tox(
    ctx: ToolContext,
    env: str = "rust-compat",
    all_envs: bool = False,
    list_only: bool = False,
) -> None:
    """Execute `tox` Rust compatibility environments (`rust-compat` or `-m rust`)."""
    if list_only:
        run_tox(ctx, list_only=True)
        return
    if all_envs:
        run_tox(ctx, label="rust")
        return
    run_tox(ctx, env=env)
