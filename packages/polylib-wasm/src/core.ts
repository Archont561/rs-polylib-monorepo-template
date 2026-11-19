/// <reference path="./wasm-bindgen.d.ts" />
import wasmInit, {
  initSync,
  wasmNormalizeSlug,
  wasmSummarizeScores,
  wasmVersion,
} from "./wasm/polylib_wasm.js";

/** Summary statistics computed over a non-empty array of finite scores. */
export interface ScoreSummary {
  readonly count: number;
  readonly min: number;
  readonly max: number;
  readonly mean: number;
  readonly total: number;
}

/** Typed error thrown when `polylib-core` rejects an invalid input. */
export class PolylibError extends Error {
  readonly code: string;

  constructor(code: string, message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = "PolylibError";
    this.code = code;
  }
}

const CODE_PATTERN = /^[a-z][a-z0-9_]*$/;

let initialized = false;

// Set by the Node entry, whose `.wasm` file can be read synchronously. The
// browser entry leaves this unset: there is no way to fetch asynchronously from
// inside a synchronous call, so the caller must await `initWasmAsync()` first.
let autoInitializer: (() => void) | undefined;

/** Register a callback that initializes the module on first use. */
export function setAutoInitializer(init: () => void): void {
  autoInitializer = init;
}

/** Initialize the WebAssembly module from an already-loaded module or bytes. */
export function initWasm(module: BufferSource | WebAssembly.Module): void {
  initSync({ module });
  initialized = true;
}

/** Report whether an API call can proceed. */
export function isInitialized(): boolean {
  return initialized;
}

/** Record that the module is loaded, for entries that initialize it themselves. */
export function markInitialized(): void {
  initialized = true;
}

/** Inputs accepted by wasm-bindgen's `--target web` initializer. */
export type WasmInput = URL | string | Response | BufferSource | WebAssembly.Module;

/**
 * Run wasm-bindgen's own initializer.
 *
 * `--target web` generates a function that fetches `polylib_wasm_bg.wasm` from
 * the module URL, or accepts an explicit input. It is async and has no Node
 * dependency, so the browser entry is the only place that uses it.
 */
export async function wasmDefaultInit(input?: WasmInput): Promise<void> {
  await wasmInit(input as Parameters<typeof wasmInit>[0]);
}

export function toPolylibError(thrown: unknown): PolylibError {
  if (thrown instanceof PolylibError) {
    return thrown;
  }
  const raw =
    typeof thrown === "string" ? thrown : thrown instanceof Error ? thrown.message : String(thrown);
  const sep = raw.indexOf(": ");
  if (sep > 0) {
    const code = raw.slice(0, sep);
    if (CODE_PATTERN.test(code)) {
      return new PolylibError(code, raw.slice(sep + 2), { cause: thrown });
    }
  }
  return new PolylibError("invalid_input", raw, { cause: thrown });
}

function requireInitialized(): void {
  if (initialized) {
    return;
  }
  autoInitializer?.();
  if (!initialized) {
    throw new PolylibError(
      "wasm_not_initialized",
      "Call `await initWasmAsync()` (or `initWasm(bytes)`) before using the WebAssembly build.",
    );
  }
}

/** Return the version embedded in the compiled `polylib-wasm` binary. */
export function getWasmVersion(): string {
  requireInitialized();
  return wasmVersion();
}

/** Normalize free-form text into a lowercase hyphen-separated ASCII slug. */
export function normalizeSlug(input: string): string {
  requireInitialized();
  try {
    return wasmNormalizeSlug(input);
  } catch (thrown) {
    throw toPolylibError(thrown);
  }
}

/** Summarize a non-empty array of finite floating-point scores. */
export function summarizeScores(values: readonly number[]): ScoreSummary {
  requireInitialized();
  try {
    const summary = wasmSummarizeScores(Float64Array.from(values)) as ScoreSummary;
    return {
      count: summary.count,
      min: summary.min,
      max: summary.max,
      mean: summary.mean,
      total: summary.total,
    };
  } catch (thrown) {
    throw toPolylibError(thrown);
  }
}
