# frozen_string_literal: true

require_relative "polylib/version"
require_relative "polylib/error"
require_relative "polylib/native_loader"
require_relative "polylib/generated/polylib_ffi"

# Idiomatic Ruby facade over the Rust `polylib-ffi` UniFFI bindings.
module Polylib
  ScoreSummary = Data.define(:count, :min, :max, :mean, :total)

  class << self
    # Return the version compiled into the native `polylib-ffi` shared library.
    def ffi_version
      PolylibFfi.ffi_version
    end

    # Normalize free-form text into a lowercase hyphen-separated ASCII slug.
    def normalize_slug(input)
      map_errors { PolylibFfi.normalize_slug(input.to_s) }
    end

    # Summarize a non-empty array of finite floating-point scores.
    def summarize_scores(values)
      floats = values.map(&:to_f)
      map_errors do
        raw = PolylibFfi.summarize_scores(floats)
        ScoreSummary.new(
          count: raw.count,
          min: raw.min,
          max: raw.max,
          mean: raw.mean,
          total: raw.total
        )
      end
    end

    private

    def map_errors
      yield
    rescue PolylibFfi::PolylibFfiError::EmptyInput => e
      raise EmptyInputError.new(detail: e.detail)
    rescue PolylibFfi::PolylibFfiError::EmptyScores => e
      raise EmptyScoresError.new(detail: e.detail)
    rescue PolylibFfi::PolylibFfiError::NonFiniteValue => e
      raise NonFiniteValueError.new(detail: e.detail)
    end
  end
end
