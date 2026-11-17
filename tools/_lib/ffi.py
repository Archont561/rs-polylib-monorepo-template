"""Shared helpers for building, testing, and packaging UniFFI bindings."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from tasknest import ToolError

from tools._lib.ffi_platform import (
    cdylib_filename,
    jna_platform_dir,
)
from tools._lib.ffi_platform import (
    require_tool as _require_tool,
)

if TYPE_CHECKING:
    from tasknest import ToolContext

TARGET_ALL = "all"
TARGET_KOTLIN = "kotlin"
TARGET_SWIFT = "swift"
TARGET_RUBY = "ruby"
VALID_FFI_TARGETS: tuple[str, ...] = (TARGET_ALL, TARGET_KOTLIN, TARGET_SWIFT, TARGET_RUBY)

_UTF8 = "utf-8"
_COMMA_SEP = ", "
_BUILD_CMD = "build"
_TEST_CMD = "test"
_GRADLE_BIN = "gradle"
_BUNDLE_BIN = "bundle"
_GEM_BIN = "gem"
_GENERATED_DIR = "generated"
_SOURCES_DIR = "Sources"
_INCLUDE_DIR = "include"
_SWIFT_FFI_MOD = "PolylibFFI"
_SWIFT_INTERNAL_MOD = "PolylibFFIInternal"
_SWIFT_FFI_FILE = f"{_SWIFT_FFI_MOD}.swift"
_SWIFT_HEADER_FILE = f"{_SWIFT_INTERNAL_MOD}.h"
_PACKAGES_DIR = "packages"
_KT_DIR = "polylib-kt"
_SWIFT_DIR = "polylib-swift"
_RB_DIR = "polylib-rb"
_LIB_STEM = "polylib_ffi"
_UNIFFI_CONFIG = "crates/polylib-ffi/uniffi.toml"
_CDYLIB_BUILD_CMD: tuple[str, ...] = (
    "cargo",
    _BUILD_CMD,
    "--release",
    "-p",
    "polylib-ffi",
    "--locked",
)
_RUBY_FFI_LIB_LINE = "  ffi_lib 'polylib_ffi'"
_RUBY_LOADER_LINE = "  ffi_lib Polylib::NativeLoader.library_candidates"
_SWIFT_MODULEMAP = (
    f'module {_SWIFT_INTERNAL_MOD} {{\n    header "{_SWIFT_HEADER_FILE}"\n    export *\n}}\n'
)


def resolve_ffi_targets(target: str) -> tuple[str, ...]:
    """Validate and expand an FFI target selector into concrete languages."""
    if target not in VALID_FFI_TARGETS:
        choices = _COMMA_SEP.join(VALID_FFI_TARGETS)
        raise ToolError(f"Unsupported FFI target {target!r}; expected one of: {choices}.")
    if target == TARGET_ALL:
        return (TARGET_KOTLIN, TARGET_SWIFT, TARGET_RUBY)
    return (target,)


def build_cdylib(ctx: ToolContext) -> Path:
    """Compile `crates/polylib-ffi` in release mode and return the cdylib path."""
    ctx.run(_CDYLIB_BUILD_CMD, cwd=ctx.repo_root)
    lib_path: Path = Path(ctx.repo_root) / "target" / "release" / cdylib_filename()
    if not lib_path.is_file():
        raise ToolError(f"Expected compiled cdylib at {lib_path}, but it was not found.")
    return lib_path


def _run_bindgen(ctx: ToolContext, cdylib: Path, language: str, out_dir: Path) -> None:
    env = dict(os.environ)
    env["CARGO_PROFILE_DEV_DEBUG"] = "0"
    cmd = [
        "cargo",
        "run",
        "--locked",
        "-p",
        "polylib-ffi",
        "--features",
        "bindgen-cli",
        "--bin",
        "uniffi-bindgen",
        "--",
        "generate",
        "--library",
        str(cdylib),
        "--language",
        language,
        "--no-format",
        "--config",
        _UNIFFI_CONFIG,
        "--out-dir",
        str(out_dir),
    ]
    ctx.run(cmd, cwd=ctx.repo_root, env=env)


def _stage_kotlin(ctx: ToolContext, cdylib: Path) -> None:
    kt_root = ctx.repo_root / _PACKAGES_DIR / _KT_DIR
    gen_src = kt_root / "src" / _GENERATED_DIR / TARGET_KOTLIN
    gen_res = kt_root / "src" / _GENERATED_DIR / "resources" / jna_platform_dir()
    if gen_src.exists():
        shutil.rmtree(gen_src)
    gen_src.mkdir(parents=True, exist_ok=True)
    _run_bindgen(ctx, cdylib, TARGET_KOTLIN, gen_src)
    gen_res.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cdylib, gen_res / cdylib.name)
    print(f"Staged Kotlin UniFFI bindings in {kt_root.relative_to(ctx.repo_root)}")


def _stage_swift(ctx: ToolContext, cdylib: Path) -> None:
    swift_root = ctx.repo_root / _PACKAGES_DIR / _SWIFT_DIR
    with tempfile.TemporaryDirectory(prefix="polylib-swift-gen-") as tmp_str:
        tmp_dir = Path(tmp_str)
        _run_bindgen(ctx, cdylib, TARGET_SWIFT, tmp_dir)
        ffi_dir = swift_root / _SOURCES_DIR / _SWIFT_FFI_MOD
        inc_dir = swift_root / _SOURCES_DIR / _SWIFT_INTERNAL_MOD / _INCLUDE_DIR
        native_dir = swift_root / ".native"
        for directory in (ffi_dir, inc_dir, native_dir):
            directory.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp_dir / _SWIFT_FFI_FILE, ffi_dir / _SWIFT_FFI_FILE)
        shutil.copy2(tmp_dir / _SWIFT_HEADER_FILE, inc_dir / _SWIFT_HEADER_FILE)
        (inc_dir / "module.modulemap").write_text(_SWIFT_MODULEMAP, encoding=_UTF8)
        shutil.copy2(cdylib, native_dir / cdylib.name)
    print(f"Staged Swift UniFFI bindings in {swift_root.relative_to(ctx.repo_root)}")


def _stage_ruby(ctx: ToolContext, cdylib: Path) -> None:
    rb_root = ctx.repo_root / _PACKAGES_DIR / _RB_DIR
    gen_dir = rb_root / "lib" / "polylib" / _GENERATED_DIR
    native_dir = rb_root / "lib" / "polylib" / "native"
    gen_dir.mkdir(parents=True, exist_ok=True)
    native_dir.mkdir(parents=True, exist_ok=True)
    _run_bindgen(ctx, cdylib, TARGET_RUBY, gen_dir)
    rb_file = gen_dir / f"{_LIB_STEM}.rb"
    text = rb_file.read_text(encoding=_UTF8)
    if _RUBY_FFI_LIB_LINE not in text:
        raise ToolError(f"Expected `{_RUBY_FFI_LIB_LINE}` in generated {rb_file}.")
    rb_file.write_text(text.replace(_RUBY_FFI_LIB_LINE, _RUBY_LOADER_LINE, 1), encoding=_UTF8)
    shutil.copy2(cdylib, native_dir / cdylib.name)
    print(f"Staged Ruby UniFFI bindings in {rb_root.relative_to(ctx.repo_root)}")


def build_ffi_targets(ctx: ToolContext, target: str = TARGET_ALL) -> None:
    """Compile `polylib-ffi` cdylib and generate requested UniFFI bindings."""
    targets = resolve_ffi_targets(target)
    cdylib = build_cdylib(ctx)
    stagers = {
        TARGET_KOTLIN: _stage_kotlin,
        TARGET_SWIFT: _stage_swift,
        TARGET_RUBY: _stage_ruby,
    }
    for lang in targets:
        stagers[lang](ctx, cdylib)


def test_kotlin(ctx: ToolContext) -> None:
    """Run Kotlin JUnit 5 and Cucumber-JVM shared conformance tests via Gradle."""
    _require_tool(_GRADLE_BIN, "kt")
    kt_root = ctx.repo_root / _PACKAGES_DIR / _KT_DIR
    ctx.run([_GRADLE_BIN, _TEST_CMD, "--no-daemon", "--rerun-tasks"], cwd=kt_root)


def _ensure_ruby_bundle(ctx: ToolContext, rb_root: Path) -> dict[str, str]:
    env = dict(os.environ)
    vendor_path = rb_root / "vendor" / _BUNDLE_BIN
    env["BUNDLE_PATH"] = str(vendor_path)
    ctx.run([_BUNDLE_BIN, "install", "--quiet"], cwd=rb_root, env=env)
    return env


def test_ruby(ctx: ToolContext) -> None:
    """Run Ruby Minitest unit tests and Cucumber shared conformance tests."""
    _require_tool(_BUNDLE_BIN, "rb")
    rb_root = ctx.repo_root / _PACKAGES_DIR / _RB_DIR
    env = _ensure_ruby_bundle(ctx, rb_root)
    ctx.run([_BUNDLE_BIN, "exec", "rake", _TEST_CMD], cwd=rb_root, env=env)


def _verify_swift_artifacts(swift_root: Path) -> None:
    sources = swift_root / _SOURCES_DIR
    required = (
        swift_root / "Package.swift",
        sources / "Polylib" / "Polylib.swift",
        sources / _SWIFT_FFI_MOD / _SWIFT_FFI_FILE,
        sources / _SWIFT_INTERNAL_MOD / _INCLUDE_DIR / _SWIFT_HEADER_FILE,
        sources / _SWIFT_INTERNAL_MOD / _INCLUDE_DIR / "module.modulemap",
        swift_root / ".native" / cdylib_filename(),
    )
    missing = [str(p.relative_to(swift_root)) for p in required if not p.is_file()]
    if missing:
        raise ToolError(f"Missing generated Swift UniFFI files: {_COMMA_SEP.join(missing)}")


def test_swift(ctx: ToolContext, *, require_toolchain: bool = False) -> None:
    """Verify generated SwiftPM artifacts and execute `swift test` when Swift is installed."""
    swift_root = ctx.repo_root / _PACKAGES_DIR / _SWIFT_DIR
    _verify_swift_artifacts(swift_root)
    if shutil.which(TARGET_SWIFT) is None:
        if require_toolchain:
            raise ToolError("`swift` toolchain not found on PATH.")
        print(
            "Swift artifacts verified (install Swift toolchain or run macOS CI for `swift test`)."
        )
        return
    ctx.run([TARGET_SWIFT, _TEST_CMD], cwd=swift_root)
