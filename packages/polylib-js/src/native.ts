import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

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

interface NativeBinding {
  nativeVersion(): string;
  normalizeSlug(input: string): string;
  summarizeScores(values: number[]): ScoreSummary;
}

const require = createRequire(import.meta.url);
let cachedBinding: NativeBinding | undefined;

function loadNativeBinding(): NativeBinding {
  if (cachedBinding !== undefined) {
    return cachedBinding;
  }
  const bindingUrl = new URL("./native/binding.cjs", import.meta.url);
  const bindingPath = fileURLToPath(bindingUrl);
  if (!existsSync(bindingPath)) {
    throw new PolylibError(
      "missing_native_binding",
      `Missing compiled NAPI-RS addon at ${bindingPath}. Run \`pixi run -e full tools run bindings build --target napi\`.`,
    );
  }
  cachedBinding = require(bindingPath) as NativeBinding;
  return cachedBinding;
}

function toPolylibError(thrown: unknown): PolylibError {
  if (thrown instanceof PolylibError) {
    return thrown;
  }
  const raw =
    typeof thrown === "string" ? thrown : thrown instanceof Error ? thrown.message : String(thrown);
  const sep = raw.indexOf(": ");
  if (sep > 0) {
    return new PolylibError(raw.slice(0, sep), raw.slice(sep + 2));
  }
  return new PolylibError("invalid_input", raw);
}

/** Return the version embedded in the compiled native `polylib-js` addon. */
export function getNativeVersion(): string {
  return loadNativeBinding().nativeVersion();
}

/** Normalize free-form text into a lowercase hyphen-separated ASCII slug. */
export function normalizeSlug(input: string): string {
  try {
    return loadNativeBinding().normalizeSlug(input);
  } catch (thrown) {
    throw toPolylibError(thrown);
  }
}

/** Summarize a non-empty array of finite floating-point scores. */
export function summarizeScores(values: readonly number[]): ScoreSummary {
  try {
    const summary = loadNativeBinding().summarizeScores(Array.from(values));
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
