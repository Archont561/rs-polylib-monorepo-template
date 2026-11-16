# frozen_string_literal: true

require "ffi"

module Polylib
  # Resolves the compiled `polylib_ffi` shared library across bundled gem and system paths.
  module NativeLoader
    def self.library_candidates
      lib_name = FFI.map_library_name("polylib_ffi")
      bundled = File.expand_path("native/#{lib_name}", __dir__)
      candidates = []
      candidates << bundled if File.exist?(bundled)
      candidates << "polylib_ffi"
      candidates
    end
  end
end
