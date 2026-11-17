"""Pack release artifacts (`rust`, `npm`, `kotlin`, `ruby`, `swift`, or `all`)."""

from __future__ import annotations

from pathlib import Path

from tasknest import ToolContext, tool

from tools._lib.release_pack import PackTarget, pack_release_artifacts


@tool(
    marks=("rust", "ts", "ffi", "writes"),
    description="Pack release artifacts (`all`, `rust`, `npm`, `kotlin`, `ruby`, `swift`).",
)
def pack_artifacts(
    ctx: ToolContext,
    target: PackTarget = "all",
    output_dir: str = "dist-release",
) -> None:
    """Stage distributable release packages into `output_dir`."""
    root = Path(ctx.repo_root)
    out_path = Path(output_dir)
    if not out_path.is_absolute():
        out_path = root / out_path
    pack_release_artifacts(ctx, out_path, target=target)
