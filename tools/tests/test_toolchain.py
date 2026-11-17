"""A missing toolchain reports `skipped`, or `failed` when it was expected.

The helper replaced six near-identical blocks. What matters is that the reason
always names the binary and how to obtain it, and that `required` is the only
thing that turns a skip into a failure.
"""

from __future__ import annotations

import pytest

from tools._lib.status import Status
from tools._lib.toolchain import missing_toolchain


@pytest.fixture
def nothing_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force every toolchain lookup to fail."""
    # `toolchain` imports `shutil` as a module, so patching the attribute reaches it.
    monkeypatch.setattr("shutil.which", lambda _binary: None)


def test_a_present_toolchain_returns_none() -> None:
    """Nothing to report when the binary is there."""
    assert missing_toolchain("demo", "python3", hint="install python") is None


def test_an_absent_toolchain_skips(nothing_on_path: None) -> None:
    """By default the lane skips, and the reason names the binary."""
    absence = missing_toolchain("kotlin", "gradle", hint="run via `pixi run -e kt`")
    assert absence is not None
    result = absence.as_result()
    assert result.status is Status.SKIPPED
    assert "`gradle`" in (result.reason or "")
    assert "pixi run -e kt" in (result.reason or "")


def test_a_required_toolchain_fails(nothing_on_path: None) -> None:
    """`required=True` is the only difference, and it must change the status."""
    absence = missing_toolchain("kotlin", "gradle", hint="install gradle", required=True)
    assert absence is not None
    assert absence.as_result().status is Status.FAILED


def test_every_missing_binary_is_named(nothing_on_path: None) -> None:
    """A multi-binary lane reports all of them, so one install fixes the list."""
    absence = missing_toolchain("jvm", ("javac", "java"), hint="install a JDK")
    assert absence is not None
    assert absence.missing == ("javac", "java")
    reason = absence.as_result().reason or ""
    assert "javac" in reason
    assert "java" in reason


def test_only_the_absent_binaries_are_named(monkeypatch: pytest.MonkeyPatch) -> None:
    """A partly-present pair reports the half that is missing."""

    def _which(binary: str) -> str | None:
        return None if binary == "java" else f"/usr/bin/{binary}"

    monkeypatch.setattr("shutil.which", _which)
    absence = missing_toolchain("jvm", ("javac", "java"), hint="install a JDK")
    assert absence is not None
    assert absence.missing == ("java",)


def test_the_reason_reads_as_a_sentence(nothing_on_path: None) -> None:
    """The log line explains what did not run, not merely that something is absent."""
    absence = missing_toolchain("swift-test", "swift", hint="install the Swift toolchain")
    assert absence is not None
    reason = absence.as_result().reason or ""
    assert reason.startswith("`swift` not found on PATH")
    assert "did not run" in reason
    assert reason.endswith(".")
