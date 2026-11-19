# `@polylib/polylib-js`

Native Node.js and Bun bindings for `polylib-core`, built with NAPI-RS.

The addon is a compiled `.node` file, so it ships as one package per platform. The
main package contains the loader and the types; npm installs the single matching
platform package from `optionalDependencies` and skips the rest.

## Install

```sh
npm install @polylib/polylib-js
```

No build step and no Rust toolchain: npm picks the prebuilt addon for your host.

```ts
import { getNativeVersion, normalizeSlug, summarizeScores } from "@polylib/polylib-js";

normalizeSlug("Hello, Polyglot World!"); // "hello-polyglot-world"
summarizeScores([10, 20, 30]);           // { count: 3, min: 10, max: 30, mean: 20 }
```

## Supported platforms

| Package | `os` | `cpu` | `libc` |
| :--- | :--- | :--- | :--- |
| `@polylib/polylib-js-linux-x64-gnu` | `linux` | `x64` | `glibc` |
| `@polylib/polylib-js-linux-arm64-gnu` | `linux` | `arm64` | `glibc` |
| `@polylib/polylib-js-linux-x64-musl` | `linux` | `x64` | `musl` |
| `@polylib/polylib-js-linux-arm64-musl` | `linux` | `arm64` | `musl` |
| `@polylib/polylib-js-darwin-x64` | `darwin` | `x64` | — |
| `@polylib/polylib-js-darwin-arm64` | `darwin` | `arm64` | — |
| `@polylib/polylib-js-win32-x64-msvc` | `win32` | `x64` | — |
| `@polylib/polylib-js-win32-arm64-msvc` | `win32` | `arm64` | — |

Every platform package is pinned to the exact version of this package, so the
loader and the addon always come from one build.

## When no addon matches

Installations that skip optional dependencies (`npm install --omit=optional`) or
run on a platform with no prebuilt addon get a single, explicit error:

```ts
import { normalizeSlug } from "@polylib/polylib-js";

normalizeSlug("Hi!");
// PolylibError: code "missing_native_binding"
//   @polylib/polylib-js has no native binding for linux-x64-musl.
//   Supported platforms: linux-x64-gnu, linux-arm64-gnu, …
//   If your platform is not listed, use the WebAssembly build instead:
//     npm i @polylib/polylib-wasm
//     import * as polylib from "@polylib/polylib/wasm";
```

The loader failure is available as `error.cause`. The supported list is generated
from `napi.targets`, so it cannot drift from the packaged set.

Use `@polylib/polylib-wasm` (or the facade's `/wasm` subpath) when you need to run
somewhere without a prebuilt addon.

## Verification

```sh
pixi run -e js tools run ts test
pixi run -e js tools run ts compat
pixi run -e full tools run bindings stage_napi --suffix linux-x64-gnu
```
