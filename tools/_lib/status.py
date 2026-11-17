"""Four-state verification results shared by every tooling verifier.

A verifier that returns ``None`` and prints its own verdict cannot tell its
caller apart ''ran and passed'', ''could not run'', and ''was never attempted''.
Each of those means a different thing to a release gate and each needs a
different remedy, so they get distinct states here and the distinction is
enforced rather than left to convention.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Status(enum.Enum):
    """Outcome of one verification step.

    ``SKIPPED`` and ``NOT_RUN`` stay separate on purpose. A skip is fixed by
    installing a toolchain or moving to another OS; a not-run is fixed by
    re-running with a different selector. Collapsing them is what lets a Linux
    runner look like a complete pass.
    """

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_RUN = "not-run"


@dataclass(frozen=True)
class CheckResult:
    """One verification step's outcome, with the reason it did not pass.

    ``reason`` is required for every status except ``PASSED``: an unexplained
    skip is indistinguishable from a pass in a log, which is the defect this
    type exists to prevent.
    """

    name: str
    status: Status
    reason: str | None = None
    evidence: str | None = None
    details: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        """Reject a non-pass without a reason, and a blank reason with a pass."""
        if not self.name.strip():
            raise ValueError("CheckResult.name must not be blank.")
        if self.status is not Status.PASSED and not (self.reason or "").strip():
            raise ValueError(
                f"CheckResult {self.name!r} has status {self.status.value!r} "
                "but no reason; a non-pass needs a reason so a skipped check "
                "cannot read as a success."
            )
        if self.status is Status.PASSED and (self.reason or "").strip():
            raise ValueError(
                f"CheckResult {self.name!r} passed but carries a reason; a pass "
                "carries evidence, not an excuse."
            )

    @property
    def passed(self) -> bool:
        """True only for an unqualified pass."""
        return self.status is Status.PASSED


def passed(name: str, evidence: str | None = None, details: tuple[str, ...] = ()) -> CheckResult:
    """Build a pass result."""
    return CheckResult(name=name, status=Status.PASSED, evidence=evidence, details=details)


def failed(name: str, reason: str, details: tuple[str, ...] = ()) -> CheckResult:
    """Build a failure result, which always blocks a release."""
    return CheckResult(name=name, status=Status.FAILED, reason=reason, details=details)


def skipped(name: str, reason: str) -> CheckResult:
    """Build a skip: attempted, but a toolchain or OS is missing."""
    return CheckResult(name=name, status=Status.SKIPPED, reason=reason)


def not_run(name: str, reason: str) -> CheckResult:
    """Build a not-run: never attempted because of mode, selector, or config."""
    return CheckResult(name=name, status=Status.NOT_RUN, reason=reason)


def merge(prefix: str, results: list[CheckResult]) -> CheckResult:
    """Collapse several results into one, keeping every non-pass visible.

    The merged status is ``FAILED`` if any child failed, otherwise ``SKIPPED``
    if any child skipped, otherwise ``NOT_RUN`` if any child never ran, and
    ``PASSED`` only when every child passed. Reasons are joined so a caller
    printing the outcome names the work that did not happen.
    """
    if not results:
        raise ValueError(f"Cannot merge an empty result list for {prefix!r}.")
    worst = _worst_status(results)
    details = tuple(f"{item.name}: {item.status.value}" for item in results)
    if worst is Status.PASSED:
        evidence = "; ".join(item.evidence for item in results if item.evidence)
        return passed(prefix, evidence=evidence or None, details=details)
    reasons = "; ".join(f"{item.name}: {item.reason}" for item in results if item.reason)
    return CheckResult(name=prefix, status=worst, reason=reasons or None, details=details)


_PRECEDENCE: tuple[Status, ...] = (Status.FAILED, Status.SKIPPED, Status.NOT_RUN)


def _worst_status(results: list[CheckResult]) -> Status:
    for candidate in _PRECEDENCE:
        if any(item.status is candidate for item in results):
            return candidate
    return Status.PASSED


def summarize(results: list[CheckResult]) -> dict[str, int]:
    """Count results per status for a log line."""
    counts = {status.value: 0 for status in Status}
    for item in results:
        counts[item.status.value] += 1
    return counts


def blocking(results: list[CheckResult]) -> list[str]:
    """Return one explanatory line per result that is not a pass."""
    return [
        f"{item.name}: {item.status.value} - {item.reason}"
        for item in results
        if item.status is not Status.PASSED
    ]


def publish_ready(results: list[CheckResult]) -> bool:
    """True only when every result passed; any non-pass blocks publication."""
    return bool(results) and all(item.passed for item in results)


def render(results: list[CheckResult]) -> str:
    """Render results as one log block: passes summarised, non-passes spelled out."""
    lines = [f"Verification: {_format_counts(results)}"]
    lines.extend(f"  - {item}" for item in blocking(results))
    return "\n".join(lines)


def _format_counts(results: list[CheckResult]) -> str:
    counts = summarize(results)
    parts = [f"{value}={count}" for value, count in counts.items() if count]
    return ", ".join(parts) if parts else "nothing ran"
