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

  constructor(code: string, message: string, options?: { cause?: unknown }) {
    super(message, options);
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

// A backend signals a domain error as `code: message`. Anything else that a
// backend throws is a bug or an environment failure, not a new error code.
const CODE_PATTERN = /^[a-z][a-z0-9_]*$/;

function isCodedError(value: unknown): value is CodedError {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.code === "string" &&
    CODE_PATTERN.test(candidate.code) &&
    typeof candidate.message === "string"
  );
}

/** Convert an error thrown by either backend into a canonical `PolylibError`. */
export function toPolylibError(thrown: unknown): PolylibError {
  if (thrown instanceof PolylibError) {
    return thrown;
  }
  if (isCodedError(thrown)) {
    return new PolylibError(thrown.code, thrown.message, { cause: thrown });
  }
  const raw =
    typeof thrown === "string" ? thrown : thrown instanceof Error ? thrown.message : String(thrown);
  const sep = raw.indexOf(": ");
  // Only a well-formed code prefix names an error. Without this guard a message
  // like "NaN detected in scores: ..." would claim the code "NaN detected in
  // scores", which is a diagnostic string masquerading as API surface.
  if (sep > 0) {
    const code = raw.slice(0, sep);
    if (CODE_PATTERN.test(code)) {
      return new PolylibError(code, raw.slice(sep + 2), { cause: thrown });
    }
  }
  return new PolylibError("invalid_input", raw, { cause: thrown });
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
