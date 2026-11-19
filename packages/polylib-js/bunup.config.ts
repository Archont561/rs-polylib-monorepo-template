import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig } from "bunup";

// The `.node` addons are not bundled into this package: they live in one
// per-platform package each, listed as `optionalDependencies`, and npm installs
// only the one matching the host. What ships here is the generated loader
// (`binding.cjs`), which resolves the right platform package at require time.
export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm"],
  dts: true,
  clean: true,
  target: "node",
  onSuccess() {
    const bindingSrc = resolve(import.meta.dir, "src/native/binding.cjs");
    if (!existsSync(bindingSrc)) {
      throw new Error(
        `Missing generated NAPI-RS loader at ${bindingSrc}. Run \`pixi run -e full tools run bindings build --target napi\` first.`,
      );
    }
    const nativeDstDir = resolve(import.meta.dir, "dist/native");
    mkdirSync(nativeDstDir, { recursive: true });
    copyFileSync(bindingSrc, resolve(nativeDstDir, "binding.cjs"));
  },
});
