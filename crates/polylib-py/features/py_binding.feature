Feature: PyO3 native extension crate

  Scenario: Expose polylib-core functions to Python via maturin
    Given the polylib-py cdylib crate built with maturin
    When Python imports polylib._native
    Then normalize_slug and summarize_scores delegate directly to polylib-core
