# frozen_string_literal: true

require_relative "coverage_helper"
require "minitest/autorun"
require "polylib"

class TestPolylib < Minitest::Test
  def test_version_matches_native_library
    assert_equal Polylib::VERSION, Polylib.ffi_version
  end

  def test_normalize_slug_is_idempotent_on_valid_inputs
    samples = [
      "Hello, Polyglot World!",
      "Rust + Ruby & UniFFI",
      "Already-Clean_123",
      "---Leading___Trailing---",
      "Cafe 2026 -- v1.2.3",
    ]
    samples.each do |sample|
      once = Polylib.normalize_slug(sample)
      twice = Polylib.normalize_slug(once)
      assert_equal once, twice
      refute_empty once
      refute once.start_with?("-")
      refute once.end_with?("-")
      refute_includes once, "--"
      assert_match(/\A[a-z0-9-]+\z/, once)
    end
  end

  def test_summarize_scores_preserves_invariants
    summary = Polylib.summarize_scores([10.0, 20.0, 30.0])
    assert_equal 3, summary.count
    assert_in_delta 10.0, summary.min, 1e-12
    assert_in_delta 30.0, summary.max, 1e-12
    assert_in_delta 20.0, summary.mean, 1e-12
    assert_in_delta 60.0, summary.total, 1e-12
  end

  def test_rejects_non_finite_scores
    nan_err = assert_raises(Polylib::NonFiniteValueError) do
      Polylib.summarize_scores([1.0, Float::NAN, 3.0])
    end
    assert_equal "non_finite_value", nan_err.code

    inf_err = assert_raises(Polylib::NonFiniteValueError) do
      Polylib.summarize_scores([Float::INFINITY])
    end
    assert_equal "non_finite_value", inf_err.code
  end

  def test_rejects_empty_inputs_with_typed_errors
    slug_err = assert_raises(Polylib::EmptyInputError) do
      Polylib.normalize_slug("   !!!   ")
    end
    assert_equal "empty_input", slug_err.code

    score_err = assert_raises(Polylib::EmptyScoresError) do
      Polylib.summarize_scores([])
    end
    assert_equal "empty_scores", score_err.code
  end
end
