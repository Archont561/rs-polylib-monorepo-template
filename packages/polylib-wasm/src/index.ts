/**
 * The package has two entry modules, selected by the consumer's runtime, so there
 * is no single `index` to import: `bunup` maps `src/index.node.ts` and
 * `src/index.browser.ts` onto the `exports` conditions in `package.json`.
 *
 * This file exists because the repository's layout policy requires every
 * WebAssembly binding package to have a `src/index.ts`, and because the two entry
 * points must be discoverable from `src/` alone. It is not a build input.
 *
 * Two things depend on that name not resolving to a real module:
 *
 * - `packages/polylib-ts/tsconfig.json` maps `@polylib/polylib-wasm` onto
 *   `src/index.node.ts` explicitly. Before that, it mapped onto `src/index.ts`,
 *   and creating this file silently replaced the package's whole type surface
 *   with `export {}` — the facade build failed with "has no exported member".
 * - `bunup` lists its entries explicitly, so nothing here is bundled.
 *
 * Re-exporting the node entry would be worse, not better: it would compile the
 * Node-only `node:fs` import into any consumer that resolves this file.
 *
 * @see ./index.node.ts - Bun and Node.js; reads the compiled module from disk.
 * @see ./index.browser.ts - Browsers and workers; requires `initWasmAsync()`.
 * @see ./core.ts - the shared implementation both entries re-export.
 */

export {};
