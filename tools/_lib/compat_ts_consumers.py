"""Consumer fixtures that pin how the published TypeScript packages behave.

Each case installs the packed tarballs into an isolated directory and runs a
small program against them. The cases exist because the interesting failures
happen outside the package: a browser bundler reaching a `node:` import, a
CommonJS consumer hitting top-level `await`, or npm silently skipping the
optional platform package that held the addon.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tasknest import ToolError

from tools._lib.program import resolve_program
from tools._lib.tarball_ref import tarball_ref

if TYPE_CHECKING:
    from pathlib import Path

_UTF8 = "utf-8"
_NODE = "node"
_NPM = "npm"
_ESBUILD = "esbuild"
_PACKAGE_JSON = "package.json"
_WASM_PKG = "@polylib/polylib-wasm"
_JS_PKG = "@polylib/polylib-js"
_FACADE_PKG = "@polylib/polylib"
_ESBUILD_VERSION = "0.28.2"
_MODULE_NOT_FOUND = "MODULE_NOT_FOUND"
_ERR_MODULE_NOT_FOUND = "ERR_MODULE_NOT_FOUND"


def _is_windows() -> bool:
    return sys.platform == "win32"


@dataclass(frozen=True)
class ConsumerCase:
    """One isolated consumer, and what its program proves.

    `dependencies` maps a package name onto the tarball it must resolve to.
    `install_args` carries the flags that make the case meaningful: omitting
    optional dependencies is what reproduces "the platform package is missing".
    """

    name: str
    dependencies: dict[str, Path]
    script: str
    script_name: str = "check.mjs"
    install_args: tuple[str, ...] = ()
    needs_bundler: bool = False
    requires_native: bool = False

    def manifest(self, consumer_dir: Path) -> dict[str, object]:
        """Build the consumer's `package.json` with relative tarball references."""
        manifest: dict[str, object] = {
            "name": f"polylib-{self.name}",
            "private": True,
            "type": "module",
            "dependencies": {
                pkg: tarball_ref(path, consumer_dir) for pkg, path in self.dependencies.items()
            },
        }
        if self.needs_bundler:
            manifest["devDependencies"] = {_ESBUILD: _ESBUILD_VERSION}
        return manifest


_SERVER_ONLY = """\
import { createRequire } from "node:module";
import { BACKEND, getEngineVersion, normalizeSlug, VERSION } from "@polylib/polylib";

if (BACKEND !== "native") throw new Error(`expected native, got ${BACKEND}`);
if (getEngineVersion() !== VERSION) throw new Error("facade and addon versions differ");
if (normalizeSlug("Hello Server!") !== "hello-server") throw new Error("unexpected slug");

// The WebAssembly package is an optional peer, so it must not be installed.
try {
  createRequire(import.meta.url).resolve("@polylib/polylib-wasm");
  throw new Error("@polylib/polylib-wasm was installed but must stay optional");
} catch (err) {
  if (err.code !== "MODULE_NOT_FOUND") throw err;
}
"""

_SERVER_PLUS_WASM = """\
import * as native from "@polylib/polylib";
import * as wasm from "@polylib/polylib/wasm";

if (native.BACKEND !== "native") throw new Error(`expected native, got ${native.BACKEND}`);
if (wasm.BACKEND !== "wasm") throw new Error(`expected wasm, got ${wasm.BACKEND}`);
if (wasm.normalizeSlug("Hello Wasm!") !== "hello-wasm") throw new Error("unexpected wasm slug");
const a = native.normalizeSlug("Parity!");
const b = wasm.normalizeSlug("Parity!");
if (a !== b) throw new Error(`backends disagree: ${a} vs ${b}`);
"""

# A `.cjs` file so `require` is genuinely the CommonJS entry point. Requiring an
# ESM graph is supported from Node 20.19 and fails if anything uses top-level
# await, which is exactly the regression this case guards.
_CJS_REQUIRE = """\
const facade = require("@polylib/polylib");
if (facade.BACKEND !== "native") throw new Error(`expected native, got ${facade.BACKEND}`);
if (facade.normalizeSlug("Hello CJS!") !== "hello-cjs") throw new Error("unexpected slug");
console.log("cjs-require ok");
"""

_MISSING_NATIVE = """\
import { normalizeSlug } from "@polylib/polylib";

let caught;
try {
  normalizeSlug("Hi!");
} catch (err) {
  caught = err;
}
if (caught === undefined) throw new Error("expected a missing_native_binding error");
if (caught.code !== "missing_native_binding") throw new Error(`unexpected code: ${caught.code}`);
if (!caught.message.includes(process.platform)) {
  throw new Error(`message does not name the platform: ${caught.message}`);
}
if (caught.message.includes("Supported platforms:") === false) {
  throw new Error(`message does not list the supported platforms: ${caught.message}`);
}
if (caught.cause === undefined) throw new Error("missing_native_binding has no cause");
"""

