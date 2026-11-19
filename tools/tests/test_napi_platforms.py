"""Per-platform npm package generation for the NAPI-RS addon.

A single `.node` file can only serve the platform it was built on, so the addon
ships as one package per target, listed in `optionalDependencies`. These tests
pin the manifest shape npm needs to pick the right one, and the checks that keep
the generated set in step with `napi.targets`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from tasknest import ToolError

from tools._lib.compat_ts_consumers import verify_facade_peer_declaration
from tools._lib.napi_platforms import (
    PLATFORM_TARGETS,
    TRIPLE_TO_SUFFIX,
    load_targets,
    optional_dependencies,
    platform_manifest,
    verify_platform_packages,
    with_optional_dependencies,
    write_platform_packages,
)

_TRIPLES = sorted(TRIPLE_TO_SUFFIX)


@dataclass
class _Package:
    """A package directory with a manifest the loader can read."""

    root: Path

    def write(self, targets: list[str] | None = None) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        manifest = {
            "name": "@polylib/polylib-js",
            "version": "0.1.0",
            "license": "MIT",
            "description": "native binding",
            "napi": {"binaryName": "polylib", "targets": targets or list(_TRIPLES)},
        }
        path = self.root / "package.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path


@pytest.fixture
def package(tmp_path: Path) -> _Package:
    return _Package(tmp_path / "polylib-js")


def test_every_known_triple_has_a_suffix() -> None:
    """The map is the only place a new target has to be added."""
    assert len(TRIPLE_TO_SUFFIX) == 8
    assert len(set(TRIPLE_TO_SUFFIX.values())) == 8
    assert "aarch64-pc-windows-msvc" in TRIPLE_TO_SUFFIX
    assert TRIPLE_TO_SUFFIX["x86_64-unknown-linux-musl"] == "linux-x64-musl"


def test_targets_carry_the_runner_that_builds_them() -> None:
    """The build matrix reads these, so a target without a runner would stall."""
    for target in PLATFORM_TARGETS:
        assert target.runner, target.suffix
        assert target.package_name == f"@polylib/polylib-js-{target.suffix}"


def test_load_targets_rejects_an_unknown_triple(package: _Package) -> None:
    """A target nobody mapped must fail loudly rather than be skipped."""
    manifest = package.write(["x86_64-unknown-linux-gnu", "sparc-unknown-linux-gnu"])
    with pytest.raises(ToolError, match="Unknown NAPI target"):
        load_targets(manifest)


def test_load_targets_follows_the_manifest(package: _Package) -> None:
    """The manifest decides, so the message cannot drift from what is built."""
    manifest = package.write(["x86_64-unknown-linux-gnu", "aarch64-apple-darwin"])
    assert [t.suffix for t in load_targets(manifest)] == ["linux-x64-gnu", "darwin-arm64"]


@pytest.mark.parametrize(
    ("suffix", "expected_os", "expected_libc"),
    [
        ("linux-x64-gnu", "linux", ["glibc"]),
        ("linux-arm64-musl", "linux", ["musl"]),
        ("darwin-arm64", "darwin", []),
        ("win32-x64-msvc", "win32", []),
    ],
)
def test_a_platform_manifest_declares_os_cpu_and_libc(
    suffix: str, expected_os: str, expected_libc: list[str]
) -> None:
    """`os`/`cpu`/`libc` are what make npm install exactly one package."""
    manifest = platform_manifest(
        {}, name=f"@polylib/polylib-js-{suffix}", suffix=suffix, version="1.2.3"
    )
    assert manifest["name"] == f"@polylib/polylib-js-{suffix}"
    assert manifest["version"] == "1.2.3"
    assert manifest["os"] == [expected_os]
    assert manifest["cpu"] == [suffix.split("-")[1]]
    assert manifest.get("libc", []) == expected_libc
    assert manifest["main"] == f"polylib.{suffix}.node"
    assert manifest["files"] == [f"polylib.{suffix}.node"]


def test_a_platform_manifest_omits_keys_the_base_does_not_define() -> None:
    """A published package must not carry `"repository": null`."""
    manifest = platform_manifest(
        {}, name="@polylib/polylib-js-linux-x64-gnu", suffix="linux-x64-gnu", version="1.0.0"
    )
    assert "repository" not in manifest
    assert "homepage" not in manifest


def test_optional_dependencies_pin_exact_versions() -> None:
    """A mixed install would mix an addon with a loader from another build."""
    deps = optional_dependencies(PLATFORM_TARGETS, version="0.4.1")
    assert len(deps) == 8
    assert set(deps.values()) == {"0.4.1"}
    assert "@polylib/polylib-js-darwin-arm64" in deps


def test_with_optional_dependencies_replaces_rather_than_merges() -> None:
    """A stale platform package must not survive into the published manifest."""
    manifest: dict[str, object] = {
        "name": "x",
        "optionalDependencies": {"@polylib/polylib-js-old-target": "0.0.1"},
    }
    updated = with_optional_dependencies(manifest, PLATFORM_TARGETS, version="1.0.0")
    dependencies = updated["optionalDependencies"]
    assert isinstance(dependencies, dict)
    assert "@polylib/polylib-js-old-target" not in dependencies


def test_writing_platform_packages_produces_one_directory_per_target(
    package: _Package,
) -> None:
    """Each target gets its own directory and manifest."""
    package.write()
    written = write_platform_packages(package.root)
    assert len(written) == len(_TRIPLES)
    names = {manifest["name"] for _, manifest in written}
    assert names == {target.package_name for target in PLATFORM_TARGETS}


def _place_addons(root: Path) -> None:
    """Drop a stand-in `.node` where `napi artifacts` would copy the real one.

    Each one is a valid header for its own target, because the verification reads
    the container and architecture out of the payload.
    """
    for target in PLATFORM_TARGETS:
        addon = root / "npm" / target.suffix / f"polylib.{target.suffix}.node"
        arch = target.suffix.split("-")[1]
        if target.suffix.startswith("win32-"):
            _write_pe(addon, arch=arch)
        elif target.suffix.startswith("darwin-"):
            _write_macho(addon, arch=arch)
        else:
            _write_elf(addon, arch="aarch64" if arch == "arm64" else "x86_64")


def test_a_written_set_verifies_clean(package: _Package) -> None:
    """Generation and verification must agree."""
    package.write()
    write_platform_packages(package.root)
    _place_addons(package.root)
    assert verify_platform_packages(package.root) == []


def test_verification_reports_a_missing_platform(package: _Package) -> None:
    """A target with no package would fail to install on that platform."""
    package.write()
    write_platform_packages(package.root)
    _place_addons(package.root)
    for name in ("linux-x64-gnu", "darwin-arm64"):
        (package.root / "npm" / name / "package.json").unlink()
    problems = verify_platform_packages(package.root)
    assert any("linux-x64-gnu: no platform package generated" in p for p in problems)


def test_verification_reports_an_unexpected_package(package: _Package) -> None:
    """A stray directory is a target nobody builds."""
    package.write()
    write_platform_packages(package.root)
    _place_addons(package.root)
    stray = package.root / "npm" / "solaris-sparc"
    stray.mkdir()
    (stray / "package.json").write_text("{}", encoding="utf-8")
    problems = verify_platform_packages(package.root)
    assert any("solaris-sparc: no matching napi target" in p for p in problems)


def test_verification_reports_a_wrong_addon_count(package: _Package) -> None:
    """Two addons in one package is ambiguous at require time."""
    package.write()
    write_platform_packages(package.root)
    _place_addons(package.root)
    (package.root / "npm" / "linux-x64-gnu" / "extra.node").write_bytes(b"\x7fELF")
    problems = verify_platform_packages(package.root)
    assert any("ships 2 .node file(s)" in p for p in problems)


def test_verification_reports_a_wrong_os_declaration(package: _Package) -> None:
    """A mislabelled `os` makes npm install the wrong package."""
    package.write()
    written = write_platform_packages(package.root)
    _place_addons(package.root)
    path = next(p for p, m in written if str(m["name"]).endswith("linux-x64-gnu")) / "package.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["os"] = ["darwin"]
    path.write_text(json.dumps(data), encoding="utf-8")
    problems = verify_platform_packages(package.root)
    assert any("os is ['darwin']" in p for p in problems)


def _facade_manifest(**overrides: object) -> dict[str, object]:
    """A packed facade manifest that satisfies every peer rule."""
    manifest: dict[str, object] = {
        "name": "@polylib/polylib",
        "dependencies": {"@polylib/polylib-js": "0.1.0"},
        "peerDependencies": {"@polylib/polylib-wasm": "~0.1.0"},
        "peerDependenciesMeta": {"@polylib/polylib-wasm": {"optional": True}},
    }
    manifest.update(overrides)
    return manifest


def test_a_correct_peer_declaration_passes() -> None:
    assert verify_facade_peer_declaration(_facade_manifest()) == []


@pytest.mark.parametrize("key", ["dependencies", "optionalDependencies"])
def test_a_hard_dependency_on_wasm_is_rejected(key: str) -> None:
    """Only an optional peer keeps the package out of a server install."""
    manifest = _facade_manifest(**{key: {"@polylib/polylib-wasm": "~0.1.0"}})
    assert any(key in problem for problem in verify_facade_peer_declaration(manifest))


def test_a_workspace_protocol_in_the_packed_range_is_rejected() -> None:
    """`workspace:~` is meaningless to npm; only a concrete range packs."""
    manifest = _facade_manifest(peerDependencies={"@polylib/polylib-wasm": "workspace:~"})
    assert any(
        "workspace protocol" in problem for problem in verify_facade_peer_declaration(manifest)
    )


@pytest.mark.parametrize("range_spec", ["^0.1.0", "0.1", "latest", "*"])
def test_a_loose_peer_range_is_rejected(range_spec: str) -> None:
    """A non-`~` range admits a version whose API may differ."""
    manifest = _facade_manifest(peerDependencies={"@polylib/polylib-wasm": range_spec})
    assert any("concrete" in problem for problem in verify_facade_peer_declaration(manifest))


def test_an_optional_peer_must_be_marked_optional() -> None:
    """Without the meta entry npm treats the peer as required."""
    manifest = _facade_manifest(peerDependenciesMeta={})
    assert any("optional" in problem for problem in verify_facade_peer_declaration(manifest))


def test_a_missing_peer_declaration_is_reported() -> None:
    manifest = _facade_manifest(peerDependencies={})
    assert any("missing" in problem for problem in verify_facade_peer_declaration(manifest))


def test_the_typescript_loader_agrees_with_this_table() -> None:
    """The loader's own copy of the suffix map must not drift from this one.

    `bunup.config.ts` needs the mapping at build time, before any Python runs, so
    it carries a copy. Two copies of a table are how `linux-aarch64-gnu` shipped
    instead of `linux-arm64-gnu` once already.
    """
    config = Path(__file__).resolve().parents[2] / "packages" / "polylib-js" / "bunup.config.ts"
    text = config.read_text(encoding="utf-8")
    for triple, suffix in TRIPLE_TO_SUFFIX.items():
        assert f'"{triple}": "{suffix}"' in text, (
            f"{triple} -> {suffix} is missing from bunup.config.ts"
        )


def test_a_dev_dependency_on_wasm_is_allowed() -> None:
    """npm never installs a dependency's devDependencies, so carrying one is fine."""
    manifest = _facade_manifest(devDependencies={"@polylib/polylib-wasm": "0.1.0"})
    assert verify_facade_peer_declaration(manifest) == []


