/// <reference path="./wasm-bindgen.d.ts" />
import { existsSync, readFileSync } from "node:fs";
import {
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

  constructor(code: string, message: string) {
    super(message);
    this.name = "PolylibError";
    this.code = code;
  }
}

let initialized = false;

/** Initialize the WebAssembly module explicitly (useful in browser and edge runtimes). */
export function initWasm(module: BufferSource | WebAssembly.Module): void {
  initSync({ module });
  initialized = true;
}

function ensureWasmLoaded(): void {
  if (initialized) {
    return;
  }
  const distWasm = new URL("./polylib_wasm_bg.wasm", import.meta.url);
  const devWasm = new URL("./wasm/polylib_wasm_bg.wasm", import.meta.url);
  const wasmUrl = existsSync(distWasm) ? distWasm : devWasm;
  initWasm(readFileSync(wasmUrl));
}

function toPolylibError(thrown: unknown): PolylibError {
  const raw =
    typeof thrown === "string" ? thrown : thrown instanceof Error ? thrown.message : String(thrown);
  const sep = raw.indexOf(": ");
  if (sep > 0) {
    return new PolylibError(raw.slice(0, sep), raw.slice(sep + 2));
  }
  return new PolylibError("invalid_input", raw);
}

/** Return the version embedded in the compiled `polylib-wasm` binary. */
export function getWasmVersion(): string {
  ensureWasmLoaded();
  return wasmVersion();
}

/** Normalize free-form text into a lowercase hyphen-separated ASCII slug. */
export function normalizeSlug(input: string): string {
  ensureWasmLoaded();
  try {
    return wasmNormalizeSlug(input);
  } catch (thrown) {
    throw toPolylibError(thrown);
  }
}

/** Summarize a non-empty array of finite floating-point scores. */
export function summarizeScores(values: readonly number[]): ScoreSummary {
  ensureWasmLoaded();
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
