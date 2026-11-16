Feature: Swift UniFFI binding parity

  Scenario: Swift facade exposes deterministic slug and score APIs
    Given the Swift Polylib package backed by UniFFI
    When callers normalize slugs and summarize finite scores
    Then outputs and typed error codes match polylib-core conformance specs
