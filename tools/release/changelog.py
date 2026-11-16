"""Generate release changelog notes and append build `report.md` when available."""

from __future__ import annotations

from pathlib import Path

from tasknest import ToolContext, tool

from tools._lib.release import generate_release_changelog


@tool(
    marks=("docs", "writes"),
    description="Generate conventional changelog and append `report.md` for GitHub Releases.",
)
def release_changelog(
    ctx: ToolContext,
    output: str = "dist-report/RELEASE_NOTES.md",
    tag: str = "",
    report_md: str = "",
) -> None:
    """Create release notes combining conventional commits and the rendered build report."""
    root = Path(ctx.repo_root)
    out_path = Path(output)
    if not out_path.is_absolute():
        out_path = root / out_path
    report_path: Path | None = None
    if report_md:
        candidate = Path(report_md)
        report_path = candidate if candidate.is_absolute() else root / candidate
    generate_release_changelog(root, out_path, tag=tag, report_md=report_path)
