"""Generate `report.json`, Jinja-rendered `report.md`, and `SHA256SUMS.txt`."""

from __future__ import annotations

from pathlib import Path

from tasknest import ToolContext, tool

from tools._lib.release import ReportMetadata, generate_build_report


@tool(
    marks=("docs", "writes"),
    description="Generate build `report.json`, Jinja-rendered `report.md`, and `SHA256SUMS.txt`.",
)
def build_report(
    ctx: ToolContext,
    artifacts_dir: str = "dist-release",
    output_dir: str = "dist-report",
    checks: str = "",
) -> None:
    """Inspect built artifacts, emit `report.json`, and render `report.md` from `report.json`."""
    root = Path(ctx.repo_root)
    art_path = Path(artifacts_dir)
    out_path = Path(output_dir)
    if not art_path.is_absolute():
        art_path = root / art_path
    if not out_path.is_absolute():
        out_path = root / out_path
    meta = ReportMetadata.from_env(checks_spec=checks)
    generate_build_report(root, art_path, out_path, meta=meta)
