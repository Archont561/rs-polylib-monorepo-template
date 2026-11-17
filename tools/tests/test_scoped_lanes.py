"""Selecting one lane must be a complete run, not a run with skips.

`--target kotlin` asks for Kotlin. Reporting Swift as `skipped` because it was
not asked for makes every scoped run fail its own readiness gate, which is a
false failure of exactly the kind this work set out to remove.

The gate now lives in the `reports_verification` decorator, so these tests
assert on observable behaviour — does the task raise, and what was printed —
rather than on a helper the decorator owns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest
from tasknest import ToolError

from tools._lib.status import Status, skipped
from tools.ffi.test import test_ffi as _test_ffi_task

if TYPE_CHECKING:
    from pathlib import Path

_test_ffi = _test_ffi_task.callable_fn


@dataclass
class _Ctx:
    """The minimal context `test_ffi` touches."""

    repo_root: Path
    commands: list[list[str]] = field(default_factory=list)

    def run(self, argv: list[str], cwd: Path | None = None) -> None:
        self.commands.append(list(argv))


def test_a_scoped_run_does_not_raise(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A single selected lane that ran is a complete run, so the gate must pass."""
    monkeypatch.setattr("tools.ffi.test.test_kotlin_with_coverage", lambda *_a, **_k: None)
    _test_ffi(_Ctx(tmp_path), target="kotlin", coverage=True)
    printed = capsys.readouterr().out
    assert "Verification: passed=1" in printed
    assert "skipped" not in printed


def test_only_the_selected_lane_is_reported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unselected lane is absent from the results, not a skip."""
    monkeypatch.setattr("tools.ffi.test.test_kotlin_with_coverage", lambda *_a, **_k: None)
    _test_ffi(_Ctx(tmp_path), target="kotlin", coverage=True)
    printed = capsys.readouterr().out
    assert "swift-test" not in printed
    assert "passed=1" in printed


def test_a_failing_lane_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The gate is real: a non-passing result must fail the task."""
    from tools._lib.status import failed

    monkeypatch.setattr(
        "tools.ffi.test.test_kotlin_with_coverage",
        lambda *_a, **_k: (_ for _ in ()).throw(ToolError("kotlin broke")),
    )
    with pytest.raises(ToolError):
        _test_ffi(_Ctx(tmp_path), target="kotlin", coverage=True)
    del failed


def test_a_selected_lane_that_skipped_blocks_the_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A skip is not a pass: selecting every lane and skipping one must fail.

    This is the counterpart to the scoped-run test. Kotlin and Ruby run, Swift's
    toolchain is absent, so the run reports one skip and refuses to pass — which
    is what makes an absent toolchain visible instead of silently green.

    Swift is stubbed out rather than left to the ambient machine. CI runners
    ship a Swift toolchain, so the real lane would build instead of skipping and
    the test would assert on whichever toolchain the host happens to have.
    """
    monkeypatch.setattr("tools.ffi.test.test_kotlin_with_coverage", lambda *_a, **_k: None)
    monkeypatch.setattr("tools.ffi.test.test_ruby_with_coverage", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "tools.ffi.test.test_swift_with_coverage",
        lambda *_a, **_k: skipped("swift-test", "`swift` not found on PATH"),
    )
    with pytest.raises(ToolError, match="FFI tests did not fully pass"):
        _test_ffi(_Ctx(tmp_path), target="all", coverage=True)
    printed = capsys.readouterr().out
    assert "Verification: passed=2, skipped=1" in printed
    assert Status.SKIPPED.value in printed
