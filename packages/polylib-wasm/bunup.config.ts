import { copyFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig } from "bunup";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm"],
  dts: true,
  clean: true,
  target: "node",
  onSuccess() {
    const wasmSrc = resolve(import.meta.dir, "src/wasm/polylib_wasm_bg.wasm");
    const wasmDst = resolve(import.meta.dir, "dist/polylib_wasm_bg.wasm");
    if (!existsSync(wasmSrc)) {
      throw new Error(
        `Missing compiled WASM module at ${wasmSrc}. Run \`pixi run -e full tools run bindings build --target wasm\` first.`,
      );
    }
    copyFileSync(wasmSrc, wasmDst);
  },
});
