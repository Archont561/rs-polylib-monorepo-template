import { existsSync, readFileSync } from "node:fs";
import { version } from "@/package.json" with { type: "json" };
import { initWasm, isInitialized, setAutoInitializer, type WasmInput } from "./core.js";

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
 * Read the compiled `.wasm` from disk.
 *
 * The build copies it next to the entry; the second path serves a source
 * checkout that has not been bundled yet.
 */
function readWasm(): BufferSource {
  const distWasm = new URL("./polylib_wasm_bg.wasm", import.meta.url);
  const devWasm = new URL("./wasm/polylib_wasm_bg.wasm", import.meta.url);
  return readFileSync(existsSync(distWasm) ? distWasm : devWasm);
}

/**
 * Load the module.
 *
 * Node reads the file synchronously, so this resolves as soon as it is called
 * and exists so that code written against the browser entry also runs here.
 */
export async function initWasmAsync(input?: WasmInput): Promise<void> {
  if (isInitialized()) {
    return;
  }
  // Node can load a module or bytes handed to it, but it has no URL fetcher, so
  // an omitted argument falls back to the file next to this module.
  if (input !== undefined) {
    initWasm(input as BufferSource | WebAssembly.Module);
    return;
  }
  initWasm(readWasm());
}

// On Node the module loads on first use, which is what callers relying on the
// previous behaviour expect. Registering rather than calling keeps `import` from
// performing a file read before anything asks for it.
setAutoInitializer(() => {
  if (!isInitialized()) {
    initWasm(readWasm());
  }
});
