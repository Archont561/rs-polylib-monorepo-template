Feature: Rust metacrate facade

  Scenario: Consumers import core APIs through the prelude
    Given a Rust consumer depending on the polylib metacrate
    When the consumer invokes normalize_slug and summarize_scores via the prelude
    Then the results match the shared conformance suite
