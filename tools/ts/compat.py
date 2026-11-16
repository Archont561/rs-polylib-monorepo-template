"""Run TypeScript/npm tarball compatibility checks (`publint`, `attw`, Bun, Node.js, `tsc`)."""

from __future__ import annotations

from tasknest import ToolContext, ToolError, tool

from tools._lib.compat_ts import MODE_ALL, verify_ts_compat


@tool(
    marks=("ci", "ts", "compat"),
    description="Pack npm tarballs and verify `publint`, `attw`, Bun, Node.js, and `tsc`.",
)
def ts_compat(ctx: ToolContext, mode: str = MODE_ALL) -> None:
    """Verify packed `.tgz` tarballs (`all`, `pack`, `bun`, `node`, or `types`)."""
    try:
        verify_ts_compat(ctx.repo_root, mode=mode)
    except (RuntimeError, ValueError) as exc:
        raise ToolError(str(exc)) from exc
