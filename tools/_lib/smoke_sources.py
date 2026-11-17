"""Packaged-artifact smoke scripts, named so a test can prove parity is checked.

Every ecosystem that ships a built artifact re-runs one of these scripts
against the *packaged* result, not the source tree. The point of running them
from the package is to prove the native library inside is the one this release
built, which is a different question from "does the code compile". A smoke
script that omits the version comparison still passes, so nothing else notices
when it goes missing.

The Ruby script lost that assertion once, when the verifier moved modules and
the line was not carried across. Keeping every script in one mapping lets a
test assert the property across all of them, including any added later.
"""

from __future__ import annotations

from tools._lib.compat_ffi import (
    _C_ABI_SMOKE_TEMPLATE,
    _JAVA_SMOKE_SRC,
    _SMOKE_RUBY,
)
from tools._lib.compat_py import _SMOKE_CODE
from tools._lib.compat_ts import (
    _BACKEND_CHECK_TEMPLATE,
    _FACADE_CHECK_TEMPLATE,
    _FACADE_PKG,
    _JS_PKG,
    _WASM_PKG,
)

# Each entry is (ecosystem, rendered source, the fragment that proves the
# packaged artifact's version is compared against the release version).
# A fragment is checked for presence, so reformatting a script is fine but
# deleting the comparison is not.
PARITY_FRAGMENTS: dict[str, str] = {
    "ruby": "Polylib.ffi_version == Polylib::VERSION",
    "python": "polylib.__version__ == polylib.VERSION",
    "kotlin": "!Polylib.VERSION.equals(Polylib.INSTANCE.ffiVersion())",
    "swift-c-abi": "ffi_polylib_ffi_uniffi_contract_version()",
    "ts-wasm": "getWasmVersion() !== VERSION",
    "ts-native": "getNativeVersion() !== VERSION",
    "ts-facade": "getEngineVersion() !== VERSION",
}

SMOKE_SOURCES: dict[str, str] = {
    "ruby": _SMOKE_RUBY,
    "python": _SMOKE_CODE,
    "kotlin": _JAVA_SMOKE_SRC,
    "swift-c-abi": _C_ABI_SMOKE_TEMPLATE.replace("__CONTRACT_VERSION__", "29"),
    "ts-wasm": _BACKEND_CHECK_TEMPLATE.format(pkg_name=_WASM_PKG, version_fn="getWasmVersion"),
    "ts-native": _BACKEND_CHECK_TEMPLATE.format(pkg_name=_JS_PKG, version_fn="getNativeVersion"),
    "ts-facade": _FACADE_CHECK_TEMPLATE.format(
        facade=_FACADE_PKG,
        expected_backend="native",
        native_import='import * as nativeApi from "@polylib/polylib/native";\n',
        native_check="",
    ),
}


def parity_fragment(ecosystem: str) -> str:
    """Return the version-parity fragment a given ecosystem's smoke script must contain."""
    return PARITY_FRAGMENTS[ecosystem]


def missing_parity() -> list[str]:
    """Return the ecosystems whose smoke script no longer compares versions."""
    return [
        ecosystem
        for ecosystem, source in SMOKE_SOURCES.items()
        if PARITY_FRAGMENTS[ecosystem] not in source
    ]
