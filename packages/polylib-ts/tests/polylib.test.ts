import { expect, test } from "@archont561/bun-test-utils";
import fc from "fast-check";
import * as browserEntry from "@/src/browser.js";
import {
  BACKEND,
  getEngineVersion,
  normalizeSlug,
  PolylibError,
  summarizeScores,
  VERSION,
} from "@/src/index.js";
import * as nativeEntry from "@/src/native.js";
import { createEngine, selectEngine, toPolylibError } from "@/src/shared.js";
import * as wasmEntry from "@/src/wasm.js";

test("auto-selects native NAPI-RS backend with synchronized versions", () => {
  expect(VERSION).toMatch(/^\d+\.\d+\.\d+/);
  expect(BACKEND).toBe("native");
  expect(getEngineVersion()).toBe(VERSION);
  expect(nativeEntry.BACKEND).toBe("native");
  expect(nativeEntry.getEngineVersion()).toBe(VERSION);
  expect(wasmEntry.BACKEND).toBe("wasm");
  expect(wasmEntry.getEngineVersion()).toBe(VERSION);
  expect(browserEntry.BACKEND).toBe("wasm");
  expect(browserEntry.getEngineVersion()).toBe(VERSION);
});

test("falls back cleanly to WebAssembly when native addon is unavailable", async () => {
  const fallback = await selectEngine(
    () => Promise.reject(new Error("native addon unavailable")),
    () =>
      Promise.resolve(
        createEngine(
          "wasm",
          wasmEntry.getEngineVersion,
          wasmEntry.normalizeSlug,
          wasmEntry.summarizeScores,
        ),
      ),
  );
  expect(fallback.backend).toBe("wasm");
  expect(fallback.getEngineVersion()).toBe(VERSION);
  expect(fallback.normalizeSlug("Fallback Test!")).toBe("fallback-test");
  expect(fallback.summarizeScores([2, 4]).mean).toBe(3);
});

test("normalizes errors from native, WASM, and fallback inputs into PolylibError", () => {
  for (const fn of [
    () => summarizeScores([1.0, Number.NaN]),
    () => nativeEntry.summarizeScores([Number.POSITIVE_INFINITY]),
    () => wasmEntry.summarizeScores([Number.NaN]),
    () => browserEntry.summarizeScores([Number.NEGATIVE_INFINITY]),
  ]) {
    let caught: unknown;
    try {
      fn();
    } catch (err) {
      caught = err;
    }
    expect(caught).toBeInstanceOf(PolylibError);
    expect((caught as PolylibError).code).toBe("non_finite_value");
  }

  const existing = new PolylibError("already_typed", "ok");
  expect(toPolylibError(existing)).toBe(existing);
  expect(toPolylibError("custom_code: detailed reason").code).toBe("custom_code");
  expect(toPolylibError(new Error("plain failure")).code).toBe("invalid_input");
  expect(toPolylibError(42).code).toBe("invalid_input");
});

test("native and WASM subpaths produce identical slugs and idempotence (property test)", () => {
  fc.assert(
    fc.property(fc.stringMatching(/^[A-Za-z0-9 _.-]{1,64}$/), (raw) => {
      let nativeOut: string | undefined;
      let nativeCode: string | undefined;
      try {
        nativeOut = nativeEntry.normalizeSlug(raw);
      } catch (err) {
        expect(err).toBeInstanceOf(PolylibError);
        nativeCode = (err as PolylibError).code;
      }

      let wasmOut: string | undefined;
      let wasmCode: string | undefined;
      try {
        wasmOut = wasmEntry.normalizeSlug(raw);
      } catch (err) {
        expect(err).toBeInstanceOf(PolylibError);
        wasmCode = (err as PolylibError).code;
      }

      expect(nativeOut).toBe(wasmOut);
      expect(nativeCode).toBe(wasmCode);
      if (nativeOut !== undefined) {
        expect(normalizeSlug(nativeOut)).toBe(nativeOut);
        expect(nativeOut.includes("--")).toBe(false);
      }
    }),
    { numRuns: 100 },
  );
});
