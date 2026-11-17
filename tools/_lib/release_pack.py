"""Helpers for packing release artifacts and re-scoping npm tarballs for GitHub Packages."""

from __future__ import annotations

import io
import json
import shutil
import tarfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from tasknest import ToolError

from tools._lib.release import read_workspace_version

if TYPE_CHECKING:
    from tasknest import ToolContext

_UTF8 = "utf-8"
_NL = "\n"
_KEY_NAME = "name"
_KEY_PACKAGE = "package"
_DIR_BUILD = "build"
_PACKAGES_DIR = "packages"
PackTarget = Literal["all", "rust", "npm", "kotlin", "ruby", "swift"]

_TARGET_ALL: PackTarget = "all"
_TARGET_RUST = "rust"
_TARGET_NPM = "npm"
_TARGET_KOTLIN = "kotlin"
_TARGET_RUBY = "ruby"
_TARGET_SWIFT = "swift"
VALID_PACK_TARGETS: tuple[str, ...] = (
    _TARGET_ALL,
    _TARGET_RUST,
    _TARGET_NPM,
    _TARGET_KOTLIN,
    _TARGET_RUBY,
    _TARGET_SWIFT,
)


def _pack_rust(ctx: ToolContext, out_dir: Path) -> None:
    rust_out = out_dir / _TARGET_RUST
    rust_out.mkdir(parents=True, exist_ok=True)
    ctx.run(
        [
            "cargo",
            _KEY_PACKAGE,
            "--locked",
            "--no-verify",
            "--allow-dirty",
            "-p",
            "polylib-core",
            "-p",
            "polylib",
        ],
        cwd=ctx.repo_root,
    )
    pkg_dir = Path(ctx.repo_root) / "target" / _KEY_PACKAGE
    for crate_file in sorted(pkg_dir.glob("*.crate")):
        shutil.copy2(crate_file, rust_out / crate_file.name)


def _pack_npm(ctx: ToolContext, out_dir: Path) -> None:
    npm_out = out_dir / _TARGET_NPM
    npm_out.mkdir(parents=True, exist_ok=True)
    for pkg in ("polylib-wasm", "polylib-js", "polylib-ts"):
        ctx.run(
            ["bun", "pm", "pack", "--cwd", f"{_PACKAGES_DIR}/{pkg}", "--destination", str(npm_out)],
            cwd=ctx.repo_root,
        )


def _pack_kotlin(ctx: ToolContext, out_dir: Path) -> None:
    kt_root = Path(ctx.repo_root) / _PACKAGES_DIR / "polylib-kt"
    kt_out = out_dir / _TARGET_KOTLIN
    kt_out.mkdir(parents=True, exist_ok=True)
    ctx.run(["gradle", "jar", "generatePomFileForMavenPublication", "--no-daemon"], cwd=kt_root)
    for jar in sorted((kt_root / _DIR_BUILD / "libs").glob("polylib-*.jar")):
        shutil.copy2(jar, kt_out / jar.name)
    pom = kt_root / _DIR_BUILD / "publications" / "maven" / "pom-default.xml"
    if pom.is_file():
        shutil.copy2(pom, kt_out / f"polylib-{read_workspace_version(ctx.repo_root)}.pom")


def _pack_ruby(ctx: ToolContext, out_dir: Path) -> None:
    rb_root = Path(ctx.repo_root) / _PACKAGES_DIR / "polylib-rb"
    rb_out = out_dir / _TARGET_RUBY
    rb_out.mkdir(parents=True, exist_ok=True)
    version = read_workspace_version(ctx.repo_root)
    gem_out = rb_out / f"polylib-{version}.gem"
    ctx.run(["gem", _DIR_BUILD, "polylib.gemspec", "--output", str(gem_out)], cwd=rb_root)


