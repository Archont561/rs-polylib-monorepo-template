import { defineConfig } from "bunup";

export default defineConfig({
  entry: ["src/index.ts", "src/not-in-browser.ts", "src/wasm.ts"],
  format: ["esm"],
  dts: true,
  clean: true,
  target: "node",
  external: ["@polylib/polylib-js", "@polylib/polylib-wasm"],
});
