Feature: Kotlin JVM UniFFI binding parity

  Scenario: Kotlin facade exposes deterministic slug and score APIs
    Given the Kotlin Polylib facade backed by UniFFI and JNA
    When callers normalize slugs and summarize finite scores
    Then outputs and typed error codes match polylib-core conformance specs
