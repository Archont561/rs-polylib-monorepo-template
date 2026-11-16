Feature: WebAssembly TypeScript bindings for polylib-core

  Scenario: Normalize a title through the WebAssembly engine
    Given a raw title "Hello, Polyglot World!"
    When polylib-wasm normalizes the title
    Then the polylib-wasm slug is "hello-polyglot-world"

  Scenario: Summarize scores through the WebAssembly engine
    Given numeric scores "10.0, 20.0, 30.0, 40.0"
    When polylib-wasm summarizes the scores
    Then the polylib-wasm summary has count 4 and mean 25.0
