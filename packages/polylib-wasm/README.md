# `@polylib/polylib-wasm`

WebAssembly TypeScript library powered by the `polylib-core` Rust engine compiled
via `wasm-bindgen` (`crates/polylib-wasm`).

Two entries share one type surface:

| Specifier | Entry | Initialization |
| :--- | :--- | :--- |
| `@polylib/polylib-wasm` on `node`/`bun` | `dist/index.node.js` | Automatic, reads the `.wasm` from disk on first use. |
| `@polylib/polylib-wasm` on `browser`/`worker`/`default` | `dist/index.browser.js` | Explicit `initWasmAsync()` before any other export. |

Both entries export the same names, and the build fails if they diverge, because a
single `index.d.ts` has to describe both.

## Install

```sh
npm install @polylib/polylib-wasm
```

## Node.js and Bun

The module loads the compiled `.wasm` synchronously from its own directory the
first time an export runs. There is nothing to initialize:

```ts
import { getWasmVersion, normalizeSlug, summarizeScores } from "@polylib/polylib-wasm";

normalizeSlug("Hello, Polyglot World!"); // "hello-polyglot-world"
summarizeScores([10, 20, 30]);           // { count: 3, min: 10, max: 30, mean: 20 }
```

If you would rather control when the module is read, `initWasmAsync(input?)`
accepts explicit bytes and is a no-op once the module is loaded.

## Browsers and edge runtimes

The browser entry has no `node:` imports, so it bundles for the browser without
polyfills or shims. It does not initialize itself, because fetching the module is
asynchronous and a top-level `await` would break CommonJS consumers of the shared
types. Call `initWasmAsync()` once, before any other export:

```ts
import { initWasmAsync, normalizeSlug } from "@polylib/polylib-wasm";

await initWasmAsync(); // fetches ./polylib_wasm_bg.wasm relative to this module
normalizeSlug("Hello, Browser!");
```

Calling another export first throws `PolylibError` with code
`wasm_not_initialized`, naming `initWasmAsync` in the message, rather than failing
with an opaque "unreachable" trap from the wasm module.

Pass the bytes yourself when the module is inlined or served from another path. The
raw module is published as a subpath:

```ts
import wasmUrl from "@polylib/polylib-wasm/polylib_wasm_bg.wasm?url";

await initWasmAsync(await fetch(wasmUrl).then((response) => response.arrayBuffer()));
```

## Responsibilities

- Loads the self-contained `.wasm` binary synchronously in Bun (`>=1.1.0`) and
  Node.js (`>=20.19.0`) with zero runtime dependencies, and exports
  `initWasmAsync(...)` for browser and edge runtimes.
- Ships strict ESM modules and `.d.ts` declarations verified by `publint --strict`
  and `@arethetypeswrong/cli` (`attw`). `dist/index.d.ts` describes both entries and
  is produced from the node declaration only after both export lists are compared.
- Stays verified against shared Gherkin `conformance/*.feature` specs using
  `@aboviq/bun-test-cucumber`, `@archont561/bun-test-utils`, and `fast-check`.

## Verification

```sh
pixi run -e full tools run bindings build --target wasm
pixi run -e js tools run ts test
pixi run -e js tools run ts compat
```
