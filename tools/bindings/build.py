"""Build PyO3, WebAssembly, NAPI-RS, TypeScript facade, and UniFFI bindings."""

from __future__ import annotations

import json
from typing import Literal

from tasknest import ToolContext, ToolError, tool

from tools._lib.compat_py import build_editable_extension
from tools._lib.ffi import (
    TARGET_KOTLIN,
    TARGET_RUBY,
    TARGET_SWIFT,
    FfiBuildTarget,
    build_ffi_targets,
)

_TARGET_PY = "py"
_TARGET_WASM = "wasm"
_TARGET_NAPI = "napi"
_TARGET_TS = "ts"
_TARGET_FFI = "ffi"
_FFI_SUBTARGET_OF: dict[str, FfiBuildTarget] = {
    TARGET_KOTLIN: TARGET_KOTLIN,
    TARGET_SWIFT: TARGET_SWIFT,
    TARGET_RUBY: TARGET_RUBY,
}
_FFI_SUBTARGETS: tuple[str, ...] = tuple(_FFI_SUBTARGET_OF)
BindingsTarget = Literal["all", "py", "wasm", "napi", "ts", "ffi", "kotlin", "swift", "ruby"]
_ALL_TARGETS: BindingsTarget = "all"
# The same word, typed for the FFI entry point so it can be forwarded directly.
_FFI_ALL: FfiBuildTarget = "all"
_VALID_TARGETS: tuple[str, ...] = (
    _ALL_TARGETS,
    _TARGET_PY,
    _TARGET_WASM,
    _TARGET_NAPI,
    _TARGET_TS,
    _TARGET_FFI,
    *_FFI_SUBTARGETS,
)
_PACKAGES_DIR = "packages"
_BUN = "bun"
_RUN = "run"
_BUILD = "build"
_WASM_BUILD_CMD: tuple[str, ...] = (
    "cargo",
    _BUILD,
    "--release",
    "--target",
    "wasm32-unknown-unknown",
    "-p",
    "polylib-wasm",
    "--locked",
)
_WASM_BINDGEN_CMD: tuple[str, ...] = (
    "wasm-bindgen",
    "--target",
    "web",
    "--out-dir",
    "packages/polylib-wasm/src/wasm",
    "target/wasm32-unknown-unknown/release/polylib_wasm.wasm",
)


def _build_bun_package(ctx: ToolContext, pkg_dir: str, script: str = _BUILD) -> None:
    ctx.run([_BUN, _RUN, script], cwd=ctx.repo_root / _PACKAGES_DIR / pkg_dir)


def _build_js_and_py(ctx: ToolContext, target: str) -> None:
    if target in (_ALL_TARGETS, _TARGET_PY):
        built = build_editable_extension(ctx.repo_root)
        print(f"Built PyO3 extension: {built.relative_to(ctx.repo_root)}")
    if target in (_ALL_TARGETS, _TARGET_WASM):
        ctx.run(_WASM_BUILD_CMD, cwd=ctx.repo_root)
        ctx.run(_WASM_BINDGEN_CMD, cwd=ctx.repo_root)
        _build_bun_package(ctx, "polylib-wasm")
    if target in (_ALL_TARGETS, _TARGET_NAPI):
        _build_bun_package(ctx, "polylib-js", "build:native")
        _build_bun_package(ctx, "polylib-js")
        _write_supported_targets(ctx)
    if target in (_ALL_TARGETS, _TARGET_TS):
        _build_bun_package(ctx, "polylib-ts")


@tool(
    marks=("rust", "python", "ts", "ffi", "writes"),
    description="Build bindings (`all`, `py`, `wasm`, `napi`, `ts`, `ffi`, `kotlin|swift|ruby`).",
)
def build_bindings(ctx: ToolContext, target: BindingsTarget = _ALL_TARGETS) -> None:
    """Compile Python, WebAssembly, NAPI-RS, TypeScript facade, and/or UniFFI bindings."""
    if target not in _VALID_TARGETS:
        choices = ", ".join(_VALID_TARGETS)
        raise ToolError(f"Unsupported binding target {target!r}; expected one of: {choices}.")
    _build_js_and_py(ctx, target)
    if target in (_ALL_TARGETS, _TARGET_FFI):
        build_ffi_targets(ctx, target=_FFI_ALL)
    elif target in _FFI_SUBTARGETS:
        # Dispatching through the table, rather than passing `target` through a
        # cast, is what lets mypy narrow: a dict lookup by key yields the value
        # type, and the FFI subtargets are exactly this table's keys.
        build_ffi_targets(ctx, target=_FFI_SUBTARGET_OF[target])


def _write_supported_targets(ctx: ToolContext) -> None:
    """Record the platforms this build's loader can recognise.

    The loader ships the list in its error message, so a consumer on an
    unsupported host is told what is available. The list is generated from
    `napi.targets` rather than written by hand, because a hand-written copy
    drifts the first time a target is added.
    """
    from tools._lib.napi_platforms import load_targets

    manifest = ctx.repo_root / _PACKAGES_DIR / "polylib-js" / "package.json"
    suffixes = [target.suffix for target in load_targets(manifest)]
    out = ctx.repo_root / _PACKAGES_DIR / "polylib-js" / "src" / "supported-targets.json"
    out.write_text(json.dumps(suffixes, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(ctx.repo_root)} ({len(suffixes)} targets)")
