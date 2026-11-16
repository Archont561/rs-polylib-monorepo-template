# frozen_string_literal: true

return unless ENV["POLYLIB_COVERAGE"] == "1"

require "coverage"
require "fileutils"
require "json"

Coverage.start(lines: true) unless Coverage.running?

at_exit do
  next unless Coverage.running?

  raw_dir = ENV["POLYLIB_COVERAGE_RAW_DIR"]
  next if raw_dir.nil? || raw_dir.empty?

  lib_root = File.expand_path("../lib/", __dir__)
  generated_root = File.expand_path("../lib/polylib/generated/", __dir__)
  result = Coverage.result.each_with_object({}) do |(path, data), acc|
    expanded = File.expand_path(path)
    next unless expanded.start_with?(lib_root)
    next if expanded.start_with?(generated_root)

    lines = data.is_a?(Hash) ? data[:lines] : data
    acc[expanded] = lines if lines.is_a?(Array)
  end

  FileUtils.mkdir_p(raw_dir)
  File.write(File.join(raw_dir, "pid-#{Process.pid}.json"), JSON.generate(result))
end
