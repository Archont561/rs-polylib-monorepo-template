"""Isolated Node.js + npm tarball compatibility consumer checks."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tools._lib.program import resolve_program
from tools._lib.status import CheckResult, failed, passed, skipped
from tools._lib.tarball_ref import tarball_ref

if TYPE_CHECKING:
    from pathlib import Path

_UTF8 = "utf-8"
_COMMA_SEP = ", "
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
    npm = resolve_program(_NPM)
    node = resolve_program(_NODE)
    _run_cmd((npm, "install", "--no-save", "--no-audit", "--no-fund", *install_args), consumer_dir)
    _run_cmd((node, _CHECK_MJS), consumer_dir)


def _node_manifest(
    name: str,
    consumer_dir: Path,
    deps: dict[str, Path],
    overrides: dict[str, Path],
) -> dict[str, object]:
    """Build a Node consumer manifest with relative `file:` tarball references."""
    return {
        "name": name,
        "type": "module",
        "dependencies": {pkg: tarball_ref(path, consumer_dir) for pkg, path in deps.items()},
        "overrides": {pkg: tarball_ref(path, consumer_dir) for pkg, path in overrides.items()},
    }


@dataclass(frozen=True)
class NodeConsumerCase:
    """One isolated Node.js consumer fixture.

    `dependencies` and `overrides` map a package name onto the packed tarball
    it must resolve to. The `file:` references are written relative to the
    consumer directory, because that is the directory npm resolves them from.
    """

    dirname: str
    name: str
    dependencies: dict[str, Path]
    overrides: dict[str, Path]
    script: str
    install_args: tuple[str, ...]


def _node_consumer_cases(tarballs: dict[str, Path]) -> tuple[NodeConsumerCase, ...]:
    """Describe the Node consumer fixtures."""
    return (
        NodeConsumerCase(
            "node-native",
            "node-consumer-native",
            {
                _FACADE_PKG: tarballs[_FACADE_PKG],
                _WASM_PKG: tarballs[_WASM_PKG],
                _JS_PKG: tarballs[_JS_PKG],
            },
            {_WASM_PKG: tarballs[_WASM_PKG], _JS_PKG: tarballs[_JS_PKG]},
            _NODE_NATIVE_MJS,
            (),
        ),
        NodeConsumerCase(
            "node-wasm-fallback",
            "node-consumer-wasm-fallback",
            {_FACADE_PKG: tarballs[_FACADE_PKG], _WASM_PKG: tarballs[_WASM_PKG]},
            {_WASM_PKG: tarballs[_WASM_PKG]},
            _NODE_WASM_FALLBACK_MJS,
            ("--omit=optional",),
        ),
    )


def verify_node_consumers(
    tmp_path: Path,
    tarballs: dict[str, Path],
    *,
    require_node: bool,
) -> CheckResult:
    """Install packed tarballs via `npm` and run native + WASM-fallback smoke tests in Node.js."""
    name = "ts-node-consumers"
    absent = [binary for binary in (_NODE, _NPM) if shutil.which(binary) is None]
    if absent:
        reason = (
            f"{_COMMA_SEP.join(absent)} not found on PATH, so the Node.js consumer install "
            "and smoke tests did not run; install Node.js or run via `pixi run -e js ...`."
        )
        if require_node:
            return failed(name, reason)
        return skipped(name, reason)
    for case in _node_consumer_cases(tarballs):
        consumer_dir = tmp_path / case.dirname
        manifest = _node_manifest(case.name, consumer_dir, case.dependencies, case.overrides)
        _run_node_consumer(consumer_dir, manifest, case.script, case.install_args)
    return passed(name, evidence="npm installed each tarball and the Node.js smoke tests ran")
