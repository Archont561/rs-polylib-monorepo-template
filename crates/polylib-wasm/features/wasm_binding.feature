Feature: WebAssembly binding crate

  Scenario: Expose polylib-core functions via wasm-bindgen
    Given the polylib-wasm crate compiled for wasm32-unknown-unknown
    When TypeScript calls wasmNormalizeSlug and wasmSummarizeScores
    Then the outputs match the shared conformance suite
