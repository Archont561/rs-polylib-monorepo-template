"""TypeScript/npm tarball compatibility verification (publint, attw, Bun, Node.js, tsc)."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from tools._lib.compat_ts_node import verify_node_consumers

_BUN = "bun"
_BUN_EXEC: tuple[str, ...] = (_BUN, "x", "--bun", "--no-install")
_BUN_INSTALL_OFFLINE: tuple[str, ...] = (_BUN, "install", "--offline")
_BUN_INSTALL: tuple[str, ...] = (_BUN, "install")
_STRICT = "--strict"
_CHECK_FILE = "check.ts"
_PACKAGE_JSON = "package.json"
_UTF8 = "utf-8"
_WASM_PKG = "@polylib/polylib-wasm"
_JS_PKG = "@polylib/polylib-js"
_FACADE_PKG = "@polylib/polylib"

MODE_ALL = "all"
MODE_PACK = "pack"
MODE_BUN = "bun"
MODE_NODE = "node"
MODE_TYPES = "types"
VALID_MODES: tuple[str, ...] = (MODE_ALL, MODE_PACK, MODE_BUN, MODE_NODE, MODE_TYPES)


@dataclass(frozen=True)
class TsPackageSpec:
    """Metadata describing one publishable TypeScript package."""

    rel_dir: str
    tarball_glob: str
    artifact_rel: str
    build_hint: str
    pkg_name: str


_PACKAGES: tuple[TsPackageSpec, ...] = (
    TsPackageSpec(
        rel_dir="packages/polylib-wasm",
        tarball_glob="polylib-polylib-wasm-*.tgz",
        artifact_rel="src/wasm/polylib_wasm_bg.wasm",
        build_hint="pixi run -e full tools run bindings build --target wasm",
        pkg_name=_WASM_PKG,
    ),
    TsPackageSpec(
        rel_dir="packages/polylib-js",
        tarball_glob="polylib-polylib-js-*.tgz",
        artifact_rel="src/native/binding.cjs",
        build_hint="pixi run -e full tools run bindings build --target napi",
        pkg_name=_JS_PKG,
    ),
    TsPackageSpec(
        rel_dir="packages/polylib-ts",
        tarball_glob="polylib-polylib-[0-9]*.tgz",
        artifact_rel="dist/index.js",
        build_hint="pixi run -e full tools run bindings build --target ts",
        pkg_name=_FACADE_PKG,
    ),
)

_BACKEND_CHECK_TEMPLATE = """\
import {{ {version_fn}, normalizeSlug, summarizeScores, VERSION }} from "{pkg_name}";
if ({version_fn}() !== VERSION || normalizeSlug("Hello Tarball!") !== "hello-tarball") {{
  throw new Error(`Unexpected runtime result: ${{VERSION}}`);
}}
const summary = summarizeScores([10, 20, 30]);
if (summary.count !== 3 || summary.mean !== 20) {{
  throw new Error("Unexpected summary result");
}}
"""

_FACADE_CHECK_TEMPLATE = """\
import {{ BACKEND, getEngineVersion, normalizeSlug, summarizeScores, VERSION }} from "{facade}";
import * as wasmApi from "{facade}/wasm";
{native_import}\
if (BACKEND !== "{expected_backend}" || getEngineVersion() !== VERSION) {{
  throw new Error(`Unexpected facade backend: ${{BACKEND}} (${{VERSION}})`);
}}
if (normalizeSlug("Hello Facade!") !== "hello-facade") {{
  throw new Error("Unexpected facade slug result");
}}
if (wasmApi.BACKEND !== "wasm" || wasmApi.normalizeSlug("Hi!") !== "hi") {{
  throw new Error("Unexpected {facade}/wasm result");
}}
{native_check}\
const summary = summarizeScores([10, 20, 30]);
if (summary.count !== 3 || summary.mean !== 20) {{
  throw new Error("Unexpected facade summary result");
}}
"""

_NATIVE_SUBPATH_CHECK = (
    'if (nativeApi.BACKEND !== "native" || nativeApi.normalizeSlug("Hi!") !== "hi") {\n'
    '  throw new Error("Unexpected @polylib/polylib/native result");\n'
    "}\n"
)


def _run_checked(argv: tuple[str, ...], cwd: Path) -> None:
    print("+ " + " ".join(argv), flush=True)
    proc = subprocess.run(argv, cwd=cwd, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(argv)}")


def _facade_consumer_source(expected_backend: str, *, include_native_subpath: bool) -> str:
    native_import = (
        f'import * as nativeApi from "{_FACADE_PKG}/native";\n' if include_native_subpath else ""
    )
    native_check = _NATIVE_SUBPATH_CHECK if include_native_subpath else ""
    return _FACADE_CHECK_TEMPLATE.format(
        facade=_FACADE_PKG,
        expected_backend=expected_backend,
        native_import=native_import,
        native_check=native_check,
    )


def _consumer_manifest(
    name: str,
    dependencies: dict[str, str],
    overrides: dict[str, str] | None = None,
) -> dict[str, object]:
    manifest: dict[str, object] = {
        "name": name,
        "type": "module",
        "dependencies": dependencies,
    }
    if overrides:
        manifest["overrides"] = overrides
    return manifest


def _tsc_argv(tsc_js: Path, module: str, resolution: str) -> tuple[str, ...]:
    return (
        _BUN,
        str(tsc_js),
        "--noEmit",
        _STRICT,
        "--module",
        module,
        "--moduleResolution",
        resolution,
        _CHECK_FILE,
    )


def _tsc_entry(root: Path) -> Path:
    """Return the TypeScript compiler entry point that runs on every platform.

    `node_modules/typescript/bin/tsc` is a POSIX shell wrapper and cannot be
    executed on Windows. `lib/tsc.js` is plain JavaScript and works everywhere.
    """
    lib_entry = root / "node_modules" / "typescript" / "lib" / "tsc.js"
    if lib_entry.is_file():
        return lib_entry
    return root / "node_modules" / "typescript" / "bin" / "tsc"


def _bun_supports_offline() -> bool:
    """Report whether the installed Bun understands `bun install --offline`.

    The flag only exists from Bun 1.4.1 onwards. Every dependency in the
    consumer fixtures is a local `file:` tarball, so the older releases install
    them without touching the network anyway.
    """
    proc = subprocess.run(
        (_BUN, "install", "--help"),
        capture_output=True,
        text=True,
        check=False,
    )
    return "--offline" in (proc.stdout + proc.stderr)


def _install_argv(extra: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Build the `bun install` invocation for the installed Bun version."""
    base = _BUN_INSTALL_OFFLINE if _bun_supports_offline() else _BUN_INSTALL
    return (*base, *extra)


