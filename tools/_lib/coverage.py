"""Per-language coverage report normalization, merging, and threshold enforcement."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from tasknest import ToolError

if TYPE_CHECKING:
    from collections.abc import Sequence

MIN_COVERAGE_PERCENT: float = 90.0
COVERAGE_ROOT_DIR: str = "coverage"
LCOV_FILENAME: str = "lcov.info"
JACOCO_FILENAME: str = "jacoco.xml"

COVERAGE_REPORT_PATHS: dict[str, str] = {
    "rust": f"{COVERAGE_ROOT_DIR}/rust/{LCOV_FILENAME}",
    "python": f"{COVERAGE_ROOT_DIR}/python/{LCOV_FILENAME}",
    "ts": f"{COVERAGE_ROOT_DIR}/ts/{LCOV_FILENAME}",
    "kotlin": f"{COVERAGE_ROOT_DIR}/kotlin/{JACOCO_FILENAME}",
    "ruby": f"{COVERAGE_ROOT_DIR}/ruby/{LCOV_FILENAME}",
    "swift": f"{COVERAGE_ROOT_DIR}/swift/{LCOV_FILENAME}",
}

_UTF8 = "utf-8"
_SF_PREFIX = "SF:"
_DA_PREFIX = "DA:"
_END_RECORD = "end_of_record"
_JACOCO_LINE_RE = re.compile(r'<counter\s+type="LINE"\s+missed="(\d+)"\s+covered="(\d+)"\s*/>')


@dataclass(frozen=True, slots=True)
class CoverageStats:
    """Line coverage counts and derived percentage for one language report."""

    covered: int
    total: int

    @property
    def percent(self) -> float:
        """Return line coverage percentage in `[0.0, 100.0]`."""
        if self.total <= 0:
            return 0.0
        return (self.covered / self.total) * 100.0


def coverage_dir(repo_root: Path, lang: str) -> Path:
    """Create and return `coverage/<lang>` under `repo_root`."""
    target = repo_root / COVERAGE_ROOT_DIR / lang
    target.mkdir(parents=True, exist_ok=True)
    return target


def _normalize_source_path(raw_path: str, base_dir: Path, repo_root: Path) -> str:
    candidate = Path(raw_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (base_dir / candidate).resolve()
    root_resolved = repo_root.resolve()
    try:
        return resolved.relative_to(root_resolved).as_posix()
    except ValueError:
        return raw_path.replace("\\", "/")


def _matches_filter(
    rel_path: str,
    include_prefixes: tuple[str, ...],
    exclude_fragments: tuple[str, ...],
) -> bool:
    if include_prefixes and not rel_path.startswith(include_prefixes):
        return False
    return not any(fragment in rel_path for fragment in exclude_fragments)


def _ingest_lcov_text(
    text: str,
    base_dir: Path,
    repo_root: Path,
    records: dict[str, dict[int, int]],
) -> None:
    current_file: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith(_SF_PREFIX):
            source = line[len(_SF_PREFIX) :]
            current_file = _normalize_source_path(source, base_dir, repo_root)
            records.setdefault(current_file, {})
        elif line.startswith(_DA_PREFIX) and current_file is not None:
            payload = line[len(_DA_PREFIX) :].split(",")
            if len(payload) >= 2:
                line_no = int(payload[0])
                hits = int(payload[1])
                file_hits = records[current_file]
                file_hits[line_no] = file_hits.get(line_no, 0) + hits
        elif line == _END_RECORD:
            current_file = None


def _write_lcov(records: dict[str, dict[int, int]], output: Path) -> CoverageStats:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines_out: list[str] = []
    total_lines = 0
    covered_lines = 0
    for rel_path in sorted(records):
        hit_map = records[rel_path]
        if not hit_map:
            continue
        lines_out.append(f"{_SF_PREFIX}{rel_path}")
        file_covered = 0
        for line_no in sorted(hit_map):
            hits = hit_map[line_no]
            lines_out.append(f"{_DA_PREFIX}{line_no},{hits}")
            if hits > 0:
                file_covered += 1
        file_total = len(hit_map)
        total_lines += file_total
        covered_lines += file_covered
        lines_out.append(f"LF:{file_total}")
        lines_out.append(f"LH:{file_covered}")
        lines_out.append(_END_RECORD)
    output.write_text("\n".join(lines_out) + ("\n" if lines_out else ""), encoding=_UTF8)
    return CoverageStats(covered=covered_lines, total=total_lines)


def merge_lcov_files(
    sources: Sequence[tuple[Path, Path]],
    output: Path,
    repo_root: Path,
    *,
    include_prefixes: tuple[str, ...] = (),
    exclude_fragments: tuple[str, ...] = (),
) -> CoverageStats:
    """Merge `(lcov_path, base_dir)` inputs into one repo-relative LCOV file."""
    raw_records: dict[str, dict[int, int]] = {}
    for lcov_path, base_dir in sources:
        if not lcov_path.is_file():
            raise ToolError(f"Expected LCOV report at {lcov_path}, but it was not found.")
        _ingest_lcov_text(lcov_path.read_text(encoding=_UTF8), base_dir, repo_root, raw_records)
    filtered = {
        path: hits
        for path, hits in raw_records.items()
        if _matches_filter(path, include_prefixes, exclude_fragments)
    }
    return _write_lcov(filtered, output)


def parse_lcov(lcov_path: Path) -> CoverageStats:
    """Compute aggregate line coverage statistics from an LCOV file."""
    if not lcov_path.is_file():
        raise ToolError(f"Missing LCOV coverage report: {lcov_path}")
    records: dict[str, dict[int, int]] = {}
    _ingest_lcov_text(lcov_path.read_text(encoding=_UTF8), lcov_path.parent, Path("/"), records)
    total = sum(len(hits) for hits in records.values())
    covered = 0
    for hits in records.values():
        covered += sum(1 for count in hits.values() if count > 0)
    return CoverageStats(covered=covered, total=total)


def parse_jacoco_xml(xml_path: Path) -> CoverageStats:
    """Extract report-level LINE coverage statistics from a JaCoCo XML report."""
    if not xml_path.is_file():
        raise ToolError(f"Missing JaCoCo coverage report: {xml_path}")
    text = xml_path.read_text(encoding=_UTF8)
    tail = text.rsplit("</package>", maxsplit=1)[-1]
    match = _JACOCO_LINE_RE.search(tail)
    if match is None:
        raise ToolError(f"Could not locate report-level LINE counter in {xml_path}.")
    missed = int(match.group(1))
    covered = int(match.group(2))
    return CoverageStats(covered=covered, total=missed + covered)


def merge_ruby_raw_coverage(raw_dir: Path, output: Path, repo_root: Path) -> CoverageStats:
    """Merge Ruby stdlib `Coverage.result` JSON dumps into `coverage/ruby/lcov.info`."""
    dumps = sorted(raw_dir.glob("*.json"))
    if not dumps:
        raise ToolError(f"No Ruby raw coverage dumps found in {raw_dir}.")
    records: dict[str, dict[int, int]] = {}
    for dump_path in dumps:
        payload = json.loads(dump_path.read_text(encoding=_UTF8))
        for raw_file, counts in payload.items():
            rel_path = _normalize_source_path(str(raw_file), repo_root, repo_root)
            if "/generated/" in rel_path or not rel_path.startswith("packages/polylib-rb/lib/"):
                continue
            hit_map = records.setdefault(rel_path, {})
            for idx, hit in enumerate(counts, start=1):
                if hit is not None:
                    hit_map[idx] = hit_map.get(idx, 0) + int(hit)
    return _write_lcov(records, output)


def enforce_threshold(
    lang: str,
    report_path: Path,
    stats: CoverageStats,
    *,
    min_percent: float = MIN_COVERAGE_PERCENT,
) -> None:
    """Print coverage summary and fail if line coverage is below `min_percent`."""
    if stats.total <= 0:
        raise ToolError(f"coverage/{lang}: report {report_path} recorded 0 executable lines.")
    pct = stats.percent
    summary = (
        f"coverage/{lang}: {stats.covered}/{stats.total} lines "
        f"({pct:.2f}% >= {min_percent:.2f}%) -> {report_path}"
    )
    if pct < min_percent:
        raise ToolError(
            f"coverage/{lang}: line coverage {pct:.2f}% ({stats.covered}/{stats.total}) "
            f"is below required {min_percent:.2f}% threshold ({report_path})."
        )
    print(summary)
