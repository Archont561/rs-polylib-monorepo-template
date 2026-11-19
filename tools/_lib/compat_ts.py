"""TypeScript/npm tarball compatibility verification (publint, attw, Bun, Node.js, tsc)."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tools._lib.compat_ts_node import ConsumerSetup, verify_node_consumers
from tools._lib.program import resolve_program
from tools._lib.status import (
    CheckResult,
    not_run,
    passed,
    publish_ready,
    render,
    skipped,
)
from tools._lib.tarball_ref import tarball_ref

_BUN = "bun"
_BUN_EXEC_ARGS: tuple[str, ...] = ("x", "--bun", "--no-install")
_BUN_INSTALL_OFFLINE_ARGS: tuple[str, ...] = ("install", "--offline")
_BUN_INSTALL_ARGS: tuple[str, ...] = ("install",)
_STRICT = "--strict"
_CHECK_FILE = "check.ts"
_PACKAGE_JSON = "package.json"
_UTF8 = "utf-8"
_WASM_PKG = "@polylib/polylib-wasm"
_JS_PKG = "@polylib/polylib-js"
_FACADE_PKG = "@polylib/polylib"

TsCompatMode = Literal["all", "pack", "bun", "node", "types"]

MODE_ALL: TsCompatMode = "all"
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
    # Subpaths `attw` cannot type-check. A raw `.wasm` binary is published for
    # bundlers to fetch, and has no JavaScript entry point and no declarations,
    # so resolution there is expected to fail. Listing it here keeps the check
    # strict for everything that is actually importable.
    attw_exclude: tuple[str, ...] = ()


_PACKAGES: tuple[TsPackageSpec, ...] = (
    TsPackageSpec(
        rel_dir="packages/polylib-wasm",
        tarball_glob="polylib-polylib-wasm-*.tgz",
        artifact_rel="src/wasm/polylib_wasm_bg.wasm",
        build_hint="pixi run -e full tools run bindings build --target wasm",
        pkg_name=_WASM_PKG,
        attw_exclude=("polylib_wasm_bg.wasm",),
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

if (BACKEND !== "{expected_backend}" || getEngineVersion() !== VERSION) {{
  throw new Error(`Unexpected facade engine: ${{BACKEND}} (${{VERSION}})`);
}}
if (normalizeSlug("Hello Facade!") !== "hello-facade") {{
  throw new Error("Unexpected facade slug result");
}}
if (wasmApi.BACKEND !== "wasm" || wasmApi.normalizeSlug("Hi!") !== "hi") {{
  throw new Error("Unexpected {facade}/wasm result");
}}
const summary = summarizeScores([10, 20, 30]);
if (summary.count !== 3 || summary.mean !== 20) {{
  throw new Error("Unexpected facade summary result");
}}
"""

# Without the addon the main entry must fail loudly, and `/wasm` must still work.
# This is the shape a `--omit=optional` install gets, so it is what a user on an
# unsupported platform sees.
# Applied with `.format(facade=...)`, hence the doubled braces. Used by the
# "peer installed, addon missing" fixture, so it asserts `missing_native_binding`
# at the first call and that `/wasm` still works.
_FACADE_WASM_ONLY_CHECK = """\
import {{ normalizeSlug }} from "{facade}";

// The loader resolves the addon lazily, so the failure lands on the first call
// rather than on import: a program that never touches the native API keeps
// working, and one that does gets a named error instead of a stack trace.
let caught: unknown;
try {{
  normalizeSlug("Hi!");
}} catch (err) {{
  caught = err;
}}
if (caught === undefined) {{
  throw new Error("The main entry ran without a native binding.");
}}
const code = (caught as {{ code?: string }}).code;
if (code !== "missing_native_binding") {{
  throw new Error(`Expected missing_native_binding, got ${{code}}`);
}}
const wasm = await import("{facade}/wasm");
if (wasm.BACKEND !== "wasm" || wasm.normalizeSlug("Only Wasm!") !== "only-wasm") {{
  throw new Error("The /wasm subpath did not work without the addon.");
}}
"""

# A browser target must resolve the main entry to the stub, never to the native
# module. Bundling this and reading the output is the only way to prove which
# file the `default` condition selected.
_FACADE_BROWSER_CHECK = """\
import * as facade from "{facade}";
export const probe = facade;
"""

