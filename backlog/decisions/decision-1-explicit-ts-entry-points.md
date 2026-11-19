# Explicit TypeScript entry points instead of a runtime native→wasm fallback

- **Status**: Accepted
- **Date**: 2026-11-16
- **Scope**: `packages/polylib-ts`, `packages/polylib-js`, `packages/polylib-wasm`

## Context

`@polylib/polylib` used to decide its backend at runtime. The main entry tried the
NAPI-RS addon and, when `require` threw, fell back to `@polylib/polylib-wasm`,
logging a notice once. Two subpaths (`/native`, `/wasm`) existed for callers who
wanted to choose, and a `selectEngine` helper exposed the decision.

Three problems accumulated:

1. **The fallback was invisible to bundlers.** Because the main entry contained
   both `import "@polylib/polylib-js"` and a dynamic import of the WebAssembly
   package, a browser bundle dragged in a `node:fs` path it could never run. The
   failure appeared at build time as `Could not resolve "node:fs"`, or at runtime
   as an opaque trap, depending on the bundler.
2. **The fallback hid packaging bugs.** An install whose optional dependency was
   skipped silently changed semantics: identical code produced different numbers of
   available features, and a `missing_native_binding` never reached the user.
3. **It forced a hard dependency on both backends.** Every consumer downloaded the
   `.wasm` binary whether or not the addon worked.

## Decision

The main entry is native only and imports the addon statically:

- `"."` → `dist/index.js`, `import "@polylib/polylib-js"` at module scope. No
  top-level `await`, no dynamic `import()`, so `require()` works on Node ≥ 20.19.
- `"./wasm"` → `dist/wasm.js`, an explicit opt-in.
- Browser bundlers resolve `"."` through the `default` condition to
  `dist/not-in-browser.js`, which throws `PolylibError("unsupported_runtime", …)` on
  import.

`@polylib/polylib-js` becomes a hard dependency; `@polylib/polylib-wasm` becomes an
**optional peer** declared as a concrete `~X.Y.Z` range. `selectEngine`,
`PolylibEngine`, `src/native.ts`, and the `./native` subpath are removed. This is a
breaking change recorded for the pre-1.0 changelog.

## Consequences

- A browser bundle that reaches the main entry fails at import with a message naming
  the supported specifier, instead of shipping an addon call.
- A missing platform addon surfaces as `missing_native_binding`, naming the detected
  platform, listing the eight supported targets, and pointing at `/wasm`. The loader
  failure is preserved as `error.cause`.
- A server install does not download the `.wasm` binary.
- Callers who want a specific backend import it: `@polylib/polylib-js`,
  `@polylib/polylib-wasm`, or `@polylib/polylib/wasm`.
- `ts compat` grows fixtures for exactly these paths: `server-only`, `server+wasm`,
  `cjs-require`, `cjs-bundle`, `browser-bundle`, `missing-native`, and
  `wasm-peer-missing`.

## Alternatives considered

**Log-once fallback (rejected).** Keep the fallback but make the notice loud. This
preserves problem 1 unchanged: the static import of the addon stays in the browser
graph, so the bundler error remains, and the runtime behaviour still depends on
which optional dependencies npm happened to install.

**An `./auto` subpath (deferred).** Move the fallback behind `@polylib/polylib/auto`
so the main entry stays native and callers who want the old behaviour opt in. This
is a sound shape, but it keeps a second code path that must be tested on every
platform, and no current consumer needs it. Deferred rather than rejected: it can
be added later without changing the main entry.
