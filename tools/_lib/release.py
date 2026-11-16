"""Shared helpers for generating build reports (`report.json`/`report.md`) and changelogs."""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import tomllib
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from tasknest import ToolError

if TYPE_CHECKING:
    from pathlib import Path

_UTF8 = "utf-8"
_NL = "\n"
_KEY_NAME = "name"
_KEY_STATUS = "status"
_REPORT_JSON = "report.json"
_REPORT_MD = "report.md"
_CHECKSUMS_FILE = "SHA256SUMS.txt"
_TEMPLATE_NAME = "build-report.md.j2"
_DIST_GLOB_SKIP = {_REPORT_JSON, _REPORT_MD, _CHECKSUMS_FILE}
_ECO_KOTLIN = "kotlin"
_ECO_SWIFT = "swift"

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
    """Read the canonical workspace package version from root `Cargo.toml`."""
    data = tomllib.loads((root / "Cargo.toml").read_text(encoding=_UTF8))
    ws_pkg = data.get("workspace", {}).get("package", {})
    return str(ws_pkg.get("version", "0.1.0"))


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
    lower = rel_path.lower()
    for suffix, ecosystem, registry in _ECOSYSTEM_RULES:
        if lower.endswith(suffix):
            return ecosystem, registry
    if _ECO_SWIFT in lower and lower.endswith(".tar.gz"):
        return _ECO_SWIFT, "GitHub Releases (SwiftPM)"
    if lower.endswith(".tar.gz"):
        return "python", "PyPI (sdist)"
    if lower.endswith(".pom"):
        return _ECO_KOTLIN, "GitHub Packages Maven / Maven Central"
    return "other", "GitHub Releases"


def _collect_artifact_records(artifacts_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(artifacts_dir.rglob("*")):
        if not path.is_file() or path.name in _DIST_GLOB_SKIP:
            continue
        rel = path.relative_to(artifacts_dir).as_posix()
        size_bytes = path.stat().st_size
        ecosystem, registry = _classify_artifact(rel)
        records.append(
            {
                _KEY_NAME: path.name,
                "path": rel,
                "ecosystem": ecosystem,
                "registry": registry,
                "size_bytes": size_bytes,
                "size_human": _format_size(size_bytes),
                "sha256": _sha256_file(path),
            }
        )
    return records


def _parse_checks(raw_checks: str) -> list[dict[str, str]]:
    if not raw_checks.strip():
        return [{_KEY_NAME: "build", _KEY_STATUS: "success"}]
    parsed: list[dict[str, str]] = []
    for entry in raw_checks.split(","):
        cleaned = entry.strip()
        if not cleaned:
            continue
        if "=" in cleaned:
            name, status = cleaned.split("=", 1)
            parsed.append({_KEY_NAME: name.strip(), _KEY_STATUS: status.strip()})
        else:
            parsed.append({_KEY_NAME: cleaned, _KEY_STATUS: "success"})
    return parsed


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
    return {
        "schema_version": 1,
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
        "checks": _parse_checks(meta.checks_spec),
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


def _convco_changelog(root: Path, tag: str) -> str:
    if shutil.which("convco") is None or not (root / ".git").exists():
        return ""
    cmd = ["convco", "changelog", "--max-versions", "1"]
    if tag:
        cmd.extend(["--unreleased", tag])
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else ""


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
    body = _convco_changelog(root, release_label)
    if not body:
        fallback_items = _git_log_fallback(root)
        body = f"## Changelog\n\n{fallback_items}"
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
