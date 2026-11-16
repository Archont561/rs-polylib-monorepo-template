Feature: NAPI-RS native binding crate

  Scenario: Expose polylib-core functions to Node.js and Bun via NAPI-RS
    Given the polylib-js cdylib crate built with napi-rs
    When JavaScript or TypeScript calls normalizeSlug and summarizeScores
    Then the outputs and typed error codes match the shared conformance suite
