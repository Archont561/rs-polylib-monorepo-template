# `@polylib/polylib`

Typed TypeScript facade over the `polylib-core` Rust engine.

The main entry is native: it imports `@polylib/polylib-js` statically and runs the
compiled NAPI-RS addon. WebAssembly is an explicit opt-in, so an install that does
not need it never downloads it, and a platform that cannot load an addon fails with
an error naming the platform rather than silently switching backend.

```ts
import { normalizeSlug, summarizeScores } from "@polylib/polylib";

normalizeSlug("Hello, Polyglot World!"); // "hello-polyglot-world"
summarizeScores([10, 20, 30]);           // { count: 3, min: 10, max: 30, mean: 20 }
```

## Entry points

| Specifier | Resolves to | Notes |
| :--- | :--- | :--- |
| `@polylib/polylib` | `dist/index.js` | Native. Requires `@polylib/polylib-js`. |
| `@polylib/polylib/wasm` | `dist/wasm.js` | WebAssembly. Requires the optional peer. |
| `@polylib/polylib` under `browser` | `dist/not-in-browser.js` | Throws `unsupported_runtime`. |

`@polylib/polylib-wasm` is an **optional peer dependency**: `npm install @polylib/polylib`
does not install it, and nothing fails until a program actually imports `/wasm`.

```ts
import * as wasm from "@polylib/polylib/wasm";

wasm.normalizeSlug("Hello, Polyglot World!"); // same result, no addon needed
```

### In a browser

The browser build reaches the main entry through the `default` export condition,
which points at a stub that throws on import:

```ts
import { PolylibError } from "@polylib/polylib"; // throws unsupported_runtime
```

Import `@polylib/polylib/wasm` instead. It has no `node:` imports, and the module
needs one explicit initialization before its exports can run:

```ts
import { initWasmAsync, normalizeSlug } from "@polylib/polylib/wasm";

await initWasmAsync(); // fetches ./polylib_wasm_bg.wasm relative to the module
normalizeSlug("Hello, Browser!");
```

Pass the bytes yourself when your bundler inlines or relocates the module:

```ts
import wasmUrl from "@polylib/polylib-wasm/polylib_wasm_bg.wasm?url";
await initWasmAsync(await fetch(wasmUrl).then((r) => r.arrayBuffer()));
```

## Errors

Every failure is a `PolylibError` with a stable `code`:

| Code | When | `code` source |
| :--- | :--- | :--- |
| `empty_input` | Slug input has no alphanumeric characters. | Engine |
| `empty_scores` | `summarizeScores` received an empty list. | Engine |
| `invalid_input` | A score was not a finite number. | Engine |
| `missing_native_binding` | No `@polylib/polylib-js-<os>-<arch>` addon for this host. | Facade loader |
| `unsupported_runtime` | The main entry was imported in a browser bundle. | Facade stub |
| `wasm_not_initialized` | A `/wasm` export ran before `initWasmAsync`. | WebAssembly entry |

A native engine error arrives as `"code: message"` and is split only when the code
prefix matches `^[a-z][a-z0-9_]*$`, so a message that merely starts with a word and
a colon keeps its text intact.

When no addon matches the host, the error names the detected platform, lists the
supported targets, and points at `/wasm`:

```text
@polylib/polylib-js has no native binding for linux-x64-musl.
Supported platforms: linux-x64-gnu, linux-arm64-gnu, linux-x64-musl, …
If your platform is not listed, use the WebAssembly build instead:
  npm i @polylib/polylib-wasm
  import * as polylib from "@polylib/polylib/wasm";
```

The original loader failure is attached as `error.cause`.

## Runtime support

`require()` of the main entry works on Node.js 20.19 or later, where `require` can
load an ESM graph. There is no top-level `await` anywhere in the native path.

## Verification

```sh
pixi run -e js tools run ts test
pixi run -e js tools run ts compat
```