_WASM_PEER_MISSING = """\
let caught;
try {
  await import("@polylib/polylib/wasm");
} catch (err) {
  caught = err;
}
if (caught === undefined) throw new Error("expected the /wasm import to fail");
if (caught.code !== "ERR_MODULE_NOT_FOUND") throw new Error(`unexpected code: ${caught.code}`);
if (!caught.message.includes("@polylib/polylib-wasm")) {
  throw new Error(`message does not name the peer: ${caught.message}`);
}
"""

_CJS_BUNDLE = """\
import { BACKEND, normalizeSlug } from "@polylib/polylib";
if (BACKEND !== "native") throw new Error(`expected native, got ${BACKEND}`);
if (normalizeSlug("Hello Bundle!") !== "hello-bundle") throw new Error("unexpected slug");
console.log("cjs-bundle ok");
"""

_BROWSER_WASM_BUNDLE = """\
import { normalizeSlug } from "@polylib/polylib-wasm";
export const probe = normalizeSlug;
"""

_BROWSER_FACADE_BUNDLE = """\
import * as facade from "@polylib/polylib";
export const probe = facade;
"""


def consumer_cases(
    tarballs: dict[str, Path], *, platform_packages: dict[str, Path]
) -> tuple[ConsumerCase, ...]:
    """Describe every consumer fixture the compatibility gate runs.

    `platform_packages` maps an npm package name onto the per-platform tarball
    built on this host. The `server-only` case installs it explicitly, because a
    local `file:` tarball cannot be reached through `optionalDependencies`.
    """
    server_only: dict[str, Path] = {
        _FACADE_PKG: tarballs[_FACADE_PKG],
        _JS_PKG: tarballs[_JS_PKG],
        **platform_packages,
    }
    facade_and_js: dict[str, Path] = {
        _FACADE_PKG: tarballs[_FACADE_PKG],
        _JS_PKG: tarballs[_JS_PKG],
    }
    return (
        ConsumerCase("server-only", server_only, _SERVER_ONLY, requires_native=True),
        ConsumerCase(
            "server+wasm",
            {
                _FACADE_PKG: tarballs[_FACADE_PKG],
                _WASM_PKG: tarballs[_WASM_PKG],
                _JS_PKG: tarballs[_JS_PKG],
                **platform_packages,
            },
            _SERVER_PLUS_WASM,
            requires_native=True,
        ),
        ConsumerCase(
            "cjs-require", server_only, _CJS_REQUIRE, script_name="check.cjs", requires_native=True
        ),
        ConsumerCase(
            "cjs-bundle",
            server_only,
            _CJS_BUNDLE,
            script_name="entry.mjs",
            needs_bundler=True,
            requires_native=True,
        ),
        ConsumerCase(
            # The facade depends on @polylib/polylib-js, so npm resolves it even
            # though a browser bundle never follows that path: it is behind the
            # `node` condition. Listing it keeps the install self-contained.
            "browser-bundle",
            {
                _FACADE_PKG: tarballs[_FACADE_PKG],
                _WASM_PKG: tarballs[_WASM_PKG],
                _JS_PKG: tarballs[_JS_PKG],
                **platform_packages,
            },
            _BROWSER_WASM_BUNDLE,
            script_name="entry.mjs",
            needs_bundler=True,
        ),
        ConsumerCase(
            "missing-native",
            facade_and_js,
            _MISSING_NATIVE,
            install_args=("--omit=optional",),
        ),
        ConsumerCase(
            "wasm-peer-missing",
            facade_and_js,
            _WASM_PEER_MISSING,
            install_args=("--omit=optional",),
        ),
    )


def _run(argv: tuple[str, ...], cwd: Path) -> None:
    print("+ " + " ".join(argv), flush=True)
    proc = subprocess.run(argv, cwd=cwd, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(argv)}")


def _bundler(consumer_dir: Path) -> Path:
    name = f"{_ESBUILD}.cmd" if _is_windows() else _ESBUILD
    path = consumer_dir / "node_modules" / ".bin" / name
    if not path.is_file():
        raise ToolError(f"esbuild was not installed in {consumer_dir}; run npm install first.")
    return path


def _assert_no_node_imports(path: Path) -> None:
    text = path.read_text(encoding=_UTF8)
    offenders = sorted({token for token in ("node:", "require(") if token in text})
    if offenders:
        raise ToolError(
            f"{path.name} still references {', '.join(offenders)}; "
            "a browser bundle cannot resolve it."
        )


