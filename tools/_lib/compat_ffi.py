"""Pure-stdlib UniFFI compatibility checks for Kotlin/JVM, Ruby, and Swift (Tasknest & tox)."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Literal

import tomllib

from tools._lib.ffi_platform import (
    cdylib_filename,
    isolated_ruby_env,
    jna_platform_dir,
    require_tool,
)
from tools._lib.status import (
    CheckResult,
    passed,
    publish_ready,
    render,
    skipped,
)
from tools._lib.stdlib_proc import run_checked
from tools._lib.toolchain import missing_toolchain

# The Literal is what tasknest reads to build `choices` for `--help`, the CLI,
# and the generated skill; the tuple is what internal code iterates. Both are
# declared here so the member names have one home.
FfiTarget = Literal["all", "kotlin", "swift", "ruby"]
TARGET_ALL: FfiTarget = "all"
TARGET_KOTLIN: FfiTarget = "kotlin"
TARGET_SWIFT: FfiTarget = "swift"
TARGET_RUBY: FfiTarget = "ruby"
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
    "raise 'version' unless Polylib.ffi_version == Polylib::VERSION; "
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
_C_ABI_SMOKE_TEMPLATE = """\
#include <stdio.h>
#include "PolylibFFIInternal.h"

int main(void) {
    uint32_t v = ffi_polylib_ffi_uniffi_contract_version();
    if (v != __CONTRACT_VERSION__) {
        fprintf(stderr, "Unexpected UniFFI contract version: %u\\n", v);
        return 1;
    }
    printf("Swift C-ABI smoke OK (UniFFI contract version %u)\\n", v);
    return 0;
}
"""


def _verify_kotlin_standalone_jar(jar_path: Path, kt_root: Path) -> CheckResult:
    """Run the standalone-JVM consumer smoke, or say why it could not run."""
    name = "kotlin-standalone-jvm"
    cp_file = kt_root / _BUILD_CMD / "runtime-classpath.txt"
    if not cp_file.is_file():
        return skipped(
            name,
            f"{cp_file.relative_to(kt_root)} is missing; the gradle `writeRuntimeClasspath` "
            "task did not run, so the standalone JVM consumer cannot be exercised.",
        )
    if absence := missing_toolchain(
        name,
        ("javac", "java"),
        hint=(
            "run via `pixi run -e kt ...` or install a JDK to exercise the standalone JVM consumer"
        ),
    ):
        return absence.as_result()
    runtime_cp = cp_file.read_text(encoding=_UTF8).strip()
    classpath = os.pathsep.join(part for part in (str(jar_path), runtime_cp) if part)
    with tempfile.TemporaryDirectory(prefix="polylib-kt-smoke-") as tmp_str:
        tmp_dir = Path(tmp_str)
        java_file = tmp_dir / "SmokeTest.java"
        java_file.write_text(_JAVA_SMOKE_SRC, encoding=_UTF8)
        run_checked(["javac", "-cp", classpath, str(java_file)], tmp_dir)
        run_cp = os.pathsep.join((str(tmp_dir), classpath))
        run_checked(["java", "-cp", run_cp, "SmokeTest"], tmp_dir)
    return passed(name, evidence="javac compiled and java ran the standalone consumer")


def verify_kotlin_compat(root: Path, *, require_toolchain: bool = False) -> list[CheckResult]:
    """Build the Kotlin JAR, verify its payload, and smoke the standalone JVM consumer."""
    if absence := missing_toolchain(
        "kotlin",
        _GRADLE_BIN,
        hint="run via `pixi run -e kt ...` to build the JAR",
        required=require_toolchain,
    ):
        return [absence.as_result()]
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
    expected_native = f"{jna_platform_dir()}/{cdylib_filename()}"
    with zipfile.ZipFile(jars[0]) as archive:
        names = set(archive.namelist())
    required = ("META-INF/MANIFEST.MF", "dev/polylib/Polylib.class", expected_native)
    missing = [item for item in required if item not in names]
    if missing:
        raise RuntimeError(f"Built Kotlin JAR missing expected entries: {_COMMA_SEP.join(missing)}")
    results = [
        passed("kotlin-jar", evidence=f"{jars[0].name} carries {expected_native}"),
        _verify_kotlin_standalone_jar(jars[0], kt_root),
    ]
    return results


def _ruby_bundle_env(rb_root: Path) -> dict[str, str]:
    require_tool(_BUNDLE_BIN, "rb")
    env = dict(os.environ)
    env["BUNDLE_PATH"] = str(rb_root / "vendor" / _BUNDLE_BIN)
    run_checked([_BUNDLE_BIN, "install", "--quiet"], rb_root, env=env)
    return env


def verify_ruby_compat(root: Path, *, require_toolchain: bool = False) -> list[CheckResult]:
    """Build the `.gem`, install it isolated, and smoke the packaged native library."""
    if absence := missing_toolchain(
        "ruby",
        _GEM_BIN,
        hint="run via `pixi run -e rb ...` to build the gem",
        required=require_toolchain,
    ):
        return [absence.as_result()]
    rb_root = root / _PACKAGES_DIR / "polylib-rb"
    env = _ruby_bundle_env(rb_root)
    with tempfile.TemporaryDirectory(prefix="polylib-rb-compat-") as tmp_str:
        tmp_dir = Path(tmp_str)
        gem_home = tmp_dir / "gems"
        gem_out = tmp_dir / "polylib.gem"
        run_checked(
            [_GEM_BIN, _BUILD_CMD, "polylib.gemspec", "--output", str(gem_out)], rb_root, env=env
        )
        iso_env = isolated_ruby_env(gem_home, rb_root)
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
    return [
        passed(
            "ruby-gem",
            evidence=f"{gem_out.name} installed into an isolated GEM_HOME and passed the "
            "version-parity smoke test",
        )
    ]


def _uniffi_contract_version(root: Path) -> int:
    """Derive the UniFFI contract version from the pinned dependency.

    UniFFI's contract version tracks the minor of its own release, so a
    hardcoded `29` breaks the C-ABI smoke on upgrade with an error pointing at
    a magic number instead of at the dependency that moved. Read it from the
    workspace manifest, falling back to `Cargo.lock` when the manifest carries
    only a caret range that resolves to a different minor.
    """
    manifest = root / "Cargo.toml"
    data = tomllib.loads(manifest.read_text(encoding=_UTF8))
    declared = data.get("workspace", {}).get("dependencies", {}).get("uniffi")
    lock = root / "Cargo.lock"
    if lock.is_file():
        locked = tomllib.loads(lock.read_text(encoding=_UTF8))
        for package in locked.get("package", ()):
            if package.get("name") == "uniffi":
                return _minor_of(str(package.get("version", "")))
    if isinstance(declared, str):
        return _minor_of(declared.lstrip("^~= "))
    raise RuntimeError(
        f"Could not derive the UniFFI contract version from {manifest} or {lock}; "
        "the C-ABI smoke test needs one to compare against."
    )


def _minor_of(version: str) -> int:
    """Return the minor component of a semver string."""
    parts = version.split(".")
    if len(parts) < 2 or not parts[1].isdigit():
        raise RuntimeError(f"Cannot read a minor version from {version!r}.")
    return int(parts[1])


def _c_abi_smoke_source(root: Path) -> str:
    """Render the C-ABI smoke with the derived contract version."""
    return _C_ABI_SMOKE_TEMPLATE.replace(
        "__CONTRACT_VERSION__", str(_uniffi_contract_version(root))
    )


def _swift_artifacts(swift_root: Path) -> CheckResult:
    """Check the generated Swift UniFFI files exist before anything runs."""
    inc_dir = swift_root / _SWIFT_SOURCES / _SWIFT_INTERNAL / _SWIFT_INCLUDE
    required = (
        swift_root / "Package.swift",
        swift_root / _SWIFT_SOURCES / "PolylibFFI" / "PolylibFFI.swift",
        inc_dir / "PolylibFFIInternal.h",
        inc_dir / "module.modulemap",
        swift_root / ".native" / cdylib_filename(),
    )
    missing = [str(item.relative_to(swift_root)) for item in required if not item.is_file()]
    if missing:
        raise RuntimeError(f"Missing generated Swift UniFFI files: {_COMMA_SEP.join(missing)}")
    return passed("swift-artifacts", evidence=f"{len(required)} generated files present")


def _verify_swift_c_abi_smoke(swift_root: Path) -> CheckResult:
    """Link and run the C-ABI smoke binary, or say which compiler is missing."""
    name = "swift-c-abi"
    # This lane needs any one of the three, so `missing_toolchain` (which wants all
    # of them present) is the wrong fit; the reason still names the binary to add.
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        return skipped(
            name,
            "no C compiler on PATH (looked for cc, gcc, clang), so the C-ABI headers "
            "and UniFFI contract version were not verified; install one or run on macOS CI.",
        )
    inc_dir = swift_root / _SWIFT_SOURCES / _SWIFT_INTERNAL / _SWIFT_INCLUDE
    lib_dir = swift_root / ".native"
    with tempfile.TemporaryDirectory(prefix="polylib-swift-cabi-") as tmp_str:
        tmp_dir = Path(tmp_str)
        src = tmp_dir / "smoke.c"
        exe = tmp_dir / "smoke"
        src.write_text(_c_abi_smoke_source(swift_root.parent.parent), encoding=_UTF8)
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
    return passed(name, evidence=f"compiled with {compiler} and ran the contract-version smoke")


def verify_swift_compat(root: Path, *, require_toolchain: bool = False) -> list[CheckResult]:
    """Verify SwiftPM artifacts, the C-ABI link smoke, and `swift test` where Swift exists."""
    swift_root = root / _PACKAGES_DIR / "polylib-swift"
    results = [_swift_artifacts(swift_root)]
    if absence := missing_toolchain(
        "swift-test",
        TARGET_SWIFT,
        hint="install the Swift toolchain or run on macOS CI",
        required=require_toolchain,
    ):
        results.append(absence.as_result())
        results.append(_verify_swift_c_abi_smoke(swift_root))
        return results
    run_checked([TARGET_SWIFT, _BUILD_CMD], swift_root)
    run_checked([TARGET_SWIFT, "test"], swift_root)
    results.append(passed("swift-test", evidence="swift build and swift test passed"))
    results.append(_verify_swift_c_abi_smoke(swift_root))
    return results


def verify_ffi_compat(
    root: Path, target: FfiTarget = TARGET_ALL, *, require_toolchain: bool = False
) -> list[CheckResult]:
    """Run UniFFI compatibility verification for one or all FFI targets."""
    if target not in VALID_TARGETS:
        expected = _COMMA_SEP.join(VALID_TARGETS)
        raise ValueError(f"Unsupported FFI target {target!r}; expected one of: {expected}.")
    results: list[CheckResult] = []
    if target in (TARGET_ALL, TARGET_KOTLIN):
        results.extend(verify_kotlin_compat(root, require_toolchain=require_toolchain))
    if target in (TARGET_ALL, TARGET_SWIFT):
        results.extend(verify_swift_compat(root, require_toolchain=require_toolchain))
    if target in (TARGET_ALL, TARGET_RUBY):
        results.extend(verify_ruby_compat(root, require_toolchain=require_toolchain))
    return results


def _main() -> int:
    parser = argparse.ArgumentParser(description="Verify UniFFI Kotlin, Ruby, and Swift compat.")
    parser.add_argument("--target", choices=VALID_TARGETS, default=TARGET_ALL)
    parser.add_argument(
        "--require-toolchain",
        action="store_true",
        help="Treat a missing toolchain as a failure rather than a skip.",
    )
    args = parser.parse_args()
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[2]
    results = verify_ffi_compat(
        repo_root, target=args.target, require_toolchain=args.require_toolchain
    )
    print(render(results))
    return 0 if publish_ready(results) else 1


if __name__ == "__main__":
    raise SystemExit(_main())
