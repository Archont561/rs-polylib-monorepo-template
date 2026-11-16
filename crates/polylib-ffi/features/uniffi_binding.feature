Feature: UniFFI multi-language binding crate

  Scenario: Expose polylib-core functions to Kotlin, Swift, and Ruby via UniFFI
    Given the polylib-ffi cdylib crate built with uniffi
    When Kotlin, Swift, or Ruby callers invoke normalize_slug and summarize_scores
    Then the outputs and typed error codes match the shared conformance suite
