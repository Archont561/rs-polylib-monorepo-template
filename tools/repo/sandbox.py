"""Manage offline `pixi-sandbox` bundle configuration and generated launchers."""

from __future__ import annotations

from tasknest import ToolContext, ToolError, tool

_CLI = "pixi-sandbox"
_PLAN_CMD = "plan"
_INIT_CMD = "init"
_SCRIPT_PATH = "scripts/restore.sh"


@tool(
    marks=("fast", "ci"),
    description="Plan, check, or regenerate pixi-sandbox offline bundles and launchers.",
)
def sandbox(ctx: ToolContext, action: str = _PLAN_CMD) -> None:
    """Run `pixi-sandbox` (`plan`, `check`, or `init`)."""
    if action == _PLAN_CMD:
        ctx.run([_CLI, _PLAN_CMD, "--config", "pixi-sandbox.toml", "--json"], cwd=ctx.repo_root)
        return
    if action == "check":
        ctx.run([_CLI, _INIT_CMD, "--script-path", _SCRIPT_PATH, "--check"], cwd=ctx.repo_root)
        return
    if action == _INIT_CMD:
        ctx.run([_CLI, _INIT_CMD, "--script-path", _SCRIPT_PATH], cwd=ctx.repo_root)
        return
    raise ToolError(
        f"Unsupported sandbox action {action!r}; expected {_PLAN_CMD}, check, or {_INIT_CMD}."
    )
