"""Isolated Node.js + npm tarball compatibility consumer checks."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_UTF8 = "utf-8"
_NPM = "npm"
_NODE = "node"
_WASM_PKG = "@polylib/polylib-wasm"
_JS_PKG = "@polylib/polylib-js"
_FACADE_PKG = "@polylib/polylib"
_CHECK_MJS = "check.mjs"
_PACKAGE_JSON = "package.json"

_NODE_NATIVE_MJS = """\
import { createRequire } from "node:module";
import * as facade from "@polylib/polylib";
import * as facadeWasm from "@polylib/polylib/wasm";
import * as facadeNative from "@polylib/polylib/native";
import * as wasmPkg from "@polylib/polylib-wasm";
import * as napiPkg from "@polylib/polylib-js";

const pkg = createRequire(import.meta.url)("@polylib/polylib/package.json");
if (pkg.name !== "@polylib/polylib") {
  throw new Error(`Unexpected package identity: ${pkg.name}`);
}
if (facade.BACKEND !== "native" || facade.getEngineVersion() !== facade.VERSION) {
  throw new Error(`Unexpected facade native backend: ${facade.BACKEND}`);
}
if (facade.normalizeSlug("Hello Node!") !== "hello-node") {
  throw new Error("Unexpected facade slug result");
}
if (facadeWasm.BACKEND !== "wasm" || facadeWasm.normalizeSlug("Hi!") !== "hi") {
  throw new Error("Unexpected @polylib/polylib/wasm result");
}
if (facadeNative.BACKEND !== "native" || facadeNative.normalizeSlug("Hi!") !== "hi") {
  throw new Error("Unexpected @polylib/polylib/native result");
}
if (wasmPkg.getWasmVersion() !== wasmPkg.VERSION) {
  throw new Error("Unexpected @polylib/polylib-wasm version");
}
if (napiPkg.getNativeVersion() !== napiPkg.VERSION) {
  throw new Error("Unexpected @polylib/polylib-js version");
}
const summary = facade.summarizeScores([10, 20, 30]);
if (summary.count !== 3 || summary.mean !== 20) {
  throw new Error("Unexpected Node.js summary result");
}
"""

_NODE_WASM_FALLBACK_MJS = """\
import { createRequire } from "node:module";
import * as facade from "@polylib/polylib";
import * as facadeWasm from "@polylib/polylib/wasm";

const pkg = createRequire(import.meta.url)("@polylib/polylib/package.json");
if (pkg.name !== "@polylib/polylib") {
  throw new Error(`Unexpected package identity: ${pkg.name}`);
}
if (facade.BACKEND !== "wasm" || facade.getEngineVersion() !== facade.VERSION) {
  throw new Error(`Expected WASM fallback backend, got: ${facade.BACKEND}`);
}
if (facade.normalizeSlug("Hello Fallback!") !== "hello-fallback") {
  throw new Error("Unexpected WASM fallback slug result");
}
if (facadeWasm.BACKEND !== "wasm" || facadeWasm.normalizeSlug("Hi!") !== "hi") {
  throw new Error("Unexpected @polylib/polylib/wasm result");
}
const summary = facade.summarizeScores([10, 20, 30]);
if (summary.count !== 3 || summary.mean !== 20) {
  throw new Error("Unexpected WASM fallback summary result");
}
"""


def _run_cmd(argv: tuple[str, ...], cwd: Path) -> None:
    print("+ " + " ".join(argv), flush=True)
    proc = subprocess.run(argv, cwd=cwd, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(argv)}")


def _run_node_consumer(
    consumer_dir: Path,
    manifest: dict[str, object],
    script: str,
    install_args: tuple[str, ...],
) -> None:
    consumer_dir.mkdir(parents=True, exist_ok=True)
    (consumer_dir / _PACKAGE_JSON).write_text(json.dumps(manifest, indent=2) + "\n", encoding=_UTF8)
    (consumer_dir / _CHECK_MJS).write_text(script, encoding=_UTF8)
    _run_cmd((_NPM, "install", "--no-save", "--no-audit", "--no-fund", *install_args), consumer_dir)
    _run_cmd((_NODE, _CHECK_MJS), consumer_dir)


def _tarball_ref(tarball: Path) -> str:
    """Return a `file:` dependency reference for a local tarball.

    `file:` followed by a bare path is ambiguous: on Windows the path starts
    with a drive letter, so `file:C:\\dir\\pkg.tgz` is parsed as a URL with
    the host `C:` instead of a local path. `Path.as_uri()` renders a proper
    `file://` URL with forward slashes on every platform.
    """
    return tarball.as_uri()


def _node_manifests(tarballs: dict[str, Path]) -> tuple[dict[str, object], dict[str, object]]:
    wasm_ref = _tarball_ref(tarballs[_WASM_PKG])
    js_ref = _tarball_ref(tarballs[_JS_PKG])
    facade_ref = _tarball_ref(tarballs[_FACADE_PKG])
    native_manifest: dict[str, object] = {
        "name": "node-consumer-native",
        "type": "module",
        "dependencies": {_FACADE_PKG: facade_ref, _WASM_PKG: wasm_ref, _JS_PKG: js_ref},
        "overrides": {_WASM_PKG: wasm_ref, _JS_PKG: js_ref},
    }
    fallback_manifest: dict[str, object] = {
        "name": "node-consumer-wasm-fallback",
        "type": "module",
        "dependencies": {_FACADE_PKG: facade_ref, _WASM_PKG: wasm_ref},
        "overrides": {_WASM_PKG: wasm_ref},
    }
    return native_manifest, fallback_manifest


def verify_node_consumers(
    tmp_path: Path,
    tarballs: dict[str, Path],
    *,
    require_node: bool,
) -> bool:
    """Install packed tarballs via `npm` and run native + WASM-fallback smoke tests in Node.js."""
    if shutil.which(_NODE) is None or shutil.which(_NPM) is None:
        if require_node:
            raise RuntimeError("`node` and `npm` are required for `--mode node` compatibility.")
        print("ts-compat: `node`/`npm` not found on PATH; skipping Node.js consumer checks.")
        return False
    native_manifest, fallback_manifest = _node_manifests(tarballs)
    _run_node_consumer(tmp_path / "node-native", native_manifest, _NODE_NATIVE_MJS, ())
    _run_node_consumer(
        tmp_path / "node-wasm-fallback",
        fallback_manifest,
        _NODE_WASM_FALLBACK_MJS,
        ("--omit=optional",),
    )
    return True
