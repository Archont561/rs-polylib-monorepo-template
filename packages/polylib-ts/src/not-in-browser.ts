import { version } from "@/package.json" with { type: "json" };
import { type BackendKind, PolylibError, type ScoreSummary } from "./shared.js";

// Resolved by bundlers and runtimes that are not Node or Bun: the `default`
// export condition maps `"."` here. Every export is present so that a type
// check, an editor, and a bundler all resolve the same shape, but touching the
// module throws. Failing at import is the point: reaching this file means the
// caller picked an entry point that cannot work, and a silent switch to a
// different backend would hide that.
export const UNSUPPORTED_RUNTIME_MESSAGE =
  '@polylib/polylib needs Node.js or Bun (native addon). In browsers and edge runtimes use "@polylib/polylib/wasm" (npm i @polylib/polylib-wasm).';

export const VERSION: string = version;

/** Never reachable here: the module throws while being evaluated. */
export const BACKEND: BackendKind = "native";

export { type BackendKind, PolylibError, type ScoreSummary };

/** Throw `unsupported_runtime`; this entry point has no engine. */
export function getEngineVersion(): string {
  throw new PolylibError("unsupported_runtime", UNSUPPORTED_RUNTIME_MESSAGE);
}

/** Throw `unsupported_runtime`; this entry point has no engine. */
export function normalizeSlug(_input: string): string {
  throw new PolylibError("unsupported_runtime", UNSUPPORTED_RUNTIME_MESSAGE);
}

/** Throw `unsupported_runtime`; this entry point has no engine. */
export function summarizeScores(_values: readonly number[]): ScoreSummary {
  throw new PolylibError("unsupported_runtime", UNSUPPORTED_RUNTIME_MESSAGE);
}

// Throwing at module evaluation is intended: a caller that cannot import the
// module can never reach the functions above, so this is the only way to fail at
// the point of the mistake rather than on the first API call.
throw new PolylibError("unsupported_runtime", UNSUPPORTED_RUNTIME_MESSAGE);
