# `@polylib/polylib-wasm`

WebAssembly TypeScript library powered by the `polylib-core` Rust engine compiled via `wasm-bindgen` (`crates/polylib-wasm`).

## Responsibilities

- Loads the self-contained `.wasm` binary synchronously in Bun (`>=1.1`) and Node.js (`>=20`) with zero runtime dependencies, and exports `initWasm(...)` for browser and edge runtimes.
- Ships strict ESM modules and `.d.ts` declarations verified by `publint --strict` and `@arethetypeswrong/cli` (`attw`).
- Stays verified against shared Gherkin `conformance/*.feature` specs using `@aboviq/bun-test-cucumber`, `@archont561/bun-test-utils`, and `fast-check`.

## Verification

```sh
pixi run -e full tools run bindings build --target wasm
pixi run -e js tools run ts test
pixi run -e js tools run ts compat
```
