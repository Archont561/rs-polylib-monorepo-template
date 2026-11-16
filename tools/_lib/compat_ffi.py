"""Pure-stdlib UniFFI compatibility checks for Kotlin/JVM, Ruby, and Swift (Tasknest & tox)."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from tools._lib.stdlib_proc import run_checked

TARGET_ALL = "all"
TARGET_KOTLIN = "kotlin"
TARGET_SWIFT = "swift"
TARGET_RUBY = "ruby"
VALID_TARGETS: tuple[str, ...] = (TARGET_ALL, TARGET_KOTLIN, TARGET_SWIFT, TARGET_RUBY)

_UTF8 = "utf-8"
_PACKAGES_DIR = "packages"
_BUILD_CMD = "build"
_GRADLE_BIN = "gradle"
_GEM_BIN = "gem"
_BUNDLE_BIN = "bundle"
_COMMA_SEP = ", "
_FFI_LIB_STEM = "polylib_ffi"
_SWIFT_SOURCES = "Sources"
_SWIFT_INTERNAL = "PolylibFFIInternal"
_SWIFT_INCLUDE = "include"
_SMOKE_RUBY = (
    "require 'polylib'; "
    "raise 'slug' unless Polylib.normalize_slug('Ruby Gem OK!') == 'ruby-gem-ok'; "
    "s = Polylib.summarize_scores([10.0, 20.0]); "
    "raise 'scores' unless s.count == 2 && s.mean == 15.0"
)
_JAVA_SMOKE_SRC = """\
import dev.polylib.Polylib;
import dev.polylib.ScoreSummary;
import java.util.List;

public class SmokeTest {
    public static void main(String[] args) {
        if (!Polylib.VERSION.equals(Polylib.INSTANCE.ffiVersion())) {
            throw new AssertionError("Version mismatch");
        }
        String slug = Polylib.INSTANCE.normalizeSlug("Hello Standalone JAR!");
        if (!"hello-standalone-jar".equals(slug)) {
            throw new AssertionError("Unexpected slug: " + slug);
        }
        ScoreSummary summary = Polylib.INSTANCE.summarizeScores(List.of(10.0, 20.0, 30.0));
        if (summary.getCount() != 3L || summary.getMean() != 20.0) {
            throw new AssertionError("Unexpected summary: " + summary);
        }
    }
}
"""
_C_ABI_SMOKE_SRC = """\
#include <stdio.h>
#include "PolylibFFIInternal.h"

