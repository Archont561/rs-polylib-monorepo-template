"""Run TypeScript/npm tarball compatibility checks (`publint`, `attw`, Bun, Node.js, `tsc`)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tasknest import ToolContext, ToolError, tool

from tools._lib.compat_ts import MODE_ALL, TsCompatMode, verify_ts_compat
from tools._lib.verification import reports_verification

if TYPE_CHECKING:
    from tools._lib.status import CheckResult


@tool(
    marks=("ci", "ts", "compat"),
    description="Pack npm tarballs and verify `publint`, `attw`, Bun, Node.js, and `tsc`.",
)
@reports_verification("npm/TypeScript compatibility")
def ts_compat(ctx: ToolContext, mode: TsCompatMode = MODE_ALL) -> list[CheckResult]:
    """Verify packed `.tgz` tarballs (`all`, `pack`, `bun`, `node`, or `types`).

    A lane whose toolchain is absent reports `skipped` with a reason rather than
    being folded into an unqualified pass.
    """
    try:
        return verify_ts_compat(ctx.repo_root, mode=mode)
    except (RuntimeError, ValueError) as exc:
        raise ToolError(str(exc)) from exc
