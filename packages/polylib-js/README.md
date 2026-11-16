# `@polylib/polylib-js`

Native Node.js and Bun TypeScript library powered by `crates/polylib-js` (`napi-rs` / Node-API v9) over `crates/polylib-core`.

## Responsibilities

- Provides an ESM TypeScript API backed by a compiled native `.node` addon (no WebAssembly runtime overhead).
- Surfaces typed `PolylibError` instances with canonical `code` strings matching Rust, Python, and WASM bindings.
- Verified against shared Gherkin `conformance/*.feature` specifications via `@aboviq/bun-test-cucumber`, plus `publint --strict` and `@arethetypeswrong/cli`.

## Verification

```sh
pixi run -e full tools run bindings build --target napi
pixi run -e full tools run ts test
pixi run -e full tools run ts compat
```
