"""Per-platform npm packages for the NAPI-RS binding.

The binding is a compiled ``.node`` addon, so a single tarball can only ever
contain the platform it was built on. The napi-rs convention splits the addon
into one package per target and lists them in ``optionalDependencies``: npm then
installs exactly the one that matches the host and skips the rest.

This module owns the target list, because three other places have to agree with
it: the build matrix that compiles them, the loader that reports a missing
binding, and the checks that confirm the published manifests line up.
"""

from __future__ import annotations

import json
import platform
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tasknest import ToolError

if TYPE_CHECKING:
    from pathlib import Path

_UTF8 = "utf-8"
_JS_PKG = "@polylib/polylib-js"
_MANIFEST = "package.json"

# npm package suffixes, which napi-rs derives from the Rust triple. The order is
# the order the build matrix runs in, and it is also the order the generated
# manifests list: platforms most likely to be used first.
PLATFORM_SUFFIXES: tuple[str, ...] = (
    "linux-x64-gnu",
    "linux-arm64-gnu",
    "linux-x64-musl",
    "linux-arm64-musl",
    "darwin-x64",
    "darwin-arm64",
    "win32-x64-msvc",
    "win32-arm64-msvc",
)

# Rust triple -> npm suffix. Kept parallel to `PLATFORM_SUFFIXES`; the pairing is
# what lets the build matrix and the manifest agree without a hand-written map
# in the workflow.
TRIPLE_TO_SUFFIX: dict[str, str] = {
    "x86_64-unknown-linux-gnu": "linux-x64-gnu",
    "aarch64-unknown-linux-gnu": "linux-arm64-gnu",
    "x86_64-unknown-linux-musl": "linux-x64-musl",
    "aarch64-unknown-linux-musl": "linux-arm64-musl",
    "x86_64-apple-darwin": "darwin-x64",
    "aarch64-apple-darwin": "darwin-arm64",
    "x86_64-pc-windows-msvc": "win32-x64-msvc",
    "aarch64-pc-windows-msvc": "win32-arm64-msvc",
}

# Runner labels, so the matrices can be generated instead of hand-maintained.
# GitHub's arm64 Linux label is the only one that differs from the OS name.
_RUNNER_FOR_SUFFIX: dict[str, str] = {
    "linux-x64-gnu": "ubuntu-latest",
    "linux-arm64-gnu": "ubuntu-24.04-arm",
    "linux-x64-musl": "ubuntu-latest",  # built inside an alpine container
    "linux-arm64-musl": "ubuntu-24.04-arm",  # built inside an alpine container
    "darwin-x64": "macos-13",
    "darwin-arm64": "macos-15",
    "win32-x64-msvc": "windows-latest",
    "win32-arm64-msvc": "windows-11-arm",
}

_MUSL_SUFFIXES = frozenset({"linux-x64-musl", "linux-arm64-musl"})
_DARWIN_X64_ONLY = frozenset({"darwin-x64"})

# `targetTriple` is the key napi-rs writes into each generated per-platform
# manifest, so it is also the most reliable way to read one back.
_TRIPLE_KEYS = ("targetTriple", "triple")


@dataclass(frozen=True)
class PlatformTarget:
    """One supported build target and where it can be compiled."""

    suffix: str
    triple: str
    runner: str

    @property
    def package_name(self) -> str:
        """Return the scoped npm name of the per-platform package."""
        return f"{_JS_PKG}-{self.suffix}"

    @property
    def is_musl(self) -> bool:
        """Report whether the target links musl instead of glibc."""
        return self.suffix in _MUSL_SUFFIXES

    @property
    def is_darwin_x64(self) -> bool:
        """Report whether the target is the Intel macOS build."""
        return self.suffix in _DARWIN_X64_ONLY


PLATFORM_TARGETS: tuple[PlatformTarget, ...] = tuple(
    PlatformTarget(suffix=suffix, triple=triple, runner=_RUNNER_FOR_SUFFIX[suffix])
    for triple, suffix in TRIPLE_TO_SUFFIX.items()
)


