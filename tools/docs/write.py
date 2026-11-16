"""Regenerate docs and GitHub templates or scaffold a unit README."""

from __future__ import annotations

from pathlib import Path

from tasknest import ToolContext, tool

from tools._lib.docs import scaffold_unit_readme, sync_docs


@tool(
    marks=("docs", "writes"),
    description="Render README.md, AGENTS.md, and .github templates from templates/.",
)
def docs_write(
    ctx: ToolContext,
    scaffold_kind: str = "",
    scaffold_name: str = "",
    scaffold_out: str = "",
) -> None:
    """Write all managed templates, or scaffold a unit README when `--scaffold-kind` is set."""
    if scaffold_kind:
        out_path = Path(scaffold_out)
        if not out_path.is_absolute():
            out_path = ctx.repo_root / out_path
        scaffold_unit_readme(ctx.repo_root, scaffold_kind, scaffold_name, out_path)
        return
    sync_docs(ctx.repo_root, check_only=False)
