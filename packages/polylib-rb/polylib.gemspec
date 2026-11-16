# frozen_string_literal: true

require_relative "lib/polylib/version"

Gem::Specification.new do |spec|
  spec.name = "polylib"
  spec.version = Polylib::VERSION
  spec.authors = ["Polylib Contributors"]
  spec.summary = "Idiomatic Ruby facade over Rust polylib-core via UniFFI"
  spec.description = "Cross-language slug normalization and deterministic score statistics backed by Rust polylib-core and UniFFI."
  spec.homepage = "https://github.com/example/polyglot-lib-template"
  spec.license = "MIT"
  spec.required_ruby_version = ">= 3.2"

  spec.files = (
    Dir.glob("lib/**/*.rb") +
    Dir.glob("lib/polylib/native/*") +
    %w[LICENSE README.md]
  ).uniq.select { |path| File.file?(path) }
  spec.require_paths = ["lib"]

  spec.add_dependency "ffi", "~> 1.17"
end