def load_targets(manifest: Path) -> tuple[PlatformTarget, ...]:
    """Read `napi.targets` from a package manifest and resolve the runners.

    Reading the manifest rather than the constants above means the loader's
    "supported platforms" message cannot drift from what is actually built.
    """
    data = json.loads(manifest.read_text(encoding=_UTF8))
    triples = (data.get("napi") or {}).get("targets") or []
    resolved: list[PlatformTarget] = []
    for triple in triples:
        suffix = TRIPLE_TO_SUFFIX.get(triple)
        if suffix is None:
            raise ToolError(
                f"Unknown NAPI target {triple!r} in {manifest}. "
                f"Add it to TRIPLE_TO_SUFFIX in tools/_lib/napi_platforms.py."
            )
        resolved.append(
            PlatformTarget(suffix=suffix, triple=triple, runner=_RUNNER_FOR_SUFFIX[suffix])
        )
    return tuple(resolved)


def platform_manifest(
    base: dict[str, object], *, name: str, suffix: str, version: str
) -> dict[str, object]:
    """Build the manifest for one per-platform package.

    npm encodes the host match in `os`, `cpu` and `libc`. Without them npm would
    install every platform package, which is exactly what the optional dependency
    scheme exists to avoid.
    """
    path = next(
        (item for item in PLATFORM_TARGETS if item.suffix == suffix),
        None,
    )
    if path is None:
        raise ToolError(f"Unknown platform suffix {suffix!r}.")
    os_name, cpu, *_rest = suffix.split("-")
    libc: list[str] = []
    if suffix.endswith("-gnu"):
        libc = ["glibc"]
    elif suffix.endswith("-musl"):
        libc = ["musl"]
    manifest: dict[str, object] = {
        "name": name,
        "version": version,
        "description": base.get("description", ""),
        "license": base.get("license", "MIT"),
        "repository": base.get("repository"),
        "homepage": base.get("homepage"),
        "bugs": base.get("bugs"),
        "engines": base.get("engines"),
        "os": [os_name],
        "cpu": [cpu],
        "main": f"polylib.{suffix}.node",
        "files": [f"polylib.{suffix}.node"],
        "publishConfig": {"access": "public"},
    }
    if libc:
        manifest["libc"] = libc
    # Drop the keys the base manifest did not define, so the generated file does
    # not carry `"repository": null` into a published package.
    return {key: value for key, value in manifest.items() if value is not None}


def _read_manifest_version(manifest: Path) -> str:
    data = json.loads(manifest.read_text(encoding=_UTF8))
    version = data.get("version")
    if not isinstance(version, str):
        raise ToolError(f"{manifest} has no string version.")
    return version


def write_platform_packages(
    pkg_dir: Path, *, staging: Path | None = None
) -> list[tuple[Path, dict[str, object]]]:
    """Write one directory per target under `staging` (default `pkg_dir/npm`).

    Returns the directory and manifest of each package so the caller can pack
    them without re-reading the filesystem.
    """
    manifest_path = pkg_dir / _MANIFEST
    base = json.loads(manifest_path.read_text(encoding=_UTF8))
    version = _read_manifest_version(manifest_path)
    out_root = staging if staging is not None else pkg_dir / "npm"
    written: list[tuple[Path, dict[str, object]]] = []
    for target in load_targets(manifest_path):
        package_dir = out_root / target.suffix
        package_dir.mkdir(parents=True, exist_ok=True)
        manifest = platform_manifest(
            base, name=target.package_name, suffix=target.suffix, version=version
        )
        (package_dir / _MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding=_UTF8)
        written.append((package_dir, manifest))
    return written


def optional_dependencies(targets: tuple[PlatformTarget, ...], *, version: str) -> dict[str, str]:
    """Map each platform package onto the exact version it must be installed at.

    The range is exact on purpose: the addon and the loader are generated
    together, and a mixed install is the failure the version check in the
    generated loader exists to catch.
    """
    return {target.package_name: version for target in targets}


def with_optional_dependencies(
    manifest: dict[str, object], targets: tuple[PlatformTarget, ...], *, version: str
) -> dict[str, object]:
    """Return the manifest with `optionalDependencies` replaced by the platform set."""
    updated = dict(manifest)
    updated["optionalDependencies"] = optional_dependencies(targets, version=version)
    return updated


def _target_of_manifest(data: dict[str, object]) -> str | None:
    for key in _TRIPLE_KEYS:
        value = data.get(key)
        if isinstance(value, str):
            return value
    main = data.get("main")
    if isinstance(main, str):
        match = re.search(r"polylib\.(?P<suffix>[a-z0-9-]+)\.node$", main)
        if match:
            return match.group("suffix")
    return None


