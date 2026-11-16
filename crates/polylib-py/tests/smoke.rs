//! Workspace boundary smoke test for `polylib-py`.
//!
//! Full end-to-end tests of the compiled `polylib._native` wheel run under
//! `packages/polylib-py/tests/` via `pytest`.

#[test]
fn crate_version_matches_core() {
    assert_eq!(env!("CARGO_PKG_VERSION"), polylib_core::VERSION);
}
