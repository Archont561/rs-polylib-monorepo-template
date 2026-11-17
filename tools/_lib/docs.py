"""Render and drift-check Jinja2 documentation and GitHub templates."""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import tomllib
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from tasknest import ToolError

if TYPE_CHECKING:
    from pathlib import Path

_UTF8 = "utf-8"
_NAME_KEY = "name"
_PACKAGES_DIR = "packages"
_FFI_MARKERS: tuple[str, ...] = ("build.gradle.kts", "Package.swift", "polylib.gemspec")

_MANAGED_TEMPLATES: tuple[tuple[str, str], ...] = (
    ("README.md.j2", "README.md"),
    ("AGENTS.md.j2", "AGENTS.md"),
    (
        "github/ISSUE_TEMPLATE/bug_report.yml.j2",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
    ),
    (
        "github/ISSUE_TEMPLATE/feature_request.yml.j2",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
    ),
    (
        "github/ISSUE_TEMPLATE/config.yml.j2",
        ".github/ISSUE_TEMPLATE/config.yml",
    ),
    (
        "github/PULL_REQUEST_TEMPLATE.md.j2",
        ".github/PULL_REQUEST_TEMPLATE.md",
    ),
)

_SCAFFOLD_MAP: dict[str, str] = {
    "crate": "crate-readme.md.j2",
    "py-package": "py-package-readme.md.j2",
    "ts-package": "ts-package-readme.md.j2",
}


@dataclass(frozen=True)
class WorkspaceFacts:
    """Live workspace metadata injected into Jinja2 documentation templates."""

    version: str
    msrv: str
    rust_crates: tuple[str, ...]
    publishable_crates: tuple[str, ...]
    python_packages: tuple[str, ...]
    ts_packages: tuple[str, ...]
    ffi_packages: tuple[str, ...]
    docs_apps: tuple[str, ...]
    issue_areas: tuple[str, ...]


def _read_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding=_UTF8))


def _read_json(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding=_UTF8))
    return data


def _discover_rust_crates(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    all_crates: list[str] = []
    publishable: list[str] = []
    for manifest in sorted((root / "crates").glob("*/Cargo.toml")):
        pkg = _read_toml(manifest).get("package", {})
        name = str(pkg.get(_NAME_KEY, manifest.parent.name))
        all_crates.append(name)
        if pkg.get("publish") is True:
            publishable.append(name)
    return tuple(all_crates), tuple(publishable)


def _python_package_name(manifest: Path) -> str:
    project = _read_toml(manifest).get("project", {})
    return str(project.get(_NAME_KEY, manifest.parent.name))


def _ts_package_name(manifest: Path) -> str:
    return str(_read_json(manifest).get(_NAME_KEY, manifest.parent.name))


def _discover_packages(root: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    packages_root = root / _PACKAGES_DIR
    py_manifests = sorted(packages_root.glob("*/pyproject.toml"))
    ts_manifests = sorted(packages_root.glob("*/package.json"))
    py_pkgs = tuple(_python_package_name(path) for path in py_manifests)
    ts_pkgs = tuple(_ts_package_name(path) for path in ts_manifests)
    return py_pkgs, ts_pkgs


def _is_ffi_package(pkg_dir: Path) -> bool:
    if not pkg_dir.is_dir():
        return False
    return any((pkg_dir / marker).is_file() for marker in _FFI_MARKERS)


def _discover_ffi_packages(root: Path) -> tuple[str, ...]:
    packages_root = root / _PACKAGES_DIR
    return tuple(pkg.name for pkg in sorted(packages_root.iterdir()) if _is_ffi_package(pkg))


def _build_issue_areas(
    rust_crates: tuple[str, ...],
    py_pkgs: tuple[str, ...],
    ts_pkgs: tuple[str, ...],
    ffi_pkgs: tuple[str, ...],
    docs_apps: tuple[str, ...],
) -> tuple[str, ...]:
    return (
        *(f"Rust crate ({name})" for name in rust_crates),
        *(f"Python package ({name})" for name in py_pkgs),
        *(f"TypeScript package ({name})" for name in ts_pkgs),
        *(f"UniFFI package (packages/{name})" for name in ffi_pkgs),
        *(f"Docs app ({name}/)" for name in docs_apps),
        "Tooling / CI / Pixi / Policy",
    )


def collect_facts(root: Path) -> WorkspaceFacts:
    """Collect live repository facts from Cargo, Python, Bun, and UniFFI manifests."""
    ws_pkg = _read_toml(root / "Cargo.toml").get("workspace", {}).get("package", {})
    rust_crates, publishable = _discover_rust_crates(root)
    py_pkgs, ts_pkgs = _discover_packages(root)
    ffi_pkgs = _discover_ffi_packages(root)
    docs_app = root / "docs"
    docs_apps = (docs_app.name,) if (docs_app / "package.json").is_file() else ()
    return WorkspaceFacts(
        version=str(ws_pkg.get("version", "0.1.0")),
        msrv=str(ws_pkg.get("rust-version", "1.88")),
        rust_crates=rust_crates,
        publishable_crates=publishable,
        python_packages=py_pkgs,
        ts_packages=ts_pkgs,
        ffi_packages=ffi_pkgs,
        docs_apps=docs_apps,
        issue_areas=_build_issue_areas(rust_crates, py_pkgs, ts_pkgs, ffi_pkgs, docs_apps),
    )


def _jinja_env(root: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(root / "templates"),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        autoescape=False,
    )


def _sync_target(root: Path, rel_path: str, expected: str, *, check_only: bool) -> bool:
    target = root / rel_path
    actual = target.read_text(encoding=_UTF8) if target.exists() else ""
    if actual == expected:
        print(f"OK {rel_path}")
        return True
    if check_only:
        diff = difflib.unified_diff(
            actual.splitlines(True),
            expected.splitlines(True),
            fromfile=rel_path,
            tofile=f"generated/{rel_path}",
        )
        print("".join(diff))
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(expected, encoding=_UTF8)
    print(f"WROTE {rel_path}")
    return True


def sync_docs(root: Path, *, check_only: bool) -> None:
    """Render all managed documentation and GitHub templates, or fail on drift."""
    facts = collect_facts(root)
    env = _jinja_env(root)
    context = {
        "version": facts.version,
        "msrv": facts.msrv,
        "rust_crates": facts.rust_crates,
        "publishable_crates": facts.publishable_crates,
        "python_packages": facts.python_packages,
        "ts_packages": facts.ts_packages,
        "ffi_packages": facts.ffi_packages,
        "docs_apps": facts.docs_apps,
        "issue_areas": facts.issue_areas,
    }
    drifted = [
        target
        for template, target in _MANAGED_TEMPLATES
        if not _sync_target(
            root,
            target,
            env.get_template(template).render(**context),
            check_only=check_only,
        )
    ]
    if drifted:
        raise ToolError(f"Generated docs/templates are out of date: {', '.join(drifted)}")


def scaffold_unit_readme(root: Path, kind: str, name: str, output: Path) -> None:
    """Render a unit README starter template (`crate`, `py-package`, `ts-package`)."""
    template_name = _SCAFFOLD_MAP.get(kind)
    if template_name is None:
        choices = ", ".join(sorted(_SCAFFOLD_MAP))
        raise ToolError(f"Unsupported unit kind {kind!r}; expected one of: {choices}")
    rendered = _jinja_env(root).get_template(template_name).render(name=name)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding=_UTF8)
    print(f"SCAFFOLDED {output}")