def _write_pe(path: Path, *, arch: str) -> None:
    """Write a minimal PE image declaring `arch`."""
    machine = 0xAA64 if arch == "arm64" else 0x8664
    header = bytearray(b"MZ" + b"\x00" * 62)
    header[0x3C:0x40] = (64).to_bytes(4, "little")  # e_lfanew
    header += b"PE\x00\x00"
    header += machine.to_bytes(2, "little") + b"\x00" * 26
    path.write_bytes(bytes(header))


def _write_macho(path: Path, *, arch: str) -> None:
    """Write a minimal 64-bit little-endian Mach-O header for `arch`."""
    cpu = 0x0100000C if arch == "arm64" else 0x01000007
    path.write_bytes(b"\xcf\xfa\xed\xfe" + cpu.to_bytes(4, "little") + b"\x00" * 24)


def _write_elf(path: Path, *, arch: str) -> None:
    """Write a minimal ELF header declaring `arch`."""
    machine = 183 if arch == "aarch64" else 62
    header = b"\x7fELF" + bytes([2, 1, 1, 0]) + b"\x00" * 8
    header += (2).to_bytes(2, "little")  # e_type
    header += machine.to_bytes(2, "little")
    path.write_bytes(header + b"\x00" * 32)


def test_a_matching_addon_payload_passes(package: _Package) -> None:
    """The common case: a Linux x64 package holding an x86_64 ELF."""
    package.write(["x86_64-unknown-linux-gnu"])
    write_platform_packages(package.root)
    addon = package.root / "npm" / "linux-x64-gnu" / "polylib.linux-x64-gnu.node"
    _write_elf(addon, arch="x86_64")
    assert verify_platform_packages(package.root) == []