int main(void) {
    uint32_t v = ffi_polylib_ffi_uniffi_contract_version();
    if (v != 29) {
        fprintf(stderr, "Unexpected UniFFI contract version: %u\\n", v);
        return 1;
    }
    printf("Swift C-ABI smoke OK (UniFFI contract version %u)\\n", v);
    return 0;
}
"""


def _cdylib_filename() -> str:
    if sys.platform == "darwin":
        return f"lib{_FFI_LIB_STEM}.dylib"
    if sys.platform == "win32":
        return f"{_FFI_LIB_STEM}.dll"
    return f"lib{_FFI_LIB_STEM}.so"


def _jna_platform_dir() -> str:
    machine = platform.machine().lower()
    arch = "aarch64" if machine in {"arm64", "aarch64"} else "x86-64"
    if sys.platform == "darwin":
        return f"darwin-{arch}"
    if sys.platform == "win32":
        return f"win32-{arch}"
    return f"linux-{arch}"


def _require_tool(binary: str, pixi_env: str) -> None:
    if shutil.which(binary) is None:
        raise RuntimeError(
            f"Required tool `{binary}` not found on PATH. Run via `pixi run -e {pixi_env} ...`."
        )


def _verify_kotlin_standalone_jar(jar_path: Path, kt_root: Path) -> None:
    cp_file = kt_root / _BUILD_CMD / "runtime-classpath.txt"
    if not cp_file.is_file() or shutil.which("javac") is None or shutil.which("java") is None:
        return
    runtime_cp = cp_file.read_text(encoding=_UTF8).strip()
    classpath = os.pathsep.join(part for part in (str(jar_path), runtime_cp) if part)
    with tempfile.TemporaryDirectory(prefix="polylib-kt-smoke-") as tmp_str:
        tmp_dir = Path(tmp_str)
        java_file = tmp_dir / "SmokeTest.java"
        java_file.write_text(_JAVA_SMOKE_SRC, encoding=_UTF8)
        run_checked(["javac", "-cp", classpath, str(java_file)], tmp_dir)
        run_cp = os.pathsep.join((str(tmp_dir), classpath))
        run_checked(["java", "-cp", run_cp, "SmokeTest"], tmp_dir)


def verify_kotlin_compat(root: Path) -> None:
    """Build Kotlin JAR/POM, verify bundled native lib, and run standalone JVM consumer smoke."""
    _require_tool(_GRADLE_BIN, "kt")
    kt_root = root / _PACKAGES_DIR / "polylib-kt"
    run_checked(
        [
            _GRADLE_BIN,
            "clean",
            "check",
            "jar",
            "generatePomFileForMavenPublication",
            "writeRuntimeClasspath",
            "--no-daemon",
        ],
        kt_root,
    )
    jars = sorted((kt_root / _BUILD_CMD / "libs").glob("polylib-*.jar"))
    if not jars:
        raise RuntimeError("Expected built Kotlin JAR under packages/polylib-kt/build/libs/.")
    expected_native = f"{_jna_platform_dir()}/{_cdylib_filename()}"
    with zipfile.ZipFile(jars[0]) as archive:
        names = set(archive.namelist())
    required = ("META-INF/MANIFEST.MF", "dev/polylib/Polylib.class", expected_native)
    missing = [item for item in required if item not in names]
    if missing:
        raise RuntimeError(f"Built Kotlin JAR missing expected entries: {_COMMA_SEP.join(missing)}")
    _verify_kotlin_standalone_jar(jars[0], kt_root)
    print(f"Kotlin JAR compatibility OK: {jars[0].name} ({len(names)} entries + standalone JVM)")


def _ruby_bundle_env(rb_root: Path) -> dict[str, str]:
    _require_tool(_BUNDLE_BIN, "rb")
    env = dict(os.environ)
    env["BUNDLE_PATH"] = str(rb_root / "vendor" / _BUNDLE_BIN)
    run_checked([_BUNDLE_BIN, "install", "--quiet"], rb_root, env=env)
    return env


def _isolated_ruby_env(gem_home: Path, rb_root: Path) -> dict[str, str]:
    iso_env = dict(os.environ)
    iso_env["GEM_HOME"] = str(gem_home)
    paths = [str(gem_home)]
    vendor_ruby = rb_root / "vendor" / _BUNDLE_BIN / TARGET_RUBY
    if vendor_ruby.is_dir():
        # Bundler installs into `<BUNDLE_PATH>/ruby/<abi>/`, and that directory
        # is a gem home: it holds `gems/` and `specifications/`. Each entry of
        # GEM_PATH must be such a directory, not one of its children.
        paths.extend(str(p) for p in sorted(vendor_ruby.iterdir()) if p.is_dir())
    iso_env["GEM_PATH"] = os.pathsep.join(paths)
    return iso_env


def verify_ruby_compat(root: Path) -> None:
    """Build Ruby `.gem`, install into isolated `GEM_HOME`, and run native FFI smoke test."""
    _require_tool(_GEM_BIN, "rb")
    rb_root = root / _PACKAGES_DIR / "polylib-rb"
    env = _ruby_bundle_env(rb_root)
    with tempfile.TemporaryDirectory(prefix="polylib-rb-compat-") as tmp_str:
        tmp_dir = Path(tmp_str)
        gem_home = tmp_dir / "gems"
        gem_out = tmp_dir / "polylib.gem"
        run_checked(
            [_GEM_BIN, _BUILD_CMD, "polylib.gemspec", "--output", str(gem_out)], rb_root, env=env
        )
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
        run_checked(install_cmd, tmp_dir, env=iso_env)
        run_checked([TARGET_RUBY, "-e", _SMOKE_RUBY], tmp_dir, env=iso_env)
    print("Ruby gem compatibility OK: isolated GEM_HOME install + native FFI smoke test passed.")


def _verify_swift_c_abi_smoke(swift_root: Path) -> None:
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        return
    inc_dir = swift_root / _SWIFT_SOURCES / _SWIFT_INTERNAL / _SWIFT_INCLUDE
    lib_dir = swift_root / ".native"
    with tempfile.TemporaryDirectory(prefix="polylib-swift-cabi-") as tmp_str:
        tmp_dir = Path(tmp_str)
        src = tmp_dir / "smoke.c"
        exe = tmp_dir / "smoke"
        src.write_text(_C_ABI_SMOKE_SRC, encoding=_UTF8)
        cmd = [
            compiler,
            "-D_Nullable=",
            "-D_Nonnull=",
            f"-I{inc_dir}",
            str(src),
            f"-L{lib_dir}",
            f"-Wl,-rpath,{lib_dir}",
            f"-l{_FFI_LIB_STEM}",
            "-o",
            str(exe),
        ]
        run_checked(cmd, tmp_dir)
        run_checked([str(exe)], tmp_dir)


def verify_swift_compat(root: Path) -> None:
    """Verify SwiftPM artifacts, C-ABI link smoke, and `swift test` when Swift is installed."""
    swift_root = root / _PACKAGES_DIR / "polylib-swift"
    inc_dir = swift_root / _SWIFT_SOURCES / _SWIFT_INTERNAL / _SWIFT_INCLUDE
    required = (
        swift_root / "Package.swift",
        swift_root / _SWIFT_SOURCES / "PolylibFFI" / "PolylibFFI.swift",
        inc_dir / "PolylibFFIInternal.h",
        inc_dir / "module.modulemap",
        swift_root / ".native" / _cdylib_filename(),
    )
    missing = [str(p.relative_to(swift_root)) for p in required if not p.is_file()]
    if missing:
        raise RuntimeError(f"Missing generated Swift UniFFI files: {_COMMA_SEP.join(missing)}")
    if shutil.which(TARGET_SWIFT) is None:
        _verify_swift_c_abi_smoke(swift_root)
        print("SwiftPM artifact + C-ABI compatibility OK (run on Swift CI for `swift test`).")
        return
    run_checked([TARGET_SWIFT, _BUILD_CMD], swift_root)
    run_checked([TARGET_SWIFT, "test"], swift_root)
    print("SwiftPM compatibility OK: build and conformance tests passed.")


def verify_ffi_compat(root: Path, target: str = TARGET_ALL) -> None:
    """Run UniFFI compatibility verification for one or all FFI targets."""
    if target not in VALID_TARGETS:
        expected = _COMMA_SEP.join(VALID_TARGETS)
        raise ValueError(f"Unsupported FFI target {target!r}; expected one of: {expected}.")
    if target in (TARGET_ALL, TARGET_KOTLIN):
        verify_kotlin_compat(root)
    if target in (TARGET_ALL, TARGET_SWIFT):
        verify_swift_compat(root)
    if target in (TARGET_ALL, TARGET_RUBY):
        verify_ruby_compat(root)


def _main() -> int:
    parser = argparse.ArgumentParser(description="Verify UniFFI Kotlin, Ruby, and Swift compat.")
    parser.add_argument("--target", choices=VALID_TARGETS, default=TARGET_ALL)
    args = parser.parse_args()
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[2]
    verify_ffi_compat(repo_root, target=args.target)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
