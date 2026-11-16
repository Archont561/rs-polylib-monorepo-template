"""Run declarative `.alint/tests/` specs and live real-schema mutation probes."""

from __future__ import annotations

from tasknest import ToolContext, tool

from tools._lib.policy import run_policy_tests


@tool(
    marks=("fast", "ci"),
    description="Run declarative alint policy tests and live real-schema mutation probes.",
)
def test_policy(ctx: ToolContext) -> None:
    """Verify `.alint/tests/` specs and `.alint/schemas/*.schema.json` negative cases."""
    run_policy_tests(ctx.repo_root)
