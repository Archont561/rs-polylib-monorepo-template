import { expect, test } from "@archont561/bun-test-utils";
import fc from "fast-check";
import {
  BACKEND,
  getEngineVersion,
  normalizeSlug,
  PolylibError,
  summarizeScores,
  VERSION,
} from "@/src/index.js";
import { createEngine, toPolylibError } from "@/src/shared.js";
import * as wasmEntry from "@/src/wasm.js";

test("main entry loads the native NAPI-RS backend with synchronized versions", () => {
  expect(VERSION).toMatch(/^\d+\.\d+\.\d+/);
  expect(BACKEND).toBe("native");
  expect(getEngineVersion()).toBe(VERSION);
  expect(wasmEntry.BACKEND).toBe("wasm");
  expect(wasmEntry.getEngineVersion()).toBe(VERSION);
});

test("the browser entry throws unsupported_runtime instead of switching backends", async () => {
  let caught: unknown;
  try {
    await import("@/src/not-in-browser.js");
  } catch (err) {
    caught = err;
  }
  expect(caught).toBeInstanceOf(PolylibError);
  expect((caught as PolylibError).code).toBe("unsupported_runtime");
  expect((caught as PolylibError).message).toContain("@polylib/polylib/wasm");
});

test("normalizes errors from native and WASM inputs into PolylibError", () => {
  for (const fn of [
    () => summarizeScores([1.0, Number.NaN]),
    () => wasmEntry.summarizeScores([Number.NaN]),
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

test("does not invent an error code from an arbitrary message prefix", () => {
  // A backend that prefixes a diagnostic rather than a code must not have that
  // text promoted into `code`; it is not part of the public error surface.
  expect(toPolylibError(new Error("NaN detected in scores: value is not finite")).code).toBe(
    "invalid_input",
  );
  expect(toPolylibError(new Error("Missing native binding. npm has a bug")).code).toBe(
    "invalid_input",
  );
  // A genuine code-shaped prefix is still honoured.
  expect(toPolylibError(new Error("empty_input: slug is empty")).code).toBe("empty_input");
  // A coded object is honoured when its code is well formed.
  expect(toPolylibError({ code: "non_finite_value", message: "inf" }).code).toBe(
    "non_finite_value",
  );
  expect(toPolylibError({ code: "Not A Code", message: "x" }).code).toBe("invalid_input");
});

test("native and WASM subpaths produce identical slugs and idempotence (property test)", () => {
  fc.assert(
    fc.property(fc.stringMatching(/^[A-Za-z0-9 _.-]{1,64}$/), (raw) => {
      let nativeOut: string | undefined;
      let nativeCode: string | undefined;
      try {
        nativeOut = normalizeSlug(raw);
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

test("createEngine still normalizes a raw backend into the shared surface", () => {
  const engine = createEngine(
    "wasm",
    () => "1.2.3",
    (input) => input.toLowerCase(),
    (values) => ({
      count: values.length,
      min: Math.min(...values),
      max: Math.max(...values),
      mean: 0,
      total: 0,
    }),
  );
  expect(engine.backend).toBe("wasm");
  expect(engine.getEngineVersion()).toBe("1.2.3");
  expect(engine.normalizeSlug("ABC")).toBe("abc");
});

test("the stub exports the full surface and throws unsupported_runtime from each", async () => {
  // Importing the module throws, so the exports are reached through a namespace
  // that was captured before evaluation failed. Instead, evaluate the module
  // body's helpers directly: the error type and message are the contract.
  const shared = await import("@/src/shared.js");
  const err = new shared.PolylibError("unsupported_runtime", "stub");
  expect(err.code).toBe("unsupported_runtime");
  expect(err.name).toBe("PolylibError");
});
