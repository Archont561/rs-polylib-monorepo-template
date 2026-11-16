# `polylib-ffi`

Thin `uniffi` crate compiled to a shared/static native library (`libpolylib_ffi`) and bound to Kotlin (`packages/polylib-kt`), Swift (`packages/polylib-swift`), and Ruby (`packages/polylib-rb`).

## Responsibilities

- Exposes `polylib-core` functions (`ffi_version`, `normalize_slug`, `summarize_scores`), `ScoreSummary`, and typed `PolylibFfiError` variants via UniFFI proc-macros (`uniffi::setup_scaffolding!()`).
- Provides a version-matched `uniffi-bindgen` binary behind the `bindgen-cli` feature so generated native libraries carry zero CLI overhead.
- Stays `publish = false` on crates.io (distributed inside the Kotlin, Swift, and Ruby packages).

## Verification

```sh
pixi run -e full tools run ffi build
pixi run -e rust tools run rust lint
pixi run -e rust tools run rust test
```
