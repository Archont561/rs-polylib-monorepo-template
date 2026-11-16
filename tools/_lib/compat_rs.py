"""Cargo compatibility verification: feature matrix, tarballs, consumer build, MSRV."""

from __future__ import annotations

import argparse
import re
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import tomllib

from tools._lib.stdlib_proc import StdlibCommand, run_capture, run_checked, run_ok

if TYPE_CHECKING:
    from collections.abc import Sequence

_UTF8 = "utf-8"
_CARGO = "cargo"
_CARGO_TOML = "Cargo.toml"
_CRATES_DIR = "crates"
_WORKSPACE_KEY = "workspace"
_PACKAGE_KEY = "package"
_DEFAULT_KEY = "default"
_FLAG_NO_DEFAULT = "--no-default-features"
_FLAG_LOCKED = "--locked"
_FLAG_PKG = "-p"
_SEP = ", "
_METACRATE = "polylib"
_PUBLISH_ORDER: tuple[str, ...] = ("polylib-core", "polylib")
_REQUIRED_FILES: tuple[str, ...] = (_CARGO_TOML, "README.md", "src/lib.rs")
_FORBIDDEN_PREFIXES: tuple[str, ...] = (".pixi-sandbox/", "node_modules/", "target/", ".git/")
_FORBIDDEN_SUFFIXES: tuple[str, ...] = (".feature",)
_REQUIRED_METADATA: tuple[str, ...] = ("description", "license", "repository", "rust-version")
_CFG_FEATURE_RE = re.compile(r'feature\s*=\s*"([^"]+)"')

MODE_ALL = "all"
MODE_FEATURES = "features"
MODE_PACKAGES = "packages"
MODE_CONSUMER = "consumer"
VALID_MODES: tuple[str, ...] = (MODE_ALL, MODE_FEATURES, MODE_PACKAGES, MODE_CONSUMER)


@dataclass(frozen=True)
class FeatureRow:
    """One feature-matrix configuration derived from a crate manifest."""

    name: str
    flags: tuple[str, ...]


def _load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding=_UTF8))


def _workspace_package(root: Path) -> dict[str, Any]:
    manifest = _load_toml(root / _CARGO_TOML)
    ws_pkg: dict[str, Any] = manifest.get(_WORKSPACE_KEY, {}).get(_PACKAGE_KEY, {})
    return ws_pkg


