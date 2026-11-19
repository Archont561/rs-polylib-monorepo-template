import {
  getWasmVersion,
  initWasm,
  initWasmAsync,
  normalizeSlug as rawNormalizeSlug,
  summarizeScores as rawSummarizeScores,
} from "@polylib/polylib-wasm";
import { version } from "@/package.json" with { type: "json" };
import { type BackendKind, createEngine, PolylibError, type ScoreSummary } from "./shared.js";

const engine = createEngine("wasm", getWasmVersion, rawNormalizeSlug, rawSummarizeScores);

export const VERSION: string = version;
export const BACKEND: BackendKind = "wasm";

export { type BackendKind, initWasm, initWasmAsync, PolylibError, type ScoreSummary };

/** Return the version embedded in the compiled WebAssembly module. */
export function getEngineVersion(): string {
  return engine.getEngineVersion();
}

/** Normalize free-form text into a lowercase hyphen-separated ASCII slug via WebAssembly. */
export function normalizeSlug(input: string): string {
  return engine.normalizeSlug(input);
}

/** Summarize a non-empty array of finite floating-point scores via WebAssembly. */
export function summarizeScores(values: readonly number[]): ScoreSummary {
  return engine.summarizeScores(values);
}