def test_an_addon_with_the_wrong_architecture_is_reported(package: _Package) -> None:
    """An aarch64 payload in an x64 package installs where it cannot load."""
    package.write(["x86_64-unknown-linux-gnu"])
    write_platform_packages(package.root)
    addon = package.root / "npm" / "linux-x64-gnu" / "polylib.linux-x64-gnu.node"
    _write_elf(addon, arch="aarch64")
    problems = verify_platform_packages(package.root)
    assert any("addon is aarch64, expected x86_64" in problem for problem in problems)


def test_an_addon_in_the_wrong_container_is_reported(package: _Package) -> None:
    """A Linux payload in a darwin package is never loadable there."""
    package.write(["x86_64-unknown-linux-gnu", "aarch64-apple-darwin"])
    write_platform_packages(package.root)
    _write_elf(package.root / "npm" / "linux-x64-gnu" / "polylib.linux-x64-gnu.node", arch="x86_64")
    _write_elf(package.root / "npm" / "darwin-arm64" / "polylib.darwin-arm64.node", arch="aarch64")
    problems = verify_platform_packages(package.root)
    assert any("darwin-arm64: addon is elf, expected macho" in problem for problem in problems)


def test_an_addon_that_is_not_a_binary_is_reported(package: _Package) -> None:
    """A text file named `.node` fails at require time, after the release."""
    package.write(["x86_64-unknown-linux-gnu"])
    write_platform_packages(package.root)
    addon = package.root / "npm" / "linux-x64-gnu" / "polylib.linux-x64-gnu.node"
    addon.write_text("module.exports = {};\n", encoding="utf-8")
    problems = verify_platform_packages(package.root)
    assert any("is not an ELF, Mach-O, or PE binary" in problem for problem in problems)
