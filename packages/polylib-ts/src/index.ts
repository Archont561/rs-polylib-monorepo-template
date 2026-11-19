import * as napi from "@polylib/polylib-js";
import { version } from "@/package.json" with { type: "json" };
import { type BackendKind, createEngine, PolylibError, type ScoreSummary } from "./shared.js";

// The main entry is native-only and does this eagerly at module load, with no
// top-level `await`. That keeps two consumer paths working: `require()` of this
// package (Node >= 20.19 can require an ESM graph, but not one with top-level
// await) and `esbuild --format=cjs`. Browsers and edge runtimes resolve to
// `./not-in-browser.js` through the `default` export condition instead.
const engine = createEngine(
  "native",
  napi.getNativeVersion,
  napi.normalizeSlug,
  napi.summarizeScores,
);

export const VERSION: string = version;

/** The backend behind the main entry. Always `"native"`; kept for diagnostics. */
export const BACKEND: BackendKind = "native";

export { type BackendKind, PolylibError, type ScoreSummary };

/** Return the version embedded in the active native engine. */
export function getEngineVersion(): string {
  return engine.getEngineVersion();
}

/** Normalize free-form text into a lowercase hyphen-separated ASCII slug. */
export function normalizeSlug(input: string): string {
  return engine.normalizeSlug(input);
}

/** Summarize a non-empty array of finite floating-point scores. */
export function summarizeScores(values: readonly number[]): ScoreSummary {
  return engine.summarizeScores(values);
}
