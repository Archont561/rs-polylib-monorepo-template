Feature: TypeScript NAPI-RS native bindings for polylib-core

  Scenario: Normalize a title through the native NAPI-RS addon
    Given a raw title "Hello, Polyglot World!"
    When native TypeScript normalizes the title
    Then the native TypeScript slug is "hello-polyglot-world"

  Scenario: Summarize scores through the native NAPI-RS addon
    Given numeric scores "10.0, 20.0, 30.0, 40.0"
    When native TypeScript summarizes the scores
    Then the native TypeScript summary has count 4 and mean 25.0