_TS_CONSUMER_CHECK = """\
import {{ BACKEND, normalizeSlug, type ScoreSummary }} from "{facade}";
import {{ getWasmVersion }} from "{wasm}";

const slug: string = normalizeSlug("Typed Consumer!");
const backend: string = BACKEND;
const summary: ScoreSummary = {{ count: 1, min: 1, max: 1, mean: 1, total: 1 }};
const version: string = getWasmVersion();
export const evidence = [slug, backend, summary.count, version] as const;
"""


def _run_checked(argv: tuple[str, ...], cwd: Path) -> None:
    print("+ " + " ".join(argv), flush=True)
    proc = subprocess.run(argv, cwd=cwd, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(argv)}")


def _bun_argv(*args: str) -> tuple[str, ...]:
    """Return a Bun invocation whose program can be spawned on every platform.

    `CreateProcess` on Windows does not consult `PATHEXT`, so a bare program
    name only resolves when it is a real `.exe`. Resolving Bun first keeps the
    call working when Bun is installed through a shim.
    """
    return (resolve_program(_BUN), *args)


def _facade_consumer_source(expected_backend: str) -> str:
    """Source for a facade consumer asserting which engine the main entry chose."""
    return _FACADE_CHECK_TEMPLATE.format(
        facade=_FACADE_PKG,
        expected_backend=expected_backend,
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
    return _bun_argv(
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
        _bun_argv("install", "--help"),
        capture_output=True,
        text=True,
        check=False,
    )
    return "--offline" in (proc.stdout + proc.stderr)


def _install_argv(extra: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Build the `bun install` invocation for the installed Bun version."""
    base = _BUN_INSTALL_OFFLINE_ARGS if _bun_supports_offline() else _BUN_INSTALL_ARGS
    return _bun_argv(*base, *extra)


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
        _run_checked(_bun_argv("run", _CHECK_FILE), consumer_dir)
    if run_types:
        tsc_js = _tsc_entry(root)
        _run_checked(_tsc_argv(tsc_js, "nodenext", "nodenext"), consumer_dir)
        _run_checked(_tsc_argv(tsc_js, "esnext", "bundler"), consumer_dir)


def _pack_tarball(root: Path, spec: TsPackageSpec, tmp_path: Path, *, lint_pkg: bool) -> Path:
    pkg_dir = root / spec.rel_dir
    if not (pkg_dir / spec.artifact_rel).exists():
        raise RuntimeError(f"Missing compiled artifact in {spec.rel_dir}. Run `{spec.build_hint}`.")
    _run_checked(
        _bun_argv("pm", "pack", "--cwd", spec.rel_dir, "--destination", str(tmp_path)),
        root,
    )
    tarball = next(tmp_path.glob(spec.tarball_glob))
    if lint_pkg:
        _run_checked(_bun_argv(*_BUN_EXEC_ARGS, "publint", "run", str(tarball), _STRICT), pkg_dir)
        attw_argv = [*_BUN_EXEC_ARGS, "attw", str(tarball), "--profile", "esm-only", "--no-emoji"]
        for entrypoint in spec.attw_exclude:
            attw_argv.extend(("--exclude-entrypoints", entrypoint))
        _run_checked(_bun_argv(*attw_argv), pkg_dir)
    return tarball


@dataclass(frozen=True)
class ConsumerCase:
    """One isolated consumer fixture for the Bun/tsc checks.

    `dependencies` and `overrides` map a package name onto the packed tarball
    it must resolve to. The `file:` references are written relative to the
    consumer directory, because that is the directory npm and Bun resolve them
    from.
    """

    name: str
    dependencies: dict[str, Path]
    overrides: dict[str, Path]
    source: str
    install_argv: tuple[str, ...]
    # True when the fixture cannot work without a compiled addon. The in-tree
    # gate has none (no Rust toolchain), while the CI matrix stages one, so these
    # are skipped here and run there.
    requires_addon: bool = False


def _backend_cases(tarballs: dict[str, Path]) -> tuple[ConsumerCase, ...]:
    """Describe the single-backend Bun consumer fixtures."""
    return (
        ConsumerCase(
            "consumer-wasm",
            {_WASM_PKG: tarballs[_WASM_PKG]},
            {},
            _BACKEND_CHECK_TEMPLATE.format(pkg_name=_WASM_PKG, version_fn="getWasmVersion"),
            _install_argv(),
        ),
        ConsumerCase(
            "consumer-js",
            {_JS_PKG: tarballs[_JS_PKG]},
            {},
            _BACKEND_CHECK_TEMPLATE.format(pkg_name=_JS_PKG, version_fn="getNativeVersion"),
            _install_argv(),
            requires_addon=True,
        ),
    )


def _facade_cases(tarballs: dict[str, Path]) -> tuple[ConsumerCase, ...]:
    """Describe the facade Bun consumer fixtures."""
    return (
        # Both backends installed: the main entry must pick the addon and the
        # `/wasm` subpath must still be usable beside it.
        ConsumerCase(
            "consumer-facade-native",
            {
                _FACADE_PKG: tarballs[_FACADE_PKG],
                _WASM_PKG: tarballs[_WASM_PKG],
                _JS_PKG: tarballs[_JS_PKG],
            },
            {_WASM_PKG: tarballs[_WASM_PKG], _JS_PKG: tarballs[_JS_PKG]},
            _facade_consumer_source("native"),
            _install_argv(),
            requires_addon=True,
        ),
        # The WebAssembly peer installed but no addon: the main entry imports the
        # addon statically, so it fails with `missing_native_binding` rather than
        # switching engine. `/wasm` still works, which is the supported escape.
        # The facade depends on `@polylib/polylib-js`, so the override points it
        # at the local tarball; without it Bun tries the registry. `--omit=optional`
        # then leaves the per-platform addon out, which is the case under test.
        ConsumerCase(
            "consumer-facade-wasm-only",
            {_FACADE_PKG: tarballs[_FACADE_PKG], _WASM_PKG: tarballs[_WASM_PKG]},
            {_JS_PKG: tarballs[_JS_PKG]},
            _FACADE_WASM_ONLY_CHECK.format(facade=_FACADE_PKG),
            _install_argv(("--omit=optional",)),
        ),
        # A browser target must reach the stub, not the addon.
        ConsumerCase(
            "consumer-facade-browser",
            {
                _FACADE_PKG: tarballs[_FACADE_PKG],
                _WASM_PKG: tarballs[_WASM_PKG],
                _JS_PKG: tarballs[_JS_PKG],
            },
            {_WASM_PKG: tarballs[_WASM_PKG], _JS_PKG: tarballs[_JS_PKG]},
            _FACADE_BROWSER_CHECK.format(facade=_FACADE_PKG),
            _install_argv(),
        ),
    )


def _verify_bun_and_types(
    root: Path,
    tmp_path: Path,
    tarballs: dict[str, Path],
    *,
    run_bun: bool,
    run_types: bool,
    addon_available: bool,
) -> tuple[str, ...]:
    skipped: list[str] = []
    for case in (*_backend_cases(tarballs), *_facade_cases(tarballs)):
        if case.requires_addon and not addon_available:
            print(
                f"- {case.name}: skipped, no compiled addon for this host",
                flush=True,
            )
            skipped.append(case.name)
            continue
        consumer_dir = tmp_path / case.name
        manifest = _consumer_manifest(
            case.name,
            {pkg: tarball_ref(path, consumer_dir) for pkg, path in case.dependencies.items()},
            overrides={
                pkg: tarball_ref(path, consumer_dir) for pkg, path in case.overrides.items()
            },
        )
        _prepare_consumer(consumer_dir, manifest, case.source, case.install_argv)
        _check_consumer_runtime_and_types(root, consumer_dir, run_bun=run_bun, run_types=run_types)
    return tuple(skipped)


def _host_platform_tarballs(tmp_path: Path) -> dict[str, Path]:
    """Pack the per-platform addon package this host would install.

    `napi artifacts` drops the compiled addon into `packages/polylib-js/npm/<suffix>/`.
    A `file:` dependency cannot reach that directory through
    `optionalDependencies`, so the consumer fixture installs it by name and this
    helper hands it the matching tarball. When the addon was never built (no
    Rust toolchain) the mapping is empty and the loader's own error path is what
    the `missing-native` fixture exercises.
    """
    from tools._lib.napi_platforms import host_suffix

    npm_dir = Path("packages/polylib-js/npm")
    if not npm_dir.is_dir():
        return {}
    suffix = host_suffix()
    target_dir = npm_dir / suffix
    if not (target_dir / _PACKAGE_JSON).is_file():
        return {}
    packed = _pack_dir_tarball(target_dir, tmp_path)
    return {f"{_JS_PKG}-{suffix}": packed}


def _pack_dir_tarball(package_dir: Path, tmp_path: Path) -> Path:
    """`npm pack` one directory and return the tarball's path."""
    npm = resolve_program("npm")
    out_dir = tmp_path / "platform-tarballs"
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        (npm, "pack", str(package_dir), "--pack-destination", str(out_dir)),
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"npm pack failed for {package_dir}: {proc.stderr.strip()}")
    tarball = out_dir / proc.stdout.strip().splitlines()[-1]
    if not tarball.is_file():
        raise RuntimeError(f"npm pack reported {tarball.name} but it does not exist.")
    return tarball


def verify_ts_compat(root: Path, mode: TsCompatMode = MODE_ALL) -> list[CheckResult]:
    """Pack and verify npm tarballs (`all`, `pack`, `bun`, `node`, or `types`)."""
    if mode not in VALID_MODES:
        expected = ", ".join(VALID_MODES)
        raise ValueError(f"Unsupported ts compat mode {mode!r}; expected one of: {expected}.")
    lint_pkg = mode in (MODE_ALL, MODE_PACK)
    results: list[CheckResult] = []
    with tempfile.TemporaryDirectory(prefix="polylib-ts-compat-") as tmp:
        tmp_path = Path(tmp)
        tarballs = {
            spec.pkg_name: _pack_tarball(root, spec, tmp_path, lint_pkg=lint_pkg)
            for spec in _PACKAGES
        }
        results.append(
            passed(
                "ts-tarballs",
                evidence=f"packed {len(tarballs)} tarballs for "
                "@polylib/polylib-wasm, @polylib/polylib-js, and @polylib/polylib",
            )
        )
        platform_packages = _host_platform_tarballs(tmp_path)
        if mode in (MODE_ALL, MODE_BUN, MODE_TYPES):
            addon_skipped = _verify_bun_and_types(
                root,
                tmp_path,
                tarballs,
                run_bun=mode in (MODE_ALL, MODE_BUN),
                run_types=mode in (MODE_ALL, MODE_TYPES),
                addon_available=bool(platform_packages),
            )
            ran = len(_backend_cases(tarballs)) + len(_facade_cases(tarballs)) - len(addon_skipped)
            results.append(
                skipped(
                    "ts-bun-consumers",
                    "no compiled addon for this host, so "
                    f"{', '.join(addon_skipped)} could not run; the other {ran} fixtures "
                    "passed. Build one with "
                    "`pixi run -e full tools run bindings build --target napi`.",
                )
                if addon_skipped
                else passed(
                    "ts-bun-consumers",
                    evidence=f"{ran} fixture(s) installed with Bun and type-checked with tsc",
                )
            )
        if mode in (MODE_ALL, MODE_NODE):
            results.append(
                verify_node_consumers(
                    tmp_path,
                    ConsumerSetup(
                        tarballs=tarballs,
                        platform_packages=platform_packages,
                    ),
                    require_node=(mode == MODE_NODE),
                )
            )
        else:
            results.append(
                not_run(
                    "ts-node-consumers",
                    f"mode {mode!r} does not include Node.js consumers; "
                    "re-run with `--mode all` or `--mode node` to exercise them.",
                )
            )
    return results


def _main() -> int:
    parser = argparse.ArgumentParser(description="Verify npm/TypeScript tarball compatibility.")
    parser.add_argument("--mode", choices=VALID_MODES, default=MODE_ALL)
    args = parser.parse_args()
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[2]
    results = verify_ts_compat(repo_root, mode=args.mode)
    print(render(results))
    return 0 if publish_ready(results) else 1


if __name__ == "__main__":
    raise SystemExit(_main())
