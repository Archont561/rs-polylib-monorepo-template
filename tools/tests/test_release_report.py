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

# Tests must not depend on the directory Pytest was invoked from.
_REPO_ROOT = Path(__file__).resolve().parents[2]


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
    payload = _build_report_payload(_REPO_ROOT, records, ReportMetadata(checks_spec="build=passed"))
    assert payload["schema_version"] == 2
    # A `.bin` classifies as `other` with no content check, so it stays verified.
    # Force the unverified path with a wheel that has no metadata.
    (art / "broken-1.0-py3-none-any.whl").write_bytes(b"not a zip")
    records = _collect_artifact_records(art)
    assert any(not item["verified"] for item in records)
    payload = _build_report_payload(_REPO_ROOT, records, ReportMetadata(checks_spec="build=passed"))
    assert payload["publish_ready"] is False
    assert payload["blocking"]


def test_all_passing_checks_and_verified_artifacts_set_publish_ready(tmp_path: Path) -> None:
    """The positive case, so the gate is not simply always false."""
    art = tmp_path / "art"
    art.mkdir()
    (art / "note.txt").write_text("hello", encoding="utf-8")
    records = _collect_artifact_records(art)
    payload = _build_report_payload(_REPO_ROOT, records, ReportMetadata(checks_spec="build=passed"))
    assert payload["publish_ready"] is True
    assert payload["blocking"] == []


def test_report_json_round_trips(tmp_path: Path) -> None:
    """The payload is JSON-serialisable, which the writer depends on."""
    art = tmp_path / "art"
    art.mkdir()
    payload = _build_report_payload(_REPO_ROOT, _collect_artifact_records(art), ReportMetadata())
    assert json.loads(json.dumps(payload))["schema_version"] == 2


def test_github_actions_conclusions_are_accepted() -> None:
    """`build.yml` passes `needs.<job>.result`, whose vocabulary is GitHub's."""
    checks = _parse_checks("build-rust=success,build-npm=success")
    assert [item["status"] for item in checks] == ["passed", "passed"]


def test_a_failed_github_conclusion_blocks_with_a_reason() -> None:
    """A failed job is `failed`, and the report says what it was told."""
    checks = _parse_checks("build-npm=failure")
    assert checks[0]["status"] == "failed"
    assert "failure" in checks[0]["reason"]


def test_a_cancelled_job_is_not_a_pass() -> None:
    """`cancelled` and `timed_out` are outcomes to report, not to ignore."""
    for conclusion in ("cancelled", "timed_out", "action_required"):
        checks = _parse_checks(f"build-npm={conclusion}")
        assert checks[0]["status"] == "failed", conclusion


def test_a_skipped_job_needs_a_reason_despite_the_shared_word() -> None:
    """`skipped` exists in both vocabularies, so it is native and must explain itself."""
    with pytest.raises(ToolError, match="no reason"):
        _parse_checks("build-swift=skipped")
    checks = _parse_checks("build-swift=skipped:Swift toolchain absent")
    assert checks[0]["status"] == "skipped"
    assert checks[0]["reason"] == "Swift toolchain absent"


def test_the_build_workflow_vocabulary_parses_end_to_end(tmp_path: Path) -> None:
    """The spec `build.yml` actually produces must parse without raising."""
    spec = (
        "build-rust=success,build-python-wheels=success,build-python-sdist=success,"
        "build-npm=success,build-uniffi-kotlin-ruby=success,build-uniffi-swift=success"
    )
    art = tmp_path / "art"
    art.mkdir()
    payload = _build_report_payload(
        _REPO_ROOT, _collect_artifact_records(art), ReportMetadata(checks_spec=spec)
    )
    assert len(payload["checks"]) == 6
    # No artifacts were supplied, so nothing can be published; the point here is
    # that the spec parses and every check is a pass.
    assert {item["status"] for item in payload["checks"]} == {"passed"}
    assert payload["publish_ready"] is False


def test_a_passing_report_renders_under_strict_undefined(tmp_path: Path) -> None:
    """A passing check carries no reason; the template must not choke on that."""
    from tools._lib.release import generate_build_report

    art = tmp_path / "art"
    art.mkdir()
    (art / "polylib-0.1.0.crate").write_bytes(b"")
    out = tmp_path / "out"
    generate_build_report(_REPO_ROOT, art, out, ReportMetadata(checks_spec="build-rust=success"))
    rendered = (out / "report.md").read_text(encoding="utf-8")
    assert "Publish-ready:" in rendered
    assert "`build-rust`" in rendered
    assert "| Gate | Status | Reason |" in rendered


def test_a_blocked_report_lists_its_blockers(tmp_path: Path) -> None:
    """When publication is blocked the report says why, not just `false`."""
    from tools._lib.release import generate_build_report

    art = tmp_path / "art"
    art.mkdir()
    out = tmp_path / "out"
    generate_build_report(_REPO_ROOT, art, out, ReportMetadata(checks_spec="build-npm=failure"))
    rendered = (out / "report.md").read_text(encoding="utf-8")
    assert "Publish-ready:** `false`" in rendered
    assert "build-npm: failed" in rendered


def test_the_build_workflow_run_block_succeeds(tmp_path: Path) -> None:
    """Run the exact command `build.yml` issues, with its own vocabulary.

    `build.yml` only triggers on push to `main`, so CI cannot catch a break
    here before merge. This test is the check that would have.
    """
    from tools._lib.release import generate_build_report

    art = tmp_path / "dist-release"
    art.mkdir()
    with zipfile.ZipFile(art / "polylib-0.1.0-cp310-abi3-manylinux_2_28_x86_64.whl", "w") as z:
        z.writestr("polylib-0.1.0.dist-info/WHEEL", "")
        z.writestr("polylib-0.1.0.dist-info/METADATA", "")
    spec = (
        "build-rust=success,build-python-wheels=success,build-python-sdist=success,"
        "build-npm=success,build-uniffi-kotlin-ruby=success,build-uniffi-swift=success"
    )
    out = tmp_path / "dist-report"
    generate_build_report(_REPO_ROOT, art, out, ReportMetadata(checks_spec=spec))
    payload = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert payload["publish_ready"] is True
    assert payload["blocking"] == []
    assert [c["status"] for c in payload["checks"]] == ["passed"] * 6
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "| Gate | Status | Reason |" in report
    assert "`build-uniffi-swift`" in report


def test_tests_do_not_depend_on_the_invocation_directory() -> None:
    """`python test --coverage` runs Pytest from the repo root; a bare `pytest`
    over both testpaths may not. Anchoring to `__file__` keeps both the same,
    which is what CI caught when this module used a cwd-relative `Path(".")`."""
    assert _REPO_ROOT.is_dir()
    assert (_REPO_ROOT / "Cargo.toml").is_file()
    assert (_REPO_ROOT / "pyproject.toml").is_file()