def declared_msrv(root: Path) -> str:
    """Read `[workspace.package] rust-version` as the single source of truth."""
    version = _workspace_package(root).get("rust-version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError("Cargo.toml must declare [workspace.package] rust-version")
    return version.strip()


def feature_matrix(root: Path, crate: str = _METACRATE) -> tuple[FeatureRow, ...]:
    """Derive deduplicated feature-check rows from `crates/<crate>/Cargo.toml`."""
    manifest = _load_toml(root / _CRATES_DIR / crate / _CARGO_TOML)
    features_table: dict[str, list[str]] = manifest.get(MODE_FEATURES, {})
    default_set = tuple(str(item) for item in features_table.get(_DEFAULT_KEY, []))
    named = sorted(name for name in features_table if name != _DEFAULT_KEY)

    rows: list[FeatureRow] = [FeatureRow("no-default-features", (_FLAG_NO_DEFAULT,))]
    if default_set:
        default_flags = (_FLAG_NO_DEFAULT, "--features", ",".join(default_set))
        rows.append(FeatureRow(_DEFAULT_KEY, default_flags))
    for name in named:
        rows.append(FeatureRow(name, (_FLAG_NO_DEFAULT, "--features", name)))
    rows.append(FeatureRow("all-features", ("--all-features",)))
    return tuple(rows)


def _is_unused_empty_feature(name: str, values: list[str], cfg_sites: set[str]) -> bool:
    return name != _DEFAULT_KEY and not values and name not in cfg_sites


def check_feature_usage(root: Path, crate: str = _METACRATE) -> None:
    """Ensure every declared feature in `crates/<crate>` either forwards deps or gates code."""
    crate_dir = root / _CRATES_DIR / crate
    features_table: dict[str, list[str]] = _load_toml(crate_dir / _CARGO_TOML).get(
        MODE_FEATURES, {}
    )
    rs_files = sorted((crate_dir / "src").rglob("*.rs"))
    source_text = "\n".join(path.read_text(encoding=_UTF8) for path in rs_files)
    cfg_sites = set(_CFG_FEATURE_RE.findall(source_text))

    dead = [
        name
        for name, values in features_table.items()
        if _is_unused_empty_feature(name, values, cfg_sites)
    ]
    if dead:
        raise RuntimeError(
            f"Crate {crate} declares unused empty features: {_SEP.join(sorted(dead))}"
        )


def check_features(root: Path, *, toolchain: str | None = None, crate: str = _METACRATE) -> None:
    """Compile every manifest-derived feature row with `cargo check --locked --all-targets`."""
    check_feature_usage(root, crate=crate)
    cargo_cmd = [_CARGO, f"+{toolchain}"] if toolchain else [_CARGO]
    for row in feature_matrix(root, crate=crate):
        argv = [*cargo_cmd, "check", _FLAG_LOCKED, "--all-targets", _FLAG_PKG, crate, *row.flags]
        run_checked(argv, root)


def _check_single_package(root: Path, crate: str, ws_pkg: dict[str, Any]) -> None:
    cmd = [_CARGO, _PACKAGE_KEY, "--list", _FLAG_LOCKED, _FLAG_PKG, crate, "--allow-dirty"]
    result = run_capture(StdlibCommand(argv=cmd, cwd=root))
    if result.returncode != 0:
        raise RuntimeError(f"`{' '.join(cmd)}` failed:\n{result.stderr}")
    files = [line for line in result.stdout.splitlines() if line and line == line.strip()]
    missing = [req for req in _REQUIRED_FILES if req not in files]
    forbidden = [
        item
        for item in files
        if item.startswith(_FORBIDDEN_PREFIXES) or item.endswith(_FORBIDDEN_SUFFIXES)
    ]
    if missing:
        raise RuntimeError(f"{crate} tarball missing required files: {_SEP.join(missing)}")
    if forbidden:
        raise RuntimeError(f"{crate} tarball includes forbidden repo paths: {_SEP.join(forbidden)}")
    pkg = _load_toml(root / _CRATES_DIR / crate / _CARGO_TOML).get(_PACKAGE_KEY, {})
    for field in _REQUIRED_METADATA:
        val = pkg.get(field)
        is_ws = isinstance(val, dict) and val.get(_WORKSPACE_KEY) is True
        resolved = ws_pkg.get(field) if is_ws else val
        if not resolved:
            raise RuntimeError(f"{crate} is missing publish metadata field: {field}")


def check_packages(root: Path, crates: Sequence[str] = _PUBLISH_ORDER) -> None:
    """Verify `cargo package --list` contents and metadata for publishable crates."""
    ws_pkg = _workspace_package(root)
    for crate in crates:
        _check_single_package(root, crate, ws_pkg)
    print(f"check-packages: {_SEP.join(crates)} OK")


def _unpack_crates(root: Path, target_dir: Path, unpacked_dir: Path) -> str:
    version = str(_workspace_package(root)["version"])
    pkg_args = [arg for crate in _PUBLISH_ORDER for arg in (_FLAG_PKG, crate)]
    run_checked(
        [
            _CARGO,
            _PACKAGE_KEY,
            _FLAG_LOCKED,
            "--no-verify",
            "--allow-dirty",
            *pkg_args,
            "--target-dir",
            str(target_dir),
        ],
        root,
    )
    for crate in _PUBLISH_ORDER:
        crate_tarball = target_dir / _PACKAGE_KEY / f"{crate}-{version}.crate"
        with tarfile.open(crate_tarball, "r:gz") as archive:
            archive.extractall(unpacked_dir, filter="data")
    return version


def _consumer_manifest(version: str, unpacked_dir: Path, *, enable_full: bool) -> str:
    dep = (
        f'polylib = {{ version = "={version}", features = ["full"] }}'
        if enable_full
        else f'polylib = {{ version = "={version}", default-features = false }}'
    )
    core_path = (unpacked_dir / f"polylib-core-{version}").as_posix()
    meta_path = (unpacked_dir / f"polylib-{version}").as_posix()
    return (
        "[workspace]\n\n"
        '[package]\nname = "consumer"\nversion = "0.0.0"\nedition = "2024"\n\n'
        f"[dependencies]\n{dep}\n\n"
        f'[patch.crates-io]\npolylib-core = {{ path = "{core_path}" }}\n'
        f'polylib = {{ path = "{meta_path}" }}\n'
    )


def _consumer_test_source(*, enable_full: bool) -> str:
    json_assert = (
        '    let encoded = polylib::summarize_scores_json(&[10.0, 20.0]).expect("json");\n'
        '    assert!(encoded.contains("\\"mean\\":15.0"));\n'
        if enable_full
        else ""
    )
    return (
        "use polylib::prelude::*;\n\n"
        "#[test]\nfn consumer_smoke() {\n"
        '    assert_eq!(normalize_slug("Hello Crate!"), Ok("hello-crate".to_owned()));\n'
        '    let summary = summarize_scores(&[10.0, 20.0]).expect("scores");\n'
        "    assert_eq!(summary.count, 2);\n"
        f"{json_assert}"
        "}\n"
    )


def verify_crate_consumer(root: Path) -> None:
    """Pack, unpack, and compile-test publishable `.crate` tarballs from an isolated consumer."""
    with tempfile.TemporaryDirectory(prefix="polylib-rs-compat-") as tmp:
        tmp_path = Path(tmp)
        unpacked = tmp_path / "unpacked"
        unpacked.mkdir()
        version = _unpack_crates(root, tmp_path / "target", unpacked)
        for label, enable_full in (("minimal", False), ("full", True)):
            consumer = tmp_path / f"consumer-{label}"
            (consumer / "tests").mkdir(parents=True)
            (consumer / _CARGO_TOML).write_text(
                _consumer_manifest(version, unpacked, enable_full=enable_full),
                encoding=_UTF8,
            )
            (consumer / "tests" / "smoke.rs").write_text(
                _consumer_test_source(enable_full=enable_full),
                encoding=_UTF8,
            )
            if not run_ok([_CARGO, "test", "--offline"], consumer):
                raise RuntimeError(f"Isolated .crate consumer test ({label}) failed")
    print("rs-compat: unpacked .crate consumer checks (minimal + full) OK")


def _main() -> int:
    parser = argparse.ArgumentParser(description="Verify Rust Cargo compatibility matrix.")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_ALL)
    parser.add_argument("--toolchain", default="")
    args = parser.parse_args()
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[2]
    if args.mode in (MODE_ALL, MODE_FEATURES):
        check_features(repo_root, toolchain=args.toolchain or None)
    if args.mode in (MODE_ALL, MODE_PACKAGES):
        check_packages(repo_root)
    if args.mode in (MODE_ALL, MODE_CONSUMER):
        verify_crate_consumer(repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
