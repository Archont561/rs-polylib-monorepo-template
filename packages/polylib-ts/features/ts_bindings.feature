Feature: Unified TypeScript facade for polylib-core

  Scenario: Auto-select native NAPI-RS with WebAssembly fallback
    Given the unified @polylib/polylib facade package
    When a TypeScript caller invokes normalizeSlug and summarizeScores
    Then it delegates to @polylib/polylib-js when available or falls back to @polylib/polylib-wasm

  Scenario: Pin explicit native or WebAssembly backend subpaths
    Given the @polylib/polylib/native and @polylib/polylib/wasm subpaths
    When a caller invokes both subpaths with identical inputs
    Then both backends return identical outputs and PolylibError codes
