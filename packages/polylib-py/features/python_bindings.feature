Feature: Python bindings for polylib-core

  Scenario: Normalize a title through the PyO3 extension
    Given a raw title "Hello, Polyglot World!"
    When Python normalizes the title
    Then the Python slug is "hello-polyglot-world"

  Scenario: Summarize scores through the PyO3 extension
    Given numeric scores "10.0, 20.0, 30.0, 40.0"
    When Python summarizes the scores
    Then the Python summary has count 4 and mean 25.0
