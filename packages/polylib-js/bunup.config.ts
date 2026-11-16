import { copyFileSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig } from "bunup";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm"],
  dts: true,
  clean: true,
  target: "node",
  onSuccess() {
    const nativeSrcDir = resolve(import.meta.dir, "src/native");
    const bindingSrc = resolve(nativeSrcDir, "binding.cjs");
    if (!existsSync(bindingSrc)) {
      throw new Error(
        `Missing compiled NAPI-RS loader at ${bindingSrc}. Run \`pixi run -e full tools run bindings build --target napi\` first.`,
      );
    }
    const nativeDstDir = resolve(import.meta.dir, "dist/native");
    mkdirSync(nativeDstDir, { recursive: true });
    copyFileSync(bindingSrc, resolve(nativeDstDir, "binding.cjs"));

    const nodeBinaries = readdirSync(nativeSrcDir).filter((name) => name.endsWith(".node"));
    if (nodeBinaries.length === 0) {
      throw new Error(
        `No compiled .node binary found in ${nativeSrcDir}. Run \`pixi run -e full tools run bindings build --target napi\` first.`,
      );
    }
    for (const file of nodeBinaries) {
      copyFileSync(resolve(nativeSrcDir, file), resolve(nativeDstDir, file));
    }
  },
});
