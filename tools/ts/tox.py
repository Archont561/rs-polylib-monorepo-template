"""Run npm / TypeScript compatibility matrix via `tox` (`tox.ini`)."""

from __future__ import annotations

from tasknest import ToolContext, tool

from tools._lib.tox_runner import run_tox


@tool(
    marks=("ts", "compat"),
    description="Run npm/TS `tox` compatibility envs (`npm-{compat,pack,bun,node,types}`).",
)
def ts_tox(
    ctx: ToolContext,
    env: str = "npm-compat",
    all_envs: bool = False,
    list_only: bool = False,
) -> None:
    """Execute `tox` npm/TypeScript environments (`npm-compat` or full `-m npm` label)."""
    if list_only:
        run_tox(ctx, list_only=True)
        return
    if all_envs:
        run_tox(ctx, label="npm")
        return
    run_tox(ctx, env=env)
