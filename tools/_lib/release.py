"""Shared helpers for generating build reports (`report.json`/`report.md`) and changelogs."""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import zipfile
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import tomllib
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from tasknest import ToolError

from tools._lib.status import Status

if TYPE_CHECKING:
    from pathlib import Path

_UTF8 = "utf-8"
_NL = "\n"
_KEY_NAME = "name"
_KEY_STATUS = "status"
_KEY_REASON = "reason"
_COMMA_SEP = ", "
_REPORT_JSON = "report.json"
_REPORT_MD = "report.md"
_CHECKSUMS_FILE = "SHA256SUMS.txt"
_TEMPLATE_NAME = "build-report.md.j2"
_DIST_GLOB_SKIP = {_REPORT_JSON, _REPORT_MD, _CHECKSUMS_FILE}
_ECO_KOTLIN = "kotlin"
_ECO_SWIFT = "swift"
_SWIFT_PREFIX = "polylib-swift"

_ECOSYSTEM_RULES: tuple[tuple[str, str, str], ...] = (
    (".crate", "rust", "crates.io"),
    (".whl", "python", "PyPI"),
    (".tgz", "npm", "npm + GitHub Packages"),
    (".jar", _ECO_KOTLIN, "GitHub Packages Maven / Maven Central"),
    (".gem", "ruby", "RubyGems + GitHub Packages"),
)


def _env_first(primary: str, secondary: str, fallback: str) -> str:
    return os.environ.get(primary) or os.environ.get(secondary) or fallback


