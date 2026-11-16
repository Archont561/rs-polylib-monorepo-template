"""Re-scope packed npm tarballs to `@<github-owner>/*` for GitHub Packages."""

from __future__ import annotations

from pathlib import Path

from tasknest import ToolContext, tool

from tools._lib.release_pack import repack_npm_for_github_packages


@tool(
    marks=("ts", "writes"),
    description="Re-scope packed npm `.tgz` tarballs for GitHub Packages (`npm.pkg.github.com`).",
)
def repack_gh_npm(
    ctx: ToolContext,
    owner: str,
    input_dir: str = "dist-release/npm",
    output_dir: str = "dist-gh-npm",
) -> None:
    """Rewrite `@polylib/*` package scopes to `@<owner>/*` for GitHub Packages npm."""
    root = Path(ctx.repo_root)
    src = Path(input_dir)
    dst = Path(output_dir)
    if not src.is_absolute():
        src = root / src
    if not dst.is_absolute():
        dst = root / dst
    repack_npm_for_github_packages(src, dst, owner=owner)
