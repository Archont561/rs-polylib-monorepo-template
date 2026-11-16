# `@polylib/polylib`

Unified TypeScript facade over the `polylib-core` Rust engine.

## Backend Selection

- **Default import (`@polylib/polylib`) on Node.js and Bun**: loads the native NAPI-RS addon (`@polylib/polylib-js`) when installed and compatible with the host platform, and falls back transparently to WebAssembly (`@polylib/polylib-wasm`) otherwise.
- **Browser and edge runtimes (`browser`, `worker`, `edge-light` export conditions)**: resolves directly to the WebAssembly entrypoint with zero native addon references.
- **Explicit subpaths**: import `@polylib/polylib/native` to require `@polylib/polylib-js` or `@polylib/polylib/wasm` to require `@polylib/polylib-wasm`.

## Verification

```sh
pixi run -e full tools run bindings build
pixi run -e js tools run ts test
pixi run -e js tools run ts compat
```
