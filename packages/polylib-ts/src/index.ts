import { version } from "@/package.json" with { type: "json" };
import {
  type BackendKind,
  createEngine,
  PolylibError,
  type ScoreSummary,
  selectEngine,
} from "./shared.js";

const activeEngine = await selectEngine(
  async () => {
    const mod = await import("@polylib/polylib-js");
    return createEngine("native", mod.getNativeVersion, mod.normalizeSlug, mod.summarizeScores);
  },
  async () => {
    const mod = await import("@polylib/polylib-wasm");
    return createEngine("wasm", mod.getWasmVersion, mod.normalizeSlug, mod.summarizeScores);
  },
);

export const VERSION: string = version;
export const BACKEND: BackendKind = activeEngine.backend;

export { type BackendKind, PolylibError, type ScoreSummary };

/** Return the version embedded in the active native or WebAssembly engine. */
export function getEngineVersion(): string {
  return activeEngine.getEngineVersion();
}

/** Normalize free-form text into a lowercase hyphen-separated ASCII slug. */
export function normalizeSlug(input: string): string {
  return activeEngine.normalizeSlug(input);
}

/** Summarize a non-empty array of finite floating-point scores. */
export function summarizeScores(values: readonly number[]): ScoreSummary {
  return activeEngine.summarizeScores(values);
}
