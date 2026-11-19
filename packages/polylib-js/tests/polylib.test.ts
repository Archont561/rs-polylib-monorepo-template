import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, test } from "@archont561/bun-test-utils";
import fc from "fast-check";
import {
  getNativeVersion,
  normalizeSlug,
  PolylibError,
  summarizeScores,
  VERSION,
} from "@/src/index.js";

test("exports synchronized package and native NAPI-RS addon versions", () => {
  expect(VERSION).toMatch(/^\d+\.\d+\.\d+/);
  expect(getNativeVersion()).toBe(VERSION);
});

test("rejects NaN and Infinity with typed non_finite_value code", () => {
  let caught: unknown;
  try {
    summarizeScores([1.0, Number.NaN]);
  } catch (err) {
    caught = err;
  }
  expect(caught).toBeInstanceOf(PolylibError);
  expect((caught as PolylibError).code).toBe("non_finite_value");
});

test("slug normalization is idempotent (property test)", () => {
  fc.assert(
    fc.property(fc.stringMatching(/^[A-Za-z0-9 _.-]{1,64}$/), (raw) => {
      try {
        const slug = normalizeSlug(raw);
        expect(normalizeSlug(slug)).toBe(slug);
        expect(slug.includes("--")).toBe(false);
      } catch (err) {
        expect(err).toBeInstanceOf(PolylibError);
      }
    }),
    { numRuns: 100 },
  );
});

test("builds a missing_native_binding error that names the platform", async () => {
  // The loader resolves `./native/binding.cjs` relative to the module, so a copy
  // of the built module in a directory with no loader is exactly the state of a
  // consumer whose platform package npm skipped. Bundling it into its own
  // directory reproduces that without touching the real package.
  const dir = mkdtempSync(join(tmpdir(), "polylib-js-noloader-"));
  try {
    const bundled = await Bun.build({
      entrypoints: [require.resolve("@/src/native.ts")],
      target: "node",
      format: "esm",
    });
    const outfile = join(dir, "native.mjs");
    const [artifact] = bundled.outputs;
    if (artifact === undefined) {
      throw new Error("bun build produced no output");
    }
    writeFileSync(outfile, await artifact.text());
    const isolated = (await import(outfile)) as typeof import("@/src/native.js");

    expect(() => isolated.normalizeSlug("Hi!")).toThrow(isolated.PolylibError);
    let caught: unknown;
    try {
      isolated.normalizeSlug("Hi!");
    } catch (err) {
      caught = err;
    }
    expect((caught as { code: string }).code).toBe("missing_native_binding");
    expect((caught as Error).message).toContain(process.platform);
    expect((caught as Error).message).toContain(process.arch);
    expect((caught as { cause?: unknown }).cause).toBeDefined();
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("toPolylibError preserves a coded error and its cause", async () => {
  const native = await import("@/src/native.js");
  const coded = new Error("empty_input: slug is empty");
  const wrapped = native.toPolylibError(coded);
  expect(wrapped.code).toBe("empty_input");
  expect(wrapped.message).toBe("slug is empty");
  expect(wrapped.cause).toBe(coded);

  // A diagnostic sentence must not become an error code.
  expect(native.toPolylibError(new Error("NaN detected: not finite")).code).toBe("invalid_input");
  expect(native.toPolylibError("plain").code).toBe("invalid_input");
  expect(native.toPolylibError(7).code).toBe("invalid_input");
  const already = new native.PolylibError("kept", "msg");
  expect(native.toPolylibError(already)).toBe(already);
});

test("the platform probe reports a concrete os-arch-libc triple", async () => {
  const native = await import("@/src/native.js");
  expect(native.detectedPlatform()).toMatch(/^(linux|darwin|win32)-[a-z0-9]+/);
  expect(native.detectedPlatform()).toContain(process.arch);
});

test("supportedTargets lists every configured napi target", async () => {
  const native = await import("@/src/native.js");
  const targets = native.supportedTargets();
  expect(targets.length).toBeGreaterThanOrEqual(8);
  expect(targets).toContain("linux-x64-gnu");
  expect(targets).toContain("win32-arm64-msvc");
  expect(targets).toContain("linux-x64-musl");
});

test("detectedPlatform names the libc and the msvc ABI", async () => {
  const native = await import("@/src/native.js");
  expect(native.detectedPlatform("linux", "x64")).toMatch(/^linux-x64-(gnu|musl)$/);
  expect(native.detectedPlatform("win32", "arm64")).toBe("win32-arm64-msvc");
  expect(native.detectedPlatform("darwin", "arm64")).toBe("darwin-arm64");
});

test("the missing-binding message explains what to install instead", async () => {
  const native = await import("@/src/native.js");
  const cause = new Error("Cannot find native binding");
  const err = native.missingBindingError(cause);
  expect(err).toBeInstanceOf(native.PolylibError);
  expect(err.code).toBe("missing_native_binding");
  expect(err.cause).toBe(cause);
  expect(err.message).toContain(process.platform);
  expect(err.message).toContain("Supported platforms:");
  expect(err.message).toContain("@polylib/polylib-wasm");
  expect(err.message).toContain('"@polylib/polylib/wasm"');
});
