"""Tests for the four-state verification result type."""

from __future__ import annotations

import pytest

from tools._lib.status import (
    CheckResult,
    Status,
    blocking,
    failed,
    merge,
    not_run,
    passed,
    publish_ready,
    skipped,
    summarize,
)


def test_non_pass_requires_a_reason() -> None:
    """A skip or not-run without a reason is the defect this type prevents."""
    with pytest.raises(ValueError, match="no reason"):
        CheckResult(name="swift", status=Status.SKIPPED)
    with pytest.raises(ValueError, match="no reason"):
        CheckResult(name="swift", status=Status.SKIPPED, reason="   ")
    with pytest.raises(ValueError, match="no reason"):
        CheckResult(name="jar", status=Status.FAILED)


def test_pass_must_not_carry_a_reason() -> None:
    """A pass carries evidence; a reason implies an excuse."""
    with pytest.raises(ValueError, match="carries a reason"):
        CheckResult(name="kotlin", status=Status.PASSED, reason="looks fine")


def test_blank_name_is_rejected() -> None:
    """An unnamed result cannot be attributed in a log."""
    with pytest.raises(ValueError, match="must not be blank"):
        CheckResult(name="  ", status=Status.PASSED)


def test_skip_and_not_run_are_distinct_states() -> None:
    """Only not-run is fixable by changing the selector."""
    assert skipped("s", "swift absent").status is not not_run("n", "target excluded").status


def test_publish_ready_requires_every_result_to_pass() -> None:
    """Any non-pass blocks publication."""
    assert publish_ready([passed("a"), passed("b")])
    assert not publish_ready([passed("a"), skipped("b", "no toolchain")])
    assert not publish_ready([passed("a"), not_run("b", "excluded")])
    assert not publish_ready([passed("a"), failed("b", "boom")])
    assert not publish_ready([])


def test_merge_keeps_the_worst_status_visible() -> None:
    """A merge reports failure over skip over not-run over pass."""
    assert merge("all", [passed("a"), passed("b")]).status is Status.PASSED
    assert merge("all", [passed("a"), not_run("b", "x")]).status is Status.NOT_RUN
    assert merge("all", [not_run("b", "x"), skipped("c", "y")]).status is Status.SKIPPED
    assert merge("all", [skipped("c", "y"), failed("d", "z")]).status is Status.FAILED


def test_merge_rejects_an_empty_list() -> None:
    """An empty merge would otherwise read as a pass."""
    with pytest.raises(ValueError, match="empty result list"):
        merge("all", [])


def test_merge_reasons_name_every_non_pass_child() -> None:
    """The merged reason must name the work that did not happen."""
    merged = merge("swift", [passed("artifacts"), skipped("c-abi", "no cc")])
    assert merged.status is Status.SKIPPED
    assert merged.reason is not None
    assert "c-abi" in merged.reason
    assert "no cc" in merged.reason


def test_blocking_lists_only_non_passes_with_reasons() -> None:
    """Blocking lines carry the reason so a log explains itself."""
    entries = blocking([passed("a", "ok"), skipped("b", "no swift")])
    assert len(entries) == 1
    assert "b" in entries[0]
    assert "no swift" in entries[0]


def test_summarize_counts_every_status() -> None:
    """Counts cover all four states so a zero is explicit."""
    counts = summarize([passed("a"), skipped("b", "x")])
    assert counts == {"passed": 1, "failed": 0, "skipped": 1, "not-run": 0}