def _default_run_url() -> str:
    server = os.environ.get("GITHUB_SERVER_URL", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if server and repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return ""


@dataclass(frozen=True)
class ReportMetadata:
    """Git and workflow metadata embedded in `report.json` and `report.md`."""

    git_ref: str = "local"
    git_sha: str = "HEAD"
    run_url: str = ""
    checks_spec: str = ""

    @classmethod
    def from_env(cls, checks_spec: str = "") -> ReportMetadata:
        """Build metadata from GitHub Actions environment variables when present."""
        return cls(
            git_ref=_env_first("GIT_REF", "GITHUB_REF_NAME", "local"),
            git_sha=_env_first("GIT_SHA", "GITHUB_SHA", "HEAD"),
            run_url=os.environ.get("RUN_URL") or _default_run_url(),
            checks_spec=checks_spec or os.environ.get("CHECKS_SPEC", ""),
        )


def read_workspace_version(root: Path) -> str:
    """Read the canonical workspace version from root `Cargo.toml`, failing closed.

    This value names real artifacts, so a default would stamp an invented
    version onto a gem and a SwiftPM tarball. There is no legitimate case for
    a fallback: a missing key means the manifest is broken.
    """
    manifest = root / "Cargo.toml"
    data = tomllib.loads(manifest.read_text(encoding=_UTF8))
    ws_pkg = data.get("workspace", {}).get("package", {})
    version = ws_pkg.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ToolError(
            f"{manifest} must declare [workspace.package] version; a missing version "
            "cannot be defaulted because it names the release artifacts."
        )
    return version


def _format_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024.0 or unit == "GiB":
            return f"{int(value)} B" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{num_bytes} B"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _classify_artifact(rel_path: str) -> tuple[str, str]:
    """Map a path to an ecosystem and registry, treating the extension as a hypothesis.

    The guess is checked against the artifact's contents in `_verify_artifact`,
    because a misnamed file reported against a registry it cannot be uploaded to
    is worse than an honest "unverified".
    """
    lower = rel_path.lower()
    for suffix, ecosystem, registry in _ECOSYSTEM_RULES:
        if lower.endswith(suffix):
            return ecosystem, registry
    # The Swift bundle is packed under a known prefix, so match that rather than
    # any directory whose name happens to contain "swift".
    if lower.startswith(_SWIFT_PREFIX) and lower.endswith(".tar.gz"):
        return _ECO_SWIFT, "GitHub Releases (SwiftPM)"
    if lower.endswith(".tar.gz"):
        return "python", "PyPI (sdist)"
    if lower.endswith(".pom"):
        return _ECO_KOTLIN, "GitHub Packages Maven / Maven Central"
    return "other", "GitHub Releases"


def _verify_artifact(path: Path, ecosystem: str) -> tuple[bool, str]:
    """Check an artifact's contents agree with the ecosystem its extension implies."""
    try:
        if ecosystem == "python" and path.suffix == ".whl":
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
            ok = any(name.endswith(".dist-info/WHEEL") for name in names) and any(
                name.endswith(".dist-info/METADATA") for name in names
            )
            return ok, "wheel carries .dist-info/WHEEL and METADATA" if ok else "no .dist-info"
        if ecosystem == "rust":
            with tarfile.open(path) as archive:
                names = archive.getnames()
            ok = any(name.endswith("Cargo.toml") for name in names)
            return ok, "crate archive carries Cargo.toml" if ok else "no Cargo.toml in archive"
        if ecosystem == "ruby":
            with tarfile.open(path) as archive:
                names = archive.getnames()
            ok = any(name.endswith("metadata.gz") for name in names)
            return ok, "gem carries metadata.gz" if ok else "no metadata.gz in gem"
        if ecosystem == "npm":
            with tarfile.open(path) as archive:
                names = archive.getnames()
            ok = "package/package.json" in names
            return ok, "tarball carries package/package.json" if ok else "no package/package.json"
        if ecosystem == _ECO_KOTLIN and path.suffix == ".jar":
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
            ok = "META-INF/MANIFEST.MF" in names
            return ok, "jar carries META-INF/MANIFEST.MF" if ok else "no MANIFEST.MF in jar"
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
        return False, f"could not open the archive: {exc}"
    return True, f"no content check defined for {ecosystem}{path.suffix}"


def _collect_artifact_records(artifacts_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(artifacts_dir.rglob("*")):
        if not path.is_file() or path.name in _DIST_GLOB_SKIP:
            continue
        rel = path.relative_to(artifacts_dir).as_posix()
        size_bytes = path.stat().st_size
        ecosystem, registry = _classify_artifact(rel)
        verified, note = _verify_artifact(path, ecosystem)
        records.append(
            {
                _KEY_NAME: path.name,
                "path": rel,
                "ecosystem": ecosystem if verified else "unverified",
                "registry": registry if verified else "unverified",
                "classified_by": f"extension{path.suffix}",
                "verified": verified,
                "verification_note": note,
                "size_bytes": size_bytes,
                "size_human": _format_size(size_bytes),
                "sha256": _sha256_file(path),
            }
        )
    return records


_VALID_CHECK_STATUSES: tuple[str, ...] = tuple(status.value for status in Status)


def _parse_checks(raw_checks: str) -> list[dict[str, Any]]:
    """Parse `name=status` pairs, rejecting unknown statuses and unreasoned non-passes.

    An empty spec reports `not-run` rather than a passing build: the report is
    read as evidence, so inventing a success is worse than saying nothing ran.
    """
    if not raw_checks.strip():
        return [
            {
                _KEY_NAME: "build",
                _KEY_STATUS: Status.NOT_RUN.value,
                _KEY_REASON: "CHECKS_SPEC was empty; no checks were reported",
            }
        ]
    parsed: list[dict[str, Any]] = []
    for entry in raw_checks.split(","):
        cleaned = entry.strip()
        if not cleaned:
            continue
        name, _, rest = cleaned.partition("=")
        status_text, _, reason = rest.partition(":")
        status = status_text.strip() or Status.PASSED.value
        if status not in _VALID_CHECK_STATUSES:
            allowed = _COMMA_SEP.join(_VALID_CHECK_STATUSES)
            raise ToolError(
                f"Unknown check status {status!r} for {name.strip()!r}; expected one of: {allowed}."
            )
        record: dict[str, Any] = {_KEY_NAME: name.strip(), _KEY_STATUS: status}
        reason_text = reason.strip()
        if status != Status.PASSED.value:
            if not reason_text:
                raise ToolError(
                    f"Check {name.strip()!r} has status {status!r} but no reason; "
                    "write `name=status:reason` so the report explains the non-pass."
                )
            record[_KEY_REASON] = reason_text
        elif reason_text:
            record[_KEY_REASON] = reason_text
        parsed.append(record)
    return parsed


def _publish_ready(checks: list[dict[str, Any]], records: list[dict[str, Any]]) -> bool:
    """Publication needs every check to pass and every artifact to be identified."""
    checks_pass = bool(checks) and all(item[_KEY_STATUS] == Status.PASSED.value for item in checks)
    artifacts_verified = all(bool(item.get("verified")) for item in records)
    return checks_pass and artifacts_verified and bool(records)


def _blocking_reasons(checks: list[dict[str, Any]], records: list[dict[str, Any]]) -> list[str]:
    """List why publication is blocked, so the report states it rather than implying it."""
    reasons = [
        f"{item[_KEY_NAME]}: {item[_KEY_STATUS]}"
        + (f" - {item[_KEY_REASON]}" if item.get(_KEY_REASON) else "")
        for item in checks
        if item[_KEY_STATUS] != Status.PASSED.value
    ]
    reasons.extend(
        f"{item['path']}: artifact could not be verified as {item['ecosystem']}"
        for item in records
        if not item.get("verified")
    )
    return reasons


def _render_report_markdown(root: Path, report_data: dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader(root / "templates"),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )
    return env.get_template(_TEMPLATE_NAME).render(**report_data)


def _build_report_payload(
    root: Path,
    records: list[dict[str, Any]],
    meta: ReportMetadata,
) -> dict[str, Any]:
    total_bytes = sum(int(item["size_bytes"]) for item in records)
    ecosystems = sorted({str(item["ecosystem"]) for item in records})
    checks = _parse_checks(meta.checks_spec)
    return {
        "schema_version": 2,
        "publish_ready": _publish_ready(checks, records),
        "blocking": _blocking_reasons(checks, records),
        "version": read_workspace_version(root),
        "git_ref": meta.git_ref,
        "git_sha": meta.git_sha,
        "run_url": meta.run_url,
        "generated_at": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_artifacts": len(records),
            "total_size_bytes": total_bytes,
            "total_size_human": _format_size(total_bytes),
            "ecosystems": ecosystems,
        },
        "checks": checks,
        "artifacts": records,
    }


def generate_build_report(
    root: Path,
    artifacts_dir: Path,
    output_dir: Path,
    meta: ReportMetadata | None = None,
) -> tuple[Path, Path, Path]:
    """Generate `report.json`, Jinja-rendered `report.md`, and `SHA256SUMS.txt`."""
    if not artifacts_dir.is_dir():
        raise ToolError(f"Artifacts directory does not exist: {artifacts_dir}")
    resolved_meta = meta or ReportMetadata.from_env()
    records = _collect_artifact_records(artifacts_dir)
    payload = _build_report_payload(root, records, resolved_meta)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / _REPORT_JSON
    md_path = output_dir / _REPORT_MD
    sums_path = output_dir / _CHECKSUMS_FILE
    json_path.write_text(json.dumps(payload, indent=2) + _NL, encoding=_UTF8)
    loaded: dict[str, Any] = json.loads(json_path.read_text(encoding=_UTF8))
    md_path.write_text(_render_report_markdown(root, loaded), encoding=_UTF8)
    sums_lines = [f"{item['sha256']}  {item['path']}{_NL}" for item in records]
    sums_path.write_text("".join(sums_lines), encoding=_UTF8)
    print(f"Wrote {json_path}, {md_path}, and {sums_path} ({len(records)} artifact(s)).")
    return json_path, md_path, sums_path


def _convco_changelog(root: Path, tag: str) -> tuple[str, str]:
    """Render the convco changelog and report why it was unavailable, if it was.

    The caller falls back to `git log`, and that fallback looks plausible in a
    release body. Returning a reason keeps a broken convco install visible in
    the workflow log instead of silently degrading every release note.
    """
    if shutil.which("convco") is None:
        return "", "convco is not on PATH"
    if not (root / ".git").exists():
        return "", "no .git directory (shallow or archive checkout)"
    cmd = ["convco", "changelog", "--max-versions", "1"]
    if tag:
        cmd.extend(["--unreleased", tag])
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        reason = detail[-1] if detail else f"exit {proc.returncode}"
        return "", f"convco exited {proc.returncode}: {reason}"
    body = proc.stdout.strip()
    if not body:
        # A repository whose history is all non-conventional commits renders an
        # empty body rather than failing, so say so explicitly.
        return "", "convco produced no changelog sections"
    return body, ""


def _git_log_fallback(root: Path) -> str:
    if not (root / ".git").exists():
        return "- Initial release artifacts built and verified across all supported ecosystems."
    proc = subprocess.run(
        ["git", "log", "-n", "20", "--pretty=format:- %s (%h)"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    output = proc.stdout.strip()
    if proc.returncode == 0 and output:
        return output
    return "- Release built and verified across all supported ecosystems."


def generate_release_changelog(
    root: Path,
    output_path: Path,
    *,
    tag: str = "",
    report_md: Path | None = None,
) -> Path:
    """Generate release changelog markdown and optionally append `report.md`."""
    version = read_workspace_version(root)
    release_label = tag or f"v{version}"
    body, reason = _convco_changelog(root, release_label)
    if not body:
        print(f"convco unavailable ({reason}); falling back to git log.")
        fallback_items = _git_log_fallback(root)
        body = f"## Changelog\n\n{fallback_items}"
    else:
        print("Rendered the changelog from conventional commits with convco.")
    sections = [f"# Release {release_label}\n\n{body.strip()}"]
    if report_md is not None and report_md.is_file():
        embedded = report_md.read_text(encoding=_UTF8).strip()
        if embedded.startswith("# "):
            embedded = "#" + embedded
        sections.append(embedded)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n\n---\n\n".join(sections) + _NL, encoding=_UTF8)
    print(f"Wrote release notes to {output_path}")
    return output_path
