# `polylib-js`

Thin `napi-rs` (Node-API v9) native addon crate compiled by `@napi-rs/cli` for `packages/polylib-js`.

## Responsibilities

- Marshals UTF-8 strings, numeric arrays, `ScoreSummary` objects, and typed `CoreError` codes across the Node-API FFI boundary.
- Delegates all domain logic to `polylib-core`.
- Stays `publish = false` on crates.io (shipped as a native `.node` addon inside `@polylib/polylib-js` on npm).

## Allowed Dependencies

- `polylib-core`, `napi`, `napi-derive`, and `napi-build` only.
- Never imports `pyo3`, `polylib-py`, `wasm-bindgen`, or `polylib-wasm`.

## Verification

```sh
pixi run -e full tools run bindings build --target napi
pixi run -e full tools run ts compat
```
