"""Selecting one lane must be a complete run, not a run with skips.

`--target kotlin` asks for Kotlin. Reporting Swift as `skipped` because it was
not asked for makes every scoped run fail its own readiness gate, which is a
false failure of exactly the kind this work set out to remove.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from tools._lib.status import Status, publish_ready

# `@tool` returns a TaskDefinition; the plain callable is `.callable_fn`.
from tools.ffi.test import test_ffi as _test_ffi_task

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    import pytest

_test_ffi = _test_ffi_task.callable_fn


@dataclass
class _Ctx:
    """The minimal context `test_ffi` touches."""

    repo_root: Path
    commands: list[list[str]] = field(default_factory=list)

    def run(self, argv: list[str], cwd: Path | None = None) -> None:
        self.commands.append(list(argv))


def test_unselected_lanes_are_not_reported_as_skipped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Only the selected lane appears in the results."""
    monkeypatch.setattr("tools.ffi.test.test_kotlin_with_coverage", lambda *_a, **_k: None)
    seen: list[str] = []

    def _record(results: Sequence[object]) -> bool:
        seen.extend(item.name for item in results)  # type: ignore[attr-defined]
        return True

    monkeypatch.setattr("tools.ffi.test.publish_ready", _record)
    _test_ffi(_Ctx(tmp_path), target="kotlin", coverage=True)
    assert seen == ["kotlin-test"]
    assert "swift-test" not in seen


def test_a_scoped_run_reaches_publish_ready(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A single selected lane that ran is a complete run."""
    monkeypatch.setattr("tools.ffi.test.test_kotlin_with_coverage", lambda *_a, **_k: None)
    captured: list[Status] = []

    def _record(results: Sequence[object]) -> bool:
        captured.extend(item.status for item in results)  # type: ignore[attr-defined]
        return bool(publish_ready(results))  # type: ignore[arg-type]

    monkeypatch.setattr("tools.ffi.test.publish_ready", _record)
    _test_ffi(_Ctx(tmp_path), target="kotlin", coverage=True)
    assert captured == [Status.PASSED]
