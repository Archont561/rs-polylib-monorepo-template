"""Tests for the build-report helpers: checks, version, and artifact classification."""

from __future__ import annotations

import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest
from tasknest import ToolError

from tools._lib.release import (
    ReportMetadata,
    _build_report_payload,
    _classify_artifact,
    _collect_artifact_records,
    _parse_checks,
    _verify_artifact,
    read_workspace_version,
)


def test_empty_checks_spec_reports_not_run() -> None:
    """An empty spec must not fabricate a passing build."""
    checks = _parse_checks("")
    assert len(checks) == 1
    assert checks[0]["status"] == "not-run"
    assert "empty" in checks[0]["reason"]


def test_unknown_status_is_rejected() -> None:
    """Statuses are a closed vocabulary."""
    with pytest.raises(ToolError, match="Unknown check status"):
        _parse_checks("build=green")


def test_non_pass_requires_a_reason() -> None:
    """A skipped or failed check without a reason is rejected."""
    with pytest.raises(ToolError, match="no reason"):
        _parse_checks("build=skipped")


def test_non_pass_with_a_reason_is_accepted() -> None:
    """`name=status:reason` carries the explanation through."""
    checks = _parse_checks("build=skipped:no toolchain")
    assert checks[0]["status"] == "skipped"
    assert checks[0]["reason"] == "no toolchain"


def test_passed_check_needs_no_reason() -> None:
    """The pass path stays terse."""
    checks = _parse_checks("lint=passed,tests=passed")
    assert [item["status"] for item in checks] == ["passed", "passed"]


def test_missing_workspace_version_raises(tmp_path: Path) -> None:
    """A version names artifacts, so it cannot default."""
    (tmp_path / "Cargo.toml").write_text('[workspace.package]\nname = "x"\n', encoding="utf-8")
    with pytest.raises(ToolError, match="must declare"):
        read_workspace_version(tmp_path)


def test_present_workspace_version_is_returned(tmp_path: Path) -> None:
    """The happy path reads the declared value."""
    (tmp_path / "Cargo.toml").write_text(
        '[workspace.package]\nversion = "9.9.9"\n', encoding="utf-8"
    )
    assert read_workspace_version(tmp_path) == "9.9.9"


def test_classification_uses_the_known_swift_prefix() -> None:
    """A Swift bundle is matched by its pack prefix, not a substring of any path."""
    eco, _ = _classify_artifact("polylib-swift-1.0.0.tar.gz")
    assert eco == "swift"
    # A non-Swift path that merely contains "swift" is not a Swift release.
    eco2, _ = _classify_artifact("notes/swift/other.tar.gz")
    assert eco2 == "python"


def test_wheel_without_dist_info_is_unverified(tmp_path: Path) -> None:
    """A wheel missing .dist-info cannot be uploaded, so it is not verified."""
    wheel = tmp_path / "polylib-1.0.0-cp310-cp310-linux_x86_64.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("polylib/__init__.py", "")
    verified, note = _verify_artifact(wheel, "python")
    assert not verified
    assert "dist-info" in note


def test_crate_without_cargo_toml_is_unverified(tmp_path: Path) -> None:
    """A `.crate` must carry Cargo.toml to be a crate."""
    crate = tmp_path / "polylib-1.0.0.crate"
    with tarfile.open(crate, "w:gz") as archive:
        data = b"nothing"
        info = tarfile.TarInfo("polylib-1.0.0/README.md")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    verified, note = _verify_artifact(crate, "rust")
    assert not verified
    assert "Cargo.toml" in note


def test_npm_tarball_requires_package_json(tmp_path: Path) -> None:
    """An npm tarball must carry `package/package.json`."""
    tgz = tmp_path / "polylib-1.0.0.tgz"
    with tarfile.open(tgz, "w:gz") as archive:
        data = b"{}"
        info = tarfile.TarInfo("package/package.json")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    verified, _ = _verify_artifact(tgz, "npm")
    assert verified


def test_unverified_artifact_blocks_publish_readiness(tmp_path: Path) -> None:
    """An artifact the tool cannot identify clears publish_ready."""
    art = tmp_path / "art"
    art.mkdir()
    (art / "mystery.bin").write_bytes(b"\x00\x01\x02")
    records = _collect_artifact_records(art)
    payload = _build_report_payload(Path("."), records, ReportMetadata(checks_spec="build=passed"))
    assert payload["schema_version"] == 2
    # A `.bin` classifies as `other` with no content check, so it stays verified.
    # Force the unverified path with a wheel that has no metadata.
    (art / "broken-1.0-py3-none-any.whl").write_bytes(b"not a zip")
    records = _collect_artifact_records(art)
    assert any(not item["verified"] for item in records)
    payload = _build_report_payload(Path("."), records, ReportMetadata(checks_spec="build=passed"))
    assert payload["publish_ready"] is False
    assert payload["blocking"]


def test_all_passing_checks_and_verified_artifacts_set_publish_ready(tmp_path: Path) -> None:
    """The positive case, so the gate is not simply always false."""
    art = tmp_path / "art"
    art.mkdir()
    (art / "note.txt").write_text("hello", encoding="utf-8")
    records = _collect_artifact_records(art)
    payload = _build_report_payload(Path("."), records, ReportMetadata(checks_spec="build=passed"))
    assert payload["publish_ready"] is True
    assert payload["blocking"] == []


def test_report_json_round_trips(tmp_path: Path) -> None:
    """The payload is JSON-serialisable, which the writer depends on."""
    art = tmp_path / "art"
    art.mkdir()
    payload = _build_report_payload(Path("."), _collect_artifact_records(art), ReportMetadata())
    assert json.loads(json.dumps(payload))["schema_version"] == 2