def _prepare_consumer(
    consumer_dir: Path,
    manifest: dict[str, object],
    source: str,
    install_argv: tuple[str, ...],
) -> None:
    consumer_dir.mkdir(parents=True, exist_ok=True)
    (consumer_dir / _PACKAGE_JSON).write_text(json.dumps(manifest, indent=2) + "\n", encoding=_UTF8)
    (consumer_dir / _CHECK_FILE).write_text(source, encoding=_UTF8)
    _run_checked(install_argv, consumer_dir)


def _check_consumer_runtime_and_types(
    root: Path,
    consumer_dir: Path,
    *,
    run_bun: bool,
    run_types: bool,
) -> None:
    if run_bun:
        _run_checked((_BUN, "run", _CHECK_FILE), consumer_dir)
    if run_types:
        tsc_js = _tsc_entry(root)
        _run_checked(_tsc_argv(tsc_js, "nodenext", "nodenext"), consumer_dir)
        _run_checked(_tsc_argv(tsc_js, "esnext", "bundler"), consumer_dir)


def _pack_tarball(root: Path, spec: TsPackageSpec, tmp_path: Path, *, lint_pkg: bool) -> Path:
    pkg_dir = root / spec.rel_dir
    if not (pkg_dir / spec.artifact_rel).exists():
        raise RuntimeError(f"Missing compiled artifact in {spec.rel_dir}. Run `{spec.build_hint}`.")
    _run_checked(
        (_BUN, "pm", "pack", "--cwd", spec.rel_dir, "--destination", str(tmp_path)),
        root,
    )
    tarball = next(tmp_path.glob(spec.tarball_glob))
    if lint_pkg:
        _run_checked((*_BUN_EXEC, "publint", "run", str(tarball), _STRICT), pkg_dir)
        _run_checked(
            (*_BUN_EXEC, "attw", str(tarball), "--profile", "esm-only", "--no-emoji"),
            pkg_dir,
        )
    return tarball


