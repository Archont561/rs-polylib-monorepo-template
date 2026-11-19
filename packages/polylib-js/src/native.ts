import { existsSync, readFileSync } from "node:fs";
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

  constructor(code: string, message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = "PolylibError";
    this.code = code;
  }
}

interface NativeBinding {
  nativeVersion(): string;
  normalizeSlug(input: string): string;
  summarizeScores(values: number[]): ScoreSummary;
}

// Hand-maintained copy of `napi.targets`, used only to word the error below.
// `bindings build --target napi` also writes `dist/supported-targets.json`; this
// fallback keeps the message useful in a source checkout, where it is absent.
const FALLBACK_TARGETS: readonly string[] = [
  "linux-x64-gnu",
  "linux-arm64-gnu",
  "linux-x64-musl",
  "linux-arm64-musl",
  "darwin-x64",
  "darwin-arm64",
  "win32-x64-msvc",
  "win32-arm64-msvc",
];

const CODE_PATTERN = /^[a-z][a-z0-9_]*$/;

export function detectedPlatform(
  platform: NodeJS.Platform = process.platform,
  arch: string = process.arch,
): string {
  if (platform === "linux") {
    // glibc reports its version at runtime; a musl host leaves it undefined.
    return `${platform}-${arch}-${hasGlibc() ? "gnu" : "musl"}`;
  }
  if (platform === "win32") {
    return `${platform}-${arch}-msvc`;
  }
  return `${platform}-${arch}`;
}

export function supportedTargets(): readonly string[] {
  try {
    const path = fileURLToPath(new URL("./supported-targets.json", import.meta.url));
    const parsed: unknown = JSON.parse(readFileSync(path, "utf8"));
    if (Array.isArray(parsed) && parsed.every((item) => typeof item === "string")) {
      return parsed as string[];
    }
  } catch {
    // No build output in a source checkout; the fallback list is accurate there.
  }
  return FALLBACK_TARGETS;
}

/** Whether this Linux host links glibc, which decides the `gnu`/`musl` suffix. */
function hasGlibc(): boolean {
  const report = process.report?.getReport() as
    | { header?: { glibcVersionRuntime?: string } }
    | undefined;
  return report?.header?.glibcVersionRuntime !== undefined;
}

/** Build the error a consumer sees when no addon matches their platform. */
export function missingBindingError(cause: unknown): PolylibError {
  const message = [
    `@polylib/polylib-js has no native binding for ${detectedPlatform()}.`,
    `Supported platforms: ${supportedTargets().join(", ")}.`,
    "If your platform is not listed, use the WebAssembly build instead:",
    "  npm i @polylib/polylib-wasm",
    '  import * as polylib from "@polylib/polylib/wasm";',
  ].join("\n");
  return new PolylibError("missing_native_binding", message, { cause });
}

export function toPolylibError(thrown: unknown): PolylibError {
  if (thrown instanceof PolylibError) {
    return thrown;
  }
  if (thrown instanceof Error) {
    // Only a genuine `code: message` prefix becomes a code. Anything else is an
    // untyped failure from the binding, and inventing a code from it would make
    // a diagnostic string look like part of the API.
    const sep = thrown.message.indexOf(": ");
    if (sep > 0) {
      const code = thrown.message.slice(0, sep);
      if (CODE_PATTERN.test(code)) {
        return new PolylibError(code, thrown.message.slice(sep + 2), { cause: thrown });
      }
    }
    return new PolylibError("invalid_input", thrown.message, { cause: thrown });
  }
  return new PolylibError("invalid_input", String(thrown), { cause: thrown });
}

const require = createRequire(import.meta.url);
let cachedBinding: NativeBinding | undefined;

function loadNativeBinding(): NativeBinding {
  if (cachedBinding !== undefined) {
    return cachedBinding;
  }
  const bindingPath = fileURLToPath(new URL("./native/binding.cjs", import.meta.url));
  if (!existsSync(bindingPath)) {
    throw missingBindingError(new Error(`Missing generated NAPI-RS loader at ${bindingPath}.`));
  }
  try {
    // The loader resolves the per-platform package, so it can exist while this
    // host's addon does not: npm skips an optional dependency whose `os` or
    // `cpu` does not match. Wrapping the require is what makes that visible as
    // a platform-named error instead of a raw loader message.
    cachedBinding = require(bindingPath) as NativeBinding;
  } catch (cause) {
    throw missingBindingError(cause);
  }
  return cachedBinding;
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
