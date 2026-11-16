Feature: Cross-language score summary conformance

  Scenario Outline: Compute deterministic score summary statistics
    Given the score list "<values>"
    When I summarize the scores
    Then the summary should have count <count>, min <min>, max <max>, and mean <mean>

    Examples:
      | values               | count | min  | max  | mean |
      | 42.5                 | 1     | 42.5 | 42.5 | 42.5 |
      | 10.0, 20.0, 30.0     | 3     | 10.0 | 30.0 | 20.0 |
      | -5.0, 0.0, 5.0       | 3     | -5.0 | 5.0  | 0.0  |
      | 1.25, 2.75, 4.0, 8.0 | 4     | 1.25 | 8.0  | 4.0  |

  Scenario: Reject an empty score list
    Given an empty score list
    When I summarize the scores
    Then score summarization should fail with error code "empty_scores"