def _tarball_ref(tarball: Path) -> str:
    """Return a `file:` dependency reference for a local tarball.

    `file:` followed by a bare path is ambiguous: on Windows the path starts
    with a drive letter, so `file:C:\\dir\\pkg.tgz` is parsed as a URL with
    the host `C:` instead of a local path. `Path.as_uri()` renders a proper
    `file://` URL with forward slashes on every platform.
    """
    return tarball.as_uri()


def _backend_cases(
    tarballs: dict[str, Path],
) -> tuple[tuple[str, dict[str, object], str, tuple[str, ...]], ...]:
    wasm_ref = _tarball_ref(tarballs[_WASM_PKG])
    js_ref = _tarball_ref(tarballs[_JS_PKG])
    return (
        (
            "consumer-wasm",
            _consumer_manifest("consumer-wasm", {_WASM_PKG: wasm_ref}),
            _BACKEND_CHECK_TEMPLATE.format(pkg_name=_WASM_PKG, version_fn="getWasmVersion"),
            _install_argv(),
        ),
        (
            "consumer-js",
            _consumer_manifest("consumer-js", {_JS_PKG: js_ref}),
            _BACKEND_CHECK_TEMPLATE.format(pkg_name=_JS_PKG, version_fn="getNativeVersion"),
            _install_argv(),
        ),
    )


def _facade_cases(
    tarballs: dict[str, Path],
) -> tuple[tuple[str, dict[str, object], str, tuple[str, ...]], ...]:
    wasm_ref = _tarball_ref(tarballs[_WASM_PKG])
    js_ref = _tarball_ref(tarballs[_JS_PKG])
    facade_ref = _tarball_ref(tarballs[_FACADE_PKG])
    return (
        (
            "consumer-facade-native",
            _consumer_manifest(
                "consumer-facade-native",
                {_FACADE_PKG: facade_ref},
                overrides={_WASM_PKG: wasm_ref, _JS_PKG: js_ref},
            ),
            _facade_consumer_source("native", include_native_subpath=True),
            _install_argv(),
        ),
        (
            "consumer-facade-wasm-fallback",
            _consumer_manifest(
                "consumer-facade-wasm-fallback",
                {_FACADE_PKG: facade_ref},
                overrides={_WASM_PKG: wasm_ref},
            ),
            _facade_consumer_source("wasm", include_native_subpath=False),
            _install_argv(("--omit=optional",)),
        ),
    )


def _verify_bun_and_types(
    root: Path,
    tmp_path: Path,
    tarballs: dict[str, Path],
    *,
    run_bun: bool,
    run_types: bool,
) -> None:
    for name, manifest, source, install_argv in (
        *_backend_cases(tarballs),
        *_facade_cases(tarballs),
    ):
        consumer_dir = tmp_path / name
        _prepare_consumer(consumer_dir, manifest, source, install_argv)
        _check_consumer_runtime_and_types(root, consumer_dir, run_bun=run_bun, run_types=run_types)


def verify_ts_compat(root: Path, mode: str = MODE_ALL) -> None:
    """Pack and verify npm tarballs (`all`, `pack`, `bun`, `node`, or `types`)."""
    if mode not in VALID_MODES:
        expected = ", ".join(VALID_MODES)
        raise ValueError(f"Unsupported ts compat mode {mode!r}; expected one of: {expected}.")
    lint_pkg = mode in (MODE_ALL, MODE_PACK)
    with tempfile.TemporaryDirectory(prefix="polylib-ts-compat-") as tmp:
        tmp_path = Path(tmp)
        tarballs = {
            spec.pkg_name: _pack_tarball(root, spec, tmp_path, lint_pkg=lint_pkg)
            for spec in _PACKAGES
        }
        if mode in (MODE_ALL, MODE_BUN, MODE_TYPES):
            _verify_bun_and_types(
                root,
                tmp_path,
                tarballs,
                run_bun=mode in (MODE_ALL, MODE_BUN),
                run_types=mode in (MODE_ALL, MODE_TYPES),
            )
        if mode in (MODE_ALL, MODE_NODE):
            verify_node_consumers(tmp_path, tarballs, require_node=(mode == MODE_NODE))
    print(
        f"ts-compat ({mode}): @polylib/polylib-wasm, @polylib/polylib-js, and @polylib/polylib OK"
    )


def _main() -> int:
    parser = argparse.ArgumentParser(description="Verify npm/TypeScript tarball compatibility.")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_ALL)
    args = parser.parse_args()
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[2]
    verify_ts_compat(repo_root, mode=args.mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
