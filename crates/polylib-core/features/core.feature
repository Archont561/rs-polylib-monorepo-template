Feature: Core slug and score engine

  Scenario: Normalize a mixed-case title into a slug
    Given the raw title "Hello, Polyglot World!"
    When I normalize the slug
    Then the resulting slug is "hello-polyglot-world"

  Scenario: Summarize a list of scores
    Given the scores "10.0, 20.0, 30.0, 40.0"
    When I summarize the scores
    Then the summary mean is 25.0 and count is 4
