# `polylib-core`

Pure Rust core library shared across the `polylib` Rust metacrate, PyO3 Python bindings, and WebAssembly TypeScript bindings.

## Responsibilities

- Owns deterministic domain logic (`normalize_slug`, `summarize_scores`, `ScoreSummary`, `CoreError`).
- Enforces `#![forbid(unsafe_code)]` with zero I/O, network, or FFI dependencies.
- Provides an optional `serde` feature flag (`default = []`).

## Allowed Dependencies

- Workspace-managed leaf crates only (`thiserror`, optional `serde`).
- Never imports `polylib`, `polylib-py`, `polylib-wasm`, `pyo3`, or `wasm-bindgen`.

## Verification

```sh
pixi run -e rust tools run rust test
```
