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
