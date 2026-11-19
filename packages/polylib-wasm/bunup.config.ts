import { copyFileSync, existsSync, readFileSync } from "node:fs";
import { rm } from "node:fs/promises";
import { resolve } from "node:path";
import { defineConfig } from "bunup";

const FORBIDDEN_IN_BROWSER = ["node:", "require("];

/**
 * Fail the build if the browser entry reaches a Node-only API.
 *
 * The whole point of the split is that a bundler targeting the browser can
 * resolve this file. A stray `node:fs` import reintroduces the original bug, and
 * the failure would otherwise surface in a consumer's bundler rather than here.
 */
function assertBrowserSafe(path: string): void {
  const source = readFileSync(path, "utf8");
  for (const token of FORBIDDEN_IN_BROWSER) {
    if (source.includes(token)) {
      throw new Error(
        `${path} contains ${JSON.stringify(token)}, which no browser runtime provides. ` +
          "Keep Node-only code in src/index.node.ts.",
      );
    }
  }
}

function exportedNames(declaration: string, path: string): string[] {
  const match = /export \{([^}]*)\}/.exec(declaration);
  if (match === null) {
    throw new Error(`${path} has no export list to compare.`);
  }
  return (match[1] ?? "")
    .split(",")
    .map(
      (entry) =>
        entry
          .trim()
          .split(/\s+as\s+/)
          .at(-1) ?? "",
    )
    .filter(Boolean)
    .sort();
}

/**
 * Publish one `index.d.ts` for both entries.
 *
 * The two entries have deliberately identical type surfaces, so one declaration
 * can describe either. `exports` names a single `types` path, and formatting two
 * near-identical files only invites drift; the check below proves they agree
 * before the shared file is written.
 */
function unifyDeclarations(outDir: string): void {
  const nodePath = resolve(outDir, "index.node.d.ts");
  const browserPath = resolve(outDir, "index.browser.d.ts");
  const nodeNames = exportedNames(readFileSync(nodePath, "utf8"), nodePath);
  const browserNames = exportedNames(readFileSync(browserPath, "utf8"), browserPath);
  if (nodeNames.join() !== browserNames.join()) {
    throw new Error(
      "The Node and browser entries must export the same names, or the shared " +
        `index.d.ts cannot describe both.\n  node:    ${nodeNames.join(", ")}\n` +
        `  browser: ${browserNames.join(", ")}`,
    );
  }
  // The Node declaration is the one to keep: it carries the same names and does
  // not mention `Response`, which only the browser initializer accepts.
  copyFileSync(nodePath, resolve(outDir, "index.d.ts"));
}

/**
 * Empty `dist/` before bundling, and wait for it.
 *
 * bunup's own `clean: true` calls its async `cleanOutDir()` without awaiting it,
 * so the recursive removal runs concurrently with the bundle and can unlink
 * files the build has just written. That is the intermittent
 * `ENOENT: no such file or directory, open '.../dist/index.js'` — it depends on
 * how full `dist/` already was, which is why a checkout that has never built is
 * fine and CI, which builds twice, is not. `onBuildStart` hooks are awaited, so
 * clearing the directory here finishes first.
 */
async function cleanDist(outDir: string): Promise<void> {
  await rm(outDir, { recursive: true, force: true });
}

export default defineConfig({
  entry: ["src/index.node.ts", "src/index.browser.ts"],
  format: ["esm"],
  dts: true,
  // bunup's own clean is unawaited; `cleanDist` replaces it.
  clean: false,
  // `node` would let the browser entry keep a `node:` import; `browser` makes
  // that a build error instead.
  target: "browser",
  plugins: [
    {
      name: "clean-dist",
      hooks: {
        async onBuildStart() {
          await cleanDist(resolve(import.meta.dir, "dist"));
        },
      },
    },
  ],
  onSuccess() {
    const outDir = resolve(import.meta.dir, "dist");
    const wasmSrc = resolve(import.meta.dir, "src/wasm/polylib_wasm_bg.wasm");
    const wasmDst = resolve(outDir, "polylib_wasm_bg.wasm");
    if (!existsSync(wasmSrc)) {
      throw new Error(
        `Missing compiled WASM module at ${wasmSrc}. Run \`pixi run -e full tools run bindings build --target wasm\` first.`,
      );
    }
    copyFileSync(wasmSrc, wasmDst);
    assertBrowserSafe(resolve(outDir, "index.browser.js"));
    unifyDeclarations(outDir);
  },
});
