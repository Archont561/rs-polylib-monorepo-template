Feature: WebAssembly TypeScript bindings for polylib-core

  The browser entry has no Node imports; the Node entry reads the module from
  disk. Both share one type surface.

  Scenario: Normalize a title through the WebAssembly engine
    Given a raw title "Hello, Polyglot World!"
    When polylib-wasm normalizes the title
    Then the polylib-wasm slug is "hello-polyglot-world"

  Scenario: Summarize scores through the WebAssembly engine
    Given numeric scores "10.0, 20.0, 30.0, 40.0"
    When polylib-wasm summarizes the scores
    Then the polylib-wasm summary has count 4 and mean 25.0

  Scenario: The browser entry requires an explicit initialization
    Given the browser entry of @polylib/polylib-wasm
    When a caller invokes normalizeSlug before initializing
    Then the error code is "wasm_not_initialized"
    And the message names initWasmAsync

  Scenario: The browser entry initializes from fetched bytes
    Given the browser entry with no Node imports
    When a caller awaits initWasmAsync with the compiled module bytes
    Then normalizeSlug returns the expected slug

  Scenario: The Node entry initializes on first use
    Given the Node entry of @polylib/polylib-wasm
    When a caller invokes normalizeSlug without an explicit initialization
    Then the call succeeds
