import {
  getNativeVersion,
  normalizeSlug as rawNormalizeSlug,
  summarizeScores as rawSummarizeScores,
} from "@polylib/polylib-js";
import { version } from "@/package.json" with { type: "json" };
import { type BackendKind, createEngine, PolylibError, type ScoreSummary } from "./shared.js";

const engine = createEngine("native", getNativeVersion, rawNormalizeSlug, rawSummarizeScores);

export const VERSION: string = version;
export const BACKEND: BackendKind = "native";

export { type BackendKind, PolylibError, type ScoreSummary };

/** Return the version embedded in the compiled native NAPI-RS addon. */
export function getEngineVersion(): string {
  return engine.getEngineVersion();
}

/** Normalize free-form text into a lowercase hyphen-separated ASCII slug via NAPI-RS. */
export function normalizeSlug(input: string): string {
  return engine.normalizeSlug(input);
}

/** Summarize a non-empty array of finite floating-point scores via NAPI-RS. */
export function summarizeScores(values: readonly number[]): ScoreSummary {
  return engine.summarizeScores(values);
}
