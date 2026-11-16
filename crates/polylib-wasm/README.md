# `polylib-wasm`

Thin `wasm-bindgen` crate compiled to `wasm32-unknown-unknown` and bundled into `packages/polylib-wasm`.

## Responsibilities

- Marshals UTF-8 strings, `Float64Array` slices, and typed `CoreError` codes across the WebAssembly ABI.
- Delegates all domain logic to `polylib-core`.
- Stays `publish = false` on crates.io (shipped inside `@polylib/polylib-wasm` on npm and consumed by `@polylib/polylib`).

## Allowed Dependencies

- `polylib-core`, `wasm-bindgen`, and `serde-wasm-bindgen` only.
- Never imports `pyo3`, `polylib-py`, or native-only I/O crates.

## Verification

```sh
pixi run -e full tools run ts compat
```