def _check_platform_manifest(
    package_dir: Path, data: dict[str, object], target: PlatformTarget
) -> list[str]:
    """Check one generated per-platform package against its target."""
    suffix = target.suffix
    problems: list[str] = []
    name = data.get("name")
    if name != target.package_name:
        problems.append(f"{suffix}: package name is {name!r}, expected {target.package_name!r}")
    os_name, cpu = suffix.split("-")[:2]
    if data.get("os") != [os_name]:
        problems.append(f"{suffix}: os is {data.get('os')!r}, expected {[os_name]!r}")
    if data.get("cpu") != [cpu]:
        problems.append(f"{suffix}: cpu is {data.get('cpu')!r}, expected {[cpu]!r}")
    addons = sorted(package_dir.glob("*.node"))
    if len(addons) != 1:
        problems.append(f"{suffix}: ships {len(addons)} .node file(s), expected exactly 1")
    elif addons[0].name != f"polylib.{suffix}.node":
        problems.append(f"{suffix}: addon is {addons[0].name}, expected polylib.{suffix}.node")
    return problems


def verify_platform_packages(pkg_dir: Path, *, npm_dir: Path | None = None) -> list[str]:
    """Check the per-platform packages describe the targets the manifest lists.

    Returns the problems found; an empty list means the set is consistent. Each
    package must name one distinct target, declare the matching `os`/`cpu`, and
    ship exactly one addon.
    """
    manifest_path = pkg_dir / _MANIFEST
    expected = {target.suffix: target for target in load_targets(manifest_path)}
    root = npm_dir if npm_dir is not None else pkg_dir / "npm"
    problems: list[str] = []
    seen: dict[str, Path] = {}
    for package_dir in sorted(root.iterdir()) if root.is_dir() else []:
        manifest_file = package_dir / _MANIFEST
        if not manifest_file.is_file():
            continue
        suffix = package_dir.name
        target = expected.get(suffix)
        if target is None:
            problems.append(f"{suffix}: no matching napi target")
            continue
        if suffix in seen:
            problems.append(f"{suffix}: declared by both {seen[suffix]} and {package_dir}")
        seen[suffix] = package_dir
        data = json.loads(manifest_file.read_text(encoding=_UTF8))
        problems.extend(_check_platform_manifest(package_dir, data, target))
    problems.extend(
        f"{suffix}: no platform package generated" for suffix in expected if suffix not in seen
    )
    return problems


_ARCH_ALIASES: dict[str, str] = {
    "x86_64": "x64",
    "amd64": "x64",
    "aarch64": "arm64",
    "arm64": "arm64",
}
_PLATFORM_ALIASES: dict[str, str] = {"win32": "win32", "windows": "win32", "darwin": "darwin"}


def _host_arch() -> str:
    """Architecture of this interpreter, spelled the way a napi suffix is."""
    machine = platform.machine().lower()
    return _ARCH_ALIASES.get(machine, machine)


def _host_os() -> str:
    """`linux`, `darwin`, or `win32`, independent of how Python names them."""
    system = platform.system().lower()
    return _PLATFORM_ALIASES.get(system, system)


def _host_suffix_for(os_name: str, arch: str, *, musl: bool) -> str:
    """Assemble the suffix a napi target would use on this host."""
    if os_name == "win32":
        return f"win32-{arch}-msvc"
    if os_name == "linux":
        return f"linux-{arch}-{'musl' if musl else 'gnu'}"
    return f"{os_name}-{arch}"


def host_suffix() -> str:
    """The napi platform suffix for the machine running the tests.

    The compatibility fixtures install the addon package by name, so they need
    to know which one this host resolves to. Detection mirrors `detectedPlatform`
    in `packages/polylib-js/src/native.ts`: glibc versus musl is read from the
    interpreter's own runtime rather than assumed.
    """
    os_name = _host_os()
    if os_name == "linux" and _host_arch() not in {"x64", "arm64"}:
        raise ToolError(f"No napi target for linux-{_host_arch()}; add it to PLATFORM_SUFFIXES.")
    return _host_suffix_for(os_name, _host_arch(), musl=is_musl_host())


def is_musl_host() -> bool:
    """Whether this Linux host links musl instead of glibc.

    `platform.libc_ver()` reports ('glibc', ...) on a glibc system and fails to
    identify musl, which is what distinguishes an Alpine image from Debian.
    """
    if _host_os() != "linux":
        return False
    libc, _ = platform.libc_ver()
    return libc != "glibc"
