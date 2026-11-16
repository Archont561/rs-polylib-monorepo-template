"""Verify per-language coverage reports under `coverage/<lang>/` against the 90% threshold."""

from __future__ import annotations

from tasknest import ToolContext, ToolError, tool

from tools._lib.coverage import (
    COVERAGE_REPORT_PATHS,
    JACOCO_FILENAME,
    MIN_COVERAGE_PERCENT,
    enforce_threshold,
    parse_jacoco_xml,
    parse_lcov,
)

_ALL = "all"
_VALID_LANGS: tuple[str, ...] = (_ALL, *COVERAGE_REPORT_PATHS)


def _select_langs(lang: str) -> tuple[str, ...]:
    if lang not in _VALID_LANGS:
        choices = ", ".join(_VALID_LANGS)
        raise ToolError(f"Unsupported language {lang!r}; expected one of: {choices}.")
    if lang == _ALL:
        return tuple(COVERAGE_REPORT_PATHS)
    return (lang,)


@tool(
    marks=("ci",),
    description="Audit `coverage/<lang>/` reports against the per-language 90% line threshold.",
)
def check_coverage(
    ctx: ToolContext,
    lang: str = _ALL,
    min_coverage: float = MIN_COVERAGE_PERCENT,
    require_all: bool = False,
) -> None:
    """Parse generated reports under `coverage/<lang>/` and enforce `min_coverage`."""
    selected = _select_langs(lang)
    checked = 0
    for item in selected:
        report = ctx.repo_root / COVERAGE_REPORT_PATHS[item]
        if not report.is_file():
            if require_all or lang != _ALL:
                raise ToolError(f"Missing coverage report for {item}: {report}")
            continue
        stats = parse_jacoco_xml(report) if report.name == JACOCO_FILENAME else parse_lcov(report)
        enforce_threshold(item, report, stats, min_percent=min_coverage)
        checked += 1
    if checked == 0:
        raise ToolError(
            "No coverage reports found under coverage/<lang>/; run tests with `--coverage`."
        )
