"""A verifier whose toolchain is absent must report a skip, never a verdict.

Each of these covers a site where a missing binary used to produce either a
reassuring message having run nothing, or silence followed by the caller
printing an unqualified pass. A happy-path test cannot catch that, so every
case here runs with the toolchain forced absent.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import tools._lib.compat_ffi as compat_ffi
import tools._lib.compat_ts_node as compat_ts_node
import tools._lib.ffi as ffi_mod
import tools._lib.ffi_cov as ffi_cov
from tools._lib.status import Status, publish_ready, render

# Tests must not depend on the directory Pytest was invoked from.
_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def no_toolchains(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force every toolchain lookup to fail."""
    monkeypatch.setattr(shutil, "which", lambda _binary: None)


def _assert_no_success_words(text: str) -> None:
    """A skipped lane must not print a verdict claiming the work succeeded."""
    lowered = text.lower()
    for forbidden in ("compatibility ok", "artifacts verified", "+ standalone jvm", "passed."):
        assert forbidden not in lowered, f"skip printed a success claim: {forbidden!r}"


def test_kotlin_compat_skips_with_a_reason(
    no_toolchains: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Site 1: absent gradle is a skip, and the reason names the binary."""
    results = compat_ffi.verify_kotlin_compat(_REPO_ROOT)
    assert [item.status for item in results] == [Status.SKIPPED]
    assert "gradle" in (results[0].reason or "")
    _assert_no_success_words(render(results))


def test_kotlin_requires_toolchain_when_asked(no_toolchains: None) -> None:
    """On a runner where the toolchain is expected, absence is a failure."""
    results = compat_ffi.verify_kotlin_compat(_REPO_ROOT, require_toolchain=True)
    assert results[0].status is Status.FAILED


def test_ruby_compat_skips_with_a_reason(no_toolchains: None) -> None:
    """Site 2: absent gem is a skip, not an unqualified OK."""
    results = compat_ffi.verify_ruby_compat(_REPO_ROOT)
    assert [item.status for item in results] == [Status.SKIPPED]
    assert "gem" in (results[0].reason or "")


def test_swift_c_abi_skips_without_a_compiler(no_toolchains: None) -> None:
    """Site 4: no cc/gcc/clang is a skip that names all three."""
    result = compat_ffi._verify_swift_c_abi_smoke(_REPO_ROOT)
    assert result.status is Status.SKIPPED
    reason = result.reason or ""
    for binary in ("cc", "gcc", "clang"):
        assert binary in reason
    _assert_no_success_words(render([result]))


def test_kotlin_standalone_skips_without_classpath(tmp_path: Path) -> None:
    """Site 5: a missing classpath file is a skip, not silence."""
    result = compat_ffi._verify_kotlin_standalone_jar(tmp_path / "x.jar", tmp_path)
    assert result.status is Status.SKIPPED
    assert "runtime-classpath.txt" in (result.reason or "")


def test_kotlin_standalone_skips_without_a_jdk(tmp_path: Path, no_toolchains: None) -> None:
    """Site 5: a missing JDK is a skip even when the classpath exists."""
    build = tmp_path / "build"
    build.mkdir()
    (build / "runtime-classpath.txt").write_text("", encoding="utf-8")
    result = compat_ffi._verify_kotlin_standalone_jar(tmp_path / "x.jar", tmp_path)
    assert result.status is Status.SKIPPED
    assert "javac" in (result.reason or "") or "java" in (result.reason or "")


def test_node_consumers_return_a_skip_when_absent(no_toolchains: None) -> None:
    """Site 6: the return value carries the skip instead of being discarded."""
    result = compat_ts_node.verify_node_consumers(Path(), {}, require_node=False)
    assert result.status is Status.SKIPPED
    assert "node" in (result.reason or "")


def test_node_consumers_fail_when_node_is_required(no_toolchains: None) -> None:
    """Site 6: `--mode node` makes an absent Node.js a failure."""
    result = compat_ts_node.verify_node_consumers(Path(), {}, require_node=True)
    assert result.status is Status.FAILED


def test_swift_test_with_coverage_skips(no_toolchains: None) -> None:
    """Site 7: absent swift is a skip carrying a reason, not a silent return."""

    class _Ctx:
        repo_root = _REPO_ROOT

    result = ffi_cov.test_swift_with_coverage(_Ctx())
    assert result.status is Status.SKIPPED
    assert "swift" in (result.reason or "")


def test_swift_test_skips_and_never_claims_a_pass(
    no_toolchains: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Site 1 in ffi.py: artifacts present but no swift is a skip, not `verified`."""

    class _Ctx:
        repo_root = Path("/nonexistent-raises")

        def run(self, *_a: object, **_k: object) -> None:
            raise AssertionError("ctx.run must not be reached when swift is absent")

    # _verify_swift_artifacts raises on missing files, so patch it to a no-op
    monkeypatch.setattr(ffi_mod, "_verify_swift_artifacts", lambda _root: None)
    result = ffi_mod.test_swift(_Ctx())
    assert result.status is Status.SKIPPED
    _assert_no_success_words(render([result]))


def test_any_skip_blocks_publish_ready() -> None:
    """The gate must not read a skip as success."""
    from tools._lib.status import passed, skipped

    assert not publish_ready([passed("a"), skipped("b", "no toolchain")])
