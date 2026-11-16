"""Run Python compatibility matrix via `tox` (`tox.ini`)."""

from __future__ import annotations

from tasknest import ToolContext, tool

from tools._lib.tox_runner import current_python_tox_env, run_tox


@tool(
    marks=("python", "rust", "compat"),
    description="Run Python `tox` compatibility environments (`py310`–`py314`, wheel & sdist).",
)
def py_tox(
    ctx: ToolContext,
    env: str = "",
    all_envs: bool = False,
    list_only: bool = False,
) -> None:
    """Execute `tox` Python environments (defaults to active interpreter's `pyXY-core`)."""
    if list_only:
        run_tox(ctx, list_only=True)
        return
    if all_envs:
        run_tox(ctx, label="python", skip_missing=True)
        return
    target_env = env or current_python_tox_env("core")
    run_tox(ctx, env=target_env)
