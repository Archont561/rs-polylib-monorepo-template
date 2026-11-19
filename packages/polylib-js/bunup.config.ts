import { copyFileSync, existsSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig } from "bunup";

import pkg from "./package.json" with { type: "json" };

/**
 * The platforms the generated loader can recognise, taken from `napi.targets`.
 *
 * The loader prints this list when no addon matches the host, so it must agree
 * with what is built. The mapping is spelled out rather than derived from the
 * triple's word order, because `x86_64-unknown-linux-gnu` and
 * `x86_64-pc-windows-msvc` do not share a shape: a derived version silently
 * produced `linux-aarch64-gnu` and `darwin-aarch64`, which no package npm
 * publishes would ever match.
 *
 * `tools/_lib/napi_platforms.py` owns the same table for the build side; a test
 * keeps the two in step.
 */
const TRIPLE_TO_SUFFIX: Record<string, string> = {
  "x86_64-unknown-linux-gnu": "linux-x64-gnu",
  "aarch64-unknown-linux-gnu": "linux-arm64-gnu",
  "x86_64-unknown-linux-musl": "linux-x64-musl",
  "aarch64-unknown-linux-musl": "linux-arm64-musl",
  "x86_64-apple-darwin": "darwin-x64",
  "aarch64-apple-darwin": "darwin-arm64",
  "x86_64-pc-windows-msvc": "win32-x64-msvc",
  "aarch64-pc-windows-msvc": "win32-arm64-msvc",
};

function supportedTargets(): string[] {
  const triples: string[] = pkg.napi.targets;
  return triples.map((triple) => {
    const suffix = TRIPLE_TO_SUFFIX[triple];
    if (suffix === undefined) {
      throw new Error(
        `Unknown napi target ${triple}. Add it to TRIPLE_TO_SUFFIX here and to PLATFORM_SUFFIXES in tools/_lib/napi_platforms.py.`,
      );
    }
    return suffix;
  });
}

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
    writeFileSync(
      resolve(import.meta.dir, "dist/supported-targets.json"),
      `${JSON.stringify(supportedTargets(), null, 2)}\n`,
    );
  },
});
