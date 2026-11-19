import { rm } from "node:fs/promises";
import { resolve } from "node:path";

import { defineConfig } from "bunup";

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
  entry: ["src/index.ts", "src/not-in-browser.ts", "src/wasm.ts"],
  format: ["esm"],
  dts: true,
  // bunup's own clean is unawaited; `cleanDist` replaces it.
  clean: false,
  target: "node",
  external: ["@polylib/polylib-js", "@polylib/polylib-wasm"],
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
});
