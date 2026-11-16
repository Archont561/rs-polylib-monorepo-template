# frozen_string_literal: true

require_relative "../test/coverage_helper"
$LOAD_PATH.unshift(File.expand_path("../lib", __dir__))
require "minitest/assertions"
require "polylib"

World(Minitest::Assertions)

def assertions
  @assertions ||= 0
end

def assertions=(value)
  @assertions = value
end

Given("the raw slug input {string}") do |raw_input|
  @slug_input = raw_input
end

Given("an empty slug input") do
  @slug_input = ""
end

When("I normalize the slug") do
  @slug_result = nil
  @slug_error = nil
  begin
    @slug_result = Polylib.normalize_slug(@slug_input)
  rescue Polylib::Error => e
    @slug_error = e
  end
end

Then("the normalized slug should be {string}") do |expected|
  assert_nil @slug_error, "Expected success, got error: #{@slug_error}"
  assert_equal expected, @slug_result
end

Then("slug normalization should fail with error code {string}") do |expected_code|
  assert_nil @slug_result, "Expected error, got slug: #{@slug_result}"
  refute_nil @slug_error, "Expected Polylib::Error"
  assert_equal expected_code, @slug_error.code
end

Given("the score list {string}") do |raw_values|
  @score_values = raw_values.split(",").map { |v| Float(v.strip) }
end

Given("an empty score list") do
  @score_values = []
end

When("I summarize the scores") do
  @score_summary = nil
  @score_error = nil
  begin
    @score_summary = Polylib.summarize_scores(@score_values)
  rescue Polylib::Error => e
    @score_error = e
  end
end

Then("the summary should have count {int}, min {float}, max {float}, and mean {float}") do |count, min, max, mean|
  assert_nil @score_error, "Expected success, got error: #{@score_error}"
  refute_nil @score_summary, "Expected ScoreSummary"
  assert_equal count, @score_summary.count
  assert_in_delta min, @score_summary.min, 1e-12
  assert_in_delta max, @score_summary.max, 1e-12
  assert_in_delta mean, @score_summary.mean, 1e-12
end

Then("score summarization should fail with error code {string}") do |expected_code|
  assert_nil @score_summary, "Expected error, got summary: #{@score_summary}"
  refute_nil @score_error, "Expected Polylib::Error"
  assert_equal expected_code, @score_error.code
end