def _bundle(bundler: Path, args: tuple[str, ...], cwd: Path) -> None:
    _run((str(bundler), *args), cwd)


def _run_bundler_case(case: ConsumerCase, consumer_dir: Path) -> None:
    """Bundle with esbuild, then assert what the target is allowed to contain."""
    bundler = _bundler(consumer_dir)
    if case.name == "cjs-bundle":
        outfile = "bundle.cjs"
        _bundle(
            bundler,
            (
                case.script_name,
                "--bundle",
                "--platform=node",
                "--format=cjs",
                "--external:@polylib/*",
                f"--outfile={outfile}",
            ),
            consumer_dir,
        )
        _run((resolve_program(_NODE), outfile), consumer_dir)
        return
    wasm_out = "wasm.bundle.js"
    _bundle(
        bundler,
        (
            case.script_name,
            "--bundle",
            "--platform=browser",
            "--format=esm",
            f"--outfile={wasm_out}",
        ),
        consumer_dir,
    )
    _assert_no_node_imports(consumer_dir / wasm_out)
    facade_out = "facade.bundle.js"
    _bundle(
        bundler,
        (
            "facade-entry.mjs",
            "--bundle",
            "--platform=browser",
            "--format=esm",
            f"--outfile={facade_out}",
        ),
        consumer_dir,
    )
    if "unsupported_runtime" not in (consumer_dir / facade_out).read_text(encoding=_UTF8):
        raise ToolError(
            "Bundling @polylib/polylib for the browser did not select the unsupported-runtime stub."
        )


def run_consumer_cases(
    cases: tuple[ConsumerCase, ...], root: Path, *, native_addon_available: bool = True
) -> tuple[str, ...]:
    """Install each fixture with npm and run its program.

    A fixture marked `requires_native` cannot pass without a compiled addon, so
    when one was never built those cases are reported as skipped instead of
    failing. Every other case still runs, which is what keeps the browser,
    CommonJS, and missing-binding guarantees enforced on a machine without a
    Rust toolchain.

    Returns the names of the cases that were skipped.
    """
    npm = resolve_program(_NPM)
    node = resolve_program(_NODE)
    skipped: list[str] = []
    for case in cases:
        if case.requires_native and not native_addon_available:
            print(f"- {case.name}: skipped, no compiled addon for this host", flush=True)
            skipped.append(case.name)
            continue
        consumer_dir = root / case.name
        consumer_dir.mkdir(parents=True, exist_ok=True)
        (consumer_dir / _PACKAGE_JSON).write_text(
            json.dumps(case.manifest(consumer_dir), indent=2) + "\n", encoding=_UTF8
        )
        (consumer_dir / case.script_name).write_text(case.script, encoding=_UTF8)
        if case.name == "browser-bundle":
            (consumer_dir / "facade-entry.mjs").write_text(_BROWSER_FACADE_BUNDLE, encoding=_UTF8)
        _run((npm, "install", "--no-audit", "--no-fund", *case.install_args), consumer_dir)
        if case.needs_bundler:
            _run_bundler_case(case, consumer_dir)
            continue
        _run((node, case.script_name), consumer_dir)
    return tuple(skipped)


def verify_facade_peer_declaration(facade_manifest: dict[str, object]) -> list[str]:
    """Check the packed facade declares wasm as an optional peer, not a dependency.

    A `workspace:` protocol that survived packing, or a peer range that is not a
    concrete `~X.Y.Z`, means the published package asks npm for a version that
    does not exist. npm only warns about a mismatched optional peer and then
    skips installing it, so the mistake would reach users as a missing package
    rather than a failed release.
    """
    problems: list[str] = []
    for key in ("dependencies", "optionalDependencies", "devDependencies"):
        declared = facade_manifest.get(key) or {}
        if isinstance(declared, dict) and _WASM_PKG in declared:
            problems.append(f"{key} must not declare {_WASM_PKG}; it belongs in peerDependencies")
    peers = facade_manifest.get("peerDependencies") or {}
    range_spec = peers.get(_WASM_PKG) if isinstance(peers, dict) else None
    if not isinstance(range_spec, str):
        problems.append(f"peerDependencies is missing {_WASM_PKG}")
        return problems
    if range_spec.startswith("workspace:"):
        problems.append(f"peer range {range_spec!r} leaked the workspace protocol")
    elif not (range_spec.startswith("~") and range_spec.count(".") >= 2):
        problems.append(f"peer range {range_spec!r} is not a concrete ~X.Y.Z")
    meta = facade_manifest.get("peerDependenciesMeta") or {}
    optional = meta.get(_WASM_PKG, {}).get("optional") if isinstance(meta, dict) else None
    if optional is not True:
        problems.append(f"peerDependenciesMeta must mark {_WASM_PKG} optional")
    return problems
