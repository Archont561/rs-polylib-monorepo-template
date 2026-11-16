"""Shared helpers for building, testing, and packaging UniFFI bindings."""

from __future__ import annotations

import os
import platform
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from tasknest import ToolError

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
_SMOKE_RUBY = (
    'require "polylib"; '
    'raise "version" unless Polylib.ffi_version == Polylib::VERSION; '
    'raise "slug" unless Polylib.normalize_slug("Hello, Ruby Gem!") == "hello-ruby-gem"; '
    "s = Polylib.summarize_scores([10.0, 20.0, 30.0]); "
    'raise "summary" unless s.count == 3 && s.mean == 20.0'
)


def resolve_ffi_targets(target: str) -> tuple[str, ...]:
    """Validate and expand an FFI target selector into concrete languages."""
    if target not in VALID_FFI_TARGETS:
        choices = _COMMA_SEP.join(VALID_FFI_TARGETS)
        raise ToolError(f"Unsupported FFI target {target!r}; expected one of: {choices}.")
    if target == TARGET_ALL:
        return (TARGET_KOTLIN, TARGET_SWIFT, TARGET_RUBY)
    return (target,)


def cdylib_filename() -> str:
    """Return the host platform shared-library filename for `polylib-ffi`."""
    system = platform.system().lower()
    if system == "darwin":
        return f"lib{_LIB_STEM}.dylib"
    if system == "windows":
        return f"{_LIB_STEM}.dll"
    return f"lib{_LIB_STEM}.so"


def jna_platform_dir() -> str:
    """Return the JNA classpath resource subdirectory for the current host OS/arch."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = "aarch64" if machine in ("arm64", "aarch64") else "x86-64"
    if system == "darwin":
        return f"darwin-{arch}"
    if system == "windows":
        return f"win32-{arch}"
    return f"linux-{arch}"


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


def _require_tool(binary: str, pixi_env: str) -> None:
    if shutil.which(binary) is None:
        raise ToolError(
            f"Required `{binary}` tool not found on PATH; run via `pixi run -e {pixi_env} ...`."
        )


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


def compat_kotlin(ctx: ToolContext) -> None:
    """Build Kotlin JAR and verify manifest, classes, and bundled JNA shared library."""
    _require_tool(_GRADLE_BIN, "kt")
    kt_root = ctx.repo_root / _PACKAGES_DIR / _KT_DIR
    ctx.run([_GRADLE_BIN, "clean", "check", "jar", "--no-daemon"], cwd=kt_root)
    jars = sorted((kt_root / _BUILD_CMD / "libs").glob("polylib-*.jar"))
    if not jars:
        raise ToolError("Expected built Kotlin JAR under packages/polylib-kt/build/libs/.")
    expected_native = f"{jna_platform_dir()}/{cdylib_filename()}"
    with zipfile.ZipFile(jars[0]) as archive:
        names = set(archive.namelist())
    required = ("META-INF/MANIFEST.MF", "dev/polylib/Polylib.class", expected_native)
    missing = [item for item in required if item not in names]
    if missing:
        raise ToolError(f"Built Kotlin JAR missing expected entries: {_COMMA_SEP.join(missing)}")
    print(f"Kotlin JAR compatibility OK: {jars[0].name} ({len(names)} entries)")


def _isolated_ruby_env(gem_home: Path, rb_root: Path) -> dict[str, str]:
    iso_env = dict(os.environ)
    iso_env["GEM_HOME"] = str(gem_home)
    paths = [str(gem_home)]
    vendor_ruby = rb_root / "vendor" / _BUNDLE_BIN / TARGET_RUBY
    if vendor_ruby.is_dir():
        paths.extend(str(p) for p in sorted(vendor_ruby.iterdir()) if p.is_dir())
    iso_env["GEM_PATH"] = os.pathsep.join(paths)
    return iso_env


def compat_ruby(ctx: ToolContext) -> None:
    """Build Ruby `.gem`, install into an isolated `GEM_HOME`, and run a smoke test."""
    _require_tool(_GEM_BIN, "rb")
    rb_root = ctx.repo_root / _PACKAGES_DIR / _RB_DIR
    env = _ensure_ruby_bundle(ctx, rb_root)
    with tempfile.TemporaryDirectory(prefix="polylib-rb-compat-") as tmp_str:
        tmp_dir = Path(tmp_str)
        gem_home = tmp_dir / "gems"
        gem_out = tmp_dir / "polylib.gem"
        build_cmd = [_GEM_BIN, _BUILD_CMD, "polylib.gemspec", "--output", str(gem_out)]
        ctx.run(build_cmd, cwd=rb_root, env=env)
        iso_env = _isolated_ruby_env(gem_home, rb_root)
        install_cmd = [
            _GEM_BIN,
            "install",
            "--local",
            "--no-document",
            "--ignore-dependencies",
            "--install-dir",
            str(gem_home),
            str(gem_out),
        ]
        ctx.run(install_cmd, cwd=tmp_dir, env=iso_env)
        ctx.run([TARGET_RUBY, "-e", _SMOKE_RUBY], cwd=tmp_dir, env=iso_env)
    print("Ruby gem compatibility OK: isolated GEM_HOME install + native FFI smoke test passed.")


def compat_swift(ctx: ToolContext) -> None:
    """Verify SwiftPM package artifacts and run `swift build`/`swift test` when Swift is present."""
    swift_root = ctx.repo_root / _PACKAGES_DIR / _SWIFT_DIR
    _verify_swift_artifacts(swift_root)
    if shutil.which(TARGET_SWIFT) is None:
        print(
            "SwiftPM artifact compatibility OK (Swift toolchain absent on host; run on macOS CI)."
        )
        return
    ctx.run([TARGET_SWIFT, _BUILD_CMD], cwd=swift_root)
    ctx.run([TARGET_SWIFT, _TEST_CMD], cwd=swift_root)
    print("SwiftPM compatibility OK: build and conformance tests passed.")
