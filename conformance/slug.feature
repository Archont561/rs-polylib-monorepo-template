Feature: Cross-language slug normalization conformance

  Scenario Outline: Normalize valid input into an ASCII lowercase slug
    Given the raw slug input "<input>"
    When I normalize the slug
    Then the normalized slug should be "<expected>"

    Examples:
      | input                        | expected               |
      | Hello, Polyglot World!       | hello-polyglot-world   |
      | Rust + Python & TypeScript   | rust-python-typescript |
      | Already-Clean_123            | already-clean-123      |
      | ---Leading___Trailing---     | leading-trailing       |
      | Cafe 2026 -- v1.2.3          | cafe-2026-v1-2-3       |

  Scenario Outline: Reject punctuation-only slug inputs
    Given the raw slug input "<input>"
    When I normalize the slug
    Then slug normalization should fail with error code "<error_code>"

    Examples:
      | input | error_code  |
      | !!!   | empty_input |
      | ---   | empty_input |

  Scenario: Reject an empty slug input
    Given an empty slug input
    When I normalize the slug
    Then slug normalization should fail with error code "empty_input"
