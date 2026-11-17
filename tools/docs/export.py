"""Verify the built documentation export contains every content page."""

from __future__ import annotations

from pathlib import Path

from tasknest import ToolContext, ToolError, tool

_UTF8 = "utf-8"
_SLASH = "/"
_EXPORT_DIR = Path("docs/out")
_CONTENT_DIR = Path("docs/content/docs")
_DOCS_ROUTE = "/docs"


def _expected_routes(content_dir: Path) -> list[str]:
    """Map every content file to the route the static export must contain."""
    routes: list[str] = []
    for mdx in sorted(content_dir.rglob("*.mdx")):
        relative = mdx.relative_to(content_dir).with_suffix("")
        parts = [part for part in relative.parts if part != "index"]
        routes.append(_SLASH + _SLASH.join(["docs", *parts]))
    return routes


def _export_file(export_dir: Path, route: str) -> Path:
    """Return the file a static export writes for `route`."""
    if route == _DOCS_ROUTE:
        return export_dir / "docs.html"
    return export_dir / f"{route.strip(_SLASH)}.html"


@tool(
    marks=("fast", "ci", "docs"),
    description="Verify the built docs export contains every content page.",
)
def check_export(ctx: ToolContext) -> None:
    """Fail when a content page has no route in the built documentation export."""
    export_dir = ctx.repo_root / _EXPORT_DIR
    content_dir = ctx.repo_root / _CONTENT_DIR

    if not export_dir.is_dir():
        raise ToolError(
            f"the documentation export is missing: {_EXPORT_DIR} does not exist. "
            "Run `pixi run -e docs tools run docs build` before checking it."
        )

    missing: list[str] = []
    for route in _expected_routes(content_dir):
        export_file = _export_file(export_dir, route)
        if not export_file.is_file():
            missing.append(route)
            continue
        body = export_file.read_text(encoding=_UTF8)
        if "fd-sidebar" not in body:
            missing.append(f"{route} (no documentation layout)")

    if missing:
        raise ToolError(
            "the documentation export is missing content pages: "
            + ", ".join(missing)
            + ". The Fumadocs route and source loader must render every MDX page."
        )
