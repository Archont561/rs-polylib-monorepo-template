/** Active runtime engine backing `@polylib/polylib`. */
export type BackendKind = "native" | "wasm";

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

/** Normalized runtime adapter implemented by both native and WASM backends. */
export interface PolylibEngine {
  readonly backend: BackendKind;
  getEngineVersion(): string;
  normalizeSlug(input: string): string;
  summarizeScores(values: readonly number[]): ScoreSummary;
}

interface CodedError {
  readonly code: string;
  readonly message: string;
}

function isCodedError(value: unknown): value is CodedError {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return typeof candidate.code === "string" && typeof candidate.message === "string";
}

/** Convert an error thrown by either backend into a canonical `PolylibError`. */
export function toPolylibError(thrown: unknown): PolylibError {
  if (thrown instanceof PolylibError) {
    return thrown;
  }
  if (isCodedError(thrown)) {
    return new PolylibError(thrown.code, thrown.message);
  }
  const raw =
    typeof thrown === "string" ? thrown : thrown instanceof Error ? thrown.message : String(thrown);
  const sep = raw.indexOf(": ");
  if (sep > 0) {
    return new PolylibError(raw.slice(0, sep), raw.slice(sep + 2));
  }
  return new PolylibError("invalid_input", raw);
}

/** Wrap raw backend functions with canonical `PolylibError` normalization. */
export function createEngine(
  backend: BackendKind,
  rawGetVersion: () => string,
  rawNormalizeSlug: (input: string) => string,
  rawSummarizeScores: (values: readonly number[]) => ScoreSummary,
): PolylibEngine {
  return {
    backend,
    getEngineVersion(): string {
      return rawGetVersion();
    },
    normalizeSlug(input: string): string {
      try {
        return rawNormalizeSlug(input);
      } catch (thrown) {
        throw toPolylibError(thrown);
      }
    },
    summarizeScores(values: readonly number[]): ScoreSummary {
      try {
        const summary = rawSummarizeScores(values);
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
    },
  };
}

/** Prefer the native NAPI-RS engine and fall back cleanly to WebAssembly if unavailable. */
export async function selectEngine(
  loadNative: () => Promise<PolylibEngine>,
  loadWasm: () => Promise<PolylibEngine>,
): Promise<PolylibEngine> {
  try {
    const nativeEngine = await loadNative();
    nativeEngine.getEngineVersion();
    return nativeEngine;
  } catch {
    return loadWasm();
  }
}
