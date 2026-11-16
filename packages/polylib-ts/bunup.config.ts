import { defineConfig } from "bunup";

export default defineConfig({
  entry: ["src/index.ts", "src/browser.ts", "src/native.ts", "src/wasm.ts"],
  format: ["esm"],
  dts: true,
  clean: true,
  target: "node",
  external: ["@polylib/polylib-js", "@polylib/polylib-wasm"],
});
