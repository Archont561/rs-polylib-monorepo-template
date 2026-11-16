Feature: Ruby UniFFI binding parity

  Scenario: Ruby facade exposes deterministic slug and score APIs
    Given the Ruby Polylib gem backed by UniFFI and FFI
    When callers normalize slugs and summarize finite scores
    Then outputs and typed error codes match polylib-core conformance specs
