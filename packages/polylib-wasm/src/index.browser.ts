import { version } from "@/package.json" with { type: "json" };
import { isInitialized, markInitialized, type WasmInput, wasmDefaultInit } from "./core.js";

export const VERSION: string = version;

export {
  getWasmVersion,
  initWasm,
  normalizeSlug,
  PolylibError,
  type ScoreSummary,
  summarizeScores,
} from "./core.js";

export type { WasmInput };

/**
 * Fetch and initialize the WebAssembly module.
 *
 * With no argument this uses the wasm-bindgen `--target web` initializer, which
 * fetches the `.wasm` emitted next to this module. Anything else is passed
 * through, so a bundler-rewritten URL, a `Response`, or raw bytes all work.
 *
 * There is deliberately no top-level `await`: Vite's default browser target
 * rejects it, and a synchronous `import` would mean a network fetch at module
 * evaluation.
 */
export async function initWasmAsync(input?: WasmInput): Promise<void> {
  if (isInitialized()) {
    return;
  }
  await wasmDefaultInit(input);
  markInitialized();
}
