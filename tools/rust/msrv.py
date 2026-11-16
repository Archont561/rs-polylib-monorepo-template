"""Prove the declared minimum supported Rust version from `Cargo.toml`."""

from __future__ import annotations

import os
from pathlib import Path

from tasknest import ToolContext, ToolError, tool

from tools._lib.compat_rs import check_features, declared_msrv


@tool(
    marks=("rust", "compat"),
    description="Read `[workspace.package] rust-version` and verify every feature row at MSRV.",
)
def prove_msrv(
    ctx: ToolContext,
    print_version: bool = False,
    github_output: str = "",
    toolchain: str = "",
) -> None:
    """Print or prove the workspace's declared MSRV across the metacrate feature matrix."""
    try:
        msrv = declared_msrv(ctx.repo_root)
        if print_version or github_output:
            print(msrv)
            output_file = os.environ.get("GITHUB_OUTPUT")
            if github_output and output_file:
                with Path(output_file).open("a", encoding="utf-8") as handle:
                    handle.write(f"{github_output}={msrv}\n")
            return
        check_features(ctx.repo_root, toolchain=toolchain or msrv)
    except RuntimeError as exc:
        raise ToolError(str(exc)) from exc
