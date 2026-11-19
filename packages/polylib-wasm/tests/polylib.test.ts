import { expect, test } from "@archont561/bun-test-utils";
import fc from "fast-check";
import {
  getWasmVersion,
  normalizeSlug,
  PolylibError,
  summarizeScores,
  VERSION,
} from "@/src/index.node.js";

test("exports synchronized package and WASM versions", () => {
  expect(VERSION).toMatch(/^\d+\.\d+\.\d+/);
  expect(getWasmVersion()).toBe(VERSION);
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

// A browser exposes only the browser entry, so nothing has initialized the
// module when the first call arrives. The suite runs the Node entry too, which
// auto-initializes the shared module in this realm, so the guard is asserted
// against a module instance that has never been initialized: `core.ts` keyed by
// a query string loads a separate instance with its own state.
test("calling before initialization reports wasm_not_initialized", async () => {
  const pristine = await import("@/src/core.js?pristine=1");
  expect(pristine.isInitialized()).toBe(false);
  let caught: unknown;
  try {
    pristine.normalizeSlug("Hi!");
  } catch (err) {
    caught = err;
  }
  expect(caught).toBeInstanceOf(pristine.PolylibError);
  expect((caught as { code: string }).code).toBe("wasm_not_initialized");
  expect((caught as Error).message).toContain("initWasmAsync");
});

test("the browser entry accepts an explicitly initialized module", async () => {
  const browser = await import("@/src/index.browser.js");
  // The Node entry has already loaded the module in this realm; handing the
  // bytes in directly is what a browser caller does after fetching them.
  const { readFileSync } = await import("node:fs");
  const { fileURLToPath } = await import("node:url");
  const wasmUrl = new URL("../src/wasm/polylib_wasm_bg.wasm", import.meta.url);
  browser.initWasm(readFileSync(fileURLToPath(wasmUrl)));
  expect(browser.getWasmVersion()).toBe(VERSION);
  expect(browser.normalizeSlug("Browser Test!")).toBe("browser-test");
});

test("toPolylibError keeps a well-formed code and rejects an arbitrary prefix", async () => {
  const core = await import("@/src/core.js");
  const coded = new Error("empty_input: slug is empty");
  expect(core.toPolylibError(coded).code).toBe("empty_input");
  // A diagnostic sentence is not an error code.
  expect(core.toPolylibError(new Error("NaN detected: not finite")).code).toBe("invalid_input");
  const already = new core.PolylibError("kept", "msg");
  expect(core.toPolylibError(already)).toBe(already);
  expect(core.toPolylibError("plain text").code).toBe("invalid_input");
});

test("the Node entry resolves initWasmAsync immediately", async () => {
  const node = await import("@/src/index.node.js");
  await node.initWasmAsync();
  expect(node.getWasmVersion()).toBe(VERSION);
});

test("initWasmAsync accepts bytes explicitly", async () => {
  const node = await import("@/src/index.node.js");
  const { readFileSync } = await import("node:fs");
  const { fileURLToPath } = await import("node:url");
  const wasmUrl = new URL("../src/wasm/polylib_wasm_bg.wasm", import.meta.url);
  await node.initWasmAsync(readFileSync(fileURLToPath(wasmUrl)));
  expect(node.getWasmVersion()).toBe(VERSION);
});

test("the browser entry's async initializer loads the module", async () => {
  const browser = await import("@/src/index.browser.ts?async");
  const { readFileSync } = await import("node:fs");
  const { fileURLToPath } = await import("node:url");
  const wasmUrl = new URL("../src/wasm/polylib_wasm_bg.wasm", import.meta.url);
  await browser.initWasmAsync(readFileSync(fileURLToPath(wasmUrl)));
  expect(browser.normalizeSlug("Async Browser!")).toBe("async-browser");
});

test("initWasmAsync is idempotent on both entries", async () => {
  const node = await import("@/src/index.node.js");
  const browser = await import("@/src/index.browser.ts?idem");
  // Already initialized in this realm: both must short-circuit and return.
  await node.initWasmAsync();
  await node.initWasmAsync();
  const { readFileSync } = await import("node:fs");
  const { fileURLToPath } = await import("node:url");
  const wasmUrl = new URL("../src/wasm/polylib_wasm_bg.wasm", import.meta.url);
  await browser.initWasmAsync(readFileSync(fileURLToPath(wasmUrl)));
  await browser.initWasmAsync();
  // The second call must be a no-op rather than a re-initialization.
  expect(browser.getWasmVersion()).toBe(VERSION);
});

test("the browser entry initializes from a fresh process", async () => {
  // The suite has already initialized the shared module, so the "first call in a
  // browser" path only exists in a process that has never loaded the Node entry.
  const script = `
    const browser = await import(${JSON.stringify(new URL("../src/index.browser.ts", import.meta.url).href)});
    const { readFileSync } = await import("node:fs");
    const bytes = readFileSync(${JSON.stringify(new URL("../src/wasm/polylib_wasm_bg.wasm", import.meta.url).pathname)});
    await browser.initWasmAsync(bytes);
    const slug = browser.normalizeSlug("Fresh Process!");
    await browser.initWasmAsync();
    if (slug !== "fresh-process") throw new Error("unexpected slug: " + slug);
    process.stdout.write("ok");
  `;
  const proc = Bun.spawn(["bun", "-e", script], { stdout: "pipe", stderr: "pipe" });
  const [out, err, code] = await Promise.all([
    new Response(proc.stdout).text(),
    new Response(proc.stderr).text(),
    proc.exited,
  ]);
  if (code !== 0) {
    throw new Error(`child failed (${code}): ${err}`);
  }
  expect(out.trim()).toBe("ok");
});