def _pack_swift(ctx: ToolContext, out_dir: Path) -> None:
    swift_root = Path(ctx.repo_root) / _PACKAGES_DIR / "polylib-swift"
    swift_out = out_dir / _TARGET_SWIFT
    swift_out.mkdir(parents=True, exist_ok=True)
    version = read_workspace_version(ctx.repo_root)
    archive = swift_out / f"polylib-swift-{version}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for path in sorted(swift_root.rglob("*")):
            rel = path.relative_to(swift_root)
            if ".build" in rel.parts or ".swiftpm" in rel.parts:
                continue
            tar.add(path, arcname=f"polylib-swift/{rel.as_posix()}", recursive=False)


def pack_release_artifacts(
    ctx: ToolContext,
    output_dir: Path,
    target: PackTarget = _TARGET_ALL,
) -> None:
    """Pack release artifacts for one or all ecosystems into `output_dir`."""
    if target not in VALID_PACK_TARGETS:
        choices = ", ".join(VALID_PACK_TARGETS)
        raise ToolError(f"Unsupported pack target {target!r}; expected one of: {choices}.")
    packers = {
        _TARGET_RUST: _pack_rust,
        _TARGET_NPM: _pack_npm,
        _TARGET_KOTLIN: _pack_kotlin,
        _TARGET_RUBY: _pack_ruby,
        _TARGET_SWIFT: _pack_swift,
    }
    selected = tuple(packers) if target == _TARGET_ALL else (target,)
    for name in selected:
        packers[name](ctx, output_dir)
    print(f"Packed release artifacts into {output_dir}")


def _rewrite_pkg_scope(pkg: dict[str, Any], scope: str) -> dict[str, Any]:
    updated = dict(pkg)
    name = str(updated.get(_KEY_NAME, ""))
    if name.startswith("@polylib/"):
        updated[_KEY_NAME] = f"@{scope}/{name.split('/', 1)[1]}"
    for field in ("dependencies", "optionalDependencies", "peerDependencies"):
        deps = updated.get(field)
        if isinstance(deps, dict):
            updated[field] = {
                (f"@{scope}/{k.split('/', 1)[1]}" if k.startswith("@polylib/") else k): v
                for k, v in deps.items()
            }
    updated["publishConfig"] = {"registry": "https://npm.pkg.github.com"}
    return updated


def _repack_single_tgz(src_tgz: Path, dst_tgz: Path, scope: str) -> None:
    with tarfile.open(src_tgz, "r:gz") as src, tarfile.open(dst_tgz, "w:gz") as dst:
        for member in src.getmembers():
            extracted = src.extractfile(member)
            if member.name == "package/package.json" and extracted is not None:
                raw_pkg: dict[str, Any] = json.loads(extracted.read().decode(_UTF8))
                rewritten = _rewrite_pkg_scope(raw_pkg, scope)
                encoded = (json.dumps(rewritten, indent=2) + _NL).encode(_UTF8)
                info = tarfile.TarInfo(member.name)
                info.size = len(encoded)
                info.mode = member.mode
                dst.addfile(info, io.BytesIO(encoded))
            elif extracted is not None:
                dst.addfile(member, extracted)
            else:
                dst.addfile(member)


def repack_npm_for_github_packages(input_dir: Path, output_dir: Path, owner: str) -> list[Path]:
    """Re-scope packed `@polylib/*` tarballs to `@<owner>/*` for GitHub Packages npm."""
    scope = owner.strip().lower().lstrip("@")
    if not scope:
        raise ToolError("GitHub repository owner must be non-empty.")
    output_dir.mkdir(parents=True, exist_ok=True)
    repacked: list[Path] = []
    for tgz in sorted(input_dir.rglob("*.tgz")):
        out_tgz = output_dir / tgz.name.replace("polylib-", f"{scope}-", 1)
        _repack_single_tgz(tgz, out_tgz, scope)
        repacked.append(out_tgz)
    if not repacked:
        raise ToolError(f"No .tgz tarballs found under {input_dir}.")
    print(f"Repacked {len(repacked)} npm tarball(s) under scope @{scope} into {output_dir}")
    return repacked
