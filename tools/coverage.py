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
from tools._lib.status import (
    CheckResult,
    failed,
    passed,
    publish_ready,
    render,
    skipped,
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
    skipped_langs: str = "",
) -> None:
    """Parse generated reports under `coverage/<lang>/` and enforce `min_coverage`.

    Every selected lane is accounted for. A lane with no report is `skipped` only
    when the caller names it in `skipped_langs` (comma-separated), which the
    producer does when a toolchain is absent. An unexplained missing report is a
    failure, because otherwise the threshold silently never applies to that lane.
    """
    selected = _select_langs(lang)
    declared = {item.strip() for item in skipped_langs.split(",") if item.strip()}
    unknown = declared - set(COVERAGE_REPORT_PATHS)
    if unknown:
        raise ToolError(f"Unknown language in skipped_langs: {', '.join(sorted(unknown))}")
    results: list[CheckResult] = []
    for item in selected:
        report = ctx.repo_root / COVERAGE_REPORT_PATHS[item]
        if not report.is_file():
            if item in declared:
                results.append(
                    skipped(
                        f"coverage-{item}",
                        f"no report at {COVERAGE_REPORT_PATHS[item]}; the producer declared this "
                        "lane skipped, so the threshold was not applied to it.",
                    )
                )
                continue
            reason = (
                f"no report at {COVERAGE_REPORT_PATHS[item]}; run the suite with `coverage=true` "
                "or name the lane in --skipped-langs when its toolchain is absent."
            )
            results.append(failed(f"coverage-{item}", reason))
            continue
        stats = parse_jacoco_xml(report) if report.name == JACOCO_FILENAME else parse_lcov(report)
        enforce_threshold(item, report, stats, min_percent=min_coverage)
        results.append(
            passed(f"coverage-{item}", evidence=f"{stats.percent:.1f}% >= {min_coverage:g}%")
        )
    if not any(item.passed for item in results):
        raise ToolError(
            f"No coverage lane produced a report; looked for {', '.join(selected)} under coverage/."
        )
    print(render(results))
    if not publish_ready(results):
        raise ToolError("Coverage did not fully pass; see the per-lane results above.")
