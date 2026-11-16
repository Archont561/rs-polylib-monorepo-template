"""Run polyglot `tox` compatibility suites across all ecosystems."""

from __future__ import annotations

from tasknest import ToolContext, tool

from tools._lib.tox_runner import run_tox


@tool(
    marks=("compat",),
    description="Run `tox` compatibility suites (`compat`, `python`, `npm`, `rust`, `ffi`, `all`).",
)
def run_polyglot_tox(
    ctx: ToolContext,
    label: str = "compat",
    env: str = "",
    list_only: bool = False,
) -> None:
    """Execute `tox` across any ecosystem label or explicit environment list."""
    if list_only:
        run_tox(ctx, list_only=True)
        return
    if env:
        run_tox(ctx, env=env)
        return
    run_tox(ctx, label=label, skip_missing=(label == "python"))
