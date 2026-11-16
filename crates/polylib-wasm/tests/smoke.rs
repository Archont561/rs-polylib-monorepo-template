//! Host-side smoke tests for `polylib-wasm`.
//!
//! Full WASM runtime and conformance tests execute against the compiled
//! `wasm32-unknown-unknown` binary under `packages/polylib-ts/tests/`.

#[test]
fn wasm_crate_version_matches_core() {
    assert_eq!(polylib_wasm::VERSION, polylib_core::VERSION);
}
